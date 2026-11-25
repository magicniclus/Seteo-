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
  "blocs": [
    {"bloc": "nom", "de": 0.4, "a": 3.9, "nom": "Prénom Nom", "role": "Portail Travaux"},
    {"bloc": "liste", "de": "m18", "a": "m27", "sur_titre": "Sur ton devis",
     "titre": "3 lignes qui font *grimper* la facture", "signe": "croix",
     "lignes": [{"texte": "La dépose", "quand": "m21"}, "Les gravats",
                {"texte": "Les finitions", "detail": "joints, plinthes, peinture"}]},
    {"bloc": "commentaire", "de": "m62"}
  ],
  "reglages": {"visage_y": 0.45, "centre_y": 1330},
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
| `blocs` | Animations prêtes à l'emploi : voir « Les blocs » ci-dessous. |
| `reglages` | Réglages de la DA pour CETTE vidéo seulement, mêmes noms que dans `config/da.yaml` (`rythme` et `sous_titres`) : `visage_y`, `centre_y`, `taille`, `mots_max`, `zoom_coupe`, `zoom_intervalle_min`... |
| `carton_fin` | `de` (défaut : au dernier « commente » / « tape » prononcé), `suite` (la ligne sous le mot-clé). `false` pour ne pas en mettre. |
| `sous_titres` | `false` pour une vidéo sans sous-titres (rare). |
| `musique` | Fichier audio (dont on a les droits) joué en fond, très bas (`son.musique_volume` de la DA). |

## Les blocs

Chaque bloc a `bloc` (son nom), `de`, et `a` (facultatif : sinon sa durée par défaut).
Les blocs plein écran acceptent tous `sur_titre` (petite étiquette) et `titre` (les `*astérisques*`
passent en couleur d'accent). Styles et animations : `montage/blocs/` ; fabriques : `machine/blocs.py`.

| Bloc | Champs | Durée par défaut |
|---|---|---|
| `liste` | `lignes` : 1 à 4, chacune un texte ou `{"texte", "detail", "quand"}` ; `signe` : `coche` (défaut), `croix`, `numero` | 7 s |
| `barres` | `lignes` : 2 à 4 `{"nom", "valeur" (nombre), "texte" (affiché, ex. "45 %"), "quand"}` ; `fort` : n° de la barre en accent (défaut : la plus grande) | 6 s |
| `comparaison` | `gauche` (carte du haut) et `droite` (carte du bas) : `{"titre", "valeur", "note"}` ; `gagnant` : `"gauche"`, `"droite"` ou rien ; `badge` (défaut « Le bon choix ») ; `verdict` : l'instant où il tombe | 6 s |
| `avant_apres` | `avant`, `apres` : deux images (chemins depuis la racine) ; `quand` : l'instant de la bascule ; `etiquette_avant`, `etiquette_apres` | 5 s |
| `commentaire` | `texte` (défaut : le mot-clé), `pseudo` (défaut « toi »), `reponse` (défaut « Je t'envoie ça en DM ») | 4 s |
| `nom` | `nom`, `role` | 3,5 s |

`quand` est un instant de la vidéo (`"m21"` ou des secondes) : la ligne apparaît quand on la dit.
Sans `quand`, les lignes arrivent en cascade. Une ligne ne peut pas arriver avant le bloc ni dans
sa dernière seconde : fais commencer le bloc un peu avant la première ligne (une demi-seconde suffit).

## Règles de placement

- Une carte de chiffre et un plan de coupe en mode `carte` occupent la même zone (le haut) : pas les
  deux en même temps. Un plan `plein` peut recevoir une carte de chiffre par-dessus.
- L'accroche occupe aussi le haut : rien d'autre avant qu'elle parte.
- Les sous-titres s'arrêtent tout seuls quand le carton de fin arrive (il dit la même chose).
- Un plan de coupe dure entre 1,5 et 5 s. Plus court on ne voit rien, plus long on perd le visage.
- Ne couvre jamais les trois premières secondes par un plan `plein` ou un bloc plein écran : c'est le
  visage qui accroche. Même chose pendant l'appel à l'action.
- Un bloc plein écran occupe tout le haut : pas de carte de chiffre ni de plan `carte` en même temps.
  Les sous-titres, eux, continuent par-dessus.
- `commentaire` occupe la zone des cartes (le haut) : rien d'autre à cet endroit pendant qu'il est là.
- `nom` se pose sous les sous-titres : il cohabite avec l'accroche.
