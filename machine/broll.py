"""Plans de coupe (b-roll) : les images qu'on pose par-dessus ta prise pour relancer l'attention.

Quatre sources, toutes mises au format de la DA (vertical 1080x1920, sans son) :
    pexels    vidéos et photos libres de droits (clé gratuite PEXELS_API_KEY dans .env)
    ecran     une page web filmée en vertical (un site officiel, un simulateur, ton site)
    importer  n'importe quel fichier à toi : plan filmé au téléphone, vidéo générée par une IA...
    liste     tout ce qui est déjà disponible

Usage :
    python machine/broll.py pexels "carrelage salle de bain" -n 3
    python machine/broll.py pexels "artisan plombier" --photos
    python machine/broll.py ecran https://france-renov.gouv.fr --nom france-renov
    python machine/broll.py importer ~/Videos/chantier.mov --debut 4 --duree 6
    python machine/broll.py liste

On n'utilise que des images dont on a les droits : pas d'extraits de films ni de vidéos
YouTube d'autres créateurs (voir CLAUDE.md, « Règles »).
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

import requests

from atelier import BROLL, ECRANS, RACINE, duree, ecrire, lire, normaliser_clip

IMAGES = {".png", ".jpg", ".jpeg", ".webp"}


def slug(texte: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texte.lower()).strip("-")[:40]


def telecharger(url: str, cible: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(cible, "wb") as f:
            for morceau in r.iter_content(1 << 20):
                f.write(morceau)


def pexels(a) -> None:
    """Doc : https://www.pexels.com/api/documentation/ (licence Pexels : usage commercial permis)."""
    cle = os.getenv("PEXELS_API_KEY")
    if not cle:
        sys.exit("Il manque PEXELS_API_KEY dans .env (clé gratuite : https://www.pexels.com/api/).")
    dossier = BROLL / "pexels"
    dossier.mkdir(parents=True, exist_ok=True)
    point = "https://api.pexels.com/v1/search" if a.photos else "https://api.pexels.com/videos/search"
    r = requests.get(point, headers={"Authorization": cle}, timeout=60,
                     params={"query": a.recherche, "orientation": "portrait", "per_page": a.n, "locale": "fr-FR"})
    if r.status_code != 200:
        sys.exit(f"Pexels a répondu {r.status_code} : {r.text[:300]}")
    resultats = r.json().get("photos" if a.photos else "videos", [])
    if not resultats:
        sys.exit(f"Rien trouvé pour « {a.recherche} » : essaie en anglais, ou un mot plus simple.")

    for x in resultats:
        base = dossier / f"{slug(a.recherche)}-{x['id']}"
        if a.photos:
            cible = base.with_suffix(".jpg")
            telecharger(x["src"]["large2x"], cible)
            auteur, page = x["photographer"], x["url"]
        else:
            # le fichier vertical le plus proche de 1920 px de haut (inutile de prendre de la 4K)
            fichiers = [f for f in x["video_files"] if f.get("height") and f.get("width") and f["height"] > f["width"]]
            if not fichiers:
                continue
            choix = min(fichiers, key=lambda f: (f["height"] < 1280, abs(f["height"] - 1920)))
            cible = base.with_suffix(".mp4")
            with tempfile.TemporaryDirectory() as tmp:
                brut = Path(tmp) / "brut.mp4"
                telecharger(choix["link"], brut)
                normaliser_clip(brut, cible, 0, a.duree)
            auteur, page = x["user"]["name"], x["url"]
        ecrire(base.with_suffix(".json"), {"source": "Pexels", "auteur": auteur, "page": page,
                                           "recherche": a.recherche, "licence": "https://www.pexels.com/license/"})
        print(f"  {cible.relative_to(RACINE)}  ({auteur})")
    print("À mettre dans plan.json, clé \"broll\" (regarde les images avant de choisir).")


def ecran(a) -> None:
    """Filme une page web en vertical, avec le même outil que machine/ecrans.py."""
    from playwright.sync_api import sync_playwright

    import ecrans
    nom = a.nom or slug(re.sub(r"^https?://(www\.)?", "", a.url))
    ecrans.DOSSIER.mkdir(exist_ok=True)
    with sync_playwright() as p:
        navigateur = p.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH") or None)
        ecrans.filmer(navigateur, {"nom": nom, "url": a.url, "cliquer": a.cliquer})
        navigateur.close()


def importer(a) -> None:
    source = Path(a.fichier).expanduser().resolve()
    if not source.exists():
        sys.exit(f"Fichier introuvable : {source}")
    dossier = BROLL / "perso"
    dossier.mkdir(parents=True, exist_ok=True)
    nom = slug(a.nom or source.stem)
    if source.suffix.lower() in IMAGES:
        cible = dossier / f"{nom}{source.suffix.lower()}"
        cible.write_bytes(source.read_bytes())
    else:
        cible = dossier / f"{nom}.mp4"
        normaliser_clip(source, cible, a.debut, a.duree)
    print(f"  {cible.relative_to(RACINE)}")


def liste(_a) -> None:
    trouves = sorted([*ECRANS.glob("*.mp4"), *BROLL.rglob("*.mp4"), *BROLL.rglob("*.jpg"),
                      *BROLL.rglob("*.png"), *BROLL.rglob("*.webp")])
    if not trouves:
        print("Aucun plan de coupe pour l'instant (broll/ et ecrans/ sont vides).")
    for f in trouves:
        detail = "image" if f.suffix.lower() in IMAGES else f"{duree(f):.1f} s"
        credit = f.with_suffix(".json")
        auteur = f" · {lire(credit)['auteur']} (Pexels)" if credit.exists() else ""
        print(f"  {str(f.relative_to(RACINE)):<60} {detail}{auteur}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = p.add_subparsers(dest="commande", required=True)
    px = sous.add_parser("pexels", help="vidéos ou photos libres de droits")
    px.add_argument("recherche")
    px.add_argument("-n", type=int, default=3, help="nombre de résultats")
    px.add_argument("--photos", action="store_true", help="des photos plutôt que des vidéos")
    px.add_argument("--duree", type=float, default=8, help="durée gardée de chaque vidéo (s)")
    px.set_defaults(action=pexels)
    ec = sous.add_parser("ecran", help="filmer une page web en vertical")
    ec.add_argument("url")
    ec.add_argument("--nom")
    ec.add_argument("--cliquer", nargs="*", default=[], help="textes des boutons à cliquer, dans l'ordre")
    ec.set_defaults(action=ecran)
    im = sous.add_parser("importer", help="mettre un fichier à toi au bon format")
    im.add_argument("fichier")
    im.add_argument("--nom")
    im.add_argument("--debut", type=float, default=0)
    im.add_argument("--duree", type=float, default=8)
    im.set_defaults(action=importer)
    sous.add_parser("liste", help="ce qui est disponible").set_defaults(action=liste)
    a = p.parse_args()
    a.action(a)


if __name__ == "__main__":
    main()
