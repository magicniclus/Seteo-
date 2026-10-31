"""Filme automatiquement le site Portail Habitat, en format vertical (téléphone).

Chaque page listée dans `pages_ecran` (config/marque.yaml) est ouverte dans un navigateur,
défile doucement (et clique sur les boutons demandés) pendant l'enregistrement. Les vidéos
servent de plans de coupe dans tes reels (« regarde, sur Portail Habitat tu fais ça... »).

Résultat : ecrans/<nom>.mp4 (vidéo 1080x1920) + ecrans/<nom>.png (capture pleine page)
Nécessite ffmpeg (voir README).

Usage :
    python machine/ecrans.py               # toutes les pages
    python machine/ecrans.py accueil       # une seule page
"""

import os
import shutil
import subprocess
import sys

from playwright.sync_api import sync_playwright

from commun import RACINE, config

DOSSIER = RACINE / "ecrans"


def filmer(navigateur, page_cfg: dict) -> None:
    contexte = navigateur.new_context(
        viewport={"width": 540, "height": 960},  # écran de téléphone
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        locale="fr-FR",
        record_video_dir=str(DOSSIER / "tmp"),
        record_video_size={"width": 540, "height": 960},
    )
    page = contexte.new_page()
    page.goto(page_cfg["url"], wait_until="networkidle")
    page.wait_for_timeout(1500)  # laisse 1,5 s sur le haut de page (le « hook » visuel)

    # Défilement doux jusqu'en bas (max ~12 s), puis petite remontée
    hauteur = page.evaluate("document.body.scrollHeight")
    pas = max(hauteur // 120, 6)
    for _ in range(min(120, hauteur // pas)):
        page.mouse.wheel(0, pas)
        page.wait_for_timeout(100)
    page.wait_for_timeout(800)
    page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
    page.wait_for_timeout(1500)

    for texte in page_cfg.get("cliquer", []):
        bouton = page.get_by_text(texte, exact=False).first
        bouton.scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        bouton.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

    page.screenshot(path=str(DOSSIER / f"{page_cfg['nom']}.png"), full_page=True)
    video = page.video
    contexte.close()  # la vidéo n'est écrite qu'à la fermeture
    brut = DOSSIER / "tmp" / f"{page_cfg['nom']}.webm"
    video.save_as(brut)
    # Agrandit en 1080x1920 (format Reels/TikTok) et convertit en MP4
    cible = DOSSIER / f"{page_cfg['nom']}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(brut), "-vf", "scale=1080:1920:flags=lanczos",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(cible)], check=True)
    print(f"  {page_cfg['nom']} -> {cible}")


def main() -> None:
    pages = config().get("pages_ecran", [])
    if len(sys.argv) > 1:
        pages = [p for p in pages if p["nom"] in sys.argv[1:]]
    DOSSIER.mkdir(exist_ok=True)
    with sync_playwright() as p:
        # CHROMIUM_PATH : seulement si Chromium est installé ailleurs que par `playwright install`
        navigateur = p.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH") or None)
        for page_cfg in pages:
            try:
                filmer(navigateur, page_cfg)
            except Exception as e:  # une page cassée ne bloque pas les autres
                print(f"  {page_cfg['nom']} : échec ({e})")
        navigateur.close()
    shutil.rmtree(DOSSIER / "tmp", ignore_errors=True)


if __name__ == "__main__":
    main()
