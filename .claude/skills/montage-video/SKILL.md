---
name: montage-video
description: Monter un reel / TikTok / Short vertical Portail Travaux à partir d'un rush (transcription, coupe des blancs et des ratés, sous-titres mot à mot, accroche, chiffres, plans de coupe, carton « Commente <MOT> », relecture). Utiliser quand on demande de monter, éditer, refaire ou corriger une vidéo, de chercher des plans de coupe, ou de changer l'univers visuel (la DA) des vidéos.
---

# Montage vidéo vertical

Tu es le monteur de Portail Travaux. Tu pars d'un rush filmé au téléphone et tu sors une vidéo
1080x1920 prête à publier dans `montages/`, dans l'univers de la marque (`config/da.yaml`).

La chaîne : **transcrire → couper → planifier → monter → regarder → corriger**.
Chaque étape est un script de `machine/`. Ton travail à toi, ce sont les décisions de monteur :
quoi couper, quoi mettre à l'écran et à quel moment.

Avant de commencer : relis `CLAUDE.md` (ton, règles) et, si le rush vient du calendrier, le post dans
`sorties/<semaine>/calendrier.json` (accroche, script, mot-clé, réseau).
Si `montage/node_modules/` n'existe pas : `cd montage && npm install` (une fois).

## 1. Transcrire

```bash
python machine/transcrire.py rushs/<semaine>-<numero>-<heure>.webm
```

- Plusieurs prises du même post : prends la dernière, sauf indication contraire.
- Le projet s'appelle `<semaine>-<numero>` (ou `--id <nom>`) et vit dans `montage/projets/<id>/`.
- Moteur : ElevenLabs Scribe si `ELEVENLABS_API_KEY` est dans `.env`, sinon Whisper en local.
  Ajoute `--mots-cles "MaPrimeRénov', RGE"` pour les noms propres du sujet.
- Le script affiche le texte phrase par phrase avec les temps du rush et les blancs. Compare avec le
  script prévu : une phrase dite deux fois, une hésitation, un « euh non » = une prise ratée.

## 2. Couper

```bash
python machine/couper.py <id> --retirer 5.4-10.9 31.2-33
```

- Les blancs partent tout seuls. Toi, tu donnes les prises ratées (`--retirer DEBUT-FIN`, temps du
  rush) : on garde toujours la DERNIÈRE version d'une phrase répétée.
- Le script affiche le texte final avec le numéro de chaque mot (`12:devis`). Ces numéros servent de
  repères dans le plan (`"m12"`). Si tu recoupes, les numéros changent : refais le plan après.

## 3. Écrire le plan de montage

Écris `montage/projets/<id>/plan.json`. Format complet et exemple : `references/plan.md`.
Les décisions à prendre, dans cet ordre :

1. **Corrections** : relis chaque mot. Corrige les fautes de transcription, écris les prix en chiffres
   (`6 000`, `€`), mets le mot-clé EN MAJUSCULES. Une faute dans un sous-titre se voit plus qu'un faux raccord.
2. **Accroche** : la phrase écrite en haut dès la 1re image. 6 à 9 mots, une promesse ou une tension,
   pas la répétition mot pour mot de ce qui est dit. Entoure la partie forte d'astérisques.
3. **Chiffres** : chaque prix ou pourcentage prononcé mérite sa carte, calée sur les mots qui le disent.
   Toujours des fourchettes réalistes (règle de `CLAUDE.md`), jamais un chiffre que le rush ne dit pas.
4. **Plans de coupe** : un changement visuel toutes les 3 à 5 secondes. Cherche-les (étape 3 bis), puis
   cale-les sur les mots qui en parlent. `carte` laisse le visage visible, `plein` le remplace.
5. **Mots forts** (`emphase`) : 3 à 6 dans la vidéo, pas plus. Les chiffres et le mot-clé le sont déjà.
6. **Carton de fin** : automatique dès que « commente » ou « tape » est dit. Adapte `suite` à la ressource
   promise (« et je t'envoie la checklist en DM »).

### 3 bis. Plans de coupe

```bash
python machine/broll.py liste                                   # ce qu'on a déjà
python machine/broll.py pexels "carrelage salle de bain" -n 3   # libre de droits (PEXELS_API_KEY)
python machine/broll.py ecran https://france-renov.gouv.fr      # une page web filmée en vertical
python machine/broll.py importer chemin/vers/clip.mp4           # un fichier fourni (téléphone, IA vidéo)
```

- Pexels : cherche en anglais si le français ne donne rien. Ouvre l'image ou une vignette avant de
  choisir : un plan hors sujet fait plus de mal que pas de plan.
- Écran web : pour montrer une source officielle, un simulateur, et le site de la marque quand il
  sera en ligne (`python machine/ecrans.py`, pages listées dans `config/marque.yaml`).
- On n'utilise que des images dont on a les droits. Pas d'extraits de films, de séries ou de vidéos
  d'autres créateurs, même courts : c'est la règle de `CLAUDE.md`, et un retrait pour droits d'auteur
  pénalise le compte. Si on te le demande, explique-le et propose un plan Pexels ou une carte à la place.

## 4. Monter et regarder les images clés

```bash
python machine/monter.py <id> --apercu
```

Ouvre `montage/projets/<id>/apercu/planche.jpg` et vérifie, image par image :
- l'accroche est lisible et complète dès 0.00 s ;
- aucun texte sur le visage, ni dans les bandes haute et basse (interface des réseaux) ;
- les sous-titres disent exactement ce qui est dit, sans faute ;
- chaque carte et chaque plan de coupe tombe sur la bonne phrase ;
- le carton de fin n'apparaît qu'à l'appel à l'action.

Corrige `plan.json` et relance tant que ce n'est pas bon. C'est rapide (quelques secondes).
Une erreur signalée par le contrôle (ligne `✗`) doit être corrigée avant tout rendu.

## 5. Rendre, puis relire avec « les yeux »

```bash
python machine/monter.py <id> --rendu     # -> montages/<id>.mp4 (compte 5 à 6 fois la durée de la vidéo)
python machine/yeux.py <id>
```

`yeux.py` produit dans `montage/projets/<id>/yeux/` :
- `planche.jpg` (une image toutes les 2 s) et `premiere-image.jpg` : ouvre-les et juge ;
- les mesures du son (niveau, blancs oubliés) ;
- si `GEMINI_API_KEY` est dans `.env` : la critique de Gemini, qui regarde la vidéo en mouvement et
  avec le son (rythme, synchronisation, accroche), avec des corrections horodatées.

Traite tout ce qui est « bloquant » ou « important », corrige le plan, rends de nouveau.
Deux passes suffisent presque toujours ; au-delà de trois, montre où tu en es et demande un avis.
Gemini donne un avis, pas un ordre : s'il réclame quelque chose de contraire à la DA ou à `CLAUDE.md`,
garde la DA et dis-le.

## 6. Livrer

- Montre la vidéo (`montages/<id>.mp4`) et résume en trois lignes : durée, ce qui a été coupé, ce
  qui a été ajouté. Signale ce qui reste discutable plutôt que de le cacher.
- Applique les retours (retour à l'étape 3) et rends une V2.
- Une fois validée : lien public de la vidéo dans la colonne `url_media` de
  `sorties/<semaine>/calendrier.csv` ; `publier_instagram.py` la publie à l'heure prévue.
- Si un retour vaut pour toutes les vidéos (« sous-titres plus gros », « moins de zooms »), change
  `config/da.yaml`, pas seulement ce plan, et note la leçon dans `CLAUDE.md`, « Ce qu'on a appris ».

## La DA (l'univers visuel)

Tout est dans `config/da.yaml` (réglages communs) et `config/univers/<nom>.yaml` (couleurs, police,
cartes, motif). Détails et marche à suivre pour créer un univers : `references/da.md`.

```bash
python machine/monter.py --planche                    # la DA sans rush -> montage/da/planche-<univers>.jpg
python machine/monter.py --planche --univers chantier # comparer un autre univers
python machine/monter.py <id> --apercu --univers plan # essayer un univers sur une vraie vidéo
```

Ne mets jamais de couleur, de police ou de taille « en dur » dans un montage : si ça doit changer,
ça change dans la DA, pour toutes les vidéos.

## Aller plus loin que le gabarit

Le montage est une composition HyperFrames (du HTML animé avec GSAP, rendu en MP4). Pour une
animation sur mesure (schéma, comparaison avant/après, liste qui se coche), ajoute un fichier
`extras.html` au projet : règles et exemple dans `references/hyperframes.md`.
Pour changer l'allure de toutes les vidéos, modifie `montage/gabarit/` (CSS et animation).
