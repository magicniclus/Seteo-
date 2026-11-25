"""Regarde la vidéo montée et dit ce qu'il faut corriger (étape 4 : les « yeux »).

Trois contrôles :
1. Planche-contact : une image toutes les ~2 s + la toute première image en grand.
   Claude Code les ouvre et juge lui-même (lisibilité, cadrage, DA).
2. Mesures du son : niveau moyen, crêtes, blancs restés dans le montage.
3. Critique par Gemini (si GEMINI_API_KEY est dans .env) : lui regarde la vidéo EN MOUVEMENT
   et avec le son, ce qu'une planche d'images ne montre pas (rythme, synchronisation des
   sous-titres, accroche). Il rend une note par critère et des corrections horodatées.

Résultat dans montage/projets/<id>/yeux/ : planche.jpg, premiere-image.jpg, son.json, critique.json

Et pour juger un raccord (l'arrivée d'un extrait, d'une animation) : --autour <instants> sort, pour
chaque instant, une bande de 12 images serrées (de 0,3 s avant à 1,2 s après). Rien d'autre n'est refait.

Usage :
    python machine/yeux.py 2026-11-30-3
    python machine/yeux.py 2026-11-30-3 --sans-gemini
    python machine/yeux.py 2026-11-30-3 --autour 9.0 11.4 34.2
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

from atelier import (MONTAGES, RACINE, da, duree, ecouter, ecrire, ffmpeg, identifiant, lire, projet,
                     silences_du_son)

API = "https://generativelanguage.googleapis.com"

GRILLE = """Tu es monteur senior de vidéos courtes verticales (Reels, TikTok, Shorts) en France.
Regarde cette vidéo en entier, avec le son, et critique le MONTAGE (pas le fond du propos).

Contexte de la marque :
{cerveau}

Direction artistique attendue : police {police} ; fonds sombres {nuit}, couleur d'accent {accent} ;
sous-titres de {mots_max} mots maximum, le mot prononcé passe sur une pastille de la couleur d'accent ;
rien d'important dans les {haut} px du haut ni les {bas} px du bas (interface des réseaux).
{script}
Note chaque critère de 0 à 10 :
- accroche : les 2 premières secondes donnent-elles envie de rester (texte à l'écran lisible dès la 1re image, promesse claire) ?
- rythme : blancs, longueurs, plans figés plus de 4 s, coupes visibles ou brutales ?
- sous_titres : synchronisés avec la voix, sans faute, lisibles sur le fond, jamais sur le visage ?
- habillage : cartes, chiffres et plans de coupe arrivent-ils au bon moment, cohérents avec la DA ?
- son : voix claire, niveau constant, pas de clic aux coupes, musique jamais au-dessus de la voix ?
- appel_action : le mot-clé à commenter est-il dit, écrit et lisible assez longtemps ?

Réponds UNIQUEMENT par un objet JSON, sans texte autour :
{{"notes": {{"accroche": 0, "rythme": 0, "sous_titres": 0, "habillage": 0, "son": 0, "appel_action": 0}},
 "verdict": "une phrase",
 "problemes": [{{"temps": "00:07", "gravite": "bloquant|important|detail", "constat": "...", "correction": "..."}}],
 "points_forts": ["..."]}}
Ne signale que ce que tu vois ou entends vraiment, avec le temps exact. Maximum 8 problèmes, les plus graves d'abord."""


def planche(video: Path, sortie: Path, total: float) -> None:
    """Une image toutes les ~2 s (16 au maximum), horodatée, sur une seule planche."""
    n = max(4, min(16, round(total / 2)))
    pas = total / n
    colonnes = 4 if n <= 8 else 6 if n <= 12 else 8
    # le temps est écrit sur chaque image AVANT le tri : l'horodatage affiché est le vrai
    texte = "drawtext=text='%{pts\\:hms}':x=30:y=h-130:fontsize=90:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=20"
    ffmpeg("-i", video, "-vf", f"{texte},fps=1/{pas:.3f}:start_time={pas / 2:.3f},scale=324:576,"
           f"tile={colonnes}x{-(-n // colonnes)}:padding=10:margin=10:color=0x16181C",
           "-frames:v", "1", "-q:v", "3", sortie / "planche.jpg")
    ffmpeg("-i", video, "-frames:v", "1", "-vf", "scale=540:960", "-q:v", "3", sortie / "premiere-image.jpg")


def bandes(video: Path, sortie: Path, instants: list[float]) -> None:
    """Pour chaque instant, 12 images serrées (8 par seconde) autour de lui : on y voit un raccord
    image par image, ce que la planche générale (une image toutes les 2 s) ne montre pas."""
    sortie.mkdir(parents=True, exist_ok=True)
    for t in instants:
        debut = max(0.0, t - 0.3)
        cible = sortie / f"autour-{t:.1f}.jpg"
        ffmpeg("-ss", debut, "-t", 1.5, "-i", video, "-frames:v", 1, "-vf", "fps=8,scale=270:-2,tile=6x2:padding=4:color=0x16181C",
               "-q:v", 3, cible)
        print(f"  {cible}  ({debut:.1f} s → {debut + 1.5:.1f} s)")


def mesurer_son(video: Path, total: float) -> dict:
    """Niveau moyen (LUFS), crête, et blancs de plus de 0,6 s restés dans le montage
    (mesurés comme à la coupe : par rapport au bruit de fond de la prise)."""
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(video), "-af",
                        "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    journal = r.stderr
    resume = journal[journal.rfind("Summary:"):] if "Summary:" in journal else ""
    lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", resume)
    crete = re.search(r"Peak:\s+(-?[\d.]+) dBFS", resume)
    niveau, seuil = ecouter(video)
    blancs = [{"debut": d, "duree": round(f - d, 2)} for d, f in silences_du_son(niveau, seuil, 0.6)] if niveau is not None else []
    blancs = [b for b in blancs if b["debut"] + b["duree"] < total - 0.3]  # le gel de fin est voulu
    return {"niveau_lufs": float(lufs.group(1)) if lufs else None,
            "crete_dbfs": float(crete.group(1)) if crete else None, "blancs": blancs}


def gemini(video: Path, consigne: str) -> dict:
    """Envoie la vidéo à Gemini (Files API puis Interactions API) et récupère sa critique en JSON.
    Doc : https://ai.google.dev/gemini-api/docs/video-understanding"""
    cle = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    taille = video.stat().st_size
    depart = requests.post(f"{API}/upload/v1beta/files", headers={
        **cle, "X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(taille), "X-Goog-Upload-Header-Content-Type": "video/mp4",
        "Content-Type": "application/json"}, json={"file": {"display_name": "montage"}}, timeout=60)
    depart.raise_for_status()
    with open(video, "rb") as f:
        envoi = requests.post(depart.headers["x-goog-upload-url"], headers={
            "Content-Length": str(taille), "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize"}, data=f, timeout=900)
    envoi.raise_for_status()
    fichier = envoi.json()["file"]
    for _ in range(60):  # Gemini prépare la vidéo (quelques secondes)
        if fichier.get("state") == "ACTIVE":
            break
        if fichier.get("state") == "FAILED":
            sys.exit("Gemini n'a pas réussi à lire la vidéo.")
        time.sleep(5)
        fichier = requests.get(f"{API}/v1beta/{fichier['name']}", headers=cle, timeout=60).json()
    else:
        sys.exit("Gemini met trop de temps à préparer la vidéo : réessaie.")

    reponse = requests.post(f"{API}/v1beta/interactions", headers=cle, timeout=600, json={
        "model": os.getenv("GEMINI_MODELE", "gemini-4-hydrogen"),
        "input": [{"type": "video", "uri": fichier["uri"], "mime_type": "video/mp4"},
                  {"type": "text", "text": consigne}]})
    requests.delete(f"{API}/v1beta/{fichier['name']}", headers=cle, timeout=60)  # ne rien laisser chez Google
    if reponse.status_code != 200:
        sys.exit(f"Gemini a répondu {reponse.status_code} : {reponse.text[:400]}")
    texte = "".join(c.get("text", "") for etape in reponse.json().get("steps", [])
                    for c in (etape.get("content") or []) if isinstance(c, dict))
    brut = re.search(r"\{.*\}", texte, re.S)
    try:
        return json.loads(brut.group(0))
    except (AttributeError, json.JSONDecodeError):
        return {"verdict": "Réponse de Gemini illisible, la voici telle quelle.", "brut": texte}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("id", help="le projet (ex. 2026-11-30-3) ou un fichier .mp4")
    p.add_argument("--sans-gemini", action="store_true", help="seulement la planche et les mesures du son")
    p.add_argument("--autour", type=float, nargs="+", metavar="SECONDES",
                   help="seulement des bandes d'images serrées autour de ces instants (pour juger un raccord)")
    a = p.parse_args()

    if a.id.endswith(".mp4"):
        video, ident = Path(a.id).resolve(), identifiant(Path(a.id).name)
    else:
        ident = identifiant(a.id)
        video = MONTAGES / f"{ident}.mp4"
    if not video.exists():
        sys.exit(f"Vidéo introuvable : {video}\nRends-la d'abord : python machine/monter.py {ident} --rendu")
    dossier = projet(ident, creer=True)
    sortie = dossier / "yeux"
    if a.autour:
        bandes(video, sortie, a.autour)
        return
    shutil.rmtree(sortie, ignore_errors=True)
    sortie.mkdir()
    charte, total = da(), duree(video)

    planche(video, sortie, total)
    son = mesurer_son(video, total)
    ecrire(sortie / "son.json", son)
    cible = charte["son"]["volume_cible_lufs"]
    print(f"Vidéo : {total:.1f} s, {video.stat().st_size / 1e6:.1f} Mo")
    if son["niveau_lufs"] is None:
        print("Son   : ✗ aucune piste audio mesurable")
    else:
        ok = abs(son["niveau_lufs"] - cible) <= 2 and (son["crete_dbfs"] or 0) <= -0.5
        print(f"Son   : {'✓' if ok else '⚠'} niveau {son['niveau_lufs']} LUFS (cible {cible}), crête {son['crete_dbfs']} dBFS")
    for b in son["blancs"]:
        print(f"        ⚠ blanc de {b['duree']:.1f} s à {b['debut']:.1f} s : à couper (baisse rythme.silence_max ou --retirer)")
    print(f"Images à regarder : {sortie / 'planche.jpg'} et {sortie / 'premiere-image.jpg'}")

    if a.sans_gemini:
        return
    if not os.getenv("GEMINI_API_KEY"):
        print("Critique Gemini : sautée (pas de GEMINI_API_KEY dans .env, https://aistudio.google.com/apikey).")
        return
    script = ""
    plan = lire(dossier / "plan.json") if (dossier / "plan.json").exists() else {}
    if plan.get("mot_cle"):
        script = f"Mot-clé que le spectateur doit commenter : {plan['mot_cle']} (réseau : {plan.get('reseau', 'instagram')}).\n"
    c, st, zs = charte["couleurs"], charte["sous_titres"], charte["zones_sures"]
    consigne = GRILLE.format(cerveau=(RACINE / "CLAUDE.md").read_text(encoding="utf-8")[:3000],
                             police=charte["police"], nuit=c["nuit"], accent=c["accent"],
                             mots_max=st["mots_max"], haut=zs["haut"], bas=zs["bas"], script=script)
    print("Gemini regarde la vidéo...")
    critique = gemini(video, consigne)
    ecrire(sortie / "critique.json", critique)
    if "notes" in critique:
        print("Notes : " + ", ".join(f"{k} {v}/10" for k, v in critique["notes"].items()))
    print(f"Verdict : {critique.get('verdict', '')}")
    for pb in critique.get("problemes", []):
        print(f"  [{pb.get('temps')}] ({pb.get('gravite')}) {pb.get('constat')}\n      -> {pb.get('correction')}")
    print(f"-> {sortie / 'critique.json'}")


if __name__ == "__main__":
    main()
