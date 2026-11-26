---
name: video-projet
description: Faire la vidéo d'un projet de travaux Portail Travaux à partir d'une vidéo de la personne et des infos du projet (numéro, ville, pièces, budgets) : l'écran coupé en deux (en haut le projet sur fond bleu, en bas la vraie vidéo de la personne, les sous-titres sur la couture), ou la personne détourée devant le projet, et autour d'elle uniquement la maquette 3D du projet filmée dans l'outil Dessin du site et les éléments clés du projet (fiche, budgets, appel « propose ton devis »). Utiliser quand on donne un projet ou une demande de travaux à mettre en vidéo, ou quand on demande une maquette 3D d'un projet. Pour un montage classique (conseils, animations, extraits), c'est le skill montage-video.
---

# Vidéo de projet

On te donne une vidéo où la personne parle face caméra et un projet de travaux (numéro, ville,
travaux, budgets). Tu sors une vidéo verticale où **le projet est derrière elle du début à la fin**,
avec elle à l'écran tout du long : écran partagé (`partage`, la mise en page préférée), en bas de
l'écran comme un présentateur (`coin`), ou au centre sous un carré animé (`vitrine`).

## Les règles de ce skill

1. **Derrière la personne, rien que le projet** :
   - les maquettes 3D du projet, construites et filmées dans l'outil Dessin du site
     (`machine/chantier3d.py`) ;
   - les éléments clés du projet : la fiche (numéro, ville, travaux, budgets), le budget de chaque
     pièce, le budget total, l'appel à l'action.

   Jamais d'extrait de film, d'Instagram, de YouTube, de Pexels, d'écran d'un autre site, jamais de
   « ponctuation », jamais d'animation qui ne parle pas du projet (pas de liste de conseils, pas de
   barres de statistiques), même si la vidéo de départ en avait. On repart de zéro sur le contenu.
2. **La personne à l'écran, tout le temps**, avec des zooms sur les coupes. Ses sous-titres
   restent : ce sont ses mots. Trois mises en scène au choix :
   - **`partage`** (celle qu'on préfère, à faire par défaut) : l'écran coupé en deux. En haut, sur
     un fond bleu de la marque, une barre de titre, la carte du projet (la 3D, la pastille du budget,
     l'étiquette de la pièce) et un encart pour le chiffre clé ; en bas, **sa vraie vidéo, avec son
     décor, sans détourage** ; les sous-titres en bandeau sur la ligne qui sépare les deux. Voir 3 ter.
     (Le détourage sur fond transparent a été jugé moche dans cette mise en page : ne le propose pas.)
   - **`coin`** : elle détourée en bas, le buste contre le bord de l'écran, le projet en plein écran
     derrière elle ; elle change de côté quand le contenu change.
   - **`vitrine`** : elle au centre, plus haut et plus présente ; au-dessus d'elle, le projet dans un
     carré encadré et légèrement animé (plaques décalées, coins de viseur, onglet du projet). À
     proposer quand on la trouve « trop en bas » ou quand on veut un rendu plus posé. Voir 3 bis.
3. **Les règles de la marque tiennent toujours** : la seule voix est la sienne ; on ne lui fait
   rien dire qu'elle n'a pas dit ; les budgets affichés sont ceux qu'on te donne (le total peut être
   leur somme, rien d'autre) ; **le client n'est jamais reconnaissable** (ni nom, ni adresse, ni
   téléphone, ni e-mail ; la ville et le numéro du projet, oui) ; tutoiement dans les textes.
4. **Une maquette est une illustration** : tant qu'on n'a pas les vraies dimensions et les vrais
   équipements, chaque plan 3D porte la mention « Illustration 3D ». Elle doit rester crédible
   (règles d'agencement : `references/maquette.md`).

## Ce qu'il te faut

- **La vidéo** : un fichier envoyé (le skill `montage-video`, étapes 0 à 2, dit comment la récupérer,
  la transcrire et la couper), ou un projet de montage déjà fait (`montage/projets/<id>/`).
- **Le projet** : numéro, ville, travaux (pièces), budget par pièce ou total. Si tu les as : surfaces,
  équipements voulus (douche à l'italienne, îlot...). Sans surface, prends une taille courante et dis-le.
- **L'appel** : par défaut « Propose ton devis, c'est gratuit. Lien dans la bio ».
- **Le site lancé sur la machine** et **le détourage installé** (voir « Si ça coince ») :

  ```bash
  python machine/site_local.py demarrer      # copie locale du site, données fictives seulement
  python -c "import torch"                   # le détourage RobustVideoMatting a besoin de PyTorch
  ```

## 1. Préparer le projet de montage

Une vidéo déjà montée pour autre chose : copie son projet, pour garder l'original intact.

```bash
cp -a montage/projets/<id> montage/projets/<id>-projet-<numero>
```

Dans le `plan.json` de la copie, **efface les clés de contenu de l'ancien montage** (`blocs`,
`broll`, `chiffres`, `accroche`, `emphase` si tu veux) : tu les réécris toutes à l'étape 3. Garde
`retirer`, `corrections` et `reglages` (cadrage du visage). Ajoute `"gel_fin": 3.4` dans
`reglages` (la dernière image reste le temps de lire l'appel), puis recoupe :

```bash
python machine/couper.py <id>-projet-<numero>
```

**Le bruit de fond part à cette étape** (clim, ventilation, rue, ronflement derrière la voix) : la
coupe passe le son dans un débruiteur fait pour la voix (RNNoise, filtre `arnndn` de ffmpeg, modèle
téléchargé au premier usage dans `montage/modeles/`). C'est le réglage par défaut
(`son.debruitage: voix` dans `config/da.yaml`) : rien à ajouter. Sur la vidéo du projet n°2114, le
bruit de fond a baissé d'une dizaine de dB, la voix n'a pas bougé de plus de 1 dB.
- Un projet copié d'un montage fait **avant** ce réglage garde son ancien son : recoupe-le (la
  commande ci-dessus), même si rien d'autre ne change. Les coupes et les numéros de mots restent
  les mêmes, le plan reste valable.
- Vidéo par vidéo, dans les `reglages` du plan : `"debruitage": "voix"` (par défaut), un nombre de
  8 à 12 (réduction douce d'un simple souffle régulier), ou `0` (aucun). Puis recoupe.
- Tu ne peux pas écouter : à la livraison, demande si le bruit est assez parti et si la voix ne
  sonne pas « sous l'eau ». S'il reste trop de bruit, on peut passer à un débruitage plus fort.

## 2. Les maquettes 3D

Une maquette par pièce du projet, filmée en format **`fond`** (plein écran, la pièce dans le haut de
l'image, au-dessus de la personne), avec **une seule rotation lente et longue** : on découpera
plusieurs passages dedans, chacun montre un autre angle.

```json
{
  "nom": "projet-2114-cuisine",
  "piece": {"type": "cuisine", "largeur": 5, "profondeur": 4, "fenetre": "fenetre_double",
            "equipements": ["colonne-frigo", "meuble-bas-60", "evier-120", "lave-vaisselle", "meuble-bas-60",
                            "plaque-60", "hotte-60", "meuble-bas-80", "meuble-haut-60", "meuble-haut-60", "ilot"]},
  "vues": [{"plan": "piece", "piece": "cuisine", "format": "fond", "duree": 22, "tour": 150, "depart": -75, "zoom": 0.95}]
}
```

- `duree` : la somme des passages où cette pièce sera à l'écran, plus une seconde. Une vidéo de
  45 s avec deux pièces : environ 22 s pour la pièce principale, 16 s pour l'autre.
- `tour` : 6 à 7 degrés par seconde (150° pour 22 s) : assez lent pour être calme, assez pour que
  chaque passage montre un angle différent. `depart` : moitié du tour, en négatif.
- Le format `fond` coûte cher : environ 1,5 s de calcul par image, à 15 images par seconde, soit
  5 à 6 minutes pour 22 s. Lance les tournages en tâche de fond pendant que tu écris le plan.
- Pour une maison (extension, toiture, façade) : vue `exterieur` ou `large`, même format.

```bash
python machine/chantier3d.py chantiers/projet-2114-cuisine.json --apercu   # vue de dessus + une image, à vérifier
python machine/chantier3d.py chantiers/projet-2114-cuisine.json            # le film : broll/chantiers/<nom>-piece-cuisine.mp4
```

Avant de filmer, ouvre la vue de dessus (`<nom>-plan.jpg`) et l'image : agencement crédible, pièce
entière dans le haut de l'image (sinon `zoom`, entre 0,8 et 1,1). Les fiches de chantier ne vont
pas dans le dépôt (`chantiers/` est ignoré, sauf `chantiers/exemples/`) : jamais le nom du client
dans une fiche ni dans un nom de fichier. Tout le détail (fiche, catalogue, agencement, vues) :
`references/maquette.md`.

## 3. Le plan : le projet derrière, du début à la fin

Le contenu doit couvrir **toute** la durée, sans trou (un trou laisse voir le fond uni). La recette :

| Moment | Derrière la personne | Texte à l'écran |
|---|---|---|
| 0 → fin de l'accroche (~5 s) | la pièce principale en 3D, dès la première image | accroche du projet : « Projet n°2114 à *Montélimar* » |
| ~6 s | la fiche du projet (bloc `demande`) | numéro, ville, travaux, budget de chaque pièce, client flouté |
| 8 à 11 s par pièce | chaque pièce en 3D | légende « Salle de bains · *5 000 €* », mention « Illustration 3D » |
| ~5 s (si plusieurs pièces) | une pièce en 3D, un autre angle | carte `chiffres` : le budget total, qui défile jusqu'à sa valeur |
| ~5 s | une pièce en 3D | légende « Projet n°2114 · Montélimar » |
| la fin (gel compris) | la pièce principale en 3D, sans légende | carton de fin : « Projet / N°2114 / Propose ton devis, c'est gratuit. Lien dans la bio » |

- Cale chaque changement sur une fin de phrase (temps des mots dans `mots.json`) : la personne
  change de côté à ce moment-là, une coupure en pleine phrase se voit.
- Un passage dans une pièce = `"debut"` : l'endroit où il commence dans la rotation filmée. Les
  passages d'une même pièce se suivent dans le film (0 → 5,15, puis 5,15 → 15,65...), pour ne jamais
  montrer deux fois le même angle.
- Pas de légende pendant l'accroche ni pendant le carton de fin, qui occupent le haut de l'écran.
- Les enchaînements se règlent seuls : un plan 3D reste 0,3 s sous le suivant (jamais d'image vide),
  une fiche monte par-dessus la 3D et repart en la découvrant. Écris des fenêtres bout à bout, sans
  chevauchement, et ajoute `"zoom": false` sur les plans 3D (la caméra bouge déjà).

```json
{
  "mise_en_scene": "coin",
  "coin": {"echelle": 0.62, "cote": "droite", "alterner": true},
  "accroche": {"texte": "Projet n°2114 à *Montélimar*", "a": "m19"},
  "blocs": [
    {"bloc": "demande", "de": 5.2, "a": 11.6, "sur_titre": "Projet n°2114", "titre": "Rénovation à *Montélimar*",
     "champs": [{"nom": "Travaux", "valeur": "Salle de bains + cuisine", "quand": "m21"},
                {"nom": "Salle de bains", "valeur": "5 000 €", "quand": "m23"},
                {"nom": "Cuisine", "valeur": "17 000 €", "quand": "m25"},
                {"nom": "Client", "flou": true, "quand": "m27"}]}
  ],
  "chiffres": [{"de": 32.6, "a": 38.4, "texte": "22 000 €", "legende": "de travaux : salle de bains + cuisine"}],
  "broll": [
    {"de": 0, "a": 5.15, "fichier": "broll/chantiers/projet-2114-cuisine-piece-cuisine.mp4", "mode": "plein"},
    {"de": 11.6, "a": 22.1, "fichier": "broll/chantiers/projet-2114-sdb-piece-salle-de-bain.mp4", "mode": "plein",
     "legende": "Salle de bains · *5 000 €*", "mention": "Illustration 3D"},
    {"de": 22.1, "a": 32.6, "fichier": "broll/chantiers/projet-2114-cuisine-piece-cuisine.mp4", "mode": "plein", "debut": 5.15,
     "legende": "Cuisine · *17 000 €*", "mention": "Illustration 3D"},
    {"de": 32.6, "a": 38.4, "fichier": "broll/chantiers/projet-2114-sdb-piece-salle-de-bain.mp4", "mode": "plein", "debut": 10.5},
    {"de": 38.4, "a": 44.3, "fichier": "broll/chantiers/projet-2114-cuisine-piece-cuisine.mp4", "mode": "plein", "debut": 15.65,
     "legende": "Projet n°2114 · *Montélimar*", "mention": "Illustration 3D"},
    {"de": 44.3, "a": 47.7, "fichier": "broll/chantiers/projet-2114-cuisine-piece-cuisine.mp4", "mode": "plein", "debut": 21.55}
  ],
  "carton_fin": {"de": 44.35, "verbe": "Projet", "mot": "N°2114", "suite": "Propose ton devis, c'est gratuit. Lien dans la bio"}
}
```

(Les clés `retirer`, `corrections`, `reglages` de la vidéo restent à côté. Le détail de chaque clé :
`montage-video`, `references/plan.md`.)

Réglages du coin, si besoin : `echelle` (taille de la personne : 0,55 laisse plus de place au
projet, 0,7 la rend plus présente), `cote` de départ, `alterner: false` pour la garder d'un seul
côté, `descente` (pixels) pour moins de buste. Les zooms sur les coupes : `"zoom_coupe": 1.1` dans
`reglages`.

## 3 bis. Variante « vitrine » : le projet dans un carré au-dessus d'elle

Tout le projet passe dans le carré : les plans 3D l'un après l'autre (fondu court, petit éclair et
battement du cadre à chaque changement), la pièce et son budget en étiquette dans le carré, le
numéro et la ville sur l'onglet, « Illustration 3D » à la verticale le long du bord. Le carré
arrive dès la première image, flotte à peine, et s'efface juste avant le carton de fin (qui prend sa
place en haut). Les sous-titres passent sous son menton.

Ce qui change par rapport à `coin` :
- **Pas de bloc plein écran, pas de carte `chiffres`, pas d'`accroche`** (le montage refuse) : le
  titre du projet va sur l'onglet (`vitrine.titre`), les budgets dans les légendes des plans, le
  total dans la légende d'un plan (« SdB + cuisine · *22 000 €* »).
- **Les plans se suivent bout à bout du début jusqu'au carton de fin** (le carré n'est jamais
  vide) ; le dernier finit à l'instant du carton (`carton_fin.de`). Pas de `mode` à donner.
- **Une légende par plan** : la pièce montrée et son budget ; à la fin, l'appel (« Propose *ton
  devis* »). Deux plans de suite avec la même légende : elle reste en place.
- **Le cadrage de la 3D dans le carré** : un rendu `fond` a la pièce vers le tiers haut de l'image.
  `"ancre_y": 0.15` (quelle hauteur de l'image on garde) et `"recul": 0.08` (une marge de la couleur
  du fond autour, pour que la pièce ne touche pas les bords) la posent entière, un peu au-dessus du
  milieu du carré : le haut des cheveux passe devant le bas du carré.
- Regarde chaque passage en entier dans la rotation filmée : une rotation finit parfois sur un mur
  qui cache la pièce. Choisis les `debut` pour l'éviter (le court film `fond` de la même pièce peut
  servir pour le dernier passage).

```json
{
  "mise_en_scene": "vitrine",
  "vitrine": {"titre": "Projet n°2114 · *Montélimar*", "mention": "Illustration 3D",
              "taille": 540, "marge": 30, "chevauche": 24, "echelle": 0.58},
  "broll": [
    {"de": 0, "a": 11.6, "fichier": "broll/chantiers/projet-2114-cuisine-piece-cuisine.mp4", "debut": 0,
     "ancre_y": 0.15, "recul": 0.08, "legende": "Cuisine · *17 000 €*"},
    {"de": 11.6, "a": 22.1, "fichier": "broll/chantiers/projet-2114-sdb-piece-salle-de-bain.mp4", "debut": 0,
     "ancre_y": 0.15, "recul": 0.08, "legende": "Salle de bains · *5 000 €*"},
    {"de": 22.1, "a": 31.4, "fichier": "broll/chantiers/projet-2114-cuisine-piece-cuisine.mp4", "debut": 11.6,
     "ancre_y": 0.15, "recul": 0.08, "legende": "Cuisine · *17 000 €*"},
    {"de": 31.4, "a": 36.5, "fichier": "broll/chantiers/projet-2114-sdb-piece-salle-de-bain.mp4", "debut": 8.8,
     "ancre_y": 0.15, "recul": 0.08, "legende": "SdB + cuisine · *22 000 €*"},
    {"de": 36.5, "a": 44.35, "fichier": "broll/chantiers/projet-2114-cuisine-court-piece-cuisine.mp4", "debut": 0,
     "ancre_y": 0.15, "recul": 0.08, "legende": "Propose *ton devis*"}
  ],
  "carton_fin": {"de": 44.35, "verbe": "Projet", "mot": "N°2114", "suite": "Propose ton devis, c'est gratuit. Lien dans la bio"}
}
```

Réglages de la vitrine : `taille` (côté du carré, en pixels), `marge` (sous l'interface du haut),
`echelle` (taille de la personne) et `chevauche` (de combien ses cheveux passent devant le carré).
Plus grand le carré, plus bas et plus petite la personne : vérifie que les sous-titres ne mordent
pas sur son menton pendant les zooms (sinon `"zoom_coupe": 1.05`).

## 3 ter. Écran partagé (`partage`) : la mise en page préférée

```
 ┌──────────────────────────────┐  fond bleu (léger grain)
 │ [⌂ Rénovation à Montélimar ] │  barre de titre : change avec le "titre" des plans
 │ ┌──────────────────────────┐ │
 │ │● Projet n°2114 · …  3D   │ │  en-tête de la carte ("entete", "mention")
 │ │        maquette 3D [17k€]│ │  pastille du budget ("badge")
 │ │ [Cuisine]       ┌───────┐│ │  étiquette de la pièce ("legende")
 │ └─────────────────│ encart│┘ │  encart qui déborde ("encarts") : le nombre monte
 ══════ BANDEAU DES SOUS-TITRES ══  la couture
 │            (elle)            │  sa vraie vidéo, sur toute la largeur, avec son décor
 └──────────────────────────────┘
```

C'est la mise en page d'une vidéo de référence qu'on a aimée (organisation de l'écran, place des
sous-titres, animations), refaite à nos couleurs et avec nos contenus : on n'en reprend ni le
design ni les textes.

- **Mêmes refus qu'en vitrine** : pas de bloc plein écran, pas de carte `chiffres`, pas
  d'`accroche` (le titre du premier plan en tient lieu). Les plans se suivent bout à bout jusqu'au
  carton de fin ; le titre, la carte et les encarts s'en vont juste avant lui, qui se pose au milieu
  du haut.
- **Par plan** : `titre` (la barre du haut, 4 à 6 mots, *astérisques* en couleur ; s'il ne change
  pas, la barre ne bouge pas), `badge` (le montant de ce qu'on voit), `legende` (la pièce).
- **La 3D faite pour la carte** : filme les vues en `"format": "partage"` (horizontal, à la taille de
  la carte) : elles la remplissent sans réglage. Une maison : vue `exterieur` (sans toit si on ne veut
  pas la toiture : `"toit": false`) avec `"zoom": 1.5`, plus les pièces du projet en vue `piece`.
- **Le cadrage d'une 3D déjà filmée en `fond`** : la carte est horizontale, un rendu `fond` est vertical. `"entier": true`
  prend un carré de l'image (la pièce, choisie par `"ancre_y": 0.15`) et le pose entier au milieu
  de la carte, les côtés remplis de la couleur du fond de la maquette ; `"recul": -0.04` resserre un
  peu. Rien n'est coupé, même quand la pièce tourne.
- **Les encarts** : `{"de": 31.6, "titre": "Budget total", "valeur": "22 000 €", "detail": "Salle de bains + cuisine"}`
  (sans `"a"`, il reste jusqu'à la fin de la carte). Un chiffre seulement s'il est donné ou s'il est
  la somme de ceux qu'on t'a donnés.
- **La personne** : sa vraie vidéo remplit tout le bas, sur toute la largeur, avec son décor (pas de
  détourage). Ses yeux se posent à `yeux_ecran` (1 370 px par défaut avec la couture à 1 040) ; ce
  qui dépasse au-dessus de la couture passe sous le fond bleu. Un selfie très serré ne tient pas en
  entier : le haut du front passe sous la couture, et `"zoom_coupe": 1.05` dans `reglages` évite que
  les zooms ne la collent à l'écran. Filmée d'un peu plus loin (le buste dans l'image), elle tiendrait
  entière : dis-le. (`"detoure": true` existe encore, mais n'est plus voulu.)

```json
{
  "mise_en_scene": "partage",
  "partage": {"entete": "Projet n°2114 · Montélimar", "mention": "Illustration 3D",
              "couture": 1040, "yeux_ecran": 1370},
  "broll": [
    {"de": 0, "a": 11.6, "fichier": "broll/chantiers/projet-2114-cuisine-piece-cuisine.mp4", "debut": 0,
     "ancre_y": 0.15, "entier": true, "recul": -0.04,
     "titre": "Rénovation à *Montélimar*", "legende": "Cuisine", "badge": "17 000 €"},
    {"de": 11.6, "a": 22.1, "fichier": "broll/chantiers/projet-2114-sdb-piece-salle-de-bain.mp4", "debut": 0,
     "ancre_y": 0.15, "entier": true, "recul": -0.04,
     "titre": "*Salle de bains* à rénover", "legende": "Salle de bains", "badge": "5 000 €"},
    {"de": 22.1, "a": 31.4, "fichier": "broll/chantiers/projet-2114-cuisine-piece-cuisine.mp4", "debut": 11.6,
     "ancre_y": 0.15, "entier": true, "recul": -0.04,
     "titre": "*Cuisine* à rénover", "legende": "Cuisine", "badge": "17 000 €"},
    {"de": 31.4, "a": 36.5, "fichier": "broll/chantiers/projet-2114-sdb-piece-salle-de-bain.mp4", "debut": 8.8,
     "ancre_y": 0.15, "entier": true, "recul": -0.04,
     "titre": "*22 000 €* de travaux", "legende": "Salle de bains", "badge": "5 000 €"},
    {"de": 36.5, "a": 44.35, "fichier": "broll/chantiers/projet-2114-cuisine-court-piece-cuisine.mp4", "debut": 0,
     "ancre_y": 0.15, "entier": true, "recul": -0.04,
     "titre": "Propose *ton devis*, c'est gratuit", "legende": "Cuisine", "badge": "17 000 €"}
  ],
  "encarts": [{"de": 31.6, "titre": "Budget total", "valeur": "22 000 €", "detail": "Salle de bains + cuisine"}],
  "carton_fin": {"de": 44.35, "verbe": "Projet", "mot": "N°2114", "suite": "Propose ton devis, c'est gratuit. Lien dans la bio"}
}
```

Réglages : `couture` (hauteur de la ligne de séparation, en pixels : plus haut, plus de place pour
elle, moins pour la carte), `yeux_ecran` (où tombent ses yeux), `taille_sous_titres` (60 par
défaut). Sa bouche doit rester au-dessus de ~1 650 px (le nom du compte et la légende de la
publication passent dessous) : regarde la planche.

## 4. Monter, vérifier, livrer

```bash
python machine/monter.py <id>-projet-<numero> --apercu      # images clés : ouvre apercu/planche.jpg
python machine/monter.py <id>-projet-<numero> --rendu       # détoure la personne la première fois (~7 min pour 45 s)
python machine/yeux.py <id>-projet-<numero> --sans-gemini
python machine/yeux.py <id>-projet-<numero> --autour 5.2 11.6 22.1 32.6 44.3   # chaque changement de contenu
```

Vérifie sur les images :
- à aucun moment le fond n'est uni : il y a toujours le projet derrière ;
- rien d'autre que le projet n'apparaît ;
- la personne n'est jamais coupée en pleine phrase par un changement de côté ;
- les budgets et le numéro affichés sont exactement ceux qu'on t'a donnés ;
- aucun nom, adresse, téléphone ou e-mail de client, même flou mais lisible ;
- le texte de chaque légende et du carton se lit en petit (taille d'un téléphone).

Vérifie aussi le son dans le bilan de `yeux.py` (niveau autour de -14 LUFS) : le débruitage est fait
à la coupe, pas au rendu.

Envoie la vidéo et dis en quelques lignes : ce qui est derrière, dans l'ordre ; ce que la maquette
suppose (tailles, équipements) ; que le bruit de fond a été retiré ; que tu ne peux pas écouter la
vidéo. Quand tout est fini :
`python machine/site_local.py arreter`.

## Si ça coince

- **Pas de PyTorch** (le détourage RobustVideoMatting en a besoin) :
  `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`. Sans lui, le
  montage prend l'ancien détourage de HyperFrames, nettement moins bon : installe plutôt PyTorch.
- **Le site ne tourne pas, la maquette n'est pas construite, le tournage est lent** :
  `references/maquette.md`, « Si ça coince ».
- **Une maquette se fige avant la fin de son passage** : la rotation filmée est trop courte pour
  les `debut` demandés. Refilme avec une `duree` plus longue.
