"""Lance une copie du site Portail Travaux sur cette machine, pour le filmer (outil Dessin, maquettes 3D).

Rien ne touche au vrai site : la copie tourne sur les émulateurs Firebase, avec des données fictives
seulement. Le dépôt, la branche et le dossier sont dans config/marque.yaml (`site_local`).

Usage :
    python machine/site_local.py demarrer    # récupère le code s'il manque, installe, lance, ouvre l'outil Dessin
    python machine/site_local.py etat        # tourne-t-il ?
    python machine/site_local.py arreter

Il faut Node 22, pnpm 10 et Java 21 (les mêmes prérequis que le site). Premier lancement : quelques minutes.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

from atelier import BROLL, RACINE

PROJET = "demo-portail-travaux"      # projet « demo- » : les émulateurs n'ont aucun accès au vrai Firebase
JOURNAL = BROLL / "site-local.log"
PID = BROLL / "site-local.pid"


def reglages() -> dict:
    r = yaml.safe_load((RACINE / "config" / "marque.yaml").read_text(encoding="utf-8")).get("site_local") or {}
    dossier = Path(os.getenv("SITE_PORTAIL") or (RACINE / r.get("dossier", "../site-portail-travaux"))).resolve()
    return {"depot": r.get("depot", ""), "branche": r.get("branche", "main"), "dossier": dossier,
            "port": int(r.get("port", 3200))}


def adresse() -> str:
    return f"http://localhost:{reglages()['port']}"


def en_marche() -> bool:
    try:
        return requests.get(f"{adresse()}/api/health", timeout=4).status_code == 200
    except requests.RequestException:
        return False


def allumer_dessin() -> None:
    """L'outil Dessin est derrière deux interrupteurs (flags `dessin` et `dessinPublic`) : on les allume
    dans la base de l'émulateur, au même endroit que l'administration du site (config/flags)."""
    r = requests.patch(
        f"http://127.0.0.1:8080/v1/projects/{PROJET}/databases/(default)/documents/config/flags",
        params=[("updateMask.fieldPaths", "valeurs.dessin"), ("updateMask.fieldPaths", "valeurs.dessinPublic")],
        headers={"Authorization": "Bearer owner"}, timeout=20,
        json={"fields": {"valeurs": {"mapValue": {"fields": {
            "dessin": {"booleanValue": True}, "dessinPublic": {"booleanValue": True}}}}}})
    if r.status_code != 200:
        sys.exit(f"Impossible d'allumer l'outil Dessin sur l'émulateur ({r.status_code}) : {r.text[:200]}")


def demarrer(_a) -> None:
    r = reglages()
    dossier = r["dossier"]
    if not (dossier / "package.json").exists():
        if not r["depot"]:
            sys.exit("config/marque.yaml : renseigne site_local.depot (ex. « moncompte/mon-site »).")
        if dossier.exists() and any(dossier.iterdir()):
            sys.exit(f"{dossier} existe mais ne contient pas le site (pas de package.json). "
                     f"Vérifie la branche (site_local.branche : {r['branche']}).")
        print(f"Récupération du site ({r['depot']}, branche {r['branche']})...")
        dossier.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "--branch", r["branche"],
                        f"https://github.com/{r['depot']}", str(dossier)],
                       check=True, env={**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"})
    if not (dossier / "node_modules").exists():
        print("Installation des dépendances du site (pnpm install)...")
        subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=dossier, check=True)
    if not (dossier / ".env.local").exists():
        (dossier / ".env.local").write_text("", encoding="utf-8")
    if en_marche():
        allumer_dessin()
        print(f"Le site tourne déjà : {adresse()}")
        return
    BROLL.mkdir(exist_ok=True)
    # Aucune statistique d'usage envoyée (Next.js, Firebase) ; contrôles réservés à la production coupés.
    env = {**os.environ, "CI": "1", "NEXT_TELEMETRY_DISABLED": "1", "FIREBASE_CLI_DISABLE_UPDATE_CHECK": "1"}
    web = (f"NEXT_TELEMETRY_DISABLED=1 APP_CHECK_MODE=desactive ADMIN_MFA=desactive DOMAINE_SITES=localhost "
           f"pnpm --filter @ph/web dev --port {r['port']}")
    with open(JOURNAL, "w", encoding="utf-8") as journal:
        p = subprocess.Popen(["pnpm", "exec", "firebase", "emulators:exec", "--project", PROJET,
                              "--only", "auth,firestore,storage", web],
                             cwd=dossier, env=env, stdout=journal, stderr=subprocess.STDOUT, start_new_session=True)
    PID.write_text(str(p.pid), encoding="utf-8")
    print("Lancement du site et des émulateurs (une à trois minutes la première fois)...")
    for _ in range(100):
        if en_marche():
            break
        if p.poll() is not None:
            sys.exit(f"Le site s'est arrêté au lancement. Fin du journal ({JOURNAL}) :\n"
                     + JOURNAL.read_text(encoding="utf-8", errors="replace")[-1500:])
        time.sleep(3)
    else:
        sys.exit(f"Le site ne répond pas après 5 minutes. Journal : {JOURNAL}")
    allumer_dessin()
    time.sleep(3)   # le site relit ses interrupteurs toutes les 2 secondes sur émulateur
    print(f"Site prêt : {adresse()}  (outil Dessin : {adresse()}/dessin/essai)")


def arreter(_a) -> None:
    if PID.exists():
        try:
            os.killpg(int(PID.read_text()), signal.SIGTERM)
        except (ProcessLookupError, ValueError, PermissionError):
            pass
        PID.unlink(missing_ok=True)
    print("Site arrêté." if not en_marche() else "Le site répond encore : il a été lancé autrement (pnpm dev ?).")


def etat(_a) -> None:
    r = reglages()
    print(f"Dossier : {r['dossier']} ({'présent' if (r['dossier'] / 'package.json').exists() else 'absent'})")
    print(f"Site    : {adresse()} ({'en marche' if en_marche() else 'arrêté'})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sous = p.add_subparsers(dest="commande", required=True)
    for nom, action in (("demarrer", demarrer), ("arreter", arreter), ("etat", etat)):
        sous.add_parser(nom).set_defaults(action=action)
    a = p.parse_args()
    a.action(a)


if __name__ == "__main__":
    main()
