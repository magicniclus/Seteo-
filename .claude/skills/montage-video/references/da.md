# La DA : l'univers visuel des vidéos

Deux niveaux :

- `config/da.yaml` : ce qui est commun à tous les univers (format, zones sûres, règles des
  sous-titres, rythme de montage, son, textes du carton de fin) et la ligne `univers:` qui choisit
  l'univers actif.
- `config/univers/<nom>.yaml` : un univers = des couleurs, une police, un style de cartes, un motif.

## Ce que contient un univers

```yaml
nom: "Atelier"
couleurs:
  nuit: "#0F1B2D"          # fonds sombres, contour des sous-titres
  marque: "#17304F"        # couleur de marque (dégradés des fonds)
  accent: "#FF6A2B"        # mot en cours, chiffres, bouton « Commente »
  accent_clair: "#FFB38A"  # mots forts déjà dits, textes secondaires sur fond sombre
  papier: "#FBF6EE"        # fond des cartes claires
  encre: "#0F1B2D"         # texte sur papier
  blanc: "#FFFFFF"
police: "Bricolage Grotesque"
graisse_titres: 800
graisse_texte: 600
cartes: clair      # clair = cartes papier ; sombre = cartes foncées
motif: uni         # uni, grille (plan d'architecte), rayures (ruban de chantier)
majuscules: false  # sous-titres en capitales
```

Le reste se déduit tout seul : sur un accent clair (jaune, vert vif) le texte de la pastille passe
en foncé ; sur des cartes claires, un accent trop clair est remplacé par l'encre pour rester lisible.

## Créer ou modifier un univers

1. Copie un fichier de `config/univers/`, change le nom et les valeurs.
2. Police : il faut les fichiers dans `montage/da/polices/`, nommés
   `<nom-en-minuscules-avec-tirets>-latin-<graisse>-normal.woff2` (c'est le nommage des paquets
   `@fontsource/<police>` sur npm : `npm pack @fontsource/<police>` puis copie les `.woff2` voulus
   et la licence). Uniquement des polices libres (OFL) ou dont la marque a la licence.
3. `python machine/monter.py --planche --univers <nom>` puis ouvre
   `montage/da/planche-<nom>.jpg`. Vérifie quatre choses : le mot en cours se lit d'un coup d'œil,
   le chiffre se lit en une demi-seconde, le carton de fin est lisible en petit (taille d'un
   téléphone), et l'ensemble ne ressemble pas à une marque existante.
4. Quand c'est validé : `univers: <nom>` dans `config/da.yaml`.

## Règles de la marque

- Un seul univers actif à la fois : la reconnaissance vient de la répétition.
- L'accent sert à trois choses seulement : le mot en cours, les chiffres, l'appel à l'action.
  S'il est partout, il ne signale plus rien.
- On ne copie jamais les couleurs, la police ou la mise en page d'une autre marque ou d'une vidéo
  qui marche (`CLAUDE.md`, « Règles ») : on reprend l'idée, pas l'habillage.
- Zones sûres (`zones_sures`) : rien d'important dans les 230 px du haut ni les 430 px du bas, ni à
  moins de 70 px des bords. Si un réseau change son interface, c'est là qu'on ajuste.
- Logo : mets un SVG ou PNG transparent dans `montage/da/` et son chemin dans `logo:` ; sinon le nom
  est écrit en lettres (`signature`).

## Réglages utiles de config/da.yaml

| Réglage | Effet |
|---|---|
| `sous_titres.mots_max`, `caracteres_max` | Longueur d'un écran de sous-titres. 3 mots = lecture instantanée. |
| `sous_titres.centre_y` | Hauteur des sous-titres. À descendre si tu te filmes de plus loin, à monter si le menton est bas. |
| `rythme.silence_max` | Blanc maximum toléré. 0,35 = dynamique ; 0,5 = plus posé. |
| `rythme.zoom_coupe`, `zoom_intervalle_min` | Force et fréquence de l'alternance plan large / plan serré. `zoom_coupe: 1` = aucun zoom. |
| `rythme.visage_y` | Où se trouve le visage dans l'image : c'est le centre des zooms. |
| `rythme.gel_fin` | Temps où la dernière image reste, pour lire le carton. |
| `habillage.barre_progression` | La fine barre de progression en haut. |
| `habillage.signature` | Le nom de la marque en haut à gauche. Éteint (`false`) : sur une vidéo où la personne est à l'écran, on n'affiche pas de logo en haut. Le nom reste sur le carton de fin. |
| `son.debruitage` | 0 = rien ; 8 à 12 pour atténuer un souffle derrière la voix. |
