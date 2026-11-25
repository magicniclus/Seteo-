# plan.json : le plan de montage

Un fichier par vidéo : `montage/projets/<id>/plan.json`. C'est la seule chose à écrire à la main ;
`machine/monter.py` en tire toute la composition. Toutes les clés sont facultatives sauf `mot_cle`
si on veut un carton de fin.

## Les temps

Partout où il faut un instant, deux écritures possibles :

- `"m34"` : le mot n° 34 de la vidéo finale (numéros affichés par `couper.py`, ou lus dans
  `mots.json`). Pour un début (`de`) c'est le début du mot, pour une fin (`a`) c'est sa fin.
  **À préférer** : ça reste juste si on déplace un réglage de rythme.
- `12.4` : des secondes de la vidéo finale (jamais du rush).

Les numéros de mots sont ceux d'AVANT corrections : une correction ne décale rien.

## Exemple complet

```json
{
  "reseau": "instagram",
  "mot_cle": "DEVIS",
  "retirer": [[5.5, 11]],
  "corrections": {"7": "année ?", "8": "Attends", "9": "", "38": "€", "63": "DEVIS", "64": ""},
  "accroche": {"texte": "Ta salle de bain : *attends avant de signer*", "a": "m12"},
  "emphase": [21, "gratuit"],
  "chiffres": [
    {"de": "m34", "a": "m39", "texte": "6 000 – 12 000 €", "legende": "une salle de bain complète, posée"}
  ],
  "broll": [
    {"de": "m55", "a": "m61", "fichier": "ecrans/france-renov.mp4", "mode": "carte", "debut": 0.5},
    {"de": "m20", "a": "m27", "fichier": "broll/pexels/bathroom-123.mp4", "mode": "plein"}
  ],
  "carton_fin": {"suite": "et je t'envoie ma checklist en DM"},
  "musique": "musique/fond-calme.mp3"
}
```

## Les clés

| Clé | Rôle |
|---|---|
| `reseau` | `instagram`, `facebook` (carton « Commente <MOT> ») ou `tiktok`, `youtube_shorts`, `linkedin` (« Lien en bio, tape <MOT> »). Défaut : `instagram`. |
| `mot_cle` | Le mot à commenter, en majuscules. Sans lui, pas de carton de fin. |
| `retirer` | Plages du RUSH à jeter (prises ratées), en secondes du rush : `[[debut, fin], ...]`. Lu par `couper.py` quand on ne lui passe pas `--retirer`. |
| `corrections` | `{"numéro du mot": "nouveau texte"}`. Texte vide = supprimer le mot. Plusieurs mots = le temps est partagé entre eux (`"62": "Commente DEVIS"`). |
| `accroche` | `texte` (les `*astérisques*` passent en couleur d'accent) et `a` : jusqu'à quand elle reste (défaut 3 s). Elle est à l'écran dès la première image. |
| `emphase` | Mots forts : numéros (`21`) ou textes (`"gratuit"`, toutes les occurrences). Les mots contenant un chiffre, `€`, `%`, et le mot-clé le sont déjà. |
| `chiffres` | Cartes en haut de l'écran : `de`, `a` (défaut 2,6 s), `texte`, `legende`. Un nombre seul (`"12 000 €"`) défile jusqu'à sa valeur ; `"compter": false` pour l'empêcher. |
| `broll` | Plans de coupe : `de`, `a`, `fichier` (vidéo ou image, chemin depuis la racine du dépôt), `mode` (`plein` = tout l'écran, les sous-titres restent ; `carte` = cadre arrondi en haut, le visage reste), `debut` (où commencer dans le fichier, en secondes). |
| `carton_fin` | `de` (défaut : au dernier « commente » / « tape » prononcé), `suite` (la ligne sous le mot-clé). `false` pour ne pas en mettre. |
| `sous_titres` | `false` pour une vidéo sans sous-titres (rare). |
| `musique` | Fichier audio (dont on a les droits) joué en fond, très bas (`son.musique_volume` de la DA). |

## Règles de placement

- Une carte de chiffre et un plan de coupe en mode `carte` occupent la même zone (le haut) : pas les
  deux en même temps. Un plan `plein` peut recevoir une carte de chiffre par-dessus.
- L'accroche occupe aussi le haut : rien d'autre avant qu'elle parte.
- Les sous-titres s'arrêtent tout seuls quand le carton de fin arrive (il dit la même chose).
- Un plan de coupe dure entre 1,5 et 5 s. Plus court on ne voit rien, plus long on perd le visage.
- Ne couvre jamais les deux premières secondes par un plan `plein` : c'est le visage qui accroche.
