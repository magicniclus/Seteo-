"""Détourage d'une personne dans une vidéo, avec RobustVideoMatting (RVM).

RVM est fait pour ça : une personne filmée, image après image, en gardant la mémoire des images
précédentes (pas de contour qui « tremble ») et en traitant les cheveux. Il tourne sur le processeur,
sans carte graphique. Le résultat est une vidéo WebM avec transparence, que le montage pose sur le
contenu.

    python machine/detourage.py montage/projets/<id>/assets/a-roll.mp4 sortie.webm

Il faut PyTorch (version processeur) :
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
Le modèle (15 Mo) est téléchargé au premier usage dans montage/modeles/ (pas enregistré dans le dépôt).
Modèle : https://github.com/PeterL1n/RobustVideoMatting (licence GPL-3.0 : on s'en sert comme d'un
outil, on ne le redistribue pas).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from atelier import MONTAGE, duree, lancer

MODELE = MONTAGE / "modeles" / "rvm_mobilenetv3.torchscript"
URL = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.torchscript"


def disponible() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def modele():
    import torch
    if not MODELE.exists():
        MODELE.parent.mkdir(parents=True, exist_ok=True)
        print("Téléchargement du modèle de détourage (15 Mo, une seule fois)...")
        lancer(["curl", "-sSL", "-o", MODELE, URL])
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    return torch.jit.load(str(MODELE), map_location="cpu").eval()


def taille(source: Path) -> tuple[int, int, float]:
    r = lancer(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                "-of", "csv=p=0", source])
    l, h, ips = r.stdout.strip().split(",")
    n, d = ips.split("/")
    return int(l), int(h), float(n) / float(d or 1)


def detourer(source: Path, cible: Path, debut: float = 0, fin: float | None = None, finesse: float = 0.375) -> None:
    """Détoure la personne de `source` (de `debut` à `fin`, en secondes) dans `cible` (WebM VP9 avec
    transparence, même cadence). `finesse` : taille de travail du modèle (0,25 rapide ; 0,5 plus fin)."""
    import torch
    net = modele()
    l, h, ips = taille(source)
    fin = duree(source) if fin is None else fin
    lire = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{debut:.3f}", "-t", f"{fin - debut:.3f}",
                             "-i", str(source), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    cible.parent.mkdir(parents=True, exist_ok=True)
    ecrire = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                               "-s", f"{l}x{h}", "-r", f"{ips:.3f}", "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                               "-b:v", "0", "-crf", "30", "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1",
                               "-auto-alt-ref", "0", str(cible)], stdin=subprocess.PIPE)
    memoire = [None] * 4
    n, depart = 0, time.monotonic()
    total = max(1, round((fin - debut) * ips))
    with torch.inference_mode():
        while True:
            brut = lire.stdout.read(l * h * 3)
            if len(brut) < l * h * 3:
                break
            image = torch.from_numpy(np.frombuffer(brut, np.uint8).reshape(h, l, 3).copy()).permute(2, 0, 1)
            source_t = image.unsqueeze(0).float().div_(255)
            avant, alpha, *memoire = net(source_t, *memoire, finesse)
            rgba = torch.cat([avant, alpha], dim=1)[0].mul_(255).clamp_(0, 255).byte().permute(1, 2, 0).numpy()
            ecrire.stdin.write(rgba.tobytes())
            n += 1
            if n % 150 == 0:
                ecoule = time.monotonic() - depart
                print(f"  détourage : {n}/{total} images ({ecoule / n:.2f} s par image)", flush=True)
    ecrire.stdin.close()
    lire.wait()
    if ecrire.wait() != 0 or not cible.exists():
        sys.exit("Le détourage (RVM) a échoué à l'écriture de la vidéo.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    detourer(Path(sys.argv[1]), Path(sys.argv[2]), *(float(x) for x in sys.argv[3:5]))
