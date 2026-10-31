"""Trouve les vidéos qui explosent dans ta niche et réécrit leur script à ta sauce.

Utilise l'API officielle Meta « Business Discovery » (pas de scraping) : elle donne les posts
publics des comptes Instagram professionnels listés dans config/marque.yaml.

Usage :
    python machine/outliers.py
"""

import os
import statistics
from datetime import date
from typing import List

import requests
from pydantic import BaseModel

from commun import RACINE, config, generer_structure

CHAMPS = ("business_discovery.username({u}){{followers_count,media.limit(50)"
          "{{caption,like_count,comments_count,permalink,media_type,timestamp}}}}")


class Adaptation(BaseModel):
    lien_original: str
    pourquoi_ca_marche: str  # le mécanisme du hook, pas le contenu
    accroche: str
    script: List[str]  # plan par plan, avec notre expertise et nos opinions
    mot_cle: str


class Adaptations(BaseModel):
    videos: List[Adaptation]


def posts_du_compte(username: str) -> list[dict]:
    version = os.getenv("META_GRAPH_VERSION", "v23.0")
    r = requests.get(
        f"https://graph.facebook.com/{version}/{os.environ['INSTAGRAM_ACCOUNT_ID']}",
        params={"fields": CHAMPS.format(u=username), "access_token": os.environ["META_ACCESS_TOKEN"]},
        timeout=60,
    )
    if not r.ok:
        print(f"  {username} : impossible ({r.json().get('error', {}).get('message')})")
        return []
    return r.json()["business_discovery"]["media"]["data"]


def main() -> None:
    cfg = config()
    trouves = []
    for compte in cfg["comptes_a_surveiller"]:
        posts = [p for p in posts_du_compte(compte) if p.get("media_type") == "VIDEO"]
        if len(posts) < 5:
            continue
        engagement = lambda p: p.get("like_count", 0) + 3 * p.get("comments_count", 0)
        mediane = statistics.median(engagement(p) for p in posts) or 1
        for p in posts:
            ratio = engagement(p) / mediane
            if ratio >= cfg["seuil_outlier"]:
                trouves.append({**p, "compte": compte, "ratio": round(ratio, 1)})
                print(f"  outlier x{ratio:.1f} chez @{compte} : {p['permalink']}")

    if not trouves:
        print("Aucun outlier aujourd'hui.")
        return
    trouves.sort(key=lambda p: p["ratio"], reverse=True)

    liste = "\n\n".join(
        f"- {p['permalink']} (@{p['compte']}, x{p['ratio']} sa médiane)\n  Légende : {p.get('caption', '')[:600]}"
        for p in trouves[:10]
    )
    print("L'IA adapte les meilleures à Portail Habitat...")
    res = generer_structure(
        f"""Voici des vidéos qui explosent dans notre niche :\n\n{liste}\n
Pour chacune : explique le mécanisme du hook, puis écris NOTRE version : même structure et même
type d'accroche, mais notre expertise habitat, nos opinions, nos mots. Ne copie aucune phrase.
Termine par « Commente <MOT> » avec un mot-clé adapté.""",
        Adaptations,
    )

    dossier = RACINE / "sorties" / "outliers"
    dossier.mkdir(parents=True, exist_ok=True)
    md = [f"# Outliers du {date.today():%d/%m/%Y}\n"]
    for v in res.videos:
        md.append(f"\n## {v.accroche}\n\nOriginal : {v.lien_original}\n\n"
                  f"**Pourquoi ça marche :** {v.pourquoi_ca_marche}\n\n**Script :**\n")
        md.extend(f"{i}. {plan}\n" for i, plan in enumerate(v.script, 1))
        md.append(f"\n**Mot-clé :** {v.mot_cle.upper()}\n")
    fichier = dossier / f"{date.today()}.md"
    fichier.write_text("".join(md), encoding="utf-8")
    print(f"Prêt : {fichier}")


if __name__ == "__main__":
    main()
