---
name: montage-video
description: Monter un reel / TikTok / Short vertical à partir d'un rush et d'un script du calendrier Portail Habitat. Utiliser quand on demande de monter, éditer ou refaire une vidéo.
---

# Montage vidéo vertical (Remotion)

Objectif : à partir d'un rush et du script du post, produire une vidéo 1080x1920 prête à
publier dans `montages/`.

- Les prises enregistrées au prompteur arrivent dans `rushs/<semaine>-<numéro>-<heure>.webm`
  (plusieurs prises possibles : prends la meilleure, ou la dernière si on ne précise pas).
- Les vidéos du site Portail Habitat sont dans `ecrans/*.mp4` (1080x1920, déjà au bon format) :
  s'il en manque une, lance `python machine/ecrans.py <nom>`.

## Étapes

1. Lis le post concerné dans `sorties/<semaine>/calendrier.json` (accroche, script, mot-clé)
   et relis `CLAUDE.md` pour le ton et la charte.
2. Si le dossier `montage/` n'existe pas, crée un projet Remotion dedans
   (`npx create-video@latest montage`, modèle « Blank »), format 1080x1920, 30 i/s.
3. Transcris le rush avec Whisper (`pip install openai-whisper`,
   `whisper rush.webm --language fr --output_format json --word_timestamps True`) pour avoir
   le minutage de chaque mot.
4. Coupe les blancs et les ratés : garde seulement les phrases du script, enchaînées serrées.
5. Ajoute :
   - sous-titres mot par mot, gros, centrés, le mot en cours surligné (couleur d'accent),
   - un zoom léger toutes les 2 à 4 secondes pour garder le rythme,
   - les chiffres et les prix en grand à l'écran quand ils sont prononcés,
   - dès que le script parle du site (inscription, recherche d'artisan, devis...), un plan de
     coupe tiré de `ecrans/` : en plein écran ou en incrustation au-dessus de la tête,
   - à la fin, un carton « Commente <MOT> » (Instagram/Facebook) ou « Lien en bio : <MOT> »
     (TikTok/Shorts).
6. Ne recopie jamais le design d'une vidéo d'origine : couleurs, polices et éléments sont
   les nôtres (voir `CLAUDE.md`).
7. Rends la vidéo : `npx remotion render <Composition> ../montages/<semaine>-<numero>.mp4`.
8. Montre le résultat et demande les retours. Applique-les, puis rends une V2.
9. Une fois validée, mets-la en ligne (lien public) et remplis la colonne `url_media` du
   `calendrier.csv` : `publier_instagram.py` la publiera à l'heure prévue.
