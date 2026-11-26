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
import sys

from atelier import (MONTAGE, PAS, REC709, RACINE, a_du_son, afficher_phrases, cadrage, da, duree, ecouter, ecrire,
                     est_hdr, ffmpeg, lancer, lire, projet, silences_du_son)

# Débruitage de la voix : RNNoise (filtre arnndn de ffmpeg), un réseau entraîné à garder la parole et à
# retirer le reste (ventilation, clim, rue, ronflement). Le modèle (300 Ko) est téléchargé au premier
# usage dans montage/modeles/ (pas enregistré dans le dépôt).
MODELE_VOIX = MONTAGE / "modeles" / "rnnoise-std.rnnn"
URL_VOIX = "https://raw.githubusercontent.com/richardpl/arnndn-models/master/std.rnnn"


def filtre_debruitage(reglage) -> str:
    """"voix" : RNNoise (le bruit de fond baisse d'une dizaine de dB, la voix bouge de moins de 1 dB) ;
    un nombre : réduction douce d'un souffle régulier (afftdn, en dB) ; 0 : rien."""
    if reglage == "voix":
        if not MODELE_VOIX.exists():
            MODELE_VOIX.parent.mkdir(parents=True, exist_ok=True)
            print("Téléchargement du modèle de débruitage de la voix (300 Ko, une seule fois)...")
            lancer(["curl", "-sSL", "-o", MODELE_VOIX, URL_VOIX])
        return f"aresample=48000,arnndn=m='{MODELE_VOIX}',"
    if reglage:
        return f"afftdn=nr={float(reglage)}:nf=-45,"
    return ""


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


def ne_pas_mordre(plages: list[dict], mots: list[dict], niveau, seuil: float, duree_rush: float) -> None:
    """La transcription donne parfois la fin d'un mot trop tôt (une syllabe qui traîne) ou son début
    trop tard : couper là mord sur la voix. Si le son est encore fort à l'endroit d'une coupe, on la
    déplace vers l'instant calme le plus proche (0,3 s au plus), à défaut vers le creux le plus bas :
    c'est là qu'un raccord s'entend le moins. On ne déborde jamais sur un autre mot ni sur la plage d'à côté."""
    place = {m["i"]: k for k, m in enumerate(mots)}
    rang = lambda t: min(max(int(round(t / PAS)), 0), len(niveau) - 1)

    def instant_calme(depart: float, limite: float, replis: float) -> float:
        """De `depart` vers `limite` : le premier instant sous le seuil, sinon le plus calme (en
        comptant aussi le petit repli `replis` de l'autre côté du départ)."""
        if niveau[rang(depart)] < seuil:
            return depart
        sens = 1 if limite >= depart else -1
        rangs = list(range(rang(depart), rang(limite) + sens, sens))
        for k in rangs:
            if niveau[k] < seuil:
                return k * PAS
        rangs += list(range(rang(depart), rang(replis), -sens))
        return min(rangs, key=lambda k: niveau[k]) * PAS

    for k, p in enumerate(plages):
        avant, apres = place[p["mots"][0]["i"]] - 1, place[p["mots"][-1]["i"]] + 1
        borne = max(mots[avant]["f"] + 0.02 if avant >= 0 else 0.0, plages[k - 1]["fin"] if k else 0.0)
        if p["debut"] > borne:
            p["debut"] = round(max(instant_calme(p["debut"], max(p["debut"] - 0.3, borne), p["debut"] + 0.04), borne), 3)
        borne = mots[apres]["d"] - 0.02 if apres < len(mots) else duree_rush
        if p["fin"] < borne:
            p["fin"] = round(min(instant_calme(p["fin"], min(p["fin"] + 0.3, borne), p["fin"] - 0.06), borne), 3)


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
    # Réglages de rythme propres à cette vidéo (plan.json, "reglages") : gel_fin, silence_max, marges
    if (dossier / "plan.json").exists():
        propres = lire(dossier / "plan.json").get("reglages", {})
        rythme.update({k: v for k, v in propres.items() if k in rythme})
        if "debruitage" in propres:   # le débruitage, vidéo par vidéo
            charte["son"]["debruitage"] = propres["debruitage"]
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
    niveau, seuil = ecouter(rush) if son else (None, None)
    silences = []
    if niveau is not None:
        ne_pas_mordre(plages, trans["mots"], niveau, seuil, trans["duree"])
        silences = silences_du_son(niveau, seuil, max(rythme["silence_max"], 0.3))
    # Une plage à retirer sans aucun mot dedans (un « euh » que la transcription n'a pas écrit) se coupe
    # comme un silence, exactement aux temps donnés.
    silences = sorted(silences + [(d - rythme["marge_apres"], f + rythme["marge_avant"]) for d, f in retirer])
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
    hdr = est_hdr(rush)
    if hdr:
        print("Rush filmé en HDR : conversion en couleurs normales (sinon l'image sort délavée).")
    filtres.append(f"{etiquettes}concat=n={len(segments)}:v=1:a={1 if son else 0}[vc]{'[ac]' if son else ''}")
    filtres.append(f"[vc]{cadrage(fmt['largeur'], fmt['hauteur'], fmt['ips'], hdr)},"
                   f"tpad=stop_mode=clone:stop_duration={gel}[v]")
    sorties = ["-map", "[v]"]
    if son:
        nettoyage = filtre_debruitage(charte["son"].get("debruitage", 0))   # bruit de fond derrière la voix
        filtres.append(f"[ac]highpass=f=80,{nettoyage}loudnorm=I={charte['son']['volume_cible_lufs']}:TP=-1.5:LRA=11,"
                       f"apad=pad_dur={gel},aresample=48000[a]")
        sorties += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]

    (dossier / "assets").mkdir(exist_ok=True)
    cible = dossier / "assets" / "a-roll.mp4"
    print(f"Découpe de {rush.name} : {len(segments)} morceaux gardés...")
    ffmpeg("-i", rush, "-filter_complex", ";".join(filtres), *sorties,
           "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-g", str(fmt["ips"]), *REC709,
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
    # Image de cadrage : 3 moments de la prise avec les repères de la DA, pour voir où tombe le visage
    st, zs = charte["sous_titres"], charte["zones_sures"]
    H = fmt["hauteur"]
    reperes = (f"drawbox=y=0:w=iw:h={zs['haut']}:color=black@0.45:t=fill,"
               f"drawbox=y={H - zs['bas']}:w=iw:h={zs['bas']}:color=black@0.45:t=fill,"
               f"drawbox=y={st['centre_y'] - 110}:w=iw:h=220:color=yellow@0.35:t=fill,"
               f"drawbox=y={round(rythme['visage_y'] * H) - 3}:w=iw:h=6:color=red@0.9:t=fill")
    ffmpeg("-i", cible, "-vf", f"fps=3/{max(curseur, 1):.3f},{reperes},scale=360:640,tile=3x1:padding=8",
           "-frames:v", "1", "-q:v", "3", dossier / "cadrage.jpg")
    print(f"\n-> {cible}\n-> {dossier / 'mots.json'}")
    print(f"-> {dossier / 'cadrage.jpg'} : bandes sombres = interface des réseaux, bande jaune = sous-titres,\n"
          f"   trait rouge = centre des zooms. Le visage doit être au-dessus du jaune, les yeux près du rouge ;\n"
          f"   sinon, règle \"reglages\": {{\"visage_y\": ..., \"centre_y\": ...}} dans plan.json.")
    print(f"Suite : écris {dossier / 'plan.json'} puis  python machine/monter.py {a.id} --apercu")


if __name__ == "__main__":
    main()
