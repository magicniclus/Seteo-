"""Génère le calendrier de contenu de la semaine + les ressources « Commente <MOT> ».

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

from pydantic import BaseModel

from commun import RACINE, config, enregistrer_ressource, generer_structure, slug


class Ressource(BaseModel):
    titre: str  # ex. « Le guide des vrais prix d'une salle de bain en 2026 »
    promesse: str  # une phrase : ce que la personne reçoit
    contenu_markdown: str  # la ressource complète, vraiment utile (guide, checklist, tableau)


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
    mot_cle: str  # UN mot à commenter, ex. DEVIS
    ressource: Ressource
    idee_visuel: str


class Calendrier(BaseModel):
    strategie_de_la_semaine: str
    lecons_tirees_des_stats: str
    posts: List[Post]


def construire_prompt(cfg: dict, stats: str | None) -> str:
    bloc_stats = (
        f"Voici les performances de nos derniers posts (CSV) :\n{stats}\n"
        "Analyse ce qui a le mieux marché (vues, abonnés gagnés, commentaires du mot-clé, "
        "inscriptions) et fais plus de ce qui marche, moins de ce qui ne marche pas."
        if stats
        else "Pas encore de statistiques : teste des formats et des accroches variés."
    )
    return f"""Prépare la semaine de contenu de {cfg['marque']}.

Cible : {cfg['cible']}
Promesse de l'inscription gratuite : {cfg['promesse_inscription']}
Thèmes possibles : {', '.join(cfg['themes'])}

{bloc_stats}

Produis {cfg['posts_par_reseau_par_semaine']} posts par réseau pour : {', '.join(cfg['reseaux'])}.
Règles :
- Adapte chaque post au réseau (Reels/TikTok/Shorts = vidéo verticale, hook fort dans les
  2 premières secondes ; LinkedIn = texte expert ; Facebook = communauté/questions).
- Chaque post apporte une vraie valeur (chiffre, astuce, erreur, avant/après).
- Chaque post a un mot-clé unique (un seul mot, en majuscules) et une ressource gratuite
  liée, vraiment utile, que la personne reçoit en échange de son inscription.
- Fin du script Instagram/Facebook : « Commente <MOT> et je t'envoie <ressource> en DM ».
  Fin TikTok/Shorts/LinkedIn : « Tape <MOT> sur le lien dans ma bio ».
- Varie les heures de publication sur les créneaux forts de chaque réseau.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", help="CSV de tes stats passées (optionnel)")
    args = parser.parse_args()

    cfg = config()
    stats = Path(args.stats).read_text(encoding="utf-8") if args.stats else None

    print("L'IA prépare la semaine de contenu...")
    cal = generer_structure(construire_prompt(cfg, stats), Calendrier)

    lundi = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
    dossier = RACINE / "sorties" / lundi.isoformat()
    dossier.mkdir(parents=True, exist_ok=True)

    lignes = []
    for i, p in enumerate(cal.posts, 1):
        mot = slug(p.mot_cle)
        enregistrer_ressource(mot, p.ressource.titre, p.ressource.promesse,
                              p.ressource.contenu_markdown)
        lignes.append({
            "numero": i,
            "date": (lundi + timedelta(days=p.jour - 1)).isoformat(),
            "heure": p.heure,
            "reseau": p.reseau,
            "format": p.format,
            "theme": p.theme,
            "mot_cle": mot.upper(),
            "accroche": p.accroche,
            "legende": f"{p.legende}\n\n{' '.join(p.hashtags)}",
            "lien_ressource": f"{cfg['url_serveur']}/ressource/{mot}?src={p.reseau}",
            "idee_visuel": p.idee_visuel,
            "script": " | ".join(p.script_ou_slides),
            "url_media": "",  # à remplir : lien public de la vidéo/image montée
        })

    (dossier / "calendrier.json").write_text(
        json.dumps(cal.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with open(dossier / "calendrier.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=lignes[0].keys())
        w.writeheader()
        w.writerows(lignes)

    md = [f"# Semaine du {lundi:%d/%m/%Y}\n", f"**Stratégie :** {cal.strategie_de_la_semaine}\n",
          f"**Leçons des stats :** {cal.lecons_tirees_des_stats}\n"]
    for l in sorted(lignes, key=lambda x: (x["date"], x["heure"])):
        md.append(f"\n## #{l['numero']} · {l['date']} {l['heure']} · {l['reseau']} · "
                  f"{l['format']} · mot-clé {l['mot_cle']}\n")
        md.append(f"**Accroche :** {l['accroche']}\n\n**Script :** {l['script']}\n")
        md.append(f"\n**Visuel :** {l['idee_visuel']}\n\n**Légende :**\n\n{l['legende']}\n")
        md.append(f"\n**Prompteur :** {cfg['url_serveur']}/prompteur/{lundi}/{l['numero']}\n")
    (dossier / "calendrier.md").write_text("".join(md), encoding="utf-8")

    print(f"{len(lignes)} posts prêts dans {dossier}")


if __name__ == "__main__":
    main()
