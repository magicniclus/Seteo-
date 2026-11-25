"""Monte la vidéo (étape 3) : plan.json + DA -> projet HyperFrames -> aperçu -> MP4.

Lit, dans montage/projets/<id>/ : mots.json (fait par couper.py) et plan.json (écrit par Claude).
Écrit index.html (une composition HyperFrames : du HTML que le moteur transforme en vidéo),
le vérifie, puis au choix sort des images clés ou le MP4 final.

Usage :
    python machine/monter.py 2026-11-30-3              # génère + vérifie
    python machine/monter.py 2026-11-30-3 --apercu     # + images clés à regarder avant de rendre
    python machine/monter.py 2026-11-30-3 --rendu      # + montages/2026-11-30-3.mp4
    python machine/monter.py 2026-11-30-3 --rendu --brouillon   # rendu rapide pour itérer
    python machine/monter.py --planche                 # planche de style : la DA sans rush
    python machine/monter.py --planche --univers plan  # essayer un autre univers (config/univers/)

Le format de plan.json est décrit dans .claude/skills/montage-video/references/plan.md
"""

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import blocs as bibliotheque
from atelier import (MONTAGE, MONTAGES, RACINE, da, ecrire, ffmpeg, hyperframes, identifiant, lire,
                     normaliser_clip, projet)

GABARIT = MONTAGE / "gabarit"
BLOCS = MONTAGE / "blocs"
POLICES = MONTAGE / "da" / "polices"
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
UNITES = {"€", "euros", "euro", "%", "ans", "mois", "minutes", "m²", "m2", "k€"}
e = html.escape


def typo(texte: str) -> str:
    """Typographie française : pas de retour à la ligne avant « ? ! : ; » ni avant « € » ou « % »."""
    return re.sub(r" ([?!:;€%])", "\u00a0\\1", texte)


def sans_accent(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if c.isalnum())


def instant(valeur, mots: list[dict], fin: bool = False) -> float:
    """Un temps du plan : des secondes (12.4) ou un repère sur un mot (« m31 »)."""
    if isinstance(valeur, str) and valeur.startswith("m"):
        indice = int(valeur[1:])
        if not 0 <= indice < len(mots):
            sys.exit(f"plan.json : le mot {valeur} n'existe pas (mots 0 à {len(mots) - 1}).")
        return mots[indice]["f" if fin else "d"]
    return float(valeur)


def corriger(mots: list[dict], corrections: dict) -> list[dict]:
    """Applique les corrections de transcription : {"7": "Attends", "8": ""} (vide = supprimer)."""
    resultat: list[dict] = []
    for m in mots:
        texte = corrections.get(str(m["i"]))
        if texte is None:
            resultat.append(dict(m))
            continue
        texte = re.sub(r"\s+([?!:;])", "\u00a0\\1", texte.strip())  # « année ? » reste un seul mot
        morceaux = [x for x in texte.split(" ") if x]  # pas split() : il casserait « 10 000 »
        if not morceaux:  # mot supprimé : son temps revient au mot d'avant
            if resultat:
                resultat[-1]["f"] = m["f"]
            continue
        total, curseur = sum(len(x) for x in morceaux), m["d"]
        for x in morceaux:
            part = (m["f"] - m["d"]) * len(x) / total
            resultat.append({"i": m["i"], "t": x, "d": round(curseur, 3), "f": round(curseur + part, 3)})
            curseur += part
    return resultat


def paginer(mots: list[dict], st: dict, coupes: list[float], jusqua: float, forts) -> list[dict]:
    """Découpe les mots en écrans de sous-titres courts (2 à 4 mots), sans couper un prix."""
    pages, page = [], []
    longueur = lambda p: sum(len(m["t"]) for m in p) + len(p) - 1
    for m in mots:
        if m["d"] >= jusqua:
            break
        if page:
            avant = page[-1]
            prix = avant["t"][0].isdigit() and sans_accent(m["t"]) in {sans_accent(u) for u in UNITES} | {""}
            rupture = (len(page) >= st["mots_max"] or longueur(page + [m]) > st["caracteres_max"]
                       or avant["t"].rstrip("»\"").endswith((".", "?", "!", ":", ";", "…", ","))
                       or m["d"] - avant["f"] > 0.45
                       or any(avant["d"] < c <= m["d"] + 0.02 for c in coupes))
            if rupture and not prix:
                pages.append(page)
                page = []
        page.append(m)
    if page:
        pages.append(page)

    sortie = []
    for k, p in enumerate(pages):
        debut = max(p[0]["d"] - 0.03, 0)
        fin = min(p[-1]["f"] + 0.4, jusqua)
        if k + 1 < len(pages):
            fin = min(fin, max(pages[k + 1][0]["d"] - 0.03, debut + 0.1))
        car = longueur(p)
        sortie.append({
            "id": f"st-{k}", "d": round(debut, 3), "f": round(fin, 3),
            "echelle": round(min(1, max(0.55, st["caracteres_max"] / max(car, 1))), 3),
            "mots": [{"t": re.sub(r"[.,;:…]+$", "", m["t"]) or m["t"], "d": m["d"], "fort": forts(m)} for m in p],
        })
    return sortie


def calculer_zooms(mots: list[dict], coupes: list[float], total: float, r: dict) -> list[dict]:
    """Alterne plan large / plan serré aux coupes et aux débuts de phrase, avec un zoom lent entre."""
    debuts_phrase = [mots[i + 1]["d"] for i, m in enumerate(mots[:-1])
                     if m["t"].rstrip("»\"").endswith((".", "?", "!"))]
    bascules, dernier = [0.0], 0.0
    for t in sorted(set(coupes + debuts_phrase)):
        if t - dernier >= r["zoom_intervalle_min"] and total - t >= 1.0:
            bascules.append(t)
            dernier = t
    zooms = []
    for k, t in enumerate(bascules):
        fin = bascules[k + 1] if k + 1 < len(bascules) else total
        base = r["zoom_coupe"] if k % 2 else 1.0
        zooms.append({"t": round(t, 3), "duree": round(fin - t, 3),
                      "de": round(base, 4), "a": round(base + r["zoom_lent"], 4)})
    return zooms


def preparer_media(source: str, dossier: Path, nom: str, debut: float, duree_utile: float) -> str:
    """Copie un plan de coupe dans le projet, au bon format et à la bonne longueur."""
    chemin = (RACINE / source) if not Path(source).is_absolute() else Path(source)
    if not chemin.exists():
        sys.exit(f"plan.json : fichier introuvable : {source}")
    if chemin.suffix.lower() in IMAGES:
        cible = dossier / "assets" / f"{nom}{chemin.suffix.lower()}"
        shutil.copyfile(chemin, cible)
        return f"assets/{cible.name}"
    empreinte = hashlib.md5(f"{chemin}{chemin.stat().st_mtime}{debut}{duree_utile:.2f}".encode()).hexdigest()[:8]
    cible = dossier / "assets" / f"{nom}-{empreinte}.mp4"
    if not cible.exists():
        normaliser_clip(chemin, cible, debut, duree_utile + 0.2)
    return f"assets/{cible.name}"


def rvb(couleur: str) -> tuple[int, int, int]:
    h = couleur.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def claire(couleur: str) -> bool:
    """Vrai si la couleur est claire (il faut alors écrire en foncé dessus)."""
    r, v, b = rvb(couleur)
    return (0.299 * r + 0.587 * v + 0.114 * b) / 255 > 0.6


def derives(charte: dict) -> dict:
    """Ce qui se déduit de l'univers : texte sur l'accent, couleurs des cartes, motifs de fond."""
    c = charte["couleurs"]
    sombre = charte.get("cartes", "clair") == "sombre"
    d = {
        "sur_accent": c["encre"] if claire(c["accent"]) else c["blanc"],
        "carte_fond": c["nuit"] if sombre else c["papier"],
        "carte_texte": c["blanc"] if sombre else c["encre"],
        # un accent clair (jaune, vert vif) ne se lit pas sur du papier clair : on écrit à l'encre
        "carte_accent": c["accent"] if sombre or not claire(c["accent"]) else c["encre"],
        "accent_vide": "rgba({}, {}, {}, 0)".format(*rvb(c["accent"])),
        "lisere": c["accent"],
        "fond_image": f"radial-gradient(120% 80% at 50% 30%, {c['marque']} 0%, {c['nuit']} 72%)",
        "fond_taille": "100% 100%", "carte_image": "none", "carte_taille": "auto",
    }
    # sur une pastille claire, le texte foncé n'a pas besoin de contour
    d["contour_actif"] = c["accent"] if claire(c["accent"]) else c["nuit"]
    motif = charte.get("motif", "uni")
    if motif == "grille":  # quadrillage de plan d'architecte
        trait = lambda couleur, a: ("linear-gradient(rgba({0}, {1}, {2}, {3}) 2px, transparent 2px), "
                                    "linear-gradient(90deg, rgba({0}, {1}, {2}, {3}) 2px, transparent 2px)"
                                    ).format(*rvb(couleur), a)
        d["fond_image"] = trait(c["blanc"], 0.07) + ", " + d["fond_image"]
        d["fond_taille"] = "72px 72px, 72px 72px, 100% 100%"
        d["carte_image"] = trait(c["blanc"] if sombre else c["encre"], 0.08)
        d["carte_taille"] = "36px 36px"
    elif motif == "rayures":  # ruban de chantier
        d["lisere"] = f"repeating-linear-gradient(-45deg, {c['accent']} 0 22px, {c['nuit']} 22px 44px)"
    elif motif != "uni":
        sys.exit(f"Univers : motif inconnu « {motif} » (uni, grille ou rayures).")
    return d


def slug_police(famille: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", famille.lower()).strip("-")


def gabarit(nom: str, donnees: dict | None = None) -> str:
    texte = (GABARIT / nom).read_text(encoding="utf-8")
    return texte.replace("__DONNEES__", json.dumps(donnees, ensure_ascii=False)) if donnees is not None else texte


def calque(dossier: Path, ident: str, fmt: dict, balises: str, css: str, js: str, origine: str) -> None:
    """Écrit une sous-composition HyperFrames (un calque posé sur la vidéo) dans compositions/."""
    (dossier / "compositions").mkdir(exist_ok=True)
    (dossier / "compositions" / f"{ident}.html").write_text(f"""<!-- Généré par machine/monter.py : modifie plan.json ou {origine} -->
<template id="{ident}-template">
  <div id="root" data-composition-id="{ident}" data-width="{fmt['largeur']}" data-height="{fmt['hauteur']}">{balises}
    <style>
{css}
    </style>
    <script>
{js}
    </script>
  </div>
</template>
""", encoding="utf-8")


def code_bloc(genre: str, donnees: dict) -> tuple[str, str]:
    """Le CSS et le JS d'un bloc : la partie commune + la sienne (montage/blocs/)."""
    lire_bloc = lambda nom: (BLOCS / nom).read_text(encoding="utf-8")
    css = lire_bloc("commun.css") + "\n" + lire_bloc(f"{genre}.css")
    js = lire_bloc("commun.js").replace("__DONNEES__", json.dumps(donnees, ensure_ascii=False)) \
        + "\n" + lire_bloc(f"{genre}.js") + lire_bloc("fin.js")
    return css, js


def construire(dossier: Path, plan: dict, donnees: dict, charte: dict) -> dict:
    """Écrit la composition HyperFrames du projet et renvoie les instants à regarder."""
    fmt, c = charte["format"], charte["couleurs"]
    # "reglages" du plan : mêmes noms que dans config/da.yaml, pour CETTE vidéo seulement
    regl = plan.get("reglages", {})
    inconnus = [k for k in regl if k not in charte["rythme"] and k not in charte["sous_titres"]]
    if inconnus:
        sys.exit(f"plan.json : réglage(s) inconnu(s) {inconnus}. Possibles : "
                 f"{sorted({**charte['rythme'], **charte['sous_titres']})}")
    r = {**charte["rythme"], **{k: v for k, v in regl.items() if k in charte["rythme"]}}
    st = {**charte["sous_titres"], **{k: v for k, v in regl.items() if k in charte["sous_titres"]}}
    zs, hab, dv = charte["zones_sures"], charte["habillage"], derives(charte)
    sig = charte["signature"]
    signature = e(sig[0]) + (f" <b>{e(' '.join(sig[1:]))}</b>" if len(sig) > 1 else "")
    mots_bruts, total = donnees["mots"], donnees["duree"]
    T = lambda v, fin=False: instant(v, mots_bruts, fin)
    (dossier / "assets" / "polices").mkdir(parents=True, exist_ok=True)
    (dossier / "lib").mkdir(exist_ok=True)
    mot_cle = (plan.get("mot_cle") or "").upper()
    reseau = plan.get("reseau", "instagram")
    mots = corriger(mots_bruts, plan.get("corrections", {}))

    # ----- Carton de fin
    fin, bloc_fin = None, ""
    cf = plan.get("carton_fin", {})
    if mot_cle and cf is not False:
        if "de" in cf:
            debut_fin = T(cf["de"])
        else:
            # Par défaut : au dernier « commente / tape » prononcé ; sinon à la dernière fois que le
            # mot-clé est dit (il peut aussi apparaître plus tôt dans le propos) ; sinon 2,5 s avant la fin.
            tardifs = [m for m in mots if m["d"] > total * 0.5]
            appel = ([m for m in tardifs if sans_accent(m["t"]) in {"commente", "commentez", "tape", "tapez"}]
                     or [m for m in tardifs if sans_accent(m["t"]) == sans_accent(mot_cle)])
            debut_fin = appel[-1]["d"] - 0.1 if appel else max(donnees.get("fin_parole", total) - 2.5, 0)
        fin = {"d": round(debut_fin, 3)}
        variante = next((v for v in charte["carton_fin"].values() if reseau in v["reseaux"]),
                        charte["carton_fin"]["commente"])
        taille = 150 if len(mot_cle) <= 6 else 120 if len(mot_cle) <= 9 else 92
        logo = charte.get("logo")
        if logo and (RACINE / logo).exists():
            shutil.copyfile(RACINE / logo, dossier / "assets" / Path(logo).name)
            marque = f'<img class="fin__logo" src="assets/{e(Path(logo).name)}" alt="">'
        else:
            marque = f'<span class="fin__marque">{signature}</span>'
        bloc_fin = f"""
    <div id="fin" class="fin"><div class="fin__fond">
      <span class="fin__verbe">{e(variante['verbe'])}</span>
      <span id="fin-mot" class="fin__mot" style="font-size:{taille}px">{e(mot_cle)}</span>
      <span class="fin__suite">{e(typo(cf.get('suite') or variante['suite']))}</span>
      {marque}
    </div></div>"""

    # ----- Sous-titres (calque « sous-titres »)
    emphase = plan.get("emphase", [])
    indices_forts = {x for x in emphase if isinstance(x, int)}
    textes_forts = {sans_accent(x) for x in emphase if isinstance(x, str)} | ({sans_accent(mot_cle)} if mot_cle else set())
    forts = lambda m: (m["i"] in indices_forts or sans_accent(m["t"]) in textes_forts
                       or bool(re.search(r"\d|€|%", m["t"])))
    pages = paginer(mots, st, donnees.get("coupes", []), fin["d"] if fin else total, forts) \
        if plan.get("sous_titres", True) else []
    bloc_st = ""
    for p in pages:
        spans = " ".join(f'<span id="{p["id"]}-{j}" class="st__mot">{e(m["t"])}</span>' for j, m in enumerate(p["mots"]))
        style = f' style="font-size:{round(st["taille"] * p["echelle"])}px"' if p["echelle"] < 1 else ""
        bloc_st += (f'\n    <div id="{p["id"]}" class="st{" st--majuscules" if charte.get("majuscules") else ""}"{style}>'
                    f'<span class="st__ligne">{spans}</span></div>')
    calque(dossier, "sous-titres", fmt, bloc_st, gabarit("sous-titres.css"), gabarit("sous-titres.js", {
        "duree": total, "apparition": st["apparition"], "motEnCours": st["mot_en_cours"],
        "accent": c["accent"], "accentVide": dv["accent_vide"], "accentClair": c["accent_clair"], "blanc": c["blanc"],
        "surAccent": dv["sur_accent"], "contour": c["nuit"], "contourActif": dv["contour_actif"],
        "ombreActive": not claire(c["accent"]),
        "pages": [{"id": p["id"], "d": p["d"], "f": p["f"],
                   "mots": [{"d": m["d"], "fort": m["fort"]} for m in p["mots"]]} for p in pages]}),
           "montage/gabarit/sous-titres.*")

    # ----- Accroche, chiffres, carton de fin, signature, barre (calque « habillage »)
    cartes, bloc_hab = [], ""
    acc = plan.get("accroche")
    if acc:
        texte = re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(typo(acc["texte"])))
        n = len(acc["texte"])
        taille = 84 if n <= 34 else 72 if n <= 60 else 60 if n <= 90 else 52
        cartes.append({"id": "accroche", "d": 0, "f": round(T(acc.get("a", 3.0), fin=True), 3)})
        bloc_hab += (f'\n    <div id="accroche" class="carte"><div class="carte__fond">'
                     f'<p class="accroche__texte" style="font-size:{taille}px">{texte}</p></div></div>')
    for k, ch in enumerate(plan.get("chiffres", []), 1):
        d = T(ch["de"])
        f = T(ch["a"], fin=True) if "a" in ch else d + 2.6
        texte = typo(ch["texte"])
        taille = min(170, int(820 / (0.62 * max(len(texte), 3))))
        carte = {"id": f"chiffre-{k}", "d": round(d, 3), "f": round(f, 3)}
        seul = re.fullmatch(r"(\D*?)(\d[\d\s]*\d|\d)(\D*)", texte)  # \s couvre les espaces insécables
        if seul and ch.get("compter", True) and int(re.sub(r"\D", "", seul.group(2))) >= 10:
            carte["compteur"] = {"avant": seul.group(1), "valeur": int(re.sub(r"\D", "", seul.group(2))),
                                 "apres": seul.group(3)}
        cartes.append(carte)
        legende = f'<span class="chiffre__legende">{e(typo(ch["legende"]))}</span>' if ch.get("legende") else ""
        bloc_hab += (f'\n    <div id="chiffre-{k}" class="carte"><div class="carte__fond">'
                     f'<span class="chiffre__valeur" style="font-size:{taille}px">{e(texte)}</span>{legende}</div></div>')
    bloc_hab += bloc_fin
    if hab.get("signature"):
        bloc_hab += f'\n    <div id="signature" class="signature">{signature}</div>'
    if hab.get("barre_progression"):
        bloc_hab += '\n    <div id="barre" class="barre"><div id="barre-plein" class="barre__plein"></div></div>'
    calque(dossier, "habillage", fmt, bloc_hab, gabarit("habillage.css"),
           gabarit("habillage.js", {"duree": total, "cartes": cartes, "fin": fin}), "montage/gabarit/habillage.*")

    # ----- Plans de coupe : l'enveloppe n'est pas minutée, seule la vidéo l'est (règle HyperFrames)
    brolls, bloc_broll = [], ""
    for k, b in enumerate(plan.get("broll", []), 1):
        d, f = T(b["de"]), T(b["a"], fin=True)
        mode = b.get("mode", "plein")
        if mode not in ("plein", "carte"):
            sys.exit(f"plan.json : mode de plan de coupe inconnu « {mode} » (plein ou carte).")
        src = preparer_media(b["fichier"], dossier, f"broll-{k}", float(b.get("debut", 0)), f - d)
        minutage = f'data-start="{round(d, 3)}" data-duration="{round(f - d, 3)}" data-track-index="1"'
        if Path(src).suffix in IMAGES:
            media = f'<img id="broll-{k}-image" class="clip" src="{e(src)}" alt="" {minutage}>'
        else:
            media = f'<video id="broll-{k}-video" src="{e(src)}" {minutage} muted playsinline></video>'
        brolls.append({"id": f"broll-{k}", "d": round(d, 3), "f": round(f, 3), "mode": mode})
        bloc_broll += f'\n      <div id="broll-{k}" class="broll broll--{mode}"><div class="broll__cadre">{media}</div></div>'

    # ----- La prise et la musique
    if (dossier / "assets" / "a-roll.mp4").exists():
        prise = (f'<div id="plan"><video id="a-roll" src="assets/a-roll.mp4" data-start="0" '
                 f'data-duration="{total}" data-track-index="0" data-has-audio="true" playsinline></video></div>')
    else:
        prise = '<div id="plan" class="plan--fond"></div>'
    musique = ""
    if plan.get("musique"):
        source = RACINE / plan["musique"]
        if not source.exists():
            sys.exit(f"plan.json : musique introuvable : {plan['musique']}")
        shutil.copyfile(source, dossier / "assets" / f"musique{source.suffix}")
        musique = (f'\n      <audio id="musique" src="assets/musique{source.suffix}" data-start="0" data-duration="{total}" '
                   f'data-track-index="2" data-volume="{charte["son"]["musique_volume"]}" data-fade-in="0.4" data-fade-out="1.2"></audio>')

    # ----- Sur mesure : extras.html (balises + <style> + window.PH_EXTRAS) est repris tel quel
    extras = (dossier / "extras.html").read_text(encoding="utf-8") if (dossier / "extras.html").exists() else ""

    # ----- Assemblage de la composition principale
    famille = slug_police(charte["police"])
    fichiers = sorted(POLICES.glob(f"{famille}-latin-*-normal.woff2"))
    if not fichiers:
        sys.exit(f"Police « {charte['police']} » absente de {POLICES} (fichiers {famille}-latin-<graisse>-normal.woff2).")
    faces = []
    for police in fichiers:
        shutil.copyfile(police, dossier / "assets" / "polices" / police.name)
        graisse = police.name.split("-latin-")[1].split("-")[0]
        faces.append(f'      @font-face {{ font-family: "{charte["police"]}"; font-weight: {graisse}; font-style: normal; '
                     f'src: url("assets/polices/{police.name}") format("woff2"); }}')
    polices = "\n".join(faces)
    gsap = MONTAGE / "node_modules" / "gsap" / "dist" / "gsap.min.js"
    if not gsap.exists():
        sys.exit("GSAP n'est pas installé. Lance une fois : cd montage && npm install")
    shutil.copyfile(gsap, dossier / "lib" / "gsap.min.js")
    variables = "\n".join(f"        --{nom.replace('_', '-')}: {valeur};" for nom, valeur in
                          {**c, **{k: v for k, v in dv.items() if k not in ("accent_vide", "contour_actif")}}.items())
    hote = lambda nom, piste, debut=0, duree=total, classe="": (
        f'\n      <div id="{nom}"{classe} data-composition-id="{nom}" data-composition-src="compositions/{nom}.html" '
        f'data-start="{round(debut, 3)}" data-duration="{round(duree, 3)}" data-track-index="{piste}" '
        f'data-width="{fmt["largeur"]}" data-height="{fmt["hauteur"]}"></div>')

    # ----- Blocs : animations prêtes à l'emploi (machine/blocs.py), une sous-composition chacun
    hotes_blocs, fenetres_blocs = "", []
    for k, b in enumerate(plan.get("blocs", []), 1):
        genre = b.get("bloc")
        if genre not in bibliotheque.BLOCS:
            sys.exit(f"plan.json : bloc inconnu « {genre} ». Disponibles : {', '.join(bibliotheque.BLOCS)}.")
        fabrique, mode, duree_defaut = bibliotheque.BLOCS[genre]
        d = T(b["de"])
        f = min(T(b["a"], fin=True) if "a" in b else d + duree_defaut, total)
        if f - d < 1.5:
            sys.exit(f"plan.json : le bloc « {genre} » n° {k} dure {f - d:.1f} s, il lui faut au moins 1,5 s.")
        contexte = {"id": f"bloc-{k}", "debut": d, "duree": round(f - d, 3), "T": T, "typo": typo,
                    "mot_cle": mot_cle, "marque": sig,
                    "media": lambda fichier, nom_media: preparer_media(fichier, dossier, nom_media, 0, 0)}
        balises, infos = fabrique(b, contexte)
        css, js = code_bloc(genre, {**infos, "id": contexte["id"], "duree": contexte["duree"]})
        calque(dossier, contexte["id"], fmt, balises, css, js, f"montage/blocs/{genre}.*")
        hotes_blocs += hote(contexte["id"], 5, d, f - d, f' class="bloc bloc--{mode}"')
        fenetres_blocs.append((d, f))

    principal = {"duree": total, "visageY": r["visage_y"], "broll": brolls,
                 "zooms": calculer_zooms(mots, donnees.get("coupes", []), total, r)}

    (dossier / "index.html").write_text(f"""<!doctype html>
<!-- Généré par machine/monter.py à partir de plan.json : modifie plutôt plan.json, ou ajoute extras.html -->
<html lang="fr" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={fmt['largeur']}, height={fmt['hauteur']}" />
    <script src="lib/gsap.min.js"></script>
    <style>
{polices}
      :root {{
{variables}
        --largeur: {fmt['largeur']}px; --hauteur: {fmt['hauteur']}px;
        --zone-haut: {zs['haut']}px; --zone-bas: {zs['bas']}px; --zone-cotes: {zs['cotes']}px;
        --st-taille: {st['taille']}px; --st-centre: {st['centre_y']}px;
        --police: "{charte['police']}"; --graisse-titres: {charte['graisse_titres']}; --graisse-texte: {charte['graisse_texte']};
      }}
{gabarit('main.css')}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}"
         data-width="{fmt['largeur']}" data-height="{fmt['hauteur']}" data-fps="{fmt['ips']}">
      {prise}{bloc_broll}{musique}{hotes_blocs}{hote('sous-titres', 3)}{hote('habillage', 4)}
      {extras}
    </div>
    <script>
{gabarit('main.js', principal)}
    </script>
  </body>
</html>
""", encoding="utf-8")
    ecrire(dossier / "meta.json", {"id": dossier.name, "name": dossier.name})
    ecrire(dossier / "hyperframes.json", {"paths": {"blocks": "compositions", "assets": "assets"}})

    # Les instants à regarder : première image, chaque carte, chaque plan de coupe, trois sous-titres, la fin
    reperes = [0.0] + [round((x["d"] + x["f"]) / 2, 2) for x in cartes + brolls]
    reperes += [round(p["mots"][-1]["d"] + 0.1, 2) for p in pages[1::max(len(pages) // 3, 1)]][:3]
    for d, f in fenetres_blocs:  # un bloc se juge au milieu de sa construction et une fois complet
        reperes += [round(d + (f - d) * 0.45, 2), round(f - 0.6, 2)]
    if fin:
        reperes.append(round(min(fin["d"] + 1.2, total - 0.1), 2))
    reperes.append(round(total - 0.1, 2))
    return {"reperes": sorted(set(t for t in reperes if 0 <= t < total)), "pages": len(pages)}


def verifier(dossier: Path) -> None:
    r = hyperframes("lint", dossier, "--json", verifier=False)
    try:
        bilan = json.loads(r.stdout)
    except json.JSONDecodeError:
        sys.exit(f"Vérification impossible :\n{(r.stdout + r.stderr)[-1500:]}")
    for f in bilan.get("findings", []):
        if f.get("severity") in ("error", "warning"):
            print(f"  {'✗' if f['severity'] == 'error' else '⚠'} {f.get('code')} : {f.get('message')}")
    if bilan.get("errorCount"):
        sys.exit(f"{bilan['errorCount']} erreur(s) dans la composition : corrige avant de rendre.")
    print(f"Composition vérifiée ({bilan.get('warningCount', 0)} avertissement(s)).")


def apercu(dossier: Path, reperes: list[float], colonnes: int = 5) -> Path:
    """Images clés + une planche-contact (une seule image à regarder)."""
    from PIL import Image, ImageDraw, ImageFont
    sortie = dossier / "apercu"
    shutil.rmtree(sortie, ignore_errors=True)
    hyperframes("snapshot", dossier, "--at", ",".join(str(t) for t in reperes), "--no-end", "--output", sortie)
    images = sorted(sortie.glob("frame-*.png"))
    if not images:
        sys.exit("HyperFrames n'a produit aucune image clé.")
    l, h, marge, bande = 324, 576, 12, 40
    colonnes = min(colonnes, len(images))
    lignes = -(-len(images) // colonnes)
    planche = Image.new("RGB", (colonnes * (l + marge) + marge, lignes * (h + bande + marge) + marge), "#16181C")
    dessin, police = ImageDraw.Draw(planche), ImageFont.load_default(size=26)
    for k, (image, t) in enumerate(zip(images, reperes)):
        x, y = marge + (k % colonnes) * (l + marge), marge + (k // colonnes) * (h + bande + marge)
        planche.paste(Image.open(image).convert("RGB").resize((l, h)), (x, y))
        dessin.text((x + 6, y + h + 6), f"{t:.2f} s", fill="#F2F2F2", font=police)
    cible = sortie / "planche.jpg"
    planche.save(cible, quality=88)
    return cible


def rendre(dossier: Path, cible: Path, brouillon: bool) -> None:
    cible.parent.mkdir(exist_ok=True)
    print(f"Rendu en cours ({'brouillon' if brouillon else 'qualité finale'})...")
    qualite = ["--quality", "draft"] if brouillon else ["--crf", "20"]  # 20 : net, et un fichier léger à envoyer
    hyperframes("render", dossier, "--output", cible, *qualite, "--quiet")
    # Les réseaux préfèrent un fichier qui démarre vite et un son AAC standard
    final = cible.with_suffix(".tmp.mp4")
    ffmpeg("-i", cible, "-c", "copy", "-movflags", "+faststart", final)
    final.replace(cible)


def planche_de_style(charte: dict) -> None:
    """La DA sans rush : un faux montage de 14 s pour juger couleurs, police, sous-titres, cartes."""
    dossier = projet(f"_planche-{charte['univers']}", creer=True)
    shutil.rmtree(dossier / "assets", ignore_errors=True)
    phrase = ("Tu refais ta salle de bain ? Attends avant de signer. Le vrai prix, c’est entre "
              "6\u00a0000 et 12\u00a0000 € posée. Compare toujours trois devis. Commente DEVIS").split(" ")
    mots = [{"i": i, "t": t, "d": round(0.2 + i * 0.36, 3), "f": round(0.2 + i * 0.36 + 0.3, 3)}
            for i, t in enumerate(phrase)]
    total = round(mots[-1]["f"] + 2.6, 3)
    plan = {"reseau": "instagram", "mot_cle": "DEVIS",
            "accroche": {"texte": "Ta salle de bain : *le vrai prix*", "a": 3.2},
            "chiffres": [{"de": "m13", "a": "m19", "texte": "12 000 €", "legende": "le haut de la fourchette"}],
            "carton_fin": {"de": "m24", "suite": "et je t’envoie la checklist en DM"}}
    donnees = {"duree": total, "fin_parole": mots[-1]["f"], "coupes": [3.4, 7.3], "mots": mots}
    construire(dossier, plan, donnees, charte)
    verifier(dossier)
    image = apercu(dossier, [1.2, 3.9, 6.9, total - 0.6], colonnes=4)
    cible = MONTAGE / "da" / f"planche-{charte['univers']}.jpg"
    shutil.copyfile(image, cible)
    print(f"Planche de style « {charte['nom']} » -> {cible}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("id", nargs="?", help="le projet, ex. 2026-11-30-3")
    p.add_argument("--apercu", action="store_true", help="sortir les images clés (à regarder avant de rendre)")
    p.add_argument("--rendu", action="store_true", help="rendre le MP4 final dans montages/")
    p.add_argument("--brouillon", action="store_true", help="rendu rapide, qualité réduite")
    p.add_argument("--planche", action="store_true", help="planche de style de la DA, sans rush")
    p.add_argument("--univers", help="essayer un autre univers de config/univers/ (défaut : celui de config/da.yaml)")
    a = p.parse_args()
    charte = da(a.univers)

    if a.planche:
        return planche_de_style(charte)
    if not a.id:
        p.error("donne l'identifiant du projet, ou --planche")

    dossier = projet(a.id)
    for requis in ("mots.json", "plan.json"):
        if not (dossier / requis).exists():
            sys.exit(f"Il manque {dossier / requis} (voir .claude/skills/montage-video/SKILL.md).")
    infos = construire(dossier, lire(dossier / "plan.json"), lire(dossier / "mots.json"), charte)
    print(f"Composition écrite : {dossier / 'index.html'} ({infos['pages']} écrans de sous-titres)")
    verifier(dossier)
    if a.apercu:
        print(f"Aperçu -> {apercu(dossier, infos['reperes'])}")
    if a.rendu:
        cible = MONTAGES / f"{identifiant(a.id)}.mp4"
        rendre(dossier, cible, a.brouillon)
        print(f"Vidéo -> {cible}\nSuite : python machine/yeux.py {a.id}")


if __name__ == "__main__":
    main()
