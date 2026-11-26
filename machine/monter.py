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
from atelier import (MONTAGE, MONTAGES, RACINE, da, detourer, duree, ecrire, ffmpeg, hyperframes, identifiant,
                     lire, normaliser_clip, projet)

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


def preparer_media(source: str, dossier: Path, nom: str, debut: float, duree_utile: float,
                   cadre: tuple[int, int] = (1080, 1920), ancre_x: float = 0.5, ancre_y: float = 0.5,
                   recul: float = 0, entier: bool = False) -> str:
    """Copie un plan de coupe dans le projet, à la bonne longueur et à la forme du cadre qui le montre
    (tout l'écran, la carte, le carré de la vitrine : on garde la partie de l'image donnée par les ancres)."""
    chemin = (RACINE / source) if not Path(source).is_absolute() else Path(source)
    if not chemin.exists():
        sys.exit(f"plan.json : fichier introuvable : {source}")
    if chemin.suffix.lower() in IMAGES:
        cible = dossier / "assets" / f"{nom}{chemin.suffix.lower()}"
        shutil.copyfile(chemin, cible)
        return f"assets/{cible.name}"
    ancres = (f"{ancre_x}" if (ancre_y, recul, entier) == (0.5, 0, False)    # (empreintes d'avant inchangées)
              else f"{ancre_x}/{ancre_y}/{recul}" + ("/entier" if entier else ""))
    empreinte = hashlib.md5(f"{chemin}{chemin.stat().st_mtime}{debut}{duree_utile:.2f}{cadre}{ancres}".encode()).hexdigest()[:8]
    cible = dossier / "assets" / f"{nom}-{empreinte}.mp4"
    if not cible.exists():
        normaliser_clip(chemin, cible, debut, duree_utile + 0.2, cadre, ancre_x, ancre_y, recul, entier)
    return f"assets/{cible.name}"


def decouper_personne(dossier: Path, a_roll: Path, d: float, f: float, total: float) -> str:
    """Découpe la personne de son décor sur un passage de la prise (fond transparent). Gardé en réserve :
    tant que la prise et le passage ne changent pas, on ne recalcule rien."""
    empreinte = hashlib.md5(f"{a_roll.stat().st_mtime}{d:.3f}{f:.3f}".encode()).hexdigest()[:8]
    cible = dossier / "assets" / f"detoure-{empreinte}.webm"
    if not cible.exists():
        print(f"Détourage de la personne de {d:.1f} s à {f:.1f} s (compter ~20 s de calcul par seconde de vidéo)...")
        if d <= 0 and f >= total:
            detourer(a_roll, cible)
        else:
            passage = dossier / "assets" / f"detoure-{empreinte}-source.mp4"
            ffmpeg("-i", a_roll, "-ss", f"{d:.3f}", "-t", f"{f - d:.3f}", "-an", "-c:v", "libx264", "-crf", "14",
                   "-preset", "fast", passage)
            detourer(passage, cible)
            passage.unlink()
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


def personne_entiere(dossier: Path, a_roll: Path, total: float) -> str:
    """La personne détourée sur toute la vidéo (assets/personne.webm), refaite si la prise a changé.
    RobustVideoMatting (machine/detourage.py) s'il est installé : net, cheveux compris, ~0,3 s par
    image ; sinon le modèle de HyperFrames (plus lent, contours moins propres)."""
    cible = dossier / "assets" / "personne.webm"
    if cible.exists() and cible.stat().st_mtime >= a_roll.stat().st_mtime:
        return "assets/personne.webm"
    import detourage
    if detourage.disponible():
        print(f"Détourage de toute la vidéo avec RVM (~{total * 30 * 0.3 / 60:.0f} min)...")
        detourage.detourer(a_roll, cible)
        return "assets/personne.webm"
    return decouper_personne(dossier, a_roll, 0.0, total, total)


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
    inconnus = [k for k in regl if k not in charte["rythme"] and k not in charte["sous_titres"] and k not in charte["son"]]
    if inconnus:
        sys.exit(f"plan.json : réglage(s) inconnu(s) {inconnus}. Possibles : "
                 f"{sorted({**charte['rythme'], **charte['sous_titres'], **charte['son']})}")
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

    # ----- Détourage : la consigne du plan, sinon le réglage de la DA
    #   "detourage": {"fond": "origine" | "flou" | "univers", "blocs": "derriere",
    #                 "mots_derriere": [{"de", "a", "texte"}]}
    if "detourage" in plan:
        det = plan["detourage"]
    else:
        det = {"blocs": "derriere"} if charte.get("personne_devant") else False
    a_roll = dossier / "assets" / "a-roll.mp4"
    detourage = a_roll.exists() and det is not False
    det = {} if det in (True, False, None) else det
    fond = det.get("fond", "origine")
    if fond not in ("origine", "flou", "univers"):
        sys.exit(f"plan.json : detourage.fond inconnu « {fond} » (origine, flou ou univers).")
    blocs_derriere = detourage and det.get("blocs") == "derriere"
    # ----- Mise en scène des animations plein écran : "plein" (elles remplacent l'image) ou "cadre"
    # (la personne passe dans un cadre arrondi en bas, l'animation au-dessus ; aucun détourage)
    # "coin" : la personne détourée en bas, d'un côté puis de l'autre, le contenu toujours derrière elle.
    # "vitrine" : la personne détourée au centre, plus haut ; au-dessus d'elle, un carré encadré et
    # légèrement animé où passent les plans de coupe (la maquette 3D d'un projet).
    # "partage" : l'écran coupé en deux. En haut, sur fond bleu, une barre de titre et la carte où
    # passent les plans (avec pastilles et encarts) ; en bas, la personne ; les sous-titres sur la couture.
    style = plan.get("mise_en_scene", charte.get("mise_en_scene", "plein"))
    if style not in ("plein", "cadre", "coin", "vitrine", "partage"):
        sys.exit(f"mise_en_scene inconnue « {style} » (plein, cadre, coin, vitrine ou partage).")
    blocs_cadre = style == "cadre" and a_roll.exists() and not blocs_derriere
    en_vitrine = style == "vitrine" and a_roll.exists()
    en_partage = style == "partage" and a_roll.exists()
    en_coin = style in ("coin", "vitrine", "partage") and a_roll.exists()   # la personne détourée du coin
    if en_vitrine or en_partage:
        ou = "dans le carré" if en_vitrine else "dans la carte du haut"
        for b in plan.get("blocs", []):
            if bibliotheque.BLOCS.get(b.get("bloc"), (None, ""))[1] == "plein":
                sys.exit(f"plan.json : en {style}, tout passe {ou} : pas de bloc plein écran "
                         f"(« {b.get('bloc')} »). Les blocs par-dessus (commentaire, nom) restent possibles.")
        if plan.get("chiffres"):
            sys.exit(f"plan.json : en {style}, les montants vont sur les plans (\"legende\", \"badge\") "
                     "ou dans un encart (\"encarts\"), pas en cartes de chiffres.")
        if plan.get("accroche"):
            sys.exit(f"plan.json : en {style}, l'accroche est le titre du haut (\"vitrine\": {{\"titre\": ...}} "
                     "ou \"titre\" sur le premier plan en partage).")

    # ----- Où est le visage dans l'image (une fois l'image décalée, si elle l'est) : les yeux, le haut
    # de la tête, le menton, en fraction de la hauteur. Tout le reste de la mise en scène en découle.
    H = fmt["hauteur"]
    yeux = r["visage_y"]
    tete_y = r.get("tete_y") or yeux - 0.115
    menton_y = r.get("menton_y") or yeux + 0.09
    normale = st["centre_y"] - zs["haut"] - 150    # la hauteur d'un bloc quand il a tout l'écran
    decalage = round(r.get("decalage_y") or 0)     # l'image remontée (négatif) ou descendue, en pixels

    # ----- Mise en scène « coin » : la personne détourée, réduite, posée en bas de l'écran (son buste
    # touche le bord du bas, un peu hors de l'écran sur le côté). Les sous-titres passent au-dessus de
    # sa tête, les animations et les cartes au-dessus des sous-titres. Pas de décalage de l'image ici :
    # on reprend les hauteurs du visage dans l'image d'origine.
    coin = None
    if en_partage:
        # Écran partagé : la couture (la ligne qui sépare le haut du bas) porte les sous-titres. Dans le
        # bas, la vraie vidéo de la personne, sur toute la largeur, avec son décor (par défaut : on ne la
        # détoure pas). Ses yeux se posent à "yeux_ecran" ; ce qui dépasse au-dessus de la couture passe
        # sous le fond bleu du haut. "detoure": true : l'ancienne façon (détourée, réduite, sur le fond
        # de l'univers, le haut de la tête "sous_couture" pixels sous la couture).
        rp = plan.get("partage", {})
        L = fmt["largeur"]
        en_video = not rp.get("detoure", False)
        couture = int(rp.get("couture", 1040 if en_video else 1120))
        s_coin = float(rp.get("echelle", 0.52))
        y_c = couture + float(rp.get("sous_couture", 50)) - (tete_y - decalage / H) * H * s_coin
        st.update(centre_y=couture, taille=int(rp.get("taille_sous_titres", 60)), mot_en_cours="couleur",
                  apparition="page", bandeau=True)
        yeux_bruts = (yeux - decalage / H) * H     # les yeux dans l'image d'origine, en pixels
        coin = {"s": s_coin, "y": round(y_c, 1), "yeux": round(yeux - decalage / H, 4), "video": en_video,
                "pousse": round(float(rp.get("yeux_ecran", couture + 330)) - yeux_bruts),
                "panneau": round(L * (1 - s_coin) / 2, 1), "place": 0, "carte": 0,
                "reglages": {**rp, "cote": "panneau", "alterner": False},
                "coupe": round((couture - y_c) / s_coin, 1),   # le haut caché de la personne (pixels de l'image)
                "partage": {"couture": couture, "x": (L - 840) // 2, "largeur": 840,
                            "titre_y": zs["haut"] + 20, "titre_h": 112, "carte_y": zs["haut"] + 162,
                            "carte_h": couture - 80 - (zs["haut"] + 162)}}
    elif en_vitrine:
        # Mise en scène « vitrine » : le carré en haut (sous l'interface), la personne centrée dessous,
        # le haut de ses cheveux passe devant le bas du carré (de la profondeur, et elle monte d'autant).
        # Les sous-titres se posent sous son menton, au-dessus de l'interface du bas.
        rc = plan.get("vitrine", {})
        L = fmt["largeur"]
        cote_v = int(rc.get("taille", 560))
        haut_v = zs["haut"] + int(rc.get("marge", 20))
        s_coin = float(rc.get("echelle", 0.58))
        tete_ecran = haut_v + cote_v - float(rc.get("chevauche", 20))
        y_c = tete_ecran - (tete_y - decalage / H) * H * s_coin
        menton_ecran = y_c + (menton_y - decalage / H) * H * s_coin
        st["centre_y"] = round(min(H - zs["bas"] - 55, menton_ecran + 85))
        coin = {"s": s_coin, "y": round(y_c, 1), "yeux": round(yeux - decalage / H, 4),
                "centre": round(L * (1 - s_coin) / 2, 1), "place": 0, "carte": 0,
                "reglages": {**rc, "cote": "centre", "alterner": False},
                "vitrine": {"x": round((L - cote_v) / 2), "y": haut_v, "cote": cote_v}}
    elif en_coin:
        rc = plan.get("coin", {})
        s_coin = float(rc.get("echelle", 0.62))
        large_c, haut_c = fmt["largeur"] * s_coin, H * s_coin
        hors = float(rc.get("hors_ecran", 0.12))
        y_c = H - haut_c + float(rc.get("descente", 0))
        tete_ecran = y_c + (tete_y - decalage / H) * haut_c
        st["centre_y"] = round(min(st["centre_y"], tete_ecran - 115))
        coin = {"s": s_coin, "y": round(y_c, 1), "yeux": round(yeux - decalage / H, 4),
                "droite": round(fmt["largeur"] - large_c * (1 - hors), 1), "gauche": round(-large_c * hors, 1),
                "place": round(st["centre_y"] - 85 - (zs["haut"] + 30)),
                "carte": round(st["centre_y"] - 95 - (zs["haut"] + 20)), "reglages": rc}

    def mise_en_scene(element: dict) -> dict:
        """Quand la personne reste DEVANT un bloc ou un plan, elle rétrécit vers le bas et ce qui est
        derrière elle occupe la place libérée au-dessus de sa tête. "visage_y" sur l'élément : la
        hauteur des yeux à ce moment-là, si elle a bougé."""
        bouge = float(element.get("visage_y", yeux)) - yeux
        tete_px, menton_px = (tete_y + bouge) * H, (menton_y + bouge) * H
        # A. Cadrage normal : le menton se pose juste au-dessus des sous-titres, qui ne bougent pas.
        echelle = min(0.9, (H - (st["centre_y"] - 65)) / (H - menton_px))
        haut_tete = H - (H - tete_px) * echelle
        place, centre = haut_tete - 30 - (zs["haut"] + 30), None   # la place libre au-dessus des cheveux
        if place < 0.64 * normale - 100:
            # B. Visage en gros plan : il faut rétrécir bien plus pour libérer de la place. Les
            # sous-titres montent alors entre l'animation et le haut de la tête.
            place = 0.64 * normale
            centre = round(zs["haut"] + 30 + place + 140)
            haut_tete = centre + 145
            echelle = (H - haut_tete) / (H - tete_px)
        return {"echelle": round(max(0.35, echelle), 3), "tete": haut_tete, "hauteur": round(place), "centre": centre}

    def mise_en_cadre(element: dict) -> dict:
        """La personne dans un cadre arrondi en bas de l'écran, l'animation au-dessus (sans détourage).
        Cadrage normal : un grand cadre, la tête en haut, les sous-titres sur le buste comme d'habitude.
        Visage en gros plan : un cadre plus petit que le visage remplit, les sous-titres juste au-dessus."""
        L = fmt["largeur"]
        bouge = float(element.get("visage_y", yeux)) - yeux
        tete_px, menton_px = (tete_y + bouge) * H, (menton_y + bouge) * H
        tete_h = menton_px - tete_px
        bas = H - zs["bas"] + 60                      # le bas du cadre : il mord à peine sur la bande de l'interface
        gros_plan = tete_h > 0.5 * L
        if gros_plan:
            large, haut_c = 450, 560
            s = max(large / L, 0.75 * haut_c / tete_h)
            marge = (haut_c - tete_h * s) / 2         # la tête au milieu du cadre
        else:
            large, haut_c = 620, 620
            s = min(1.0, max(large / L, 0.44 * haut_c / tete_h))
            marge = 0.09 * haut_c                     # la tête en haut, le buste dessous
        haut = bas - haut_c
        # la partie de l'image montrée dans le cadre (en pixels de l'image), sans sortir de l'image
        image_haut, image_bas = max(0, decalage), H + min(0, decalage) - (110 if decalage else 0)
        vue_haut = min(max(tete_px - marge / s, image_haut), max(image_haut, image_bas - haut_c / s))
        cote = (L - large / s) / 2
        if gros_plan:
            centre = round(haut - 90)
            place = centre - 100 - (zs["haut"] + 30)
        else:
            menton_ecran = haut + (menton_px - vue_haut) * s
            centre = round(min(max(st["centre_y"], menton_ecran + 80), bas - 85))
            centre = None if centre == st["centre_y"] else centre
            place = haut - 40 - (zs["haut"] + 30)
        return {"hauteur": round(place), "centre": centre, "s": round(s, 4),
                "y": round(haut - H - (vue_haut - H) * s, 1),     # #prise rétrécit depuis son bord bas
                "clip": f"inset({vue_haut:.1f}px {cote:.1f}px {H - vue_haut - haut_c / s:.1f}px {cote:.1f}px round {52 / s:.1f}px)",
                "rect": (round((L - large) / 2), round(haut), large, haut_c)}

    # ----- Les passages « en cadre » : un par bloc plein écran quand la mise en scène est "cadre", et un
    # par plan de coupe en carte quand le visage est en gros plan (rétrécie comme d'habitude sous la
    # carte, la personne aurait la carte sur les yeux). Deux fenêtres qui se suivent de près partagent
    # le même passage : le cadre reste en place.
    gros_plan = (menton_y - tete_y) * H > 0.5 * fmt["largeur"]
    carte_bas = zs["haut"] + 20 + 660          # le bas d'une carte au-dessus du cadre (elle fait 660 px de haut)
    scenes, fenetres, cartes_cadre = {}, [], set()
    if blocs_cadre:
        for k, b in enumerate(plan.get("blocs", []), 1):
            fiche = bibliotheque.BLOCS.get(b.get("bloc"))
            if fiche and fiche[1] == "plein":
                d = T(b["de"])
                scenes["bloc", k] = g = mise_en_cadre(b)
                fenetres.append((d, min(T(b["a"], fin=True) if "a" in b else d + fiche[2], total), g, g["centre"]))
    if gros_plan and a_roll.exists() and not detourage and not coin:
        for k, b in enumerate(plan.get("broll", []), 1):
            if b.get("mode", "plein") == "carte":
                cartes_cadre.add(k)   # les sous-titres se posent sur le bas de la carte
                # + 0,5 s : la personne ne reprend tout l'écran qu'une fois la carte partie
                fenetres.append((T(b["de"]), min(T(b["a"], fin=True) + 0.5, total), mise_en_cadre(b), carte_bas - 95))
    if cartes_cadre and not blocs_cadre:
        # animations en plein écran : la personne doit avoir repris tout l'écran avant qu'un bloc la couvre
        for k in cartes_cadre:
            fin_carte = T(plan["broll"][k - 1]["a"], fin=True)
            for b in plan.get("blocs", []):
                fiche = bibliotheque.BLOCS.get(b.get("bloc"))
                if fiche and fiche[1] == "plein" and fin_carte - 0.05 < T(b["de"]) < fin_carte + 0.65:
                    sys.exit(f"plan.json : le plan de coupe n° {k} (carte) finit à {fin_carte:.1f} s, trop près du bloc "
                             f"qui commence à {T(b['de']):.1f} s. Laisse 0,7 s entre les deux, ou passe en mise en scène \"cadre\".")
    cadres, zones_st = [], []
    for d, f, g, centre in sorted(fenetres, key=lambda x: x[0]):
        if cadres and d - cadres[-1]["f"] < 0.8:
            cadres[-1]["f"] = round(max(f, cadres[-1]["f"]), 3)
            zones_st[-1]["f"] = d + 0.3        # pas de retour à la place habituelle entre les deux
            zones_st[-1]["suite"] = True
        else:
            cadres.append({"d": round(d, 3), "f": round(f, 3), "s": g["s"], "y": g["y"], "clip": g["clip"],
                           "rect": g["rect"], "bord": f"cadre-bord-{len(cadres) + 1}"})
        zones_st.append({"d": d, "f": f, "centre": centre})
    for w in cadres:
        w["reste"] = w["f"] >= total - 0.05   # jusqu'à la dernière image : la personne ne reprend pas sa place
    for z in zones_st:
        z["suite"] = z.get("suite") or z["f"] >= total - 0.05

    # ----- Les passages où la personne reste devant quelque chose (blocs plein écran, plans « derriere »)
    devant = []
    for k, b in enumerate(plan.get("blocs", []), 1):
        fiche = bibliotheque.BLOCS.get(b.get("bloc"))
        if fiche and blocs_derriere and fiche[1] == "plein":
            d = T(b["de"])
            scenes["bloc", k] = mise_en_scene(b)
            devant.append((d, min(T(b["a"], fin=True) if "a" in b else d + fiche[2], total), "bloc", scenes["bloc", k]))
    for k, b in enumerate(plan.get("broll", []), 1):
        if b.get("mode") == "derriere":
            if not detourage:
                sys.exit('plan.json : un plan de coupe en mode "derriere" demande "detourage" dans le plan.')
            scenes["plan", k] = mise_en_scene(b)
            devant.append((T(b["de"]), T(b["a"], fin=True), "plan", scenes["plan", k]))
    passages = []
    for d, f, genre, scene_ in sorted(devant, key=lambda x: x[0]):
        if passages and genre == "plan" and passages[-1]["genre"] == "plan" and d - passages[-1]["f"] <= 0.06:
            passages[-1]["f"] = round(f, 3)  # des plans qui se suivent sans trou : un seul passage
            continue
        if passages and d - passages[-1]["f"] < 0.8:
            sys.exit(f"plan.json : à {d:.1f} s, laisse au moins 0,8 s après le passage précédent où la personne "
                     "est devant (bloc et plans « derriere » ne se collent pas : elle doit reprendre sa place).")
        passages.append({"d": round(d, 3), "f": round(f, 3), "genre": genre, "echelle": scene_["echelle"],
                         "tete": scene_["tete"], "centre": scene_["centre"]})

    def centre_sous_titres(t: float):
        """Le milieu des sous-titres à l'instant t : remonté quand la personne, en gros plan, est rétrécie."""
        return next((p["centre"] for p in passages + zones_st
                     if p["centre"] and p["d"] + 0.3 <= t < p["f"] - (0 if p.get("suite") else 0.5)), None)

    # ----- Carton de fin
    fin, bloc_fin = None, ""
    cf = plan.get("carton_fin", {})
    # Le carton de fin affiche le mot-clé ; le plan peut le remplacer ("mot"), ainsi que la phrase du
    # dessus ("verbe") et celle du dessous ("suite") : « Projet / N°2114 / Lien dans la bio ».
    mot_fin = (cf.get("mot") or mot_cle) if isinstance(cf, dict) else mot_cle
    if mot_fin and cf is not False:
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
        taille = 150 if len(mot_fin) <= 6 else 120 if len(mot_fin) <= 9 else 92
        logo = charte.get("logo")
        if logo and (RACINE / logo).exists():
            shutil.copyfile(RACINE / logo, dossier / "assets" / Path(logo).name)
            marque = f'<img class="fin__logo" src="assets/{e(Path(logo).name)}" alt="">'
        else:
            marque = f'<span class="fin__marque">{signature}</span>'
        # « *Lien dans la bio* » : la partie entre astérisques ressort (habillage.css, .fin__suite em)
        # (sans astérisques, « lien dans la bio » / « dans ma bio » ressort d'office : c'est l'action à faire)
        suite_brute = cf.get('suite') or variante['suite']
        if "*" not in suite_brute:
            suite_brute = re.sub(r"((?:le )?lien (?:est )?dans (?:la|ma) bio)", r"*\1*", suite_brute, flags=re.I)
        suite_fin = re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(typo(suite_brute)))
        bloc_fin = f"""
    <div id="fin" class="fin"{f' style="top:{(zs["haut"] + coin["partage"]["couture"]) // 2 - 190 if en_partage else zs["haut"] + 40}px;bottom:auto"' if coin else ''}><div class="fin__fond">
      <span class="fin__verbe">{e(typo(cf.get('verbe') or variante['verbe']))}</span>
      <span id="fin-mot" class="fin__mot" style="font-size:{taille}px">{e(typo(mot_fin))}</span>
      <span class="fin__suite">{suite_fin}</span>
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
        regles = [f'font-size:{round(st["taille"] * p["echelle"])}px'] if p["echelle"] < 1 else []
        milieu = (p["d"] + p["f"]) / 2
        if centre_sous_titres(milieu):
            regles.append(f'top:{centre_sous_titres(milieu) - 170}px')
        style = f' style="{";".join(regles)}"' if regles else ""
        bloc_st += (f'\n    <div id="{p["id"]}" class="st{" st--majuscules" if charte.get("majuscules") or st.get("bandeau") else ""}'
                    f'{" st--bandeau" if st.get("bandeau") else ""}"{style}>'
                    f'<span class="st__ligne">{spans}</span></div>')
    calque(dossier, "sous-titres", fmt, bloc_st, gabarit("sous-titres.css"), gabarit("sous-titres.js", {
        "duree": total, "apparition": st["apparition"], "motEnCours": st["mot_en_cours"],
        "accent": c["accent"], "accentVide": dv["accent_vide"], "accentClair": c["accent_clair"], "blanc": c["blanc"],
        "surAccent": dv["sur_accent"], "contour": c["nuit"], "contourActif": dv["contour_actif"],
        "repos": "rgba(255, 255, 255, 0.62)" if st.get("bandeau") else c["blanc"],
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
    # Fenêtres des plans et des blocs plein écran : pour qu'aucune image ne tombe entre deux contenus
    fen_plans = [(T(x["de"]), T(x["a"], fin=True), x.get("mode", "plein")) for x in plan.get("broll", [])]
    fen_blocs = []
    for x in plan.get("blocs", []):
        fiche = bibliotheque.BLOCS.get(x.get("bloc"))
        if fiche and fiche[1] == "plein":
            dx = T(x["de"])
            fen_blocs.append((dx, min(T(x["a"], fin=True) if "a" in x else dx + fiche[2], total)))
    for k, b in enumerate([] if en_vitrine or en_partage else plan.get("broll", []), 1):
        d, f = T(b["de"]), T(b["a"], fin=True)
        # Un plan plein écran suivi bout à bout d'un autre (ou, en coin, d'un bloc qui monte par-dessus)
        # reste un peu plus longtemps dessous : la première image du suivant n'est jamais un trou.
        reste = 0.0
        if b.get("mode", "plein") == "plein":
            if any(m2 == "plein" and abs(d2 - f) < 0.1 for d2, _, m2 in fen_plans):
                reste = 0.3
            if coin and any(abs(d2 - f) < 0.15 for d2, _ in fen_blocs):
                reste = 0.5
            reste = min(reste, max(0.0, total - f))
        mode = b.get("mode", "plein")
        if mode not in ("plein", "carte", "derriere"):
            sys.exit(f"plan.json : mode de plan de coupe inconnu « {mode} » (plein, carte ou derriere).")
        # la carte fait 940 x 700 avec 10 px de bord : son image intérieure fait 920 x 680
        cadre = (920, 680) if mode == "carte" else (fmt["largeur"], fmt["hauteur"])
        src = preparer_media(b["fichier"], dossier, f"broll-{k}", float(b.get("debut", 0)), f - d + reste, cadre,
                             float(b.get("ancre_x", 0.5)))
        minutage = f'data-start="{round(d, 3)}" data-duration="{round(f - d + reste, 3)}" data-track-index="1"'
        if Path(src).suffix in IMAGES:
            media = f'<img id="broll-{k}-image" class="clip" src="{e(src)}" alt="" {minutage}>'
        else:
            media = f'<video id="broll-{k}-video" src="{e(src)}" {minutage} muted playsinline></video>'
        # "cadre" : la personne est déjà dans son cadre sous la carte, inutile de la rétrécir en plus
        brolls.append({"id": f"broll-{k}", "d": round(d, 3), "f": round(f, 3), "mode": mode, "cadre": k in cartes_cadre or bool(coin),
                       # "zoom": false : pas de lent zoom arrière sur l'image (une maquette 3D bouge déjà)
                       "zoom": b.get("zoom", True), "cache": round(f + reste, 3)})
        # Deux plans de même mode bout à bout : on passe de l'un à l'autre en coupe franche, sans sortie ni entrée animées
        if mode in ("carte", "plein") and len(brolls) > 1 and brolls[-2]["mode"] == mode and abs(brolls[-2]["f"] - d) < 0.1:
            brolls[-2]["suite"] = True
            brolls[-1]["apres"] = True
        if mode == "carte" and f - d < 1.2:
            sys.exit(f"plan.json : le plan de coupe n° {k} en carte dure {f - d:.1f} s, il lui faut au moins 1,2 s.")
        petite = ' style="height:660px"' if k in cartes_cadre else f' style="height:{coin["carte"]}px"' if coin and mode == "carte" else ""
        # Légende posée sur l'image (ce qu'on montre, un prix entre *astérisques* en couleur) et petite
        # mention dans l'autre coin (« Illustration 3D », « Extrait : @compte »)
        dessus = ""
        if b.get("legende"):
            texte = re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(typo(b["legende"])))
            dessus += f'<span class="broll__legende">{texte}</span>'
        if b.get("mention"):
            dessus += f'<span class="broll__mention">{e(typo(b["mention"]))}</span>'
        bloc_broll += (f'\n      <div id="broll-{k}" class="broll broll--{mode}"{petite}>'
                       f'<div class="broll__cadre">{media}</div>{dessus}</div>')

    # ----- La vitrine : les plans de coupe passent l'un après l'autre dans le carré du haut, bout à bout
    # (le carré n'est jamais vide). Chaque plan reste un instant sous le suivant, le temps du fondu.
    # Sur le bord du haut, l'onglet ("titre") ; dedans, en haut à gauche, la légende du plan (la pièce
    # et son budget) ; le long du bord gauche, la mention (« Illustration 3D »).
    vitrine = None
    if en_vitrine:
        v, rv = coin["vitrine"], coin["reglages"]
        plans_v = plan.get("broll", [])
        if not plans_v:
            sys.exit("plan.json : la vitrine montre les plans de coupe (\"broll\") : il en faut au moins un.")
        bornes = [(T(b["de"]), T(b["a"], fin=True)) for b in plans_v]
        items, dedans, legendes = [], "", ""
        for k, (b, (d, f)) in enumerate(zip(plans_v, bornes), 1):
            if k > 1 and abs(d - bornes[k - 2][1]) > 0.1:
                sys.exit(f"plan.json : en vitrine, les plans se suivent bout à bout (le n° {k} commence à {d:.2f} s, "
                         f"le précédent finit à {bornes[k - 2][1]:.2f} s) : le carré n'est jamais vide.")
            reste = min(0.35 if k < len(plans_v) else 0.0, max(0.0, total - f))
            src = preparer_media(b["fichier"], dossier, f"vitrine-{k}", float(b.get("debut", 0)), f - d + reste,
                                 (v["cote"], v["cote"]), float(b.get("ancre_x", 0.5)), float(b.get("ancre_y", 0.5)),
                                 float(b.get("recul", 0)))
            minutage = f'data-start="{round(d, 3)}" data-duration="{round(f - d + reste, 3)}" data-track-index="1"'
            media = (f'<img id="vitrine-{k}-image" class="clip" src="{e(src)}" alt="" {minutage}>' if Path(src).suffix in IMAGES
                     else f'<video id="vitrine-{k}-video" src="{e(src)}" {minutage} muted playsinline></video>')
            dedans += f'<div id="vitrine-{k}" class="vitrine__plan">{media}</div>'
            item = {"id": f"vitrine-{k}", "d": round(d, 3), "f": round(f, 3), "cache": round(f + reste, 3)}
            if b.get("legende"):
                if items and items[-1].get("texte") == b["legende"]:
                    item["legende"] = items[-1]["legende"]   # même légende que le plan d'avant : elle reste
                else:
                    texte = re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(typo(b["legende"])))
                    legendes += f'<span id="vitrine-{k}-legende" class="vitrine__legende">{texte}</span>'
                    item["legende"] = f"vitrine-{k}-legende"
                item["texte"] = b["legende"]
            items.append(item)
        titre = re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(typo(rv.get("titre", ""))))
        titre = (f'<div id="vitrine-onglet" class="vitrine__onglet"><span id="vitrine-point" class="vitrine__point"></span>'
                 f'<span>{titre}</span></div>') if titre else ""
        mention = f'<span class="vitrine__mention">{e(typo(rv["mention"]))}</span>' if rv.get("mention") else ""
        coins_v = "".join(f'<span class="vitrine__coin vitrine__coin--{c}"></span>' for c in ("hg", "hd", "bg", "bd"))
        bloc_broll = (f'\n      <div id="vitrine" class="vitrine" style="left:{v["x"]}px;top:{v["y"]}px;'
                      f'width:{v["cote"]}px;height:{v["cote"]}px">'
                      f'<div id="vitrine-plaque-2" class="vitrine__plaque vitrine__plaque--2"></div>'
                      f'<div id="vitrine-plaque-1" class="vitrine__plaque vitrine__plaque--1"></div>'
                      f'<div id="vitrine-cadre" class="vitrine__cadre">{dedans}<div class="vitrine__reflet"></div>'
                      f'<div id="vitrine-eclair" class="vitrine__eclair"></div>{legendes}</div>'
                      f'<div id="vitrine-coins" class="vitrine__coins">{coins_v}</div>{mention}{titre}</div>')
        vitrine = {"plans": [{k: x[k] for k in x if k != "texte"} for x in items],
                   "d": items[0]["d"], "f": items[-1]["f"], "reste": items[-1]["f"] >= total - 0.05}

    # ----- L'écran partagé : en haut, la barre de titre (elle change quand le "titre" d'un plan change)
    # et la carte où passent les plans bout à bout, avec la pastille du montant ("badge", en haut à
    # droite) et l'étiquette de ce qu'on voit ("legende", en bas à gauche). Les encarts ("encarts" du
    # plan : un chiffre clé) débordent du coin bas droit de la carte, et leur nombre monte jusqu'à sa valeur.
    partage = None
    if en_partage:
        g, rp = coin["partage"], coin["reglages"]
        plans_p = plan.get("broll", [])
        if not plans_p:
            sys.exit("plan.json : l'écran partagé montre les plans de coupe (\"broll\") : il en faut au moins un.")
        ecran = (g["largeur"] - 20, g["carte_h"] - 80)      # la vidéo dans la carte (sous son en-tête)
        bornes = [(T(b["de"]), T(b["a"], fin=True)) for b in plans_p]
        items, titres, dedans, dessus, en_titre = [], [], "", "", ""
        for k, (b, (d, f)) in enumerate(zip(plans_p, bornes), 1):
            if k > 1 and abs(d - bornes[k - 2][1]) > 0.1:
                sys.exit(f"plan.json : en partage, les plans se suivent bout à bout (le n° {k} commence à {d:.2f} s, "
                         f"le précédent finit à {bornes[k - 2][1]:.2f} s) : la carte n'est jamais vide.")
            reste = min(0.35 if k < len(plans_p) else 0.0, max(0.0, total - f))
            src = preparer_media(b["fichier"], dossier, f"partage-{k}", float(b.get("debut", 0)), f - d + reste, ecran,
                                 float(b.get("ancre_x", 0.5)), float(b.get("ancre_y", 0.5)), float(b.get("recul", 0)),
                                 bool(b.get("entier", False)))
            minutage = f'data-start="{round(d, 3)}" data-duration="{round(f - d + reste, 3)}" data-track-index="1"'
            media = (f'<img id="partage-{k}-image" class="clip" src="{e(src)}" alt="" {minutage}>' if Path(src).suffix in IMAGES
                     else f'<video id="partage-{k}-video" src="{e(src)}" {minutage} muted playsinline></video>')
            dedans += f'<div id="partage-{k}" class="partage__plan">{media}</div>'
            item = {"id": f"partage-{k}", "d": round(d, 3), "f": round(f, 3), "cache": round(f + reste, 3)}
            for cle, classe in (("badge", "partage__badge"), ("legende", "partage__legende")):
                if not b.get(cle):
                    continue
                if items and items[-1].get(cle + "_texte") == b[cle]:
                    item[cle] = items[-1][cle]      # le même que sur le plan d'avant : il reste en place
                else:
                    texte = re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(typo(b[cle])))
                    dessus += f'<span id="partage-{k}-{cle}" class="{classe}">{texte}</span>'
                    item[cle] = f"partage-{k}-{cle}"
                item[cle + "_texte"] = b[cle]
            titre = b.get("titre") or (titres[-1]["texte"] if titres else "")
            if titre and (not titres or titres[-1]["texte"] != titre):
                n = len(titre.replace("*", ""))
                taille = min(46, int((g["largeur"] - 150) / (0.56 * max(n, 1))))
                texte = re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(typo(titre)))
                en_titre += (f'<span id="partage-titre-{len(titres) + 1}" class="partage-titre__texte" '
                             f'style="font-size:{taille}px"><span>{texte}</span></span>')   # (span : garde les espaces en flex)
                titres.append({"id": f"partage-titre-{len(titres) + 1}", "d": round(d, 3), "texte": titre})
            items.append(item)
        fin_p = items[-1]["f"]
        for k, x in enumerate(titres):
            x["f"] = titres[k + 1]["d"] if k + 1 < len(titres) else fin_p
        encarts, html_encarts = [], ""
        for k, x in enumerate(plan.get("encarts", []), 1):
            d, f = T(x["de"]), min(T(x["a"], fin=True) if "a" in x else fin_p, fin_p)
            valeur = typo(x["valeur"])
            seul = re.fullmatch(r"(\D*?)(\d[\d\s]*\d|\d)(\D*)", valeur)
            encart = {"id": f"encart-{k}", "d": round(d, 3), "f": round(f, 3), "avec_carte": f >= fin_p - 0.05}
            if seul and int(re.sub(r"\D", "", seul.group(2))) >= 10:
                encart["compteur"] = {"avant": seul.group(1), "valeur": int(re.sub(r"\D", "", seul.group(2))),
                                      "apres": seul.group(3)}
            encarts.append(encart)
            detail = f'<span class="encart__detail">{e(typo(x["detail"]))}</span>' if x.get("detail") else ""
            html_encarts += (f'\n      <div id="encart-{k}" class="encart" style="right:{g["x"] - 34}px;'
                             f'bottom:{fmt["hauteur"] - g["carte_y"] - g["carte_h"] - 10}px">'
                             f'<span class="encart__titre">{e(typo(x.get("titre", "")))}</span>'
                             f'<span id="encart-{k}-valeur" class="encart__valeur">{e(valeur)}</span>{detail}</div>')
        maison = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 11.2 12 4l8.5 7.2V20a1 1 0 0 1-1 1h-5v-6h-5v6'
                  'h-5a1 1 0 0 1-1-1z" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/></svg>')
        mention = f'<span class="partage-carte__mention">{e(typo(rp["mention"]))}</span>' if rp.get("mention") else ""
        bloc_broll = (f'\n      <div id="partage-haut" class="partage-haut" style="height:{g["couture"]}px"></div>'
                      f'\n      <div id="partage-titre" class="partage-titre" style="left:{g["x"]}px;top:{g["titre_y"]}px;'
                      f'width:{g["largeur"]}px;height:{g["titre_h"]}px"><span id="partage-icone" class="partage-titre__icone">'
                      f'{maison}</span><span class="partage-titre__textes">{en_titre}</span></div>'
                      f'\n      <div id="partage-carte" class="partage-carte" style="left:{g["x"]}px;top:{g["carte_y"]}px;'
                      f'width:{g["largeur"]}px;height:{g["carte_h"]}px"><div class="partage-carte__entete">'
                      f'<span id="partage-point" class="partage-carte__point"></span>'
                      f'<span class="partage-carte__nom">{e(typo(rp.get("entete", "")))}</span>{mention}</div>'
                      f'<div id="partage-ecran" class="partage-carte__ecran">{dedans}{dessus}</div></div>'
                      f'{html_encarts}'
                      f'\n      <div class="partage-couture" style="top:{g["couture"] - 2}px"></div>')
        partage = {"plans": [{k: x[k] for k in x if not k.endswith("_texte")} for x in items],
                   "titres": [{k: x[k] for k in x if k != "texte"} for x in titres], "encarts": encarts,
                   "d": items[0]["d"], "f": fin_p, "reste": fin_p >= total - 0.05}

    # ----- La prise. Si le visage est trop bas dans l'image, on remonte l'image (rythme.decalage_y) :
    # la bande vide du bas tombe sous l'interface des réseaux et se fond dans le fond de l'univers.
    # (écran partagé, vraie vidéo : l'image descend pour poser les yeux dans le bas de l'écran)
    dy = coin["pousse"] if coin and coin.get("video") else decalage
    decale = f'<div class="decale{" decale--fondu" if dy < 0 else ""}" style="transform:translateY({dy}px)">'
    if a_roll.exists():
        flou = ' class="plan--flou"' if detourage and fond == "flou" else ""
        prise = (f'<div id="plan"{flou}>{decale}<video id="a-roll" src="assets/a-roll.mp4" data-start="0" '
                 f'data-duration="{total}" data-track-index="0" data-has-audio="true" playsinline></video></div></div>')
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
        if coin and mode == "plein" and any(abs(d2 - f) < 0.15 for d2, _, _ in fen_plans):
            f = min(f + 0.4, total)       # il remonte par-dessus le plan suivant, déjà là
        if f - d < 1.5:
            sys.exit(f"plan.json : le bloc « {genre} » n° {k} dure {f - d:.1f} s, il lui faut au moins 1,5 s.")
        contexte = {"id": f"bloc-{k}", "debut": d, "duree": round(f - d, 3), "T": T, "typo": typo,
                    # en coin, l'animation tient au-dessus des sous-titres, la personne reste devant
                    "devant": scenes.get(("bloc", k)) or ({"hauteur": coin["place"]} if coin and mode == "plein" else None),
                    "mot_cle": mot_cle, "marque": sig,
                    "media": lambda fichier, nom_media: preparer_media(fichier, dossier, nom_media, 0, 0)}
        balises, infos = fabrique(b, contexte)
        place_bloc = contexte["devant"]["hauteur"] if contexte["devant"] else 0   # 0 : le bloc a tout l'écran
        # un bloc qui va jusqu'à la dernière image y reste : la vidéo se termine sur lui, sans sortie
        css, js = code_bloc(genre, {**infos, "id": contexte["id"], "duree": contexte["duree"], "place": place_bloc,
                                    "reste": f >= total - 0.05})
        calque(dossier, contexte["id"], fmt, balises, css, js, f"montage/blocs/{genre}.*")
        hotes_blocs += hote(contexte["id"], 5, d, f - d, f' class="bloc bloc--{mode}"')
        fenetres_blocs.append((d, f))

    # Plan de coupe en carte : la prise rétrécit vers le bas, le menton se pose au-dessus des sous-titres.
    reduit = round(min(0.86, max(0.45, (H - (st["centre_y"] - 115)) / (H - menton_y * H))), 3)

    # ----- La personne détourée : posée au-dessus des blocs, pour que le décor et les animations
    # passent derrière elle. On ne la découpe que là où c'est utile (c'est le calcul le plus long).
    ips, fond_html, mots_html, personne, mots_derriere = fmt["ips"], "", "", "", []
    if detourage:
        if fond == "univers":
            fond_html = '\n      <div id="fond-univers" class="fond-univers"></div>'
        for k, m in enumerate(det.get("mots_derriere", []), 1):
            d, f = T(m["de"]), T(m["a"], fin=True) if "a" in m else T(m["de"]) + 2.5
            texte = typo(m["texte"])
            taille = min(420, int(980 / (0.74 * max(len(texte), 2))))  # des capitales : larges
            # le bas du mot se glisse derrière la tête : plus bas quand la personne est rétrécie
            passage = next((p for p in passages if p["d"] - 0.1 <= d and f <= p["f"] + 0.1), None)
            if passage and passage["centre"]:   # gros plan : les sous-titres sont au-dessus de la tête, le mot au-dessus d'eux
                haut = round(passage["centre"] - 120 - taille)
            else:
                haut = round((passage["tete"] if passage else tete_y * H) - taille * 0.7)
            haut = max(haut, zs["haut"] + 20)
            mots_derriere.append({"id": f"derriere-{k}", "d": round(d, 3), "f": round(f, 3)})
            mots_html += (f'\n      <div id="derriere-{k}" class="derriere" style="top:{haut}px"><span class="derriere__mot" '
                          f'style="font-size:{taille}px">{e(texte)}</span></div>')
        if fond in ("flou", "univers"):
            besoins = [(0.0, total)]
        else:  # décor d'origine : seulement là où quelque chose passe derrière elle
            besoins = []
            for d, f in sorted([(p["d"] - 0.25, p["f"] + 0.25) for p in passages]
                               + [(m["d"] - 0.25, m["f"] + 0.25) for m in mots_derriere]):
                d, f = max(0.0, int(d * ips) / ips), min(total, -(-f * ips // 1) / ips)
                if besoins and d <= besoins[-1][1]:
                    besoins[-1] = (besoins[-1][0], max(besoins[-1][1], f))
                else:
                    besoins.append((d, f))
        videos = ""
        for k, (d, f) in enumerate(besoins, 1):
            src = decouper_personne(dossier, a_roll, d, f, total)
            videos += (f'<video id="detoure-{k}" src="{src}" data-start="{round(d, 3)}" data-duration="{round(f - d, 3)}" '
                       f'data-track-index="0" muted playsinline></video>')
        personne = (f'\n      <div id="personne"><div id="plan-detoure">'
                    f'<div class="decale" style="transform:translateY({decalage}px)">{videos}</div></div></div>')

    if coin and not coin.get("video"):
        # La personne détourée sur toute la vidéo, le décor remplacé par le fond de l'univers. Elle
        # change de côté quand le contenu change (4 s d'écart au moins), sauf "alterner": false.
        fond_html = '\n      <div id="fond-univers" class="fond-univers"></div>'
        src = personne_entiere(dossier, a_roll, total)
        # (écran partagé : rien de la personne au-dessus de la couture ; la découpe suit ses zooms)
        coupe = f' style="clip-path:inset({coin["coupe"]}px 0 0 0)"' if partage else ""
        personne = (f'\n      <div id="personne" class="personne--coin" data-cote="{coin["reglages"].get("cote", "droite")}"{coupe}>'
                    f'<div id="plan-detoure"><video id="detoure-1" src="{src}" data-start="0" data-duration="{total}" '
                    f'data-track-index="0" muted playsinline></video></div></div>')
        cote = coin["reglages"].get("cote", "droite")
        cotes = [{"t": 0.0, "cote": cote, "x": coin[cote]}]
        changements = sorted({round(T(b["de"]), 3) for b in plan.get("blocs", [])
                              if bibliotheque.BLOCS.get(b.get("bloc"), (None, ""))[1] == "plein"} | {x["d"] for x in brolls})
        if coin["reglages"].get("alterner", True):
            for t in changements:
                if t - cotes[-1]["t"] >= 4 and t < total - 1:
                    cote = "gauche" if cote == "droite" else "droite"
                    cotes.append({"t": t, "cote": cote, "x": coin[cote]})
        coin["cotes"] = cotes

    bords = "".join(f'\n      <div id="{w["bord"]}" class="cadre-bord" style="left:{w["rect"][0]}px;top:{w["rect"][1]}px;'
                    f'width:{w["rect"][2]}px;height:{w["rect"][3]}px"></div>' for w in cadres)
    visage_zoom = ((coin["yeux"] * H + coin["pousse"]) / H if coin.get("video") else coin["yeux"]) if coin else r["visage_y"]
    principal = {"duree": total, "visageY": round(visage_zoom, 4), "derriere": mots_derriere, "reduit": reduit,
                 "coin": {k: coin[k] for k in ("s", "y", "cotes")} if coin and not coin.get("video") else None, "vitrine": vitrine, "partage": partage,
                 "broll": brolls, "cadres": [{k: v for k, v in w.items() if k != "rect"} for w in cadres],
                 "devant": [{k: v for k, v in p.items() if k not in ("tete", "centre")} for p in passages],
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
    <div id="root"{' class="coin partage-scene"' if partage else ' class="coin vitrine-scene"' if vitrine else ' class="coin"' if coin else ''} data-composition-id="main" data-start="0" data-duration="{total}"
         data-width="{fmt['largeur']}" data-height="{fmt['hauteur']}" data-fps="{fmt['ips']}">
      <div class="fond-scene"></div>
      <div id="prise">{prise}{fond_html}</div>{bords}{personne}{bloc_broll}{musique}{hotes_blocs}{mots_html}{hote('sous-titres', 3)}{hote('habillage', 4)}
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
    reperes = [0.0] + [round((x["d"] + x["f"]) / 2, 2) for x in cartes + brolls + mots_derriere]
    for v_ in (vitrine, partage):  # chaque plan au milieu, et juste après chaque changement de plan
        if v_:
            reperes += [round((x["d"] + x["f"]) / 2, 2) for x in v_["plans"]] + [round(x["d"] + 0.25, 2) for x in v_["plans"][1:]]
    if partage:
        reperes += [round(x["d"] + 1.2, 2) for x in partage["encarts"]]
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
