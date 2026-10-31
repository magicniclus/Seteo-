"""Le serveur de la machine (l'équivalent de « Hermès » dans la vidéo).

- /webhook/instagram : quelqu'un commente un mot-clé -> DM automatique avec le lien
                       quelqu'un écrit en DM -> l'IA répond dans ton style
- /ressource/<mot>   : page « prénom + email » -> inscription Portail Habitat -> ressource
- /stats             : DM envoyés, ouvertures, inscriptions, conversion par mot-clé
- /studio            : tes scripts à tourner, les écrans du site, les hooks du moment
- /prompteur/...     : prompteur + caméra ; chaque prise est envoyée dans rushs/

Lancer : uvicorn serveur.app:app --host 0.0.0.0 --port 8000
"""

import hashlib
import hmac
import html
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import markdown
import requests
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "machine"))
from commun import DOSSIER_RESSOURCES, MODELE, RACINE, cerveau, client, config, slug  # noqa: E402

VERSION = os.getenv("META_GRAPH_VERSION", "v23.0")
BASE = RACINE / "serveur" / "machine.db"
app = FastAPI()


def db() -> sqlite3.Connection:
    c = sqlite3.connect(BASE)
    c.execute("CREATE TABLE IF NOT EXISTS evenements (type TEXT, mot TEXT, qui TEXT, "
              "quand TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS inscrits (prenom TEXT, email TEXT, mot TEXT, "
              "source TEXT, quand TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (qui TEXT, role TEXT, texte TEXT, "
              "quand TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    return c


def noter(type_: str, mot: str, qui: str = "") -> None:
    with db() as c:
        c.execute("INSERT INTO evenements (type, mot, qui) VALUES (?, ?, ?)", (type_, mot, qui))


def ressource(mot: str) -> dict | None:
    fichier = DOSSIER_RESSOURCES / f"{slug(mot)}.json"
    return json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else None


def envoyer_dm(destinataire: dict, texte: str) -> None:
    requests.post(
        f"https://graph.facebook.com/{VERSION}/me/messages",
        json={"recipient": destinataire, "message": {"text": texte}},
        params={"access_token": os.environ["META_ACCESS_TOKEN"]},
        timeout=30,
    ).raise_for_status()


# ---------- Instagram : commentaires et DM ----------

@app.get("/webhook/instagram")
def verifier_webhook(request: Request):
    q = request.query_params
    if q.get("hub.verify_token") != os.environ["META_VERIFY_TOKEN"]:
        raise HTTPException(403)
    return PlainTextResponse(q.get("hub.challenge", ""))


@app.post("/webhook/instagram")
async def recevoir_webhook(request: Request, taches: BackgroundTasks):
    corps = await request.body()
    signature = "sha256=" + hmac.new(os.environ["META_APP_SECRET"].encode(), corps,
                                     hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, request.headers.get("X-Hub-Signature-256", "")):
        raise HTTPException(403)

    for entree in json.loads(corps).get("entry", []):
        for changement in entree.get("changes", []):
            if changement.get("field") == "comments":
                taches.add_task(traiter_commentaire, changement["value"])
        for evt in entree.get("messaging", []):
            msg = evt.get("message", {})
            if msg.get("text") and not msg.get("is_echo"):
                taches.add_task(repondre_dm, evt["sender"]["id"], msg["text"])
    return {"ok": True}


def traiter_commentaire(valeur: dict) -> None:
    """Commentaire « DEVIS » -> DM privé avec le lien de la ressource."""
    mots = [slug(m) for m in valeur.get("text", "").split()]
    mot = next((m for m in mots if ressource(m)), None)
    if not mot:
        return
    r = ressource(mot)
    lien = f"{config()['url_serveur']}/ressource/{mot}?src=dm"
    envoyer_dm({"comment_id": valeur["id"]},
               f"Hello ! Tu as commenté {mot.upper()} 🙌 J'ai préparé encore mieux : "
               f"{r['titre']}. Inscris-toi gratuitement et récupère ton accès à vie 👉 {lien}")
    noter("dm_envoye", mot, valeur.get("from", {}).get("id", ""))


def repondre_dm(qui: str, texte: str) -> None:
    """L'IA répond aux DM dans le style de la marque (comme un « setter »)."""
    with db() as c:
        c.execute("INSERT INTO messages (qui, role, texte) VALUES (?, 'user', ?)", (qui, texte))
        historique = c.execute("SELECT role, texte FROM messages WHERE qui = ? "
                               "ORDER BY quand DESC LIMIT 20", (qui,)).fetchall()[::-1]

    liste = "\n".join(f"- {r['mot'].upper()} : {r['titre']} -> {config()['url_serveur']}/ressource/{r['mot']}?src=dm"
                      for r in (json.loads(f.read_text(encoding="utf-8"))
                                for f in DOSSIER_RESSOURCES.glob("*.json")))
    consignes = (f"{cerveau()}\n\nTu réponds aux DM Instagram de la marque. Réponses courtes "
                 f"(1 à 3 phrases), naturelles, dans notre style. Si la personne a un projet, "
                 f"propose la ressource adaptée ou l'inscription gratuite sur {config()['site']}. "
                 f"Si tu ne sais pas, dis qu'un humain revient vers elle vite.\n\n"
                 f"Ressources disponibles :\n{liste}")
    messages = []
    for role, t in historique:  # l'API veut des rôles qui alternent
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + t
        else:
            messages.append({"role": role, "content": t})

    reponse = client().beta.messages.create(
        model=MODELE, max_tokens=2000, system=consignes, messages=messages,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    )
    if reponse.stop_reason == "refusal":
        return
    texte_ia = "".join(b.text for b in reponse.content if b.type == "text").strip()
    if texte_ia:
        envoyer_dm({"id": qui}, texte_ia)
        with db() as c:
            c.execute("INSERT INTO messages (qui, role, texte) VALUES (?, 'assistant', ?)", (qui, texte_ia))


# ---------- Pages ressources : la capture d'inscrits ----------

STYLE = """<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:0 auto;padding:24px 16px;
color:#1d2a35;background:#f7f5f0;line-height:1.55}h1{font-size:1.7rem}input,button{width:100%;
padding:14px;margin:6px 0;font-size:1rem;border-radius:10px;border:1px solid #c9c3b6;box-sizing:border-box}
button{background:#1f6f5c;color:#fff;border:0;font-weight:600;cursor:pointer}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:8px;text-align:left}</style>"""


@app.get("/ressource/{mot}", response_class=HTMLResponse)
def page_ressource(mot: str, src: str = "direct"):
    r = ressource(mot)
    if not r:
        raise HTTPException(404)
    noter("ouverture", r["mot"], src)
    t = html.escape
    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t(r['titre'])}</title>{STYLE}
<h1>{t(r['titre'])}</h1><p>{t(r['promesse'])}</p>
<form method="post"><input type="hidden" name="src" value="{t(src)}">
<input name="prenom" placeholder="Ton prénom" required>
<input name="email" type="email" placeholder="Ton email" required>
<button>Reçois la ressource tout de suite (gratuit)</button></form>
<p><small>En t'inscrivant, tu crées ton compte gratuit {t(config()['marque'])}.</small></p>"""


@app.post("/ressource/{mot}", response_class=HTMLResponse)
def inscription(mot: str, prenom: str = Form(...), email: str = Form(...), src: str = Form("direct")):
    r = ressource(mot)
    if not r:
        raise HTTPException(404)
    with db() as c:
        c.execute("INSERT INTO inscrits (prenom, email, mot, source) VALUES (?, ?, ?, ?)",
                  (prenom, email, r["mot"], src))
    noter("inscription", r["mot"], src)
    # Envoie l'inscrit vers Portail Habitat (ton site, ton CRM, ou un outil d'emailing)
    if url := os.getenv("PORTAIL_HABITAT_WEBHOOK_URL"):
        try:
            requests.post(url, json={"prenom": prenom, "email": email, "mot_cle": r["mot"],
                                     "source": src}, timeout=15)
        except requests.RequestException:
            pass  # l'inscrit est déjà sauvé en local, on ne bloque pas la personne
    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(r['titre'])}</title>{STYLE}
<p>Bienvenue {html.escape(prenom)} 🎉 Ton compte gratuit est créé. Voici ta ressource :</p>
{markdown.markdown(html.escape(r['contenu']), extensions=['tables'])}
<p><a href="{html.escape(config()['site'])}">Découvrir {html.escape(config()['marque'])} →</a></p>"""


# ---------- Statistiques ----------

@app.get("/stats", response_class=HTMLResponse)
def stats(cle: str = ""):
    verifier_cle(cle)
    with db() as c:
        lignes = c.execute("""SELECT mot,
            SUM(type='dm_envoye'), SUM(type='ouverture'), SUM(type='inscription')
            FROM evenements GROUP BY mot ORDER BY 4 DESC""").fetchall()
        total = c.execute("SELECT COUNT(DISTINCT email) FROM inscrits").fetchone()[0]
    rangs = "".join(
        f"<tr><td>{m.upper()}</td><td>{d}</td><td>{o}</td><td>{i}</td>"
        f"<td>{(100 * i / o if o else 0):.0f} %</td></tr>" for m, d, o, i in lignes)
    return f"""<!doctype html><meta charset="utf-8"><title>Stats machine</title>{STYLE}
<h1>{total} inscrits uniques</h1><table><tr><th>Mot-clé</th><th>DM envoyés</th>
<th>Ouvertures</th><th>Inscriptions</th><th>Conversion</th></tr>{rangs}</table>"""


# ---------- Studio : s'enregistrer sur les textes de Claude ----------

RUSHS = RACINE / "rushs"
ECRANS = RACINE / "ecrans"


def verifier_cle(cle: str) -> None:
    if not hmac.compare_digest(cle, os.environ["STATS_KEY"]):
        raise HTTPException(403)


def post_du_calendrier(semaine: str, numero: int) -> dict:
    fichier = RACINE / "sorties" / Path(semaine).name / "calendrier.json"
    if not fichier.exists():
        raise HTTPException(404)
    posts = json.loads(fichier.read_text(encoding="utf-8"))["posts"]
    if not 1 <= numero <= len(posts):
        raise HTTPException(404)
    return posts[numero - 1]


@app.get("/studio", response_class=HTMLResponse)
def studio(cle: str = ""):
    verifier_cle(cle)
    t = html.escape
    lignes = []
    for cal in sorted((RACINE / "sorties").glob("20*/calendrier.json"), reverse=True)[:2]:
        semaine = cal.parent.name
        for n, p in enumerate(json.loads(cal.read_text(encoding="utf-8"))["posts"], 1):
            if p["format"] not in ("reel", "short"):
                continue
            fait = any(RUSHS.glob(f"{semaine}-{n}-*"))
            lignes.append(
                f"<tr><td>{'✅' if fait else '⏺'}</td><td>{semaine} #{n}<br><small>{t(p['reseau'])} · "
                f"{t(p['mot_cle'].upper())}</small></td><td>{t(p['accroche'])}</td>"
                f"<td><a href='/prompteur/{semaine}/{n}?cle={t(cle)}'>Enregistrer</a></td></tr>")
    ecrans = "".join(
        f"<figure style='display:inline-block;width:150px;margin:4px'><video src='/ecrans/{f.name}?cle={t(cle)}' "
        f"muted loop playsinline onmouseover='this.play()' style='width:100%'></video>"
        f"<figcaption>{t(f.stem)}</figcaption></figure>" for f in sorted(ECRANS.glob("*.mp4")))
    biblio = RACINE / "sorties" / "tendances" / "hooks.json"
    hooks = json.loads(biblio.read_text(encoding="utf-8"))[-10:][::-1] if biblio.exists() else []
    liste_hooks = "".join(f"<li>{t(h['version_portail_habitat'])}</li>" for h in hooks)
    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Studio</title>{STYLE}
<h1>Studio</h1><h2>Vidéos à enregistrer</h2>
<table><tr><th></th><th>Post</th><th>Accroche</th><th></th></tr>{''.join(lignes) or '<tr><td colspan=4>Lance generer.py</td></tr>'}</table>
<h2>Écrans du site</h2>{ecrans or '<p>Lance machine/ecrans.py</p>'}
<h2>Hooks du moment</h2><ul>{liste_hooks or '<li>Lance machine/tendances.py</li>'}</ul>"""


@app.get("/prompteur/{semaine}/{numero}", response_class=HTMLResponse)
def prompteur(semaine: str, numero: int, cle: str = ""):
    verifier_cle(cle)
    p = post_du_calendrier(semaine, numero)
    texte = html.escape("\n\n".join([p["accroche"], *p["script_ou_slides"]]))
    envoi = f"/rushs/{Path(semaine).name}/{numero}?cle={html.escape(cle)}"
    return ((RACINE / "serveur" / "prompteur.html").read_text(encoding="utf-8")
            .replace("{{TEXTE}}", texte).replace("{{URL_ENVOI}}", envoi))


@app.post("/rushs/{semaine}/{numero}")
async def recevoir_rush(semaine: str, numero: int, video: UploadFile = File(...), cle: str = ""):
    """Le prompteur envoie ici chaque prise : rushs/<semaine>-<numero>-<heure>.webm"""
    verifier_cle(cle)
    post_du_calendrier(semaine, numero)
    RUSHS.mkdir(exist_ok=True)
    cible = RUSHS / f"{Path(semaine).name}-{numero}-{datetime.now():%H%M%S}.webm"
    with open(cible, "wb") as f:
        while morceau := await video.read(1 << 20):
            f.write(morceau)
    return {"ok": True, "fichier": cible.name}


@app.get("/ecrans/{fichier}")
def ecran(fichier: str, cle: str = ""):
    verifier_cle(cle)
    chemin = ECRANS / Path(fichier).name
    if not chemin.exists():
        raise HTTPException(404)
    return FileResponse(chemin)
