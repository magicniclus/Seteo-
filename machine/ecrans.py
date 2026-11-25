"""Filme automatiquement ton site, en format vertical (téléphone).

Chaque page listée dans `pages_ecran` (config/marque.yaml) est ouverte dans un navigateur,
défile doucement (et clique sur les boutons demandés) pendant l'enregistrement. Les vidéos
servent de plans de coupe dans tes reels (« regarde, sur le site tu fais ça... »).

Résultat : ecrans/<nom>.mp4 (vidéo 1080x1920) + ecrans/<nom>.png (capture pleine page)
Nécessite ffmpeg (voir README).

Usage :
    python machine/ecrans.py               # toutes les pages
    python machine/ecrans.py accueil       # une seule page
"""

import json
import os
import shutil
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

from commun import RACINE, config

DOSSIER = RACINE / "ecrans"

# Masquage des données privées, exécuté dans la page AVANT son premier affichage et à chaque changement.
# Les éléments désignés (et, en mode privé, tout e-mail ou numéro de téléphone) voient leurs lettres
# remplacées par des « x » et leurs chiffres par des « 0 », puis sont floutés : la vraie valeur
# n'est jamais dessinée, donc elle n'est dans aucune image de la vidéo.
MASQUAGE = r"""
(() => {
  const SELECTEURS = __SELECTEURS__, PRIVE = __PRIVE__;
  const COORD = /[\w.+-]+@[\w-]+(?:\.[\w-]+)+|(?:\+33\s?|0)[1-9](?:[\s.-]?\d{2}){4}/g;
  const masque = (t) => t.replace(/\p{L}/gu, "x").replace(/\d/g, "0");
  const style = document.createElement("style");
  style.textContent = (SELECTEURS.length ? SELECTEURS.join(",") + "{filter:blur(11px)!important;}" : "") +
    (SELECTEURS.length ? SELECTEURS.map((s) => s + " input," + s + " textarea," + "input" + s + ",textarea" + s).join(",") +
      "{-webkit-text-security:disc!important;}" : "") + "[data-masque]{filter:blur(11px)!important;}";
  const textes = (racine) => {
    const w = document.createTreeWalker(racine, NodeFilter.SHOW_TEXT), liste = [];
    while (w.nextNode()) liste.push(w.currentNode);
    return liste;
  };
  const passer = () => {
    if (!style.isConnected && document.documentElement) (document.head || document.documentElement).appendChild(style);
    if (!document.body) return;
    for (const s of SELECTEURS) for (const zone of document.querySelectorAll(s)) for (const n of textes(zone)) {
      const m = masque(n.nodeValue);
      if (m !== n.nodeValue) n.nodeValue = m;
    }
    if (!PRIVE) return;
    for (const n of textes(document.body)) {
      if (n.parentElement && (n.parentElement.closest("[data-masque],script,style"))) continue;
      COORD.lastIndex = 0;
      const t = COORD.exec(n.nodeValue);
      if (!t) continue;
      const suite = n.splitText(t.index), reste = suite.splitText(t[0].length);
      const span = document.createElement("span");
      span.dataset.masque = "1";
      span.textContent = masque(t[0]);
      suite.replaceWith(span);
      void reste;
    }
  };
  new MutationObserver(passer).observe(document, { childList: true, subtree: true, characterData: true });
  document.addEventListener("DOMContentLoaded", passer);
  passer();
})();
"""


SANS_BANDEAUX = r"""
(() => {
  const style = document.createElement("style");
  style.textContent = "nextjs-portal,[data-nextjs-toast],#__next-build-watcher{display:none!important}";
  const poser = () => { if (!style.isConnected && document.documentElement) (document.head || document.documentElement).appendChild(style); };
  // Bandeau de cookies : on le referme (« Tout refuser ») dès qu'il apparaît.
  const refuser = () => {
    for (const b of document.querySelectorAll("button")) {
      const t = (b.textContent || "").trim().toLowerCase();
      if (t === "tout refuser" || t === "refuser" || t === "continuer sans accepter") { b.click(); return true; }
    }
    return false;
  };
  new MutationObserver(() => { poser(); refuser(); }).observe(document, { childList: true, subtree: true });
  poser();
})();
"""


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
    if page_cfg.get("flouter") or page_cfg.get("prive"):
        contexte.add_init_script(MASQUAGE.replace("__SELECTEURS__", json.dumps(page_cfg.get("flouter") or []))
                                 .replace("__PRIVE__", "true" if page_cfg.get("prive") else "false"))
    # Ni bandeau de cookies ni pastille de développement (copie locale du site) dans le plan filmé
    contexte.add_init_script(SANS_BANDEAUX)
    page = contexte.new_page()
    debut_film = time.monotonic()  # l'enregistrement démarre ici, page encore blanche
    page.goto(page_cfg["url"], wait_until="networkidle")
    chargement = time.monotonic() - debut_film
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
    # -ss : on jette le temps de chargement (écran blanc) pour que le plan démarre sur la page
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{chargement:.2f}", "-i", str(brut),
                    "-vf", "scale=1080:1920:flags=lanczos",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(cible)], check=True)
    print(f"  {page_cfg['nom']} -> {cible}")


def main() -> None:
    pages = config().get("pages_ecran") or []
    if not pages:
        print("Aucune page à filmer : remplis pages_ecran dans config/marque.yaml quand le site sera en ligne.")
        return
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
