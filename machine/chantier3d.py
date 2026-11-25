"""Maquette 3D d'un chantier : la construit avec l'outil Dessin du site, puis la filme.

On écrit une fiche (JSON) qui décrit le chantier ; ce script construit la maquette avec le code du
site, l'ouvre dans l'éditeur (copie locale du site : machine/site_local.py) et filme la vue 3D en tournant
autour. Le plan se choisit vue par vue :
    piece       zoom sur une pièce (murs de devant abaissés)
    large       toute la maison vue de dedans (murs abaissés)
    exterieur   la maison fermée, avec son toit et son jardin

Usage :
    python machine/site_local.py demarrer                                   # une fois par session
    python machine/chantier3d.py chantiers/ma-fiche.json              # filme toutes les "vues" de la fiche
    python machine/chantier3d.py chantiers/ma-fiche.json --apercu     # une image par vue, pour vérifier vite
    python machine/chantier3d.py chantiers/ma-fiche.json --plan piece --piece cuisine --tour 50
    python machine/chantier3d.py --catalogue                          # ce qu'on peut mettre dans une fiche

Résultat : broll/chantiers/<nom>-<plan>.mp4 (+ .jpg et une planche), à poser dans plan.json ("broll").
Le format de la fiche est décrit dans le skill video-chantier.
"""

import argparse
import base64
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from atelier import BROLL, RACINE, da, ffmpeg
from site_local import adresse, en_marche, reglages

SORTIE = BROLL / "chantiers"
FORMATS = {"carte": (1380, 990), "vertical": (1080, 1920), "carre": (1080, 1080)}
# La vue 3D du site s'ouvre de trois quarts, au-dessus de la maison (Cadrage.tsx) :
DIRECTION = (-0.45, 0.75, 0.85)
CHAMP = math.radians(45)
ELEVATION = math.degrees(math.asin(0.75 / math.hypot(*DIRECTION)))   # ~39° au-dessus de l'horizon


def tsx(*args: str) -> str:
    site = reglages()["dossier"]
    binaire = site / "node_modules" / ".bin" / "tsx"
    if not binaire.exists():
        sys.exit(f"Le site n'est pas installé dans {site}. Lance : python machine/site_local.py demarrer")
    r = subprocess.run([str(binaire), str(RACINE / "machine" / "chantier3d" / "scene.mts"), *args],
                       capture_output=True, text=True, env={**__import__("os").environ, "SITE_PORTAIL": str(site)})
    if r.returncode != 0:
        erreur = [l for l in r.stderr.splitlines() if "Error" in l or "error" in l] or r.stderr.splitlines()[-3:]
        sys.exit("La maquette n'a pas pu être construite :\n  " + "\n  ".join(erreur[:4]))
    for ligne in r.stderr.splitlines():
        if ligne.strip():
            print("  ⚠ " + ligne.strip())
    return r.stdout


def catalogue() -> None:
    c = json.loads(tsx("--catalogue"))
    print("Modèles de maison :", " · ".join(c["modeles"]))
    for cle, titre in (("pieces", "Pièces"), ("ouvertures", "Ouvertures"), ("toits", "Toits"), ("piscines", "Piscines")):
        print(f"{titre} : {', '.join(c[cle])}")
    print("Objets :")
    for categorie, objets in c["objets"].items():
        print(f"  {categorie} : {', '.join(objets)}")


def distance_de_cadrage(rayon: float, aspect: float, marge: float = 1.1) -> float:
    """La distance à laquelle le site place sa caméra pour cadrer une sphère de ce rayon."""
    horizontal = 2 * math.atan(math.tan(CHAMP / 2) * aspect)
    return rayon * marge / math.sin(min(CHAMP, horizontal) / 2)


def cible_de(vue: dict, reperes: dict) -> tuple[dict | None, tuple[float, float], float]:
    """Pour une vue : la pièce visée (ou rien), le point regardé (x, y du plan, en mètres) et le rayon à cadrer."""
    plan = vue.get("plan", "exterieur")
    if plan == "exterieur":
        return None, tuple(reperes["cadre"]["centre"]), reperes["cadre"]["rayon"]
    if plan == "large":
        return None, tuple(reperes["contenu"]["centre"]), reperes["contenu"]["rayon"]
    if plan != "piece":
        sys.exit(f"Plan inconnu « {plan} » (piece, large ou exterieur).")
    voulu = vue.get("piece")
    pieces = reperes["pieces"]
    if isinstance(voulu, int):
        choix = pieces[voulu:voulu + 1]
    else:
        choix = [p for p in pieces if p["type"] == voulu or (p.get("nom") or "").lower() == str(voulu).lower()]
    if not choix:
        dispo = ", ".join(f"{i}:{p['type']}" for i, p in enumerate(pieces))
        sys.exit(f"Pièce « {voulu} » introuvable dans la maquette. Pièces : {dispo}")
    piece = max(choix, key=lambda p: p["surface"]) if not isinstance(voulu, int) else choix[0]
    return piece, tuple(piece["centre"]), max(piece["rayon"], 1.6)


def glisser(page, bouton: str, dx: float, dy: float, largeur: int, hauteur: int) -> None:
    """Glisse la souris du centre de l'image, par morceaux qui restent dans l'image."""
    maxi = 0.38 * min(largeur, hauteur)
    morceaux = max(1, math.ceil(max(abs(dx), abs(dy)) / maxi))
    for _ in range(morceaux):
        page.mouse.move(largeur / 2, hauteur / 2)
        page.mouse.down(button=bouton)
        page.mouse.move(largeur / 2 + dx / morceaux, hauteur / 2 + dy / morceaux, steps=4)
        page.mouse.up(button=bouton)


def deux_images(page) -> None:
    page.evaluate("() => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(ok)))")


def image_3d(page) -> bytes:
    """L'image de la vue 3D, prise à la source (le canevas WebGL), après le rendu de l'image en cours.
    Quatre fois plus rapide qu'une capture de la page entière."""
    url = page.evaluate("""() => new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(() => {
        const c = document.querySelector('canvas[data-testid="vue-3d"]') || document.querySelector('[data-testid="vue-3d"] canvas') || document.querySelector('canvas');
        ok(c.toDataURL('image/jpeg', 0.95));
    })))""")
    return base64.b64decode(url.split(",", 1)[1])


OUVRIR = """(scene) => new Promise((ok, ko) => {
    const r = indexedDB.open('portail-dessin', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('brouillons');
    r.onsuccess = () => {
      const t = r.result.transaction('brouillons', 'readwrite');
      t.objectStore('brouillons').put({ scene, revision: 0, le: Date.now() }, 'essai');
      t.oncomplete = () => ok(); t.onerror = () => ko(t.error);
    };
    r.onerror = () => ko(r.error);
})"""


def plan_2d(navigateur, scene: dict, nom: str) -> Path:
    """Le plan vu de dessus, tel que l'éditeur le dessine : c'est là qu'on vérifie les alignements,
    les passages et les portes avant de filmer."""
    contexte = navigateur.new_context(viewport={"width": 1380, "height": 990}, device_scale_factor=1, reduced_motion="reduce")
    page = contexte.new_page()
    page.goto(f"{adresse()}/api/health")
    page.evaluate(OUVRIR, scene)
    page.goto(f"{adresse()}/dessin/essai", wait_until="networkidle", timeout=180_000)
    for bouton in ("Tout refuser", "Réduire le bandeau d’essai", "Replier structure", "Replier propriétés", "Ajuster à l’écran"):
        b = page.get_by_role("button", name=bouton)
        if b.count():
            b.first.click()
            page.wait_for_timeout(250)
    page.add_style_tag(content="nextjs-portal,[data-nextjs-toast]{display:none!important}")
    page.wait_for_timeout(800)
    image = SORTIE / f"{nom}-plan.jpg"
    SORTIE.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(image), type="jpeg", quality=90)
    contexte.close()
    return image


def filmer(navigateur, scene: dict, reperes: dict, vue: dict, nom: str, apercu: bool) -> Path:
    plan = vue.get("plan", "exterieur")
    fmt = vue.get("format", "carte")
    if fmt not in FORMATS:
        sys.exit(f"Format inconnu « {fmt} » ({', '.join(FORMATS)}).")
    L, H = FORMATS[fmt]
    piece, cible, rayon = cible_de(vue, reperes)
    suffixe = plan + (f"-{piece['type'].replace('_', '-')}" if piece else "") + (f"-{vue['nom']}" if vue.get("nom") else "")
    sortie = SORTIE / f"{nom}-{suffixe}.mp4"
    SORTIE.mkdir(parents=True, exist_ok=True)

    contexte = navigateur.new_context(viewport={"width": L, "height": H}, device_scale_factor=1, reduced_motion="reduce")
    page = contexte.new_page()
    page.goto(f"{adresse()}/api/health")
    # La maquette est déposée là où l'éditeur d'essai garde son plan (IndexedDB), puis l'éditeur est ouvert.
    page.evaluate(OUVRIR, scene)
    page.goto(f"{adresse()}/dessin/essai", wait_until="networkidle", timeout=180_000)
    refuser = page.get_by_role("button", name="Tout refuser")
    if refuser.count():
        refuser.click()
    page.get_by_role("radio", name="3D", exact=True).click()
    page.wait_for_selector('[data-testid="vue-3d"]', timeout=60_000)
    niveaux = page.locator("select").first
    if plan == "exterieur":
        niveaux.select_option("__exterieur")          # « Extérieur · tout fermé » : le toit se montre
    elif piece and piece["niveau"] > 0:
        niveaux.select_option(piece["niveauId"])
    if vue.get("murs") == "entiers" and plan != "exterieur":
        page.get_by_role("radio", name="Murs entiers").click()
    page.wait_for_timeout(600)

    # La vue 3D prend toute l'image (le reste de l'éditeur passe dessous), puis le site recadre.
    page.add_style_tag(content="nextjs-portal,[data-nextjs-toast]{display:none!important}")
    page.evaluate("""() => {
        const el = document.querySelector('[data-testid="vue-3d"]');
        const racine = el.tagName === 'CANVAS' ? el.parentElement.parentElement : el;
        racine.style.cssText += ';position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;z-index:2147483000!important';
        window.dispatchEvent(new Event('resize'));
    }""")
    page.wait_for_timeout(800)
    page.get_by_role("button", name="Ajuster à l’écran").evaluate("(e) => e.click()")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)        # modèles 3D et textures chargés

    # ----- La caméra. Le site l'a posée à `depart` du centre du cadre ; on la déplace à la souris :
    # glisser = déplacer le point regardé, molette = distance, clic droit glissé = tourner.
    aspect = L / H
    depart = distance_de_cadrage(reperes["cadre"]["rayon"], aspect)
    # le cadre du site compte tout le jardin : en extérieur on serre d'office (zoom 1.45), sinon 1
    marge = {"piece": 1.25, "large": 1.2, "exterieur": 1.1 / 1.45}[plan]
    voulue = distance_de_cadrage(rayon, aspect, marge) / float(vue.get("zoom", 1))
    cx, cz = reperes["cadre"]["centre"]
    wx, wz = cible[0] - cx, cible[1] - cz
    norme = math.hypot(DIRECTION[0], DIRECTION[2])
    avant = (-DIRECTION[0] / norme, -DIRECTION[2] / norme)     # vers où regarde la caméra, au sol
    droite = (-avant[1], avant[0])
    k = 2 * depart * math.tan(CHAMP / 2) / H                    # mètres au sol par pixel glissé
    glisser(page, "left", -(wx * droite[0] + wz * droite[1]) / k, (wx * avant[0] + wz * avant[1]) / k, L, H)
    page.mouse.move(L / 2, H / 2)
    crans = math.log(voulue / depart) / math.log(0.95)           # un cran de molette = 5 % de distance
    for _ in range(int(abs(crans))):
        page.mouse.wheel(0, -100 if crans > 0 else 100)
    reste = abs(crans) - int(abs(crans))
    if reste > 0.05:
        page.mouse.wheel(0, (-100 if crans > 0 else 100) * reste)
    hauteur_vue = float(vue.get("hauteur", 52 if plan == "piece" else 45 if plan == "large" else ELEVATION))
    tour = float(vue.get("tour", 40))
    debut = float(vue.get("depart", -tour / 2))
    par_degre = H / 360                                          # pixels de clic droit glissé par degré
    glisser(page, "right", -debut * par_degre, (hauteur_vue - ELEVATION) * par_degre, L, H)
    page.wait_for_timeout(700)
    deux_images(page)

    if apercu:
        image = sortie.with_suffix(".jpg")
        image.write_bytes(image_3d(page))
        contexte.close()
        return image

    # ----- Le tournage : la caméra tourne d'un petit angle, une image, et ainsi de suite.
    ips = da()["format"]["ips"]
    images = max(2, round(float(vue.get("duree", 4)) * ips))
    with tempfile.TemporaryDirectory() as tmp:
        page.mouse.move(L / 2, H / 2)
        page.mouse.down(button="right")
        for i in range(images):
            page.mouse.move(L / 2 - tour * par_degre * i / (images - 1), H / 2)
            Path(f"{tmp}/{i:04d}.jpg").write_bytes(image_3d(page))
        page.mouse.up(button="right")
        contexte.close()
        ffmpeg("-framerate", ips, "-i", f"{tmp}/%04d.jpg", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", sortie)
        shutil.copyfile(f"{tmp}/{images // 2:04d}.jpg", sortie.with_suffix(".jpg"))
    ffmpeg("-i", sortie, "-frames:v", 1, "-vf", f"fps={6 / (images / ips):.3f},scale=320:-2,tile=6x1", "-q:v", 4,
           sortie.with_name(sortie.stem + "-planche.jpg"))
    return sortie


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("fiche", nargs="?", help="la fiche du chantier (JSON)")
    p.add_argument("--catalogue", action="store_true", help="liste ce qu'on peut mettre dans une fiche")
    p.add_argument("--apercu", action="store_true", help="une image par vue au lieu d'une vidéo")
    p.add_argument("--plan", choices=["piece", "large", "exterieur"], help="filmer cette seule vue (au lieu des \"vues\" de la fiche)")
    p.add_argument("--piece", help="la pièce visée (type : cuisine, salle_de_bain... ou son numéro)")
    p.add_argument("--tour", type=float, help="angle parcouru par la caméra, en degrés (défaut 40 ; négatif = autre sens)")
    p.add_argument("--duree", type=float, help="durée de la vidéo, en secondes (défaut 4)")
    p.add_argument("--format", choices=list(FORMATS), help="carte (défaut, pour une carte dans la vidéo), vertical ou carre")
    p.add_argument("--zoom", type=float, help="1 = cadrage normal ; 1.3 = plus près ; 0.8 = plus loin")
    a = p.parse_args()
    if a.catalogue:
        catalogue()
        return
    if not a.fiche:
        p.error("donne une fiche de chantier, ou --catalogue")
    chemin = Path(a.fiche)
    if not chemin.exists():
        sys.exit(f"Fiche introuvable : {chemin}")
    fiche = json.loads(chemin.read_text(encoding="utf-8"))
    if not en_marche():
        sys.exit("Le site ne tourne pas sur cette machine. Lance d'abord : python machine/site_local.py demarrer")
    nom = fiche.get("nom") or chemin.stem
    resultat = json.loads(tsx(str(chemin)))
    scene, reperes = resultat["scene"], resultat["reperes"]
    print(f"Maquette « {nom} » : {len(scene['niveaux'])} niveau(x), {reperes['objets']} objet(s), pièces : "
          + ", ".join(f"{q['type']} ({q['surface']} m²)" for q in reperes["pieces"]))
    if a.plan:
        vues = [{"plan": a.plan, **({"piece": int(a.piece) if a.piece.isdigit() else a.piece} if a.piece else {})}]
    else:
        vues = fiche.get("vues") or [{"plan": "piece", "piece": reperes["pieces"][0]["type"]} if fiche.get("piece")
                                     else {"plan": "exterieur"}]
    for v in vues:
        for cle in ("tour", "duree", "format", "zoom"):
            if getattr(a, cle) is not None:
                v[cle] = getattr(a, cle)

    from playwright.sync_api import sync_playwright
    import os
    with sync_playwright() as pw:
        # Rendu 3D sans carte graphique : le moteur logiciel de Chromium
        navigateur = pw.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH") or None,
                                        args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        if a.apercu:
            print(f"  {plan_2d(navigateur, scene, nom).relative_to(RACINE)}   (vue de dessus : à regarder en premier)")
        for v in vues:
            fichier = filmer(navigateur, scene, reperes, v, nom, a.apercu)
            print(f"  {fichier.relative_to(RACINE)}")
        navigateur.close()
    if not a.apercu:
        print("À poser dans plan.json, clé \"broll\" (mode \"carte\"), après avoir regardé les planches.")


if __name__ == "__main__":
    main()
