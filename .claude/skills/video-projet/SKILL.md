---
name: video-projet
description: Faire la vidéo d'un projet de travaux Portail Travaux à partir d'une vidéo de la personne et des infos du projet (numéro, ville, pièces, budgets) : la personne détourée en bas de l'écran pendant toute la vidéo, et derrière elle uniquement la maquette 3D du projet filmée dans l'outil Dessin du site et les éléments clés du projet (fiche, budgets, appel « propose ton devis »). Utiliser quand on donne un projet ou une demande de travaux à mettre en vidéo, ou quand on demande une maquette 3D d'un projet. Pour un montage classique (conseils, animations, extraits), c'est le skill montage-video.
---

# Vidéo de projet

On te donne une vidéo où la personne parle face caméra et un projet de travaux (numéro, ville,
travaux, budgets). Tu sors une vidéo verticale où **le projet est derrière elle du début à la fin**,
et elle devant, détourée, en bas de l'écran, comme un présentateur.

## Les règles de ce skill

1. **Derrière la personne, rien que le projet** :
   - les maquettes 3D du projet, construites et filmées dans l'outil Dessin du site
     (`machine/chantier3d.py`) ;
   - les éléments clés du projet : la fiche (numéro, ville, travaux, budgets), le budget de chaque
     pièce, le budget total, l'appel à l'action.

   Jamais d'extrait de film, d'Instagram, de YouTube, de Pexels, d'écran d'un autre site, jamais de
   « ponctuation », jamais d'animation qui ne parle pas du projet (pas de liste de conseils, pas de
   barres de statistiques), même si la vidéo de départ en avait. On repart de zéro sur le contenu.
2. **La personne devant, tout le temps** : mise en scène `coin` (elle détourée en bas, le buste
   contre le bord de l'écran), elle change de côté quand le contenu change, avec des zooms sur les
   coupes. Ses sous-titres restent : ce sont ses mots.
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

Envoie la vidéo et dis en quelques lignes : ce qui est derrière, dans l'ordre ; ce que la maquette
suppose (tailles, équipements) ; que tu ne peux pas écouter la vidéo. Quand tout est fini :
`python machine/site_local.py arreter`.

## Si ça coince

- **Pas de PyTorch** (le détourage RobustVideoMatting en a besoin) :
  `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`. Sans lui, le
  montage prend l'ancien détourage de HyperFrames, nettement moins bon : installe plutôt PyTorch.
- **Le site ne tourne pas, la maquette n'est pas construite, le tournage est lent** :
  `references/maquette.md`, « Si ça coince ».
- **Une maquette se fige avant la fin de son passage** : la rotation filmée est trop courte pour
  les `debut` demandés. Refilme avec une `duree` plus longue.
