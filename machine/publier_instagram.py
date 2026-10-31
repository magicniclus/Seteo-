"""Publie automatiquement les posts Instagram du jour via l'API officielle de Meta.

Prérequis : compte Instagram Professionnel relié à une Page Facebook + token
(voir README, étape 4). Chaque post doit avoir une image accessible en ligne :
ajoute une colonne `url_image` dans calendrier.csv (lien public vers l'image).

Usage :
    python machine/publier_instagram.py sorties/2026-11-02/calendrier.csv
"""

import csv
import os
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent


def publier(ig_id: str, token: str, version: str, url_image: str, legende: str) -> str:
    base = f"https://graph.facebook.com/{version}/{ig_id}"
    conteneur = requests.post(
        f"{base}/media",
        data={"image_url": url_image, "caption": legende, "access_token": token},
        timeout=60,
    )
    conteneur.raise_for_status()
    pub = requests.post(
        f"{base}/media_publish",
        data={"creation_id": conteneur.json()["id"], "access_token": token},
        timeout=60,
    )
    pub.raise_for_status()
    return pub.json()["id"]


def main() -> None:
    load_dotenv(RACINE / ".env")
    ig_id = os.environ["INSTAGRAM_ACCOUNT_ID"]
    token = os.environ["META_ACCESS_TOKEN"]
    version = os.getenv("META_GRAPH_VERSION", "v23.0")

    aujourd_hui = date.today().isoformat()
    with open(sys.argv[1], encoding="utf-8") as f:
        posts = [p for p in csv.DictReader(f)
                 if p["reseau"] == "instagram" and p["date"] == aujourd_hui]

    for p in posts:
        if not p.get("url_image"):
            print(f"Post {p['numero']} ignoré : pas d'url_image")
            continue
        media_id = publier(ig_id, token, version, p["url_image"], p["legende"])
        print(f"Post {p['numero']} publié (id {media_id})")


if __name__ == "__main__":
    main()
