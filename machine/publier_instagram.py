"""Publie automatiquement les posts Instagram prévus maintenant (reels et images).

Remplis la colonne `url_media` du calendrier.csv avec le lien public de chaque vidéo/image
montée. À lancer toutes les 15 minutes (cron sur ton serveur, voir README).

Usage :
    python machine/publier_instagram.py            # parcourt tous les calendriers de sorties/
"""

import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from commun import RACINE

VERSION = os.getenv("META_GRAPH_VERSION", "v23.0")
DEJA_PUBLIES = RACINE / "sorties" / "publies.txt"


def api(methode: str, chemin: str, **params) -> dict:
    params["access_token"] = os.environ["META_ACCESS_TOKEN"]
    r = requests.request(methode, f"https://graph.facebook.com/{VERSION}/{chemin}",
                         data=params if methode == "POST" else None,
                         params=params if methode == "GET" else None, timeout=120)
    r.raise_for_status()
    return r.json()


def publier(url_media: str, legende: str, est_video: bool) -> str:
    ig = os.environ["INSTAGRAM_ACCOUNT_ID"]
    if est_video:
        conteneur = api("POST", f"{ig}/media", media_type="REELS", video_url=url_media, caption=legende)
        # Instagram doit d'abord télécharger et traiter la vidéo
        for _ in range(60):
            statut = api("GET", conteneur["id"], fields="status_code")["status_code"]
            if statut == "FINISHED":
                break
            if statut == "ERROR":
                raise RuntimeError("Instagram n'a pas pu traiter la vidéo")
            time.sleep(10)
    else:
        conteneur = api("POST", f"{ig}/media", image_url=url_media, caption=legende)
    return api("POST", f"{ig}/media_publish", creation_id=conteneur["id"])["id"]


def main() -> None:
    publies = set(DEJA_PUBLIES.read_text().split()) if DEJA_PUBLIES.exists() else set()
    maintenant = datetime.now()
    fichiers = sys.argv[1:] or sorted((RACINE / "sorties").glob("*/calendrier.csv"))
    posts = []
    for fichier in fichiers:
        with open(fichier, encoding="utf-8") as f:
            posts += list(csv.DictReader(f))

    for p in posts:
        cle = f"{p['date']}#{p['numero']}"
        heure_prevue = datetime.fromisoformat(f"{p['date']}T{p['heure']}")
        if p["reseau"] != "instagram" or cle in publies or heure_prevue > maintenant:
            continue
        if not p.get("url_media"):
            print(f"Post {p['numero']} en attente : pas encore de url_media")
            continue
        legende = f"{p['legende']}\n\nCommente {p['mot_cle']} et je t'envoie la ressource en DM"
        media_id = publier(p["url_media"], legende, p["format"] in ("reel", "short"))
        with open(DEJA_PUBLIES, "a") as f:
            f.write(cle + "\n")
        print(f"Post {p['numero']} publié (id {media_id})")


if __name__ == "__main__":
    main()
