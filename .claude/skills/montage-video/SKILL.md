---
name: montage-video
description: Monter un reel / TikTok / Short vertical Portail Travaux à partir d'une vidéo filmée au téléphone (transcription, coupe des blancs et des ratés, sous-titres mot à mot, accroche, chiffres, animations plein écran, plans de coupe, carton « Commente <MOT> », relecture). Utiliser quand on envoie ou mentionne une vidéo à monter, quand on demande de monter, éditer, refaire ou corriger une vidéo, de chercher des plans de coupe, d'ajouter une animation, ou de changer l'univers visuel (la DA) des vidéos.
---

# Montage vidéo vertical

Tu es le monteur de Portail Travaux. On te donne une vidéo filmée au téléphone (une personne qui
parle face caméra) et tu sors une vidéo 1080x1920 prête à publier dans `montages/`, animée dans
l'univers de la marque (`config/da.yaml`).

La chaîne : **récupérer → transcrire → couper → planifier → monter → regarder → corriger**.
Chaque étape est un script de `machine/`. Ton travail à toi, ce sont les décisions de monteur :
quoi couper, quoi mettre à l'écran et à quel moment.

Trois règles qui ne se discutent pas :
- **La seule voix est celle de la vidéo.** On n'ajoute jamais de voix off, de voix de synthèse ni de
  doublage. De la musique seulement si on la demande et qu'on fournit le fichier.
- **On ne fait pas dire à la personne ce qu'elle n'a pas dit** : sous-titres fidèles, pas de chiffre
  ni de promesse ajoutés à l'écran.
- **Aucune donnée d'un client en clair** (nom, adresse, téléphone, e-mail) dans une vidéo : voir
  « Demandes de clients » plus bas.

Avant de commencer : relis `CLAUDE.md` (ton, règles). Si la vidéo vient du calendrier, lis le post
dans `sorties/<semaine>/calendrier.json` (accroche, script, mot-clé, réseau). Sinon, demande le
mot-clé à commenter et le réseau visé s'ils ne sont pas dits dans la vidéo.
Si `montage/node_modules/` n'existe pas : `cd montage && npm install` (une fois).
Il faut aussi `pip install -r requirements.txt -r requirements-montage.txt`.

## 0. Récupérer la vidéo

- Jointe à la conversation : elle est déjà sur le disque, son chemin est indiqué avec le message.
- Enregistrée au prompteur : `rushs/<semaine>-<numero>-<heure>.webm` (plusieurs prises : la dernière).
- Donnée par un lien : télécharge-la dans `rushs/` avec `curl -L -o rushs/<nom>.mp4 "<lien>"`.
  Dropbox : remplace `dl=0` par `dl=1`. Google Drive : `https://drive.google.com/uc?export=download&id=<ID>`.
  Vérifie avec `ffprobe` que c'est bien une vidéo (une page web téléchargée à la place = lien non direct).
- Tous les formats de téléphone passent (MP4, MOV, HEVC, HDR, 4K, 60 i/s, horizontal) : `couper.py`
  remet tout en 1080x1920, 30 i/s, couleurs normales. Une vidéo horizontale est rognée au centre :
  si la personne n'y est pas, recadre d'abord le fichier avec ffmpeg (`crop`) avant de transcrire.

## 1. Transcrire

```bash
python machine/transcrire.py rushs/ma-video.mp4 --id <nom-court>
```

- Le projet vit dans `montage/projets/<id>/`. Pour un rush du prompteur, l'id est `<semaine>-<numero>`.
- Moteur : ElevenLabs Scribe si `ELEVENLABS_API_KEY` existe, sinon Whisper en local. Avec Whisper,
  s'il y a beaucoup de fautes, relance avec `--modele-whisper medium` (plus lent, plus juste).
  `--mots-cles "MaPrimeRénov', RGE"` aide pour les noms propres du sujet.
- Le script affiche le texte phrase par phrase avec les temps du rush et les blancs. Une phrase dite
  deux fois, une hésitation, un « euh non » = une prise ratée à retirer.

## 2. Couper et vérifier le cadrage

```bash
python machine/couper.py <id> --retirer 5.4-10.9 31.2-33
```

- Les blancs partent tout seuls. Toi, tu donnes les prises ratées (`--retirer DEBUT-FIN`, temps du
  rush) : on garde toujours la DERNIÈRE version d'une phrase répétée.
- Le script affiche le texte final avec le numéro de chaque mot (`12:devis`). Ces numéros servent de
  repères dans le plan (`"m12"`). Si tu recoupes, les numéros changent : refais le plan après.
- **Ouvre `montage/projets/<id>/cadrage.jpg`** : trois moments de la prise avec les repères de la DA.
  Bandes sombres = interface des réseaux, bande jaune = sous-titres, trait rouge = centre des zooms.
  Le menton doit être au-dessus du jaune et les yeux près du rouge. Sinon, corrige pour cette vidéo
  dans le plan : `"reglages": {"visage_y": 0.45, "centre_y": 1330}` (`visage_y` = hauteur des yeux
  de 0 à 1 ; `centre_y` = milieu des sous-titres en pixels, 1380 au plus pour rester hors de la bande basse).
  Si la personne est filmée de trop loin ou mal centrée, dis-le : c'est au tournage que ça se règle.

## 3. Écrire le plan de montage

Écris `montage/projets/<id>/plan.json`. Format complet et exemple : `references/plan.md`.
Les décisions à prendre, dans cet ordre :

1. **Corrections** : relis chaque mot. Corrige les fautes de transcription, écris les prix en chiffres
   (`6 000`, `€`), mets le mot-clé EN MAJUSCULES. Une faute dans un sous-titre se voit plus qu'un faux raccord.
2. **Accroche** : la phrase écrite en haut dès la 1re image. 6 à 9 mots, une promesse ou une tension,
   pas la répétition mot pour mot de ce qui est dit. Entoure la partie forte d'astérisques.
3. **Chiffres** : chaque prix ou pourcentage prononcé mérite sa carte, calée sur les mots qui le disent.
   Toujours des fourchettes réalistes (règle de `CLAUDE.md`), jamais un chiffre que la vidéo ne dit pas.
4. **Blocs** (animations) : dès que la personne énumère, compare ou chiffre, remplace la prise par une
   animation plein écran pendant qu'elle parle. Voir « Les blocs » ci-dessous.
5. **Plans de coupe** : des images réelles sur ce qui est dit (étape 3 bis). `carte` laisse le visage
   visible, `plein` le remplace.
6. **Mots forts** (`emphase`) : 3 à 6 dans la vidéo, pas plus. Les chiffres et le mot-clé le sont déjà.
7. **Carton de fin** : automatique dès que « commente » ou « tape » est dit. Adapte `suite` à la ressource
   promise (« et je t'envoie la checklist en DM »).

Le rythme à viser : quelque chose change à l'écran toutes les 3 à 5 secondes (zoom, carte, bloc, plan
de coupe), mais le visage reste à l'écran au moins la moitié du temps, et toujours pendant les 3
premières secondes et pendant l'appel à l'action. C'est la personne qu'on suit, pas un diaporama.

### Les blocs

Des animations prêtes à l'emploi, inspirées du catalogue HyperFrames et refaites dans la DA.
Détail des champs : `references/plan.md`.

| Bloc | Quand l'utiliser | Type |
|---|---|---|
| `liste` | « les 3 erreurs », « ce qu'il faut vérifier » : 2 à 4 lignes qui se cochent (ou se barrent) | plein écran |
| `barres` | répartition d'un budget, qui coûte quoi : 2 à 4 barres | plein écran |
| `comparaison` | deux devis, deux solutions, avant/après en chiffres ; le bon choix s'encadre | plein écran |
| `avant_apres` | deux photos d'un chantier : celle d'après balaie celle d'avant | plein écran |
| `demande` | la fiche d'une demande de travaux reçue : projet, surface, budget... et le client flouté | plein écran |
| `commentaire` | à l'appel à l'action : une bulle où le mot-clé se tape, puis la réponse | par-dessus, visage visible |
| `nom` | dans les premières secondes : qui parle (nom + rôle) | par-dessus, visage visible |

- Un bloc plein écran dure 3 à 8 s. Cale chaque ligne sur le mot qui la dit (`"quand": "m21"`).
- Le texte d'un bloc résume ce qui est dit : 2 à 4 mots par ligne. Ce n'est pas une retranscription.
- N'invente rien : les chiffres d'un bloc `barres` ou `comparaison` sont ceux que la personne donne.
- Pas de carte de chiffre ni de plan de coupe `carte` pendant un bloc plein écran.
- Besoin d'une animation qui n'existe pas : `references/hyperframes.md` (« Ajouter un bloc »).

### Détourer la personne : deux styles au choix

Pendant une animation, deux mises en scène existent. Le réglage par défaut est `personne_devant`
dans `config/da.yaml` ; le plan d'une vidéo peut décider autrement avec `"detourage"`.

- **L'animation remplace l'image** (`personne_devant: false`, ou `"detourage": false`) : le bloc
  occupe tout l'écran, on ne voit plus la personne quelques secondes. Net, rapide à calculer.
- **La personne reste devant** (`personne_devant: true`, ou `"detourage": {"blocs": "derriere"}`) :
  elle est découpée de son décor, rétrécit vers le bas, et le fond de l'univers avec l'animation
  monte derrière elle. On ne la perd jamais de vue : c'est le style à proposer quand la personne
  est le sujet de la vidéo.

Avec le détourage, on peut aussi :
- faire passer un **plan de coupe derrière elle** (`"mode": "derriere"` dans `broll`) : l'image
  remplit l'écran, elle reste devant. Plusieurs plans peuvent s'enchaîner sans trou (le suivant
  commence exactement où le précédent finit) : elle ne bouge pas entre deux.
- glisser un **mot géant derrière sa tête** (`"mots_derriere"`) : le mot dit à ce moment-là, en un
  ou deux mots, en capitales. Très bon sur un plan « derriere » pour nommer ce qu'on montre.
- changer son décor pour toute la vidéo : `"fond": "flou"` (décor flouté et assombri, pardonne
  beaucoup) ou `"fond": "univers"` (le fond de la DA tout du long ; les contours se voient
  davantage, à vérifier de près).

Règles de cette mise en scène :
- La position du visage décide de tout (taille de la personne, place laissée à l'animation). Si la
  personne bouge d'un passage à l'autre, donne `"visage_y"` sur le bloc ou le plan concerné
  (hauteur des yeux à ce moment-là, de 0 à 1) : regarde `cadrage.jpg` ou une image de la prise.
- Laisse au moins 0,8 s entre un bloc derrière elle et un plan « derriere » : elle doit reprendre
  sa place entre les deux.
- Le détourage se calcule sur la machine (rien n'est envoyé ailleurs), seulement sur les passages
  qui en ont besoin, et il est gardé en réserve : changer un texte ne le relance pas, changer le
  début ou la fin d'un passage si. Compte environ 20 s par seconde de vidéo sans carte graphique,
  et préviens avant de lancer un long calcul.
- Il marche bien sur une personne nette devant un décor qui contraste. Il peine sur les cheveux fins
  devant un fond chargé, les gestes rapides, les objets tenus en main ou posés devant elle (bureau,
  ordinateur). Regarde les contours sur la planche ; s'ils sont laids, reviens au premier style.

### Demandes de clients

Montrer une vraie demande de travaux est un très bon contenu, à une condition : on ne voit rien qui
permette de reconnaître le client.
- **Fiche redessinée** (le plus sûr, le plus lisible) : le bloc `demande`. On y met le projet, la
  surface, le budget, la ville si elle est grande ; le nom, le téléphone, l'e-mail et l'adresse sont
  des champs `"flou": true`. Un champ flou n'est jamais écrit dans la vidéo, même si le plan
  contient sa valeur : n'écris pas la vraie valeur dans le plan, ce n'est pas nécessaire.
- **Écran filmé** de l'outil : `python machine/broll.py ecran <url> --prive --flouter "<sélecteur>" ...`.
  `--prive` masque tout e-mail et tout numéro de téléphone ; `--flouter` désigne les zones du nom et
  de l'adresse (ouvre la page et lis son code pour trouver les bons sélecteurs). Le masquage se fait
  dans la page avant son premier affichage : la vraie valeur n'est dans aucune image.
- Dans les deux cas, regarde chaque image de la planche avant de livrer. Un nom lisible dans un coin,
  une photo de façade reconnaissable, une plaque de rue : on reprend. En cas de doute, on masque.
- Le texte libre du client (sa description) peut contenir son nom ou son adresse : résume-le au lieu
  de le recopier.

### 3 bis. Plans de coupe

```bash
python machine/broll.py liste                                   # ce qu'on a déjà
python machine/broll.py pexels "carrelage salle de bain" -n 3   # libre de droits (PEXELS_API_KEY)
python machine/broll.py ecran https://france-renov.gouv.fr      # une page web filmée en vertical
python machine/broll.py ecran <url de l'outil> --prive --flouter ".client"   # avec des données de clients
python machine/broll.py importer chemin/vers/clip.mp4 --debut 12 --duree 4   # un fichier fourni, un extrait de film
```

- Pexels : cherche en anglais si le français ne donne rien. Ouvre l'image ou une vignette avant de
  choisir : un plan hors sujet fait plus de mal que pas de plan.
- Écran web : pour montrer une source officielle, un simulateur, et le site de la marque quand il
  sera en ligne (`python machine/ecrans.py`, pages listées dans `config/marque.yaml`).
- **Extraits de films, d'émissions, de vidéos d'autres comptes** : c'est un bon ressort (une image
  drôle ou connue posée sur une phrase), à manier selon la source.
  - Film du domaine public (Internet Archive : muets, burlesques, vieux films d'entreprise) : libre.
    Télécharge le film, repère l'instant, puis `broll.py importer <film> --debut <s> --duree <s>`.
  - Film ou série récents, vidéo d'un autre compte (Instagram, TikTok, YouTube) : ne les télécharge
    pas toi-même. Les plateformes l'interdisent, et c'est le genre de pratique qui fait retirer une
    vidéo ou pénaliser un compte. Si on te fournit le fichier (un enregistrement d'écran du
    téléphone suffit), tu peux l'insérer : dis une fois, simplement, que l'extrait appartient à
    quelqu'un d'autre et qu'il peut entraîner un retrait, puis fais ce qui est demandé. Garde
    l'extrait court (2 à 4 s) et, pour la vidéo d'un autre compte, laisse son nom visible.
  - Un extrait horizontal se montre en `carte` (toute son image tient) ; en `plein` il est rogné aux
    côtés : choisis ce qu'on garde avec `"ancre_x"` (0 = la gauche, 0.5 = le centre, 1 = la droite).
  - Cale l'instant fort de l'extrait sur le mot qui le justifie : c'est `"debut"` (où commencer dans
    le fichier) qui se règle, à l'image près. Regarde l'extrait image par image avant de choisir.
- `carte` : pendant que la carte occupe le haut, la prise rétrécit et descend dessous, le visage
  reste visible. `plein` : l'extrait remplace toute l'image, les sous-titres restent.
  `derriere` : l'extrait remplit l'écran derrière la personne détourée (voir « Détourer la personne »).
- **Choisir l'image** : elle doit montrer exactement ce que dit la phrase, au moment où elle le dit
  (il dit « le bois », on voit une scie dans du bois). Une image seulement drôle ou jolie, sans
  rapport direct, distrait. Pour une référence que tout le monde connaît (mème, scène culte,
  tendance du moment), demande l'extrait : c'est la personne qui sait ce qui parle à son public.

## 4. Monter et regarder les images clés

```bash
python machine/monter.py <id> --apercu
```

Ouvre `montage/projets/<id>/apercu/planche.jpg` et vérifie, image par image :
- l'accroche est lisible et complète dès 0.00 s ;
- aucun texte sur le visage, ni dans les bandes haute et basse (interface des réseaux) ;
- les sous-titres disent exactement ce qui est dit, sans faute ;
- chaque carte, bloc et plan de coupe tombe sur la bonne phrase, et rien ne se chevauche ;
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
- si `GEMINI_API_KEY` existe : la critique de Gemini, qui regarde la vidéo en mouvement et
  avec le son (rythme, synchronisation, accroche), avec des corrections horodatées.

Traite tout ce qui est « bloquant » ou « important », corrige le plan, rends de nouveau.
Deux passes suffisent presque toujours ; au-delà de trois, montre où tu en es et demande un avis.
Gemini donne un avis, pas un ordre : s'il réclame quelque chose de contraire à la DA ou à `CLAUDE.md`,
garde la DA et dis-le.

## 6. Livrer

- Envoie la vidéo (`montages/<id>.mp4`) et résume en trois lignes : durée, ce qui a été coupé, ce
  qui a été ajouté. Signale ce qui reste discutable plutôt que de le cacher.
- Applique les retours (retour à l'étape 3) et rends une V2.
- Une fois validée, si la vidéo vient du calendrier : lien public dans la colonne `url_media` de
  `sorties/<semaine>/calendrier.csv` ; `publier_instagram.py` la publie à l'heure prévue.
- Si un retour vaut pour toutes les vidéos (« sous-titres plus gros », « moins de zooms »), change
  `config/da.yaml`, pas seulement ce plan, et note la leçon dans `CLAUDE.md`, « Ce qu'on a appris ».

## La DA (l'univers visuel)

Tout est dans `config/da.yaml` (réglages communs) et `config/univers/<nom>.yaml` (couleurs, police,
cartes, motif). Détails et marche à suivre pour créer un univers : `references/da.md`.

```bash
python machine/monter.py --planche                    # la DA sans vidéo -> montage/da/planche-<univers>.jpg
python machine/monter.py --planche --univers chantier # comparer un autre univers
python machine/monter.py <id> --apercu --univers plan # essayer un univers sur une vraie vidéo
```

Ne mets jamais de couleur, de police ou de taille « en dur » dans un montage : si ça doit changer,
ça change dans la DA, pour toutes les vidéos.

## Aller plus loin que le gabarit

Le montage est une composition HyperFrames (du HTML animé avec GSAP, rendu en MP4).
`references/hyperframes.md` explique les règles du moteur, comment ajouter un bloc à partir du
catalogue HyperFrames, et comment glisser une animation sur mesure dans une seule vidéo (`extras.html`).
