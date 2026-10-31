"""Outils partagés : config, cerveau IA, appel à Claude."""

import json
import re
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent
MODELE = "claude-opus-5-5"
DOSSIER_RESSOURCES = RACINE / "ressources"

load_dotenv(RACINE / ".env")


def config() -> dict:
    return yaml.safe_load((RACINE / "config" / "marque.yaml").read_text(encoding="utf-8"))


def cerveau() -> str:
    """Le « cerveau IA » : qui on est, comment on parle (CLAUDE.md)."""
    return (RACINE / "CLAUDE.md").read_text(encoding="utf-8")


def client() -> anthropic.Anthropic:
    return anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans .env


def generer_structure(prompt: str, schema, effort: str = "high"):
    """Demande à Claude une réponse qui respecte exactement le schéma Pydantic."""
    reponse = client().beta.messages.parse(
        model=MODELE,
        max_tokens=64000,
        system=cerveau(),
        output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
    )
    if reponse.stop_reason == "refusal":
        raise SystemExit("La génération a été refusée, reformule la demande.")
    return reponse.parsed_output


def slug(mot: str) -> str:
    return re.sub(r"[^a-z0-9]", "", mot.lower())


def enregistrer_ressource(mot: str, titre: str, promesse: str, contenu: str) -> None:
    """Sauvegarde une ressource servie sur /ressource/<mot>."""
    DOSSIER_RESSOURCES.mkdir(exist_ok=True)
    fichier = DOSSIER_RESSOURCES / f"{slug(mot)}.json"
    if fichier.exists():  # on n'écrase jamais une ressource déjà en ligne
        return
    fichier.write_text(
        json.dumps({"mot": slug(mot), "titre": titre, "promesse": promesse, "contenu": contenu},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
