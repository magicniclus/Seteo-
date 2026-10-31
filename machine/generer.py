"""Génère le calendrier de contenu de la semaine pour tous les réseaux.

Usage :
    python machine/generer.py                      # semaine standard
    python machine/generer.py --stats stats.csv    # l'IA apprend de tes résultats passés
"""

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import List, Literal
from urllib.parse import urlencode

import anthropic
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

RACINE = Path(__file__).resolve().parent.parent
MODELE = "claude-opus-5-5"


class Post(BaseModel):
    reseau: Literal["instagram", "tiktok", "facebook", "linkedin", "youtube_shorts"]
    jour: int  # 1 = lundi ... 7 = dimanche
    heure: str  # "HH:MM"
    format: Literal["reel", "carrousel", "image", "texte", "short"]
    theme: str
    accroche: str  # les 2 premières secondes / la première ligne
    script_ou_slides: List[str]  # plan vidéo plan par plan, ou texte de chaque slide
    legende: str
    hashtags: List[str]
    appel_a_l_action: str  # pousse vers l'inscription gratuite
    idee_visuel: str  # ce qu'il faut filmer / générer comme image


class Calendrier(BaseModel):
    strategie_de_la_semaine: str
    lecons_tirees_des_stats: str
    posts: List[Post]


def lien_suivi(url: str, reseau: str, numero: int) -> str:
    """Ajoute des UTM pour savoir quel post amène des inscrits."""
    params = {"utm_source": reseau, "utm_medium": "social", "utm_campaign": f"post{numero}"}
    return f"{url}{'&' if '?' in url else '?'}{urlencode(params)}"


def construire_prompt(cfg: dict, stats: str | None) -> str:
    bloc_stats = (
        f"Voici les performances de nos derniers posts (CSV) :\n{stats}\n"
        "Analyse ce qui a le mieux marché (vues, abonnés gagnés, clics, inscriptions) "
        "et fais plus de ce qui marche, moins de ce qui ne marche pas."
        if stats
        else "Pas encore de statistiques : teste des formats et des accroches variés."
    )
    return f"""Tu es le responsable acquisition de la marque {cfg['marque']} ({cfg['site']}).
Objectif n°1 : gagner des abonnés sur chaque réseau. Objectif n°2 : convertir ces abonnés
en inscrits gratuits sur {cfg['page_inscription']}.

Cible : {cfg['cible']}
Promesse de l'inscription gratuite : {cfg['promesse_inscription']}
Ton : {cfg['ton']}
Langue : {cfg['langue']}
Thèmes possibles : {', '.join(cfg['themes'])}

{bloc_stats}

Produis {cfg['posts_par_reseau_par_semaine']} posts par réseau pour : {', '.join(cfg['reseaux'])}.
Règles :
- Adapte vraiment chaque post au réseau (TikTok/Reels/Shorts = vidéo verticale avec accroche
  forte dans les 2 premières secondes ; LinkedIn = texte expert ; Facebook = communauté/questions).
- Chaque post doit apporter une vraie valeur (chiffre, astuce, erreur, avant/après), pas de pub.
- L'appel à l'action renvoie vers l'inscription gratuite (« lien en bio » sur Instagram/TikTok).
- Pas de fausses promesses, pas de faux chiffres : si tu cites un prix, donne une fourchette réaliste.
- Varie les heures de publication sur les créneaux forts de chaque réseau.
"""


def main() -> None:
    load_dotenv(RACINE / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", help="CSV de tes stats passées (optionnel)")
    args = parser.parse_args()

    cfg = yaml.safe_load((RACINE / "config" / "marque.yaml").read_text(encoding="utf-8"))
    stats = Path(args.stats).read_text(encoding="utf-8") if args.stats else None

    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans .env
    print("L'IA prépare la semaine de contenu...")
    reponse = client.beta.messages.parse(
        model=MODELE,
        max_tokens=64000,
        output_config={"effort": "high"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": construire_prompt(cfg, stats)}],
        output_format=Calendrier,
    )
    if reponse.stop_reason == "refusal":
        raise SystemExit("La génération a été refusée, reformule la config.")
    cal = reponse.parsed_output

    lundi = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
    dossier = RACINE / "sorties" / lundi.isoformat()
    dossier.mkdir(parents=True, exist_ok=True)

    lignes = []
    for i, p in enumerate(cal.posts, 1):
        jour = lundi + timedelta(days=p.jour - 1)
        lien = lien_suivi(cfg["page_inscription"], p.reseau, i)
        lignes.append({
            "numero": i,
            "date": jour.isoformat(),
            "heure": p.heure,
            "reseau": p.reseau,
            "format": p.format,
            "theme": p.theme,
            "accroche": p.accroche,
            "legende": f"{p.legende}\n\n{p.appel_a_l_action}\n\n{' '.join(p.hashtags)}",
            "lien_suivi": lien,
            "idee_visuel": p.idee_visuel,
            "script": " | ".join(p.script_ou_slides),
        })

    (dossier / "calendrier.json").write_text(
        json.dumps(cal.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # CSV importable dans Metricool / Buffer / Notion / Google Sheets
    with open(dossier / "calendrier.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=lignes[0].keys())
        w.writeheader()
        w.writerows(lignes)

    md = [f"# Semaine du {lundi:%d/%m/%Y}\n", f"**Stratégie :** {cal.strategie_de_la_semaine}\n",
          f"**Leçons des stats :** {cal.lecons_tirees_des_stats}\n"]
    for l in sorted(lignes, key=lambda x: (x["date"], x["heure"])):
        md.append(f"\n## {l['date']} {l['heure']} · {l['reseau']} · {l['format']}\n")
        md.append(f"**Accroche :** {l['accroche']}\n\n**Script :** {l['script']}\n")
        md.append(f"\n**Visuel :** {l['idee_visuel']}\n\n**Légende :**\n\n{l['legende']}\n")
        md.append(f"\n**Lien suivi :** {l['lien_suivi']}\n")
    (dossier / "calendrier.md").write_text("".join(md), encoding="utf-8")

    print(f"{len(lignes)} posts prêts dans {dossier}")


if __name__ == "__main__":
    main()
