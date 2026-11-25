---
name: ponctuations
description: Trouver, couper et poser des extraits courts (gags de vieux films du domaine public, extraits fournis par la personne) qui ponctuent une vidéo Portail Travaux, et tenir la banque d'extraits prêts à resservir (montage/ponctuations/). Utiliser quand on demande d'animer davantage une vidéo, d'ajouter des extraits de films, d'Instagram ou des mèmes, de trouver une image ou un gag pour une phrase, d'insérer un enregistrement d'écran dans une vidéo, ou d'ajouter un extrait à la banque.
---

# Ponctuations : des extraits courts qui relancent l'attention

Une ponctuation est un extrait de 2 à 3 secondes, sans son, posé sur une phrase où l'on ne voit que
la personne : un gag de vieux film, une image qui fait sourire, une scène que les gens reconnaissent.
Elle montre ce que la phrase dit, au moment où elle le dit.

Ce skill sert dans trois cas :
- **ponctuer une vidéo** déjà montée ou en cours de montage (on te donne son identifiant ou le fichier) ;
- **insérer un extrait qu'on te fournit** (enregistrement d'écran d'Instagram, d'un film, d'une série) ;
- **enrichir la banque** : préparer d'avance des extraits sur les sujets qui reviennent.

Le montage lui-même (transcription, coupe, plan, rendu) est le skill `montage-video`. Si la vidéo
n'a pas encore de projet dans `montage/projets/<id>/`, commence par lui.

## Les règles

- **Deux ou trois par vidéo, pas plus.** Une ponctuation toutes les 10 à 15 secondes au maximum :
  au-delà, on ne suit plus la personne.
- **2 à 3 secondes** chacune (1,5 s au moins, 4 s au plus).
- **Jamais** pendant l'accroche (les 3 à 5 premières secondes), pendant une animation (un bloc), ni
  pendant l'appel à l'action.
- **L'image dit la même chose que la phrase.** Il dit « tu passes pour un lourd », on voit le vendeur
  se faire jeter. Une image seulement drôle, sans rapport direct, distrait : mieux vaut rien.
- **Jamais le son de l'extrait.** La seule voix est celle de la personne (règle de `montage-video`).
- **Les droits** (détail plus bas) : tu vas chercher toi-même ce qui est libre. Ce qui appartient à
  quelqu'un, tu ne l'insères que si on te donne le fichier, et tu ne le ranges pas dans la banque.

## La marche à suivre

### 1. Trouver où ponctuer

Lis le texte de la vidéo avec les temps (`montage/projets/<id>/mots.json`, ou la sortie de
`python machine/couper.py <id>`) et son plan (`plan.json`). Les candidats sont les passages de plus
de 4 s sans animation ni plan de coupe. Pour chacun, résume la phrase en une idée simple : « tout le
monde veut le même client », « il faut rappeler vite », « le chantier part de travers ».

### 2. Regarder la banque d'abord

```bash
python machine/broll.py banque
```

Chaque extrait est donné avec l'idée qu'il illustre et les mots qui doivent y faire penser. Si l'un
d'eux colle, passe à l'étape 5. Les fiches sont dans `montage/ponctuations/index.yaml`.

### 3. Sinon, chercher un gag dans un vieux film

```bash
python machine/broll.py films "keaton one week"            # chercher (titre en anglais, réalisateur, acteur)
python machine/broll.py films --prendre <identifiant>      # télécharger le film dans broll/films/ (une fois)
```

Le script ne propose que des films sortis il y a plus de 95 ans : voir « Les droits ». Si le
téléchargement coupe sans arrêt, prends une autre copie du même film (un autre identifiant).

Des pistes qui marchent pour nos sujets (à chercher, puis à regarder avant de choisir) :

| L'idée de la phrase | Où chercher |
|---|---|
| Un chantier qui part de travers, une maison mal montée | Buster Keaton, *One Week* (1920) ; Laurel et Hardy, *The Finishing Touch* (1928) |
| Tout le monde court après la même chose, la concurrence | Buster Keaton, *Seven Chances* (1925), *Cops* (1922) |
| Appeler vite, le premier qui appelle, le téléphone | Harold Lloyd, *Number, Please?* (1920) |
| Le démarchage, insister, se faire jeter | Laurel et Hardy, *Big Business* (1929) |
| Le délai, l'urgence, être suspendu à quelque chose | Harold Lloyd, *Safety Last!* (1923) |
| Une installation qui se dérègle, la technique | Buster Keaton, *The Electric House* (1922) |

### 4. Repérer l'instant et couper

```bash
python machine/broll.py planche broll/films/<film>.mp4 --de 0 --a 600 --pas 15     # vue large
python machine/broll.py planche broll/films/<film>.mp4 --de 243 --a 258 --pas 0.5  # vue fine
python machine/broll.py importer broll/films/<film>.mp4 --debut 249.9 --duree 2.6 --nom coup-de-marteau
```

- Ouvre la planche (`broll/films/<film>-planche.jpg`) : chaque image porte son temps en secondes.
  Fais d'abord une vue large (une image toutes les 15 à 20 s), puis une vue fine autour du bon moment.
- Un bon extrait se comprend sans le film : un geste net, lisible en petit, avec un début et une
  chute. Évite les cartons de texte des films muets et les plans où il ne se passe rien.
- Note à quelle seconde tombe la chute du gag (le coup, la porte qui claque) : c'est elle qu'on
  calera sur le mot.

### 5. Poser l'extrait dans le plan de la vidéo

Dans `montage/projets/<id>/plan.json`, clé `"broll"` :

```json
{"de": "m135", "a": 36.45, "fichier": "montage/ponctuations/coup-de-marteau.mp4", "mode": "carte"}
```

- `de` / `a` : les repères du plan (`"m135"` = le mot n° 135, ou des secondes de la vidéo finale).
- **Cale la chute sur le mot.** Si la chute tombe 1,8 s après le début de l'extrait et que le mot
  fort est dit à 36,0 s, l'extrait commence à 34,2 s. Pour décaler dans le fichier sans le recouper :
  `"debut": 0.4`.
- Mode `carte` : l'extrait dans une carte en haut, la personne visible dessous. C'est le mode des
  ponctuations. (`plein` remplace toute l'image : seulement pour une image nette et verticale, un
  vieux film agrandi plein écran est flou.)
- Laisse respirer : au moins 2 s de visage plein écran entre une ponctuation et l'animation suivante.
  Exception en mise en scène `cadre` : elles peuvent se toucher (moins de 0,8 s d'écart), le cadre
  reste en place et l'animation prend la suite de la carte. En `plein`, avec un visage en gros plan,
  garde 0,7 s entre la fin de la carte et le bloc (le script refuse sinon).

### 6. Vérifier, puis rendre

```bash
python machine/monter.py <id> --apercu                 # images clés : l'extrait est-il sur la bonne phrase ?
python machine/monter.py <id> --rendu
python machine/yeux.py <id> --autour 34.2 36.4         # 12 images serrées autour de l'entrée et de la sortie
```

Ouvre les bandes `montage/projets/<id>/yeux/autour-<t>.jpg` et vérifie : la carte n'est jamais
posée sur le visage en plein écran, la chute tombe sur le mot, la personne a repris sa place avant
la suite. Sinon, déplace `de` / `a` et rends de nouveau. Envoie la vidéo et dis en une ligne quel
extrait est où, et sur quelle phrase.

### 7. Ranger ce qui peut resservir

```bash
python machine/broll.py banque --ajouter broll/perso/<nom>.mp4 \
    --idee "Le vendeur qui sonne une fois de trop se prend un coup de marteau : passer pour un lourd" \
    --mots lourd insister relance démarchage porte \
    --source "Big Business (Laurel et Hardy, 1929), Internet Archive" --droits "domaine public (film américain de 1929)"
```

- `--idee` : ce que l'extrait illustre, écrit comme la phrase qu'il accompagnera. C'est elle qu'on
  relira dans six mois pour savoir s'il convient.
- La banque est gardée dans le dépôt (fichiers légers, sans son). N'y mets que des extraits libres
  (domaine public, Pexels) ou qui appartiennent à la marque.
- Pour enrichir la banque d'avance : prends les sujets du calendrier (`sorties/<semaine>/`) ou ceux
  qu'on te donne, et prépare un extrait par idée qui revient.

## Les droits

- **Vieux films américains** (`broll.py films`) : un film entre dans le domaine public aux États-Unis
  95 ans après sa sortie (en 2026 : tout ce qui est sorti jusqu'en 1930), et le script ne cherche que
  ceux-là. C'est la source à utiliser sans rien demander. Préfère les films d'auteurs américains
  (Keaton, Harold Lloyd, Laurel et Hardy chez Hal Roach). Tu n'es pas juriste : si on te demande une
  garantie pour un usage commercial, dis-le simplement.
- **Film ou série récents, vidéo d'un autre compte (Instagram, TikTok, YouTube), mème du moment** :
  ne les télécharge pas toi-même. Les plateformes l'interdisent, ces images appartiennent à
  quelqu'un, et `CLAUDE.md` dit de ne pas reprendre les images des autres. Dis-le une fois, sans
  sermon, et propose la suite : la personne t'envoie le fichier (un enregistrement d'écran du
  téléphone suffit) et tu l'insères.
- **Extrait fourni par la personne** : insère-le.
  `python machine/broll.py importer <fichier> --debut <s> --duree <s> --nom <nom>` le met au format
  (sans son) dans `broll/perso/`. Dis une fois que l'extrait appartient à quelqu'un d'autre et qu'il
  peut entraîner un retrait de la vidéo, puis fais ce qui est demandé. Garde-le court (2 à 4 s),
  laisse visible le nom du compte d'origine, et ne le mets pas dans la banque.
- **Pexels** (`broll.py pexels`, clé `PEXELS_API_KEY`) : libre, utile pour une image réelle (un
  chantier, un outil) plutôt qu'un gag.
- **Données de clients** : jamais en clair dans un extrait (règle de `montage-video`, « Demandes de clients »).
