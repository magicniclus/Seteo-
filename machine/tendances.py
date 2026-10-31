"""Veille tendances & hooks : ce qui cartonne en ce moment dans ta niche.

Sources (APIs officielles, pas de piratage de compte) :
- Instagram : les posts « top » des hashtags de config/marque.yaml (Hashtag Search API)
- YouTube Shorts : les Shorts les plus vus des 14 derniers jours sur tes recherches

L'IA en sort :
- les tendances du moment (sujets, formats) et comment Portail Habitat peut surfer dessus,
- une bibliothèque de hooks réutilisables, qui grossit chaque jour :
  sorties/tendances/hooks.json (utilisée automatiquement par generer.py)

Usage :
    python machine/tendances.py
"""

import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import List

import requests
from pydantic import BaseModel

from commun import RACINE, config, generer_structure

DOSSIER = RACINE / "sorties" / "tendances"
BIBLIOTHEQUE = DOSSIER / "hooks.json"


class Tendance(BaseModel):
    sujet: str
    pourquoi_ca_marche: str
    exemples: List[str]  # liens
    idee_portail_habitat: str  # notre angle pour surfer dessus


class Hook(BaseModel):
    hook_original: str
    modele: str  # le hook rendu générique, ex. « Personne ne te dit ça avant de [ACTION] »
    version_portail_habitat: str
    source: str  # lien de la vidéo


class Veille(BaseModel):
    tendances: List[Tendance]
    hooks: List[Hook]


# ---------- Sources ----------

def instagram_hashtags(hashtags: list[str]) -> list[dict]:
    ig, token = os.getenv("INSTAGRAM_ACCOUNT_ID"), os.getenv("META_ACCESS_TOKEN")
    if not (ig and token):
        print("  Instagram ignoré (INSTAGRAM_ACCOUNT_ID / META_ACCESS_TOKEN manquants)")
        return []
    base = f"https://graph.facebook.com/{os.getenv('META_GRAPH_VERSION', 'v23.0')}"
    posts = []
    for tag in hashtags:
        r = requests.get(f"{base}/ig_hashtag_search",
                         params={"user_id": ig, "q": tag, "access_token": token}, timeout=30)
        if not r.ok or not r.json().get("data"):
            print(f"  #{tag} : introuvable")
            continue
        r = requests.get(
            f"{base}/{r.json()['data'][0]['id']}/top_media",
            params={"user_id": ig, "access_token": token, "limit": 50,
                    "fields": "caption,like_count,comments_count,permalink,media_type"},
            timeout=30,
        )
        if r.ok:
            for p in r.json().get("data", []):
                posts.append({
                    "source": f"Instagram #{tag}",
                    "lien": p.get("permalink", ""),
                    "texte": (p.get("caption") or "")[:500],
                    "score": p.get("like_count", 0) + 3 * p.get("comments_count", 0),
                })
    return posts


def youtube_shorts(recherches: list[str]) -> list[dict]:
    cle = os.getenv("YOUTUBE_API_KEY")
    if not cle:
        print("  YouTube ignoré (YOUTUBE_API_KEY manquante)")
        return []
    depuis = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    videos = []
    for q in recherches:
        r = requests.get("https://www.googleapis.com/youtube/v3/search", params={
            "part": "snippet", "q": q, "type": "video", "videoDuration": "short",
            "order": "viewCount", "publishedAfter": depuis, "regionCode": "FR",
            "relevanceLanguage": "fr", "maxResults": 25, "key": cle}, timeout=30)
        if not r.ok:
            print(f"  YouTube « {q} » : erreur {r.status_code}")
            continue
        ids = [i["id"]["videoId"] for i in r.json().get("items", [])]
        if not ids:
            continue
        stats = requests.get("https://www.googleapis.com/youtube/v3/videos", params={
            "part": "statistics,snippet", "id": ",".join(ids), "key": cle}, timeout=30).json()
        for v in stats.get("items", []):
            videos.append({
                "source": f"YouTube « {q} »",
                "lien": f"https://www.youtube.com/shorts/{v['id']}",
                "texte": f"{v['snippet']['title']}\n{v['snippet'].get('description', '')[:300]}",
                "score": int(v["statistics"].get("viewCount", 0)),
            })
    return videos


# ---------- Analyse ----------

def main() -> None:
    cfg = config()
    print("Récupération des tendances...")
    ig = sorted(instagram_hashtags(cfg.get("hashtags_a_surveiller", [])), key=lambda p: -p["score"])
    yt = sorted(youtube_shorts(cfg.get("recherches_youtube", [])), key=lambda p: -p["score"])
    meilleurs = ig[:30] + yt[:30]
    if not meilleurs:
        print("Aucune donnée : renseigne les clés dans .env (voir README).")
        return

    liste = "\n\n".join(f"[{p['source']} · score {p['score']}] {p['lien']}\n{p['texte']}"
                        for p in meilleurs)
    print(f"L'IA analyse {len(meilleurs)} contenus...")
    veille = generer_structure(
        f"""Voici les contenus qui performent le plus en ce moment dans notre niche :\n\n{liste}\n
1. Dégage les tendances (sujets, formats, angles) et notre angle Portail Habitat pour chacune.
2. Extrais les hooks (la première phrase / le titre qui accroche). Pour chacun : le hook
   original, un modèle générique réutilisable avec des [TROUS], et notre version habitat.
   Garde seulement les hooks vraiment forts (15 maximum).""",
        Veille,
    )

    DOSSIER.mkdir(parents=True, exist_ok=True)
    bibliotheque = json.loads(BIBLIOTHEQUE.read_text(encoding="utf-8")) if BIBLIOTHEQUE.exists() else []
    connus = {h["modele"].lower() for h in bibliotheque}
    nouveaux = [h.model_dump() | {"date": date.today().isoformat()}
                for h in veille.hooks if h.modele.lower() not in connus]
    bibliotheque += nouveaux
    BIBLIOTHEQUE.write_text(json.dumps(bibliotheque, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# Tendances du {date.today():%d/%m/%Y}\n"]
    for t in veille.tendances:
        md.append(f"\n## {t.sujet}\n\n{t.pourquoi_ca_marche}\n\n**Notre angle :** "
                  f"{t.idee_portail_habitat}\n\n" + "".join(f"- {e}\n" for e in t.exemples))
    md.append("\n# Hooks du jour\n")
    for h in veille.hooks:
        md.append(f"\n- **{h.version_portail_habitat}**\n  - modèle : {h.modele}\n"
                  f"  - original : « {h.hook_original} » ({h.source})\n")
    fichier = DOSSIER / f"{date.today()}.md"
    fichier.write_text("".join(md), encoding="utf-8")
    print(f"Prêt : {fichier} · {len(nouveaux)} nouveaux hooks (bibliothèque : {len(bibliotheque)})")


if __name__ == "__main__":
    main()
