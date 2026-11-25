"""Outils partagés de l'atelier de montage : chemins, DA, ffmpeg, HyperFrames."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent
MONTAGE = RACINE / "montage"          # l'atelier : HyperFrames, DA, projets
PROJETS = MONTAGE / "projets"         # un dossier par vidéo
MONTAGES = RACINE / "montages"        # les MP4 finis
BROLL = RACINE / "broll"              # plans de coupe (Pexels, clips perso)
ECRANS = RACINE / "ecrans"            # vidéos du site (machine/ecrans.py)

load_dotenv(RACINE / ".env")
os.environ.setdefault("HYPERFRAMES_NO_TELEMETRY", "1")  # aucun envoi de statistiques d'usage
os.environ.setdefault("HYPERFRAMES_SKIP_SKILLS", "1")


def da(univers: str | None = None) -> dict:
    """La direction artistique : les réglages communs (config/da.yaml) + l'univers choisi
    (config/univers/<nom>.yaml : couleurs, police, cartes, motif)."""
    charte = yaml.safe_load((RACINE / "config" / "da.yaml").read_text(encoding="utf-8"))
    nom = univers or charte["univers"]
    fichier = RACINE / "config" / "univers" / f"{nom}.yaml"
    if not fichier.exists():
        dispo = ", ".join(sorted(f.stem for f in fichier.parent.glob("*.yaml")))
        sys.exit(f"Univers « {nom} » introuvable dans config/univers/ (disponibles : {dispo}).")
    charte.update(yaml.safe_load(fichier.read_text(encoding="utf-8")))
    charte["univers"] = nom
    return charte


def marque() -> str:
    """Le nom de la marque (config/marque.yaml)."""
    return yaml.safe_load((RACINE / "config" / "marque.yaml").read_text(encoding="utf-8"))["marque"]


def identifiant(nom: str) -> str:
    """« rushs/2026-11-30-3-143012.webm » -> « 2026-11-30-3 » (semaine-numéro du calendrier)."""
    base = Path(nom).stem
    m = re.match(r"(\d{4}-\d{2}-\d{2}-\d+)(-\d{6})?$", base)
    return m.group(1) if m else re.sub(r"[^a-zA-Z0-9_-]", "-", base)


def projet(ident: str, creer: bool = False) -> Path:
    dossier = PROJETS / identifiant(ident)
    if creer:
        dossier.mkdir(parents=True, exist_ok=True)
    elif not dossier.exists():
        sys.exit(f"Projet introuvable : {dossier}\nCommence par : python machine/transcrire.py <rush>")
    return dossier


def lire(fichier: Path):
    return json.loads(fichier.read_text(encoding="utf-8"))


def ecrire(fichier: Path, donnees) -> None:
    fichier.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")


def lancer(cmd: list, **kw) -> subprocess.CompletedProcess:
    """Lance une commande ; en cas d'échec, montre la fin de ses messages et s'arrête."""
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"Échec : {' '.join(str(c) for c in cmd[:4])} ...\n{(r.stderr or r.stdout)[-1500:]}")
    return r


def ffmpeg(*args) -> None:
    lancer(["ffmpeg", "-nostdin", "-v", "error", "-y", *args])


def duree(fichier: Path) -> float:
    r = lancer(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", fichier])
    return float(r.stdout.strip())


def a_du_son(fichier: Path) -> bool:
    r = lancer(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                "-of", "csv=p=0", fichier])
    return bool(r.stdout.strip())


def est_hdr(fichier: Path) -> bool:
    """Les téléphones récents filment souvent en HDR (HLG ou PQ) : sans conversion, l'image sort délavée."""
    r = lancer(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                "-of", "csv=p=0", fichier])
    return r.stdout.strip() in ("smpte2084", "arib-std-b67")


# HDR -> couleurs normales (SDR, Rec. 709), celles que tous les téléphones et réseaux affichent pareil
HDR_VERS_SDR = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                "zscale=t=bt709:m=bt709:r=tv,")


# Filtre ffmpeg : remplit un cadre vertical 1080x1920 sans déformer (rogne ce qui dépasse)
def cadrage(largeur: int, hauteur: int, ips: int, hdr: bool = False) -> str:
    return (f"scale={largeur}:{hauteur}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={largeur}:{hauteur},fps={ips},{HDR_VERS_SDR if hdr else ''}setsar=1,format=yuv420p")


REC709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def normaliser_clip(source: Path, cible: Path, debut: float = 0, duree_max: float = 8) -> None:
    """Met un plan de coupe au format de la DA (vertical, 30 i/s, sans son, court)."""
    f = da()["format"]
    cible.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-ss", debut, "-t", duree_max, "-i", source, "-an", "-vf",
           cadrage(f["largeur"], f["hauteur"], f["ips"], est_hdr(source)),
           "-c:v", "libx264", "-crf", "18", "-preset", "medium", *REC709, "-movflags", "+faststart", cible)


def hyperframes(*args, cwd: Path | None = None, verifier: bool = True) -> subprocess.CompletedProcess:
    """Lance le HyperFrames installé dans montage/ (version figée dans package.json)."""
    binaire = MONTAGE / "node_modules" / ".bin" / "hyperframes"
    if not binaire.exists():
        sys.exit("HyperFrames n'est pas installé. Lance une fois : cd montage && npm install")
    cmd = [str(binaire), *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if verifier and r.returncode != 0:
        sys.exit(f"HyperFrames a échoué ({' '.join(str(a) for a in args[:2])}) :\n{(r.stdout + r.stderr)[-2500:]}")
    return r


def phrases(mots: list[dict], silence: float = 0.6) -> list[list[dict]]:
    """Regroupe les mots en phrases (ponctuation forte ou blanc) pour les relire facilement."""
    groupes, courant = [], []
    for i, m in enumerate(mots):
        courant.append(m)
        suivant = mots[i + 1] if i + 1 < len(mots) else None
        fin_phrase = m["t"].rstrip("»\" ").endswith((".", "?", "!", "…"))
        blanc = suivant is not None and suivant["d"] - m["f"] > silence
        if suivant is None or fin_phrase or blanc:
            groupes.append(courant)
            courant = []
    return groupes


def afficher_phrases(mots: list[dict], silence: float = 0.6, numeros: bool = False) -> None:
    """Liste lisible : début → fin  texte, avec les blancs entre les phrases.
    numeros=True : chaque mot est précédé de son numéro (celui qu'on écrit « m12 » dans plan.json)."""
    precedent = None
    for g in phrases(mots, silence):
        if precedent is not None and g[0]["d"] - precedent > silence:
            print(f"            ... blanc de {g[0]['d'] - precedent:.1f} s ...")
        if numeros:
            print(f"  {g[0]['d']:6.2f} → {g[-1]['f']:6.2f}  " + "  ".join(f"{m['i']}:{m['t']}" for m in g))
        else:
            print(f"  {g[0]['d']:6.2f} → {g[-1]['f']:6.2f}  {' '.join(m['t'] for m in g)}")
        precedent = g[-1]["f"]
