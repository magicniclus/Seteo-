"""Transcrit un rush mot par mot (étape 1 du montage).

Deux moteurs, au choix :
- ElevenLabs Scribe (le plus précis en français) si ELEVENLABS_API_KEY est dans .env ;
- sinon Whisper, en local sur ta machine (gratuit, un peu moins précis sur les noms propres).

Résultat : montage/projets/<id>/transcription.json (chaque mot avec son début et sa fin)
et, à l'écran, le texte phrase par phrase avec les blancs : c'est là qu'on repère les ratés.

Usage :
    python machine/transcrire.py rushs/2026-11-30-3-143012.webm
    python machine/transcrire.py ma-video.mp4 --id test --moteur whisper
    python machine/transcrire.py rush.webm --mots-cles "MaPrimeRénov', Leroy Merlin"
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

from atelier import RACINE, afficher_phrases, duree, ecrire, ffmpeg, identifiant, lire, marque, projet


def post_du_calendrier(ident: str) -> dict | None:
    """Retrouve le post (script, mot-clé) si l'identifiant est <semaine>-<numéro>."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})-(\d+)$", ident)
    if not m:
        return None
    fichier = RACINE / "sorties" / m.group(1) / "calendrier.json"
    if not fichier.exists():
        return None
    posts = lire(fichier)["posts"]
    numero = int(m.group(2))
    return posts[numero - 1] if 1 <= numero <= len(posts) else None


def scribe(audio: Path, mots_cles: list[str]) -> list[dict]:
    """ElevenLabs Scribe : https://elevenlabs.io/docs/api-reference/speech-to-text/convert"""
    donnees = [("model_id", os.getenv("ELEVENLABS_MODELE", "scribe_v2")), ("language_code", "fr"),
               ("timestamps_granularity", "word"), ("tag_audio_events", "false")]
    donnees += [("keyterms", k) for k in mots_cles]
    with open(audio, "rb") as f:
        r = requests.post("https://api.elevenlabs.io/v1/speech-to-text",
                          headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                          data=donnees, files={"file": (audio.name, f, "audio/mpeg")}, timeout=600)
    if r.status_code != 200:
        sys.exit(f"ElevenLabs a répondu {r.status_code} : {r.text[:400]}")
    return [{"t": w["text"].strip(), "d": w["start"], "f": w["end"]}
            for w in r.json()["words"] if w.get("type") == "word" and w.get("start") is not None]


def whisper(audio: Path, mots_cles: list[str], modele: str) -> list[dict]:
    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("Whisper n'est pas installé : pip install faster-whisper\n"
                 "(ou mets ELEVENLABS_API_KEY dans .env pour utiliser Scribe)")
    # ffmpeg décode le son (16 kHz mono) : Whisper reçoit directement les échantillons
    brut = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(audio), "-f", "s16le",
                           "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    signal = np.frombuffer(brut, np.int16).astype(np.float32) / 32768
    segments, _ = WhisperModel(modele, compute_type="int8").transcribe(
        signal, language="fr", word_timestamps=True, vad_filter=True,
        initial_prompt=("Vocabulaire : " + ", ".join(mots_cles)) if mots_cles else None)
    return [{"t": w.word.strip(), "d": round(float(w.start), 3), "f": round(float(w.end), 3)}
            for s in segments for w in s.words if w.word.strip()]


def recoller(mots: list[dict]) -> list[dict]:
    """Recolle ce que les moteurs séparent à tort : « c » + « 'est », « 10 » + « 000 »."""
    propres: list[dict] = []
    for m in mots:
        avant = propres[-1] if propres else None
        apostrophe = m["t"][0] in "'’" or (avant and avant["t"][-1] in "'’")
        milliers = avant and re.fullmatch(r"\d{1,3}", avant["t"].split("\u00a0")[-1]) and re.fullmatch(r"\d{3}", m["t"])
        seule = re.fullmatch(r"[?!:;.,…»]+", m["t"])   # une ponctuation isolée appartient au mot d'avant
        if avant and (apostrophe or milliers or seule):
            avant["t"] += ("\u00a0" if milliers or (seule and m["t"][0] in "?!:;") else "") + m["t"]
            if not seule:
                avant["f"] = m["f"]
        else:
            propres.append(dict(m))
    for m in propres:
        m["t"] = m["t"].replace("'", "’")
    return propres


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("rush", help="la vidéo enregistrée (webm, mp4, mov)")
    p.add_argument("--id", help="nom du projet (par défaut : tiré du nom du fichier)")
    p.add_argument("--moteur", choices=["auto", "scribe", "whisper"], default="auto")
    p.add_argument("--modele-whisper", default="small", help="small (rapide), medium, large-v3 (précis)")
    p.add_argument("--mots-cles", default="", help="noms propres à bien reconnaître, séparés par des virgules")
    a = p.parse_args()

    rush = Path(a.rush).resolve()
    if not rush.exists():
        sys.exit(f"Fichier introuvable : {rush}")
    ident = identifiant(a.id or rush.name)
    dossier = projet(ident, creer=True)

    post = post_du_calendrier(ident)
    mots_cles = [m.strip() for m in a.mots_cles.split(",") if m.strip()] + [marque()]
    if post:
        mots_cles.append(post["mot_cle"].upper())

    moteur = a.moteur
    if moteur == "auto":
        moteur = "scribe" if os.getenv("ELEVENLABS_API_KEY") else "whisper"
    if moteur == "scribe" and not os.getenv("ELEVENLABS_API_KEY"):
        sys.exit("Il manque ELEVENLABS_API_KEY dans .env (https://elevenlabs.io -> API Keys)")

    print(f"Transcription de {rush.name} avec {moteur}...")
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "voix.mp3"  # seule la voix part vers le moteur, pas l'image
        ffmpeg("-i", rush, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", audio)
        mots = scribe(audio, mots_cles) if moteur == "scribe" else whisper(audio, mots_cles, a.modele_whisper)
    if not mots:
        sys.exit("Aucune parole détectée dans ce rush.")
    mots = recoller(mots)
    for i, m in enumerate(mots):
        m["i"] = i

    try:
        chemin = str(rush.relative_to(RACINE))
    except ValueError:
        chemin = str(rush)
    ecrire(dossier / "transcription.json",
           {"rush": chemin, "moteur": moteur, "duree": round(duree(rush), 3), "mots": mots})

    print(f"\n{len(mots)} mots, rush de {duree(rush):.1f} s. Temps du rush, en secondes :\n")
    afficher_phrases(mots)
    if post:
        print("\nScript prévu au calendrier :\n  " + "\n  ".join([post["accroche"], *post["script_ou_slides"]]))
    print(f"\n-> {dossier / 'transcription.json'}")
    print(f"Suite : repère les prises ratées (phrases dites deux fois, hésitations), puis\n"
          f"  python machine/couper.py {ident} --retirer DEBUT-FIN [DEBUT-FIN ...]")


if __name__ == "__main__":
    main()
