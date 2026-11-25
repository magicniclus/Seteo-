"""Coupe les blancs et les prises ratées d'un rush (étape 2 du montage).

- Les blancs plus longs que `rythme.silence_max` (config/da.yaml) sont retirés tout seuls.
- Les prises ratées se retirent avec --retirer DEBUT-FIN (temps du rush, donnés par
  transcrire.py) ou avec la clé "retirer" du plan.json.
- La vidéo est mise au format de la DA (1080x1920, 30 i/s) et la voix au niveau des réseaux.

Résultat, dans montage/projets/<id>/ :
    assets/a-roll.mp4   la prise nettoyée, enchaînée serrée
    mots.json           chaque mot avec son temps DANS LA VIDÉO FINALE + les instants de coupe

Usage :
    python machine/couper.py 2026-11-30-3
    python machine/couper.py 2026-11-30-3 --retirer 5.4-10.9 31.2-33
"""

import argparse
import re
import subprocess
import sys

from atelier import RACINE, a_du_son, afficher_phrases, cadrage, da, duree, ecrire, ffmpeg, lire, projet


def plages_a_garder(mots: list[dict], retirer: list[tuple], r: dict, duree_rush: float) -> list[dict]:
    """Regroupe les mots gardés en plages continues (un blanc trop long = une coupe)."""
    gardes = [m for m in mots if not any(d <= (m["d"] + m["f"]) / 2 <= f for d, f in retirer)]
    if not gardes:
        sys.exit("Tout le rush est retiré : vérifie les plages --retirer.")
    plages = []
    for m in gardes:
        suite = plages and m["d"] - plages[-1]["mots"][-1]["f"] <= r["silence_max"] \
            and m["i"] == plages[-1]["mots"][-1]["i"] + 1
        if suite:
            plages[-1]["mots"].append(m)
        else:
            plages.append({"mots": [m]})
    for k, p in enumerate(plages):
        debut = p["mots"][0]["d"] - r["marge_avant"]
        fin = p["mots"][-1]["f"] + r["marge_apres"]
        if k > 0:  # ne jamais mordre sur la plage d'avant
            debut = max(debut, plages[k - 1]["fin"])
        p["debut"], p["fin"] = max(0.0, debut), min(duree_rush, fin)
    return plages


def silences_du_son(rush, minimum: float) -> list[tuple[float, float]]:
    """Les vrais silences du rush, mesurés sur le son (35 dB sous les crêtes de la voix).
    Les moteurs de transcription étirent parfois un mot sur un blanc : le son, lui, ne ment pas."""
    mesure = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(rush), "-vn", "-af", "volumedetect",
                             "-f", "null", "-"], capture_output=True, text=True).stderr
    crete = re.search(r"max_volume: (-?[\d.]+) dB", mesure)
    if not crete:
        return []
    seuil = float(crete.group(1)) - 35
    journal = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(rush), "-vn", "-af",
                              f"silencedetect=noise={seuil:.1f}dB:d={minimum}", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
    debuts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", journal)]
    fins = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", journal)]
    return list(zip(debuts, fins))


def retirer_silences(plages: list[dict], silences: list[tuple], r: dict) -> list[tuple[float, float]]:
    """Découpe chaque plage aux silences mesurés, en gardant un peu d'air de chaque côté."""
    segments = []
    for pl in plages:
        debut = pl["debut"]
        for d, f in silences:
            trou_d, trou_f = d + r["marge_apres"], f - r["marge_avant"]
            if trou_f - trou_d >= 0.15 and debut < trou_d and trou_f < pl["fin"]:
                segments.append((debut, trou_d))
                debut = trou_f
        segments.append((debut, pl["fin"]))
    return [(d, f) for d, f in segments if f - d > 0.05]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("id", help="le projet, ex. 2026-11-30-3")
    p.add_argument("--retirer", nargs="*", default=[], metavar="DEBUT-FIN",
                   help="plages du rush à jeter (prises ratées), en secondes")
    p.add_argument("--silence", type=float, help="blanc maximum gardé (défaut : config/da.yaml)")
    a = p.parse_args()

    dossier = projet(a.id)
    charte = da()
    rythme = dict(charte["rythme"])
    if a.silence is not None:
        rythme["silence_max"] = a.silence
    trans = lire(dossier / "transcription.json")
    rush = RACINE / trans["rush"]
    if not rush.exists():
        sys.exit(f"Rush introuvable : {rush}")

    retirer = [tuple(float(x) for x in plage.split("-")) for plage in a.retirer]
    fichier_plan = dossier / "plan.json"
    if not retirer and fichier_plan.exists():
        retirer = [tuple(x) for x in lire(fichier_plan).get("retirer", [])]

    plages = plages_a_garder(trans["mots"], retirer, rythme, trans["duree"])
    son = a_du_son(rush)
    silences = silences_du_son(rush, max(rythme["silence_max"], 0.3)) if son else []
    segments = retirer_silences(plages, silences, rythme)

    # Un seul passage ffmpeg : chaque segment est découpé, puis tout est recollé et mis au format
    filtres, etiquettes = [], ""
    for k, (d, f) in enumerate(segments):
        filtres.append(f"[0:v]trim={d:.3f}:{f:.3f},setpts=PTS-STARTPTS[v{k}]")
        etiquettes += f"[v{k}]"
        if son:  # mini-fondus de 12 ms : pas de « clic » aux raccords
            filtres.append(f"[0:a]atrim={d:.3f}:{f:.3f},asetpts=PTS-STARTPTS,"
                           f"afade=t=in:d=0.012,afade=t=out:st={max(f - d - 0.012, 0):.3f}:d=0.012[a{k}]")
            etiquettes += f"[a{k}]"
    fmt, gel = charte["format"], rythme.get("gel_fin", 0)
    filtres.append(f"{etiquettes}concat=n={len(segments)}:v=1:a={1 if son else 0}[vc]{'[ac]' if son else ''}")
    filtres.append(f"[vc]{cadrage(fmt['largeur'], fmt['hauteur'], fmt['ips'])},"
                   f"tpad=stop_mode=clone:stop_duration={gel}[v]")
    sorties = ["-map", "[v]"]
    if son:
        filtres.append(f"[ac]highpass=f=80,loudnorm=I={charte['son']['volume_cible_lufs']}:TP=-1.5:LRA=11,"
                       f"apad=pad_dur={gel},aresample=48000[a]")
        sorties += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]

    (dossier / "assets").mkdir(exist_ok=True)
    cible = dossier / "assets" / "a-roll.mp4"
    print(f"Découpe de {rush.name} : {len(segments)} morceaux gardés...")
    ffmpeg("-i", rush, "-filter_complex", ";".join(filtres), *sorties,
           "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-g", str(fmt["ips"]),
           "-movflags", "+faststart", cible)

    # Recale chaque mot sur la vidéo finale (un temps tombé dans une coupe se cale sur le raccord)
    departs, curseur = [], 0.0
    for d, f in segments:
        departs.append(curseur)
        curseur += f - d
    coupes = [round(t, 3) for t in departs[1:]]

    def vers_final(t: float) -> float:
        for (d, f), depart in zip(segments, departs):
            if t < d:
                return depart
            if t <= f:
                return depart + t - d
        return curseur

    mots = []
    for pl in plages:
        for m in pl["mots"]:
            d = vers_final(m["d"])
            mots.append({"i": len(mots), "t": m["t"], "d": round(d, 3),
                         "f": round(max(vers_final(m["f"]), d + 0.05), 3)})
    total = duree(cible)
    ecrire(dossier / "mots.json", {"duree": round(total, 3), "fin_parole": round(curseur, 3),
                                   "coupes": coupes, "retire": [list(x) for x in retirer], "mots": mots})

    print(f"\nRush {trans['duree']:.1f} s -> vidéo {total:.1f} s "
          f"({len(coupes)} coupes, {trans['duree'] - total:.1f} s de gagné).")
    print("Temps de la VIDÉO FINALE, et numéro de chaque mot (« m12 » dans plan.json) :\n")
    afficher_phrases(mots, silence=10, numeros=True)
    print(f"\n-> {cible}\n-> {dossier / 'mots.json'}")
    print(f"Suite : écris {dossier / 'plan.json'} puis  python machine/monter.py {a.id} --apercu")


if __name__ == "__main__":
    main()
