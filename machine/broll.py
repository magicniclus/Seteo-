"""Plans de coupe (b-roll) : les images qu'on pose par-dessus ta prise pour relancer l'attention.

Les sources, toutes mises au format de la DA (sans son) :
    pexels    vidéos et photos libres de droits (clé gratuite PEXELS_API_KEY dans .env)
    films     vieux films tombés dans le domaine public (Internet Archive) : burlesques, muets
    planche   une planche d'images d'un film, pour repérer à la seconde près l'instant à garder
    ecran     une page web filmée en vertical (un site officiel, un simulateur, ton site)
    importer  n'importe quel fichier : plan filmé au téléphone, extrait de film, enregistrement d'écran
    banque    les ponctuations déjà prêtes (montage/ponctuations/), à réutiliser d'une vidéo à l'autre
    liste     tout ce qui est déjà disponible

Usage :
    python machine/broll.py pexels "carrelage salle de bain" -n 3
    python machine/broll.py films "seven chances keaton"            # chercher
    python machine/broll.py films --prendre SevenChances            # télécharger (une fois) dans broll/films/
    python machine/broll.py planche broll/films/SevenChances.mp4 --de 2400 --a 2520 --pas 4
    python machine/broll.py importer broll/films/SevenChances.mp4 --debut 2463.5 --duree 3 --nom course
    python machine/broll.py banque                                   # ce qu'il y a dans la banque
    python machine/broll.py banque --ajouter broll/perso/course.mp4 --idee "tout le monde veut la même chose" \
        --mots concurrence foule course --source "Seven Chances (Buster Keaton, 1925)" --droits "domaine public"
    python machine/broll.py ecran https://france-renov.gouv.fr --nom france-renov
    python machine/broll.py ecran http://localhost:3000/demandes/42 --prive --flouter ".client" "#adresse"
    python machine/broll.py liste

Les droits : Pexels et le domaine public sont libres. Un film récent ou la vidéo d'un autre compte
appartient à quelqu'un : on ne le télécharge pas d'ici, on n'insère que le fichier qu'on nous fournit
(voir le skill montage-video, « Plans de coupe »).
"""

import argparse
import datetime
import os
import re
import sys
import tempfile
from pathlib import Path

import requests
import yaml

from atelier import BROLL, ECRANS, MONTAGE, RACINE, duree, ecrire, ffmpeg, lire, normaliser_clip

BANQUE = MONTAGE / "ponctuations"     # les extraits prêts à resservir (petits, gardés dans le dépôt)
ARCHIVE = "https://archive.org"

IMAGES = {".png", ".jpg", ".jpeg", ".webp"}


def slug(texte: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texte.lower()).strip("-")[:40]


def telecharger(url: str, cible: Path) -> None:
    """Télécharge un fichier ; si la liaison coupe en route, reprend là où elle s'est arrêtée."""
    partiel = cible.with_name(cible.name + ".partiel")
    for essai in range(5):
        deja = partiel.stat().st_size if partiel.exists() else 0
        try:
            with requests.get(url, stream=True, timeout=120, headers={"Range": f"bytes={deja}-"} if deja else {}) as r:
                if r.status_code == 416:      # tout était déjà là
                    break
                r.raise_for_status()
                with open(partiel, "ab" if deja and r.status_code == 206 else "wb") as f:
                    for morceau in r.iter_content(1 << 20):
                        f.write(morceau)
            break
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
            if essai == 4:
                sys.exit(f"Le téléchargement coupe sans arrêt ({url.split('/')[2]}) : réessaie plus tard, "
                         "ou prends une autre copie du fichier.")
    partiel.replace(cible)


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
                normaliser_clip(brut, cible, 0, a.duree, (1080, 1920))
            auteur, page = x["user"]["name"], x["url"]
        ecrire(base.with_suffix(".json"), {"source": "Pexels", "auteur": auteur, "page": page,
                                           "recherche": a.recherche, "licence": "https://www.pexels.com/license/"})
        print(f"  {cible.relative_to(RACINE)}  ({auteur})")
    print("À mettre dans plan.json, clé \"broll\" (regarde les images avant de choisir).")


def films(a) -> None:
    """Vieux films d'Internet Archive. Un film américain entre dans le domaine public 95 ans après sa
    sortie (en 2026 : tout ce qui est sorti jusqu'en 1930), et la France suit la durée du pays d'origine
    pour un film américain. On ne cherche donc que jusqu'à cette année-là. Le son n'est jamais repris :
    la musique ajoutée sur un film muet, elle, a souvent un auteur."""
    limite = datetime.date.today().year - 96
    dossier = BROLL / "films"
    if a.prendre:
        r = requests.get(f"{ARCHIVE}/metadata/{a.prendre}", timeout=60)
        fiche = r.json() if r.status_code == 200 else {}
        meta = fiche.get("metadata") or {}
        if not meta:
            sys.exit(f"Film introuvable sur Internet Archive : {a.prendre}")
        annee = int(str(meta.get("year") or meta.get("date") or "9999")[:4])
        if annee > limite and not a.forcer:
            sys.exit(f"« {meta.get('title')} » date de {annee} : après {limite}, il n'est sans doute pas dans le "
                     "domaine public. Vérifie ses droits, puis relance avec --forcer si tu en es sûr.")
        videos = [x for x in fiche.get("files", []) if x["name"].lower().endswith(".mp4") and x.get("size")]
        if not videos:
            sys.exit(f"Pas de fichier MP4 pour {a.prendre} : choisis une autre copie du film.")
        # la copie la plus légère d'au moins 480 px de haut suffit pour un extrait de 3 secondes
        nettes = [x for x in videos if int(x.get("height") or 0) >= 480] or videos
        choix = min(nettes, key=lambda x: int(x["size"]))
        dossier.mkdir(parents=True, exist_ok=True)
        cible = dossier / f"{slug(a.prendre)}.mp4"
        if not cible.exists():
            print(f"Téléchargement de « {meta.get('title')} » ({int(choix['size']) / 1e6:.0f} Mo)...")
            telecharger(f"{ARCHIVE}/download/{a.prendre}/{requests.utils.quote(choix['name'])}", cible)
        ecrire(cible.with_suffix(".json"), {"source": "Internet Archive", "titre": meta.get("title"), "annee": annee,
                                            "auteur": meta.get("creator") or meta.get("director") or "",
                                            "page": f"{ARCHIVE}/details/{a.prendre}",
                                            "droits": f"domaine public (sorti en {annee})"})
        print(f"  {cible.relative_to(RACINE)}  ({duree(cible) / 60:.0f} min)")
        print("Repère l'instant : python machine/broll.py planche <fichier> --de <s> --a <s>")
        return
    if not a.recherche:
        sys.exit("Donne des mots à chercher, ou --prendre <identifiant>.")
    r = requests.get(f"{ARCHIVE}/advancedsearch.php", timeout=60, params={
        "q": f"({a.recherche}) AND mediatype:(movies) AND year:[1890 TO {limite}]",
        "fl[]": ["identifier", "title", "year", "downloads"], "sort[]": "downloads desc", "rows": a.n, "output": "json"})
    if r.status_code != 200:
        sys.exit(f"Internet Archive a répondu {r.status_code}.")
    trouves = r.json()["response"]["docs"]
    if not trouves:
        sys.exit(f"Rien trouvé pour « {a.recherche} » (films sortis jusqu'en {limite}) : essaie le titre en anglais.")
    for x in trouves:
        print(f"  {x['identifier']:<50} {x.get('year', '?')}  {str(x.get('title'))[:60]}")
    print("Pour en prendre un : python machine/broll.py films --prendre <identifiant>")


def planche(a) -> None:
    """Une planche d'images horodatées d'un passage de film : on y lit l'instant à garder."""
    source = Path(a.fichier).expanduser().resolve()
    if not source.exists():
        sys.exit(f"Fichier introuvable : {source}")
    fin = a.a if a.a is not None else duree(source)
    n = max(1, int((fin - a.de) / a.pas))
    colonnes = min(6, n)
    cible = source.with_name(f"{source.stem}-planche.jpg")
    ffmpeg("-ss", a.de, "-t", fin - a.de, "-i", source, "-frames:v", 1, "-vf",
           f"fps=1/{a.pas},scale=360:-2,drawtext=text='%{{eif\\:t+{a.de}\\:d}} s':x=8:y=8:fontsize=26:fontcolor=white:"
           f"box=1:boxcolor=black@0.7:boxborderw=6,tile={colonnes}x{-(-n // colonnes)}", "-q:v", 4, cible)
    print(f"  {cible.relative_to(RACINE) if cible.is_relative_to(RACINE) else cible}  ({n} images, une toutes les {a.pas} s)")


def banque(a) -> None:
    """La banque de ponctuations : des extraits courts (2 à 4 s) déjà coupés, chacun avec l'idée qu'il
    illustre. On y pioche d'une vidéo à l'autre au lieu de tout rechercher à chaque montage."""
    index = BANQUE / "index.yaml"
    fiches = yaml.safe_load(index.read_text(encoding="utf-8")) if index.exists() else []
    if a.ajouter:
        source = Path(a.ajouter).expanduser().resolve()
        if not source.exists():
            sys.exit(f"Fichier introuvable : {source}")
        if not (a.idee and a.source and a.droits):
            sys.exit("Pour ajouter à la banque, il faut --idee, --source et --droits (d'où vient l'extrait, et à qui il est).")
        nom = slug(a.nom or source.stem)
        BANQUE.mkdir(parents=True, exist_ok=True)
        cible = BANQUE / f"{nom}.mp4"
        # la banque est gardée dans le dépôt : des fichiers légers (960 px de large au plus, sans son)
        ffmpeg("-i", source, "-an", "-vf", "scale='min(960,iw)':-2,setsar=1,format=yuv420p", "-c:v", "libx264",
               "-crf", "22", "-preset", "slow", "-movflags", "+faststart", cible)
        fiches = [x for x in fiches if x["nom"] != nom] + [{
            "nom": nom, "fichier": f"montage/ponctuations/{nom}.mp4", "duree": round(duree(cible), 1), "idee": a.idee,
            "mots": a.mots, "source": a.source, "droits": a.droits}]
        index.write_text("# La banque de ponctuations : voir python machine/broll.py banque\n"
                         + yaml.safe_dump(fiches, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
        print(f"  {cible.relative_to(RACINE)} ajouté à la banque.")
        return
    if not fiches:
        print("La banque est vide (montage/ponctuations/).")
    for x in fiches:
        print(f"  {x['fichier']:<52} {x['duree']} s  {x['idee']}\n      mots : {', '.join(x.get('mots') or [])}"
              f"  ·  {x['source']}  ·  {x['droits']}")


def ecran(a) -> None:
    """Filme une page web en vertical, avec le même outil que machine/ecrans.py."""
    from playwright.sync_api import sync_playwright

    import ecrans
    nom = a.nom or slug(re.sub(r"^https?://(www\.)?", "", a.url))
    ecrans.DOSSIER.mkdir(exist_ok=True)
    with sync_playwright() as p:
        navigateur = p.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH") or None)
        ecrans.filmer(navigateur, {"nom": nom, "url": a.url, "cliquer": a.cliquer,
                                   "flouter": a.flouter, "prive": a.prive})
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
    trouves = sorted(x for x in [*ECRANS.glob("*.mp4"), *BANQUE.glob("*.mp4"), *BROLL.rglob("*.mp4"), *BROLL.rglob("*.jpg"),
                                 *BROLL.rglob("*.png"), *BROLL.rglob("*.webp")] if not x.stem.endswith("-planche"))
    if not trouves:
        print("Aucun plan de coupe pour l'instant (broll/ et ecrans/ sont vides).")
    for f in trouves:
        detail = "image" if f.suffix.lower() in IMAGES else f"{duree(f):.1f} s"
        credit = f.with_suffix(".json")
        auteur = f" · {lire(credit).get('auteur') or lire(credit).get('titre')} ({lire(credit)['source']})" if credit.exists() else ""
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
    fi = sous.add_parser("films", help="vieux films du domaine public (Internet Archive)")
    fi.add_argument("recherche", nargs="?")
    fi.add_argument("-n", type=int, default=8, help="nombre de résultats")
    fi.add_argument("--prendre", metavar="IDENTIFIANT", help="télécharger ce film dans broll/films/")
    fi.add_argument("--forcer", action="store_true", help="prendre un film plus récent dont tu as vérifié les droits")
    fi.set_defaults(action=films)
    pl = sous.add_parser("planche", help="images horodatées d'un passage, pour repérer l'instant à garder")
    pl.add_argument("fichier")
    pl.add_argument("--de", type=float, default=0, help="début du passage (s)")
    pl.add_argument("--a", type=float, help="fin du passage (s)")
    pl.add_argument("--pas", type=float, default=5, help="une image toutes les N secondes")
    pl.set_defaults(action=planche)
    ba = sous.add_parser("banque", help="les ponctuations prêtes à resservir")
    ba.add_argument("--ajouter", metavar="FICHIER", help="mettre cet extrait dans la banque")
    ba.add_argument("--nom")
    ba.add_argument("--idee", help="ce que l'extrait illustre, en une phrase")
    ba.add_argument("--mots", nargs="*", default=[], help="les mots qui doivent y faire penser")
    ba.add_argument("--source", help="titre, auteur, année")
    ba.add_argument("--droits", help="domaine public, Pexels, à toi, ou « appartient à ... »")
    ba.set_defaults(action=banque)
    ec = sous.add_parser("ecran", help="filmer une page web en vertical")
    ec.add_argument("url")
    ec.add_argument("--nom")
    ec.add_argument("--cliquer", nargs="*", default=[], help="textes des boutons à cliquer, dans l'ordre")
    ec.add_argument("--flouter", nargs="*", default=[], metavar="SELECTEUR",
                    help="sélecteurs CSS des zones à masquer (nom, adresse, e-mail du client...)")
    ec.add_argument("--prive", action="store_true",
                    help="masque aussi tout e-mail et tout numéro de téléphone trouvés dans la page")
    ec.set_defaults(action=ecran)
    im = sous.add_parser("importer", help="mettre un fichier à toi au bon format")
    im.add_argument("fichier")
    im.add_argument("--nom")
    im.add_argument("--debut", type=float, default=0)
    im.add_argument("--duree", type=float, default=8, help="durée gardée (s) ; l'extrait garde sa forme d'origine")
    im.set_defaults(action=importer)
    sous.add_parser("liste", help="ce qui est disponible").set_defaults(action=liste)
    a = p.parse_args()
    a.action(a)


if __name__ == "__main__":
    main()
