# Maquettes 3D : la fiche, les règles d'agencement, les vues

Comment construire et filmer la maquette d'un projet avec l'outil Dessin du site. Le skill
`video-projet` dit quand et comment la poser dans la vidéo ; ici, tout ce qui concerne la maquette.

## Avant de commencer

1. **Les infos du chantier.** Type de travaux, pièces concernées, dimensions ou surface, équipements
   voulus, ce qu'il y a dehors (terrasse, piscine, clôture), budget si la personne le donne. S'il
   manque une dimension, prends une valeur plausible et dis laquelle ; ne bloque pas pour ça.
2. **Le plan voulu pour chaque vue.** C'est la personne qui décide ; si elle ne dit rien, choisis
   d'après le chantier et dis ton choix :

   | Plan | Ce qu'on voit | Pour quel chantier |
   |---|---|---|
   | `piece` | zoom sur une pièce, murs de devant abaissés | salle de bains, cuisine, chambre, une pièce à refaire |
   | `large` | toute la maison vue de dedans | rénovation complète, redistribution des pièces, sols, électricité |
   | `exterieur` | la maison fermée, son toit, son jardin | toiture, façade, extension, terrasse, piscine, clôture, construction |

3. **Le site lancé sur la machine** (une copie locale, données fictives seulement) :

   ```bash
   python machine/site_local.py demarrer     # une fois par session ; récupère et installe le site s'il manque
   ```

   Le dépôt et la branche du site sont dans `config/marque.yaml` (`site_local`). Dans une session
   cloud, le dépôt du site doit être accessible à la session : s'il ne l'est pas, ajoute-le
   (lecture seule suffit). On ne pousse jamais rien dans le dépôt du site depuis ici.

## 1. Écrire la fiche de la maquette

Un fichier `chantiers/<nom>.json` (le dossier n'est pas enregistré dans le dépôt, sauf
`chantiers/exemples/` : une salle de bains, une cuisine avec îlot, un T3 avec jardin, à copier). **Jamais le nom du client ni son adresse dans la fiche ou dans son nom de
fichier** : nomme-la d'après les travaux (`salle-de-bain-6m2`, `extension-20m2`).

Deux sortes de maquettes.

**Une pièce seule** (posée comme une maquette, pour un chantier intérieur) :

```json
{
  "nom": "salle-de-bain-6m2",
  "piece": {
    "type": "salle_de_bain", "largeur": 2.6, "profondeur": 2.4,
    "equipements": ["douche-italienne", "vasque", "wc-suspendu", "seche-serviettes"]
  },
  "vues": [{"plan": "piece", "piece": "salle_de_bain", "tour": 40, "duree": 4}]
}
```

- `largeur` × `profondeur` : la pièce de mur à mur, en mètres. Depuis une surface, prends des
  proportions courantes (6 m² : 2,6 × 2,4 ; 12 m² : 4 × 3).
- `equipements` : des identifiants du catalogue. Le script les place selon les règles d'agencement
  (voir « Une maquette crédible ») ; sans liste, il prend l'équipement courant de la pièce. Pour
  placer un objet toi-même : `["ilot-repas", [2.2, 2.0]]` (son centre, en mètres depuis le coin
  extérieur en haut à gauche ; un troisième nombre le tourne : 900 = quart de tour). Ce qui ne tient
  pas sans tricher est laissé de côté, avec un avertissement : lis-les tous.
- La porte est sur le mur de devant, dans l'angle gauche (`"porte_a_droite": true` pour l'autre).
  `porte` : un type de porte ; `fenetre` : `false` ou un type (`"fenetre_double"`). La fenêtre se
  place seule : au-dessus de l'évier dans une cuisine, sinon sur un pan de mur sans meuble haut.
- Le sol et la faïence se posent d'office selon le type de pièce.

**Une maison** (pour une vue large ou extérieure) :

```json
{
  "nom": "maison-t3-terrasse",
  "maison": "t3",
  "toit": "quatre_pans",
  "exterieur": {"terrasse": true, "piscine": "rectangle", "allee": true, "arbres": 3, "cloture": "grillage"},
  "vues": [
    {"plan": "exterieur", "tour": 50},
    {"plan": "large"},
    {"plan": "piece", "piece": "sejour"}
  ]
}
```

- `maison` : un modèle tout fait (`"studio"`, `"t2"`, `"t3"`, `"plain_pied"`, `"etage"`), la maison
  de démonstration meublée avec jardin et piscine (`"demo"`), ou des dimensions :
  `{"largeur": 12, "profondeur": 8}` (ajoute `"forme": "L", "decoupe": [5, 4]` pour une maison en L,
  et `"etage": true` à côté pour un étage).
- Les modèles et les dimensions libres reçoivent d'office, pièce par pièce : une porte vers la
  pièce de vie, une fenêtre sur le mur extérieur, la porte d'entrée et la baie vitrée sur la
  façade de devant, les sols, et les meubles selon les règles d'agencement. Une maison sans pièce
  « cuisine » reçoit une cuisine ouverte dans le séjour. Pour un intérieur précis, écris-le dans `"plan"` (mêmes repères que ci-dessus, en mètres ;
  les murs extérieurs font 20 cm, leur axe est à 0,1 m du bord) :

  ```json
  "plan": {
    "cloisons": [[[5, 0.1], [5, 6.9]], [[5, 3.5], [9.9, 3.5]]],
    "pieces": [[[2.5, 3.5], "sejour"], [[7.5, 1.8], "chambre"], [[7.5, 5.2], "cuisine"]],
    "ouvertures": [[[2.5, 6.9], "porte_entree"], [[5, 2], "porte"], [[7.5, 0.1], "fenetre_double"]],
    "objets": [["canape-3", [2, 5.5], 1800], ["lit-160", [7.5, 1]], ["evier-120", [7, 6.6]]]
  }
  ```

  Une pièce se désigne par un point qui est dedans, une ouverture par un point sur son mur, un objet
  par son centre (le troisième nombre le fait tourner : 1800 = demi-tour).
- `toit` : `deux_pans` (défaut), `quatre_pans`, `croupe`, `monopente`, `plate`, `mansarde`, ou `false`.
- `exterieur` : `terrasse`, `piscine` (`true` ou une forme : `rectangle`, `ronde`, `ovale`,
  `haricot`, `L`, `couloir`, `hors_sol`), `allee`, `arbres` (un nombre, 4 au plus), `cloture`.
  `true` les place comme sur une vraie parcelle : l'allée mène à la porte d'entrée, la terrasse
  est devant la baie vitrée, la piscine au-delà de la terrasse avec 2 m de plage, les arbres
  derrière la maison (devant, ils la cacheraient à la caméra). Des points les placent où tu veux
  (`"terrasse": [[4, 7.1], [9, 10.5]]`). `"parcelle"` : la marge de terrain autour de la maison, en
  mètres (6 par défaut, 10,5 avec une piscine).

Tout ce qu'on peut écrire (objets par catégorie, ouvertures, pièces, toits, piscines) :

```bash
python machine/chantier3d.py --catalogue
```

**Fidélité** : la maquette illustre le chantier, ce n'est pas le plan de la vraie maison. Dans le
récap, dis ce qui vient des infos données et ce que tu as supposé.

### Une maquette crédible

Une maquette fausse se voit tout de suite (une douche au milieu de la pièce, un évier collé au
réfrigérateur sans plan de travail, un lit sous la fenêtre) et décrédibilise la vidéo. Le script
(`machine/chantier3d/agencement.mts`) applique les règles d'usage ; ne les contourne pas en plaçant
les objets à la main sans les respecter.

| Pièce | Règles appliquées |
|---|---|
| Salle de bains, salle d'eau | Douche ou baignoire calée dans un angle, le plus loin possible de la porte. Vasque avec 70 cm libres devant, de préférence sur le mur de la douche. WC sur un mur de côté, 20 cm de chaque côté, 60 cm devant, jamais face à la porte. Sèche-serviettes à portée de main de la douche. Rien dans le débattement de la porte. |
| Cuisine | Meubles bas bord à bord (plan de travail continu) : réfrigérateur en bout de ligne, évier, lave-vaisselle contre l'évier, 60 cm de plan au moins entre l'évier et la plaque, un plan au bout. Hotte centrée au-dessus de la plaque, meubles hauts hors de la fenêtre. 90 cm de passage devant la ligne. Îlot seulement avec 1 m de passage côté cuisine et 90 cm autour. Triangle évier-plaque-réfrigérateur vérifié (3,6 à 7,9 m). Si la ligne ne tient pas, le script prend un autre mur, puis une ligne plus courte, et le dit. |
| Chambre | Lit tête contre un mur, centré, pas sous la fenêtre ni sur le mur de la porte, 60 cm de passage de chaque côté et 70 cm au pied ; chevets de part et d'autre ; armoire en face. |
| Séjour | Canapé contre un mur (ou dos à l'autre partie d'une pièce en L), table basse à 40 cm devant, meuble télé en face ; table à manger loin du canapé avec 70 cm libres autour (une 4 places si la 6 ne tient pas), chaises de part et d'autre. |
| Maison | Une porte par pièce, vers la pièce de vie, dans un angle ; une fenêtre par pièce sur son mur extérieur ; pas de fenêtre dans un WC ; porte d'entrée dans l'angle de la façade de devant, baie vitrée sur le séjour. |

Ce que tu vérifies toi-même, sur la vue de dessus (`<nom>-plan.jpg`) avant tout tournage :
- les dimensions annoncées sont réalistes (une douche à l'italienne fait 1,20 × 0,90 m au moins, un
  îlot demande une cuisine de 4,5 × 4 m environ, une salle de bains avec baignoire 2,2 × 1,9 m) ;
- chaque pièce a sa porte et on peut y entrer sans traverser une chambre ;
- les équipements demandés sont tous là ; sinon lis l'avertissement, agrandis la pièce ou retire un
  élément, plutôt que de forcer une place.

## 2. Régler les vues

Chaque entrée de `"vues"` donne une vidéo. Les réglages, tous facultatifs sauf `plan` :

| Réglage | Effet | Défaut |
|---|---|---|
| `plan` | `piece`, `large` ou `exterieur` | |
| `piece` | la pièce visée : son type (`"cuisine"`) ou son numéro dans la liste affichée | la plus grande de ce type |
| `tour` | l'angle parcouru par la caméra pendant la vidéo, en degrés (négatif = autre sens) | 40 |
| `depart` | l'angle de départ, par rapport à la vue de trois quarts | la moitié du tour, pour finir symétrique |
| `duree` | en secondes ; cale-la sur la phrase à couvrir | 4 |
| `zoom` | 1.3 = plus près, 0.8 = plus loin | 1 |
| `hauteur` | la caméra plus ou moins haut, en degrés au-dessus de l'horizon | 39 dehors, 45 en large, 52 sur une pièce |
| `murs` | `"entiers"` : garder les murs de devant (on voit moins dedans) | abaissés |
| `format` | `carte` (pour une carte dans la vidéo), `vertical` (plein écran), `carre`, `fond` (plein écran, la pièce dans le haut de l'image : pour la mise en scène `coin`, où la personne occupe le bas ; filmé à 15 images/s, environ 3 min pour 4 s) | `carte` |
| `nom` | un suffixe, pour filmer deux fois la même vue avec des réglages différents | |

Une rotation lente se regarde mieux qu'un tour complet : 30 à 60° en 3 à 5 secondes.

## 3. Vérifier en image, puis filmer

```bash
python machine/chantier3d.py chantiers/<nom>.json --apercu     # la vue de dessus et une image par vue, 20 s chacune
python machine/chantier3d.py chantiers/<nom>.json              # les vidéos (une à deux minutes par vue)
python machine/chantier3d.py chantiers/<nom>.json --plan piece --piece cuisine --tour 50   # une vue seule
```

Ouvre d'abord la vue de dessus (`broll/chantiers/<nom>-plan.jpg`, le plan dessiné par l'éditeur du
site, avec les cotes) : c'est là qu'on voit un alignement faux ou un passage trop étroit. Puis chaque
image de vue, et vérifie :
- la pièce ou la maison est bien au centre et entière (sinon `zoom`, `depart`, `hauteur`) ;
- les équipements demandés y sont tous (lis les avertissements du script) et rien ne se chevauche ;
- rien ne cache le sujet au premier plan (un arbre devant la maison : déplace-le ou retire-le) ;
- la maquette ressemble à ce que la personne a décrit (nombre de pièces, étage, forme du toit).

Après le tournage, ouvre la planche `<nom>-<plan>-planche.jpg` (six images du mouvement).

## Si ça coince

- **« Le site ne tourne pas »** : `python machine/site_local.py demarrer`, puis `etat`. Le journal est
  dans `broll/site-local.log`.
- **La page Dessin est introuvable (404)** : la branche du site n'a pas l'outil, ou ses deux
  interrupteurs sont éteints ; `demarrer` les rallume sur l'émulateur.
- **La maquette n'a pas pu être construite** : le message dit quel élément est refusé (cloison hors
  de la maison, pièce introuvable sous un point, objet inconnu). Corrige la fiche.
- **Un tournage très lent** : le rendu 3D se fait sans carte graphique. Baisse `duree`, ou filme
  une vue à la fois.
