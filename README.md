# Machine d'acquisition : Portail Habitat

Une IA (Claude) prépare chaque semaine tout ton contenu pour Instagram, TikTok, Facebook,
LinkedIn et YouTube Shorts. Ensuite elle regarde tes résultats et refait plus de ce qui marche.
Tout le contenu pousse vers **l'inscription gratuite sur Portail Habitat**.

```
config/marque.yaml  ──►  generer.py (Claude)  ──►  sorties/<semaine>/calendrier.{md,csv,json}
        ▲                                                   │
        │                                                   ▼
   stats.csv  ◄──  tes résultats  ◄──  publication (Metricool/Buffer ou publier_instagram.py)
```

## Ce qu'il faut installer, et où

| Quoi | Où | Pourquoi |
|---|---|---|
| **Python 3.11+** | Sur ton ordi : https://www.python.org/downloads/ (sur Windows, coche « Add to PATH ») | Lance les scripts |
| **VS Code** (facultatif) | Sur ton ordi : https://code.visualstudio.com | Pour modifier les fichiers facilement |
| **Une clé API Anthropic** | https://console.anthropic.com → *API Keys* (ajoute quelques € de crédit) | C'est le « cerveau » qui écrit le contenu |
| **Metricool** ou **Buffer** | https://metricool.com / https://buffer.com (compte gratuit pour commencer) | Programme les posts sur tous les réseaux et donne les stats |
| **CapCut** | Sur ton téléphone ou ordi | Monter les vidéos à partir des scripts |
| **Compte Meta Developer** (facultatif) | https://developers.facebook.com | Seulement pour la publication 100 % auto sur Instagram |

## Mise en route

**1. Récupérer le projet et installer les dépendances** (dans un terminal, dans le dossier du projet) :
```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Mettre ta clé API** : copie `.env.example` en `.env`, colle ta clé après `ANTHROPIC_API_KEY=`.

**3. Remplir `config/marque.yaml`** : ta vraie URL, ta page d'inscription, ta cible, ta promesse.
Plus tu es précis, meilleur est le contenu.

**4. Générer la semaine :**
```bash
python machine/generer.py
```
Résultat dans `sorties/<date-du-lundi>/` :
- `calendrier.md` : à lire, avec accroche, script plan par plan, légende et idée de visuel pour chaque post
- `calendrier.csv` : à importer dans Metricool, Buffer ou Google Sheets
- chaque post a un **lien suivi** (UTM), donc dans Google Analytics tu vois quel post amène des inscrits

**5. Produire et programmer** : tourne les vidéos d'après les scripts (CapCut), puis programme-les
dans Metricool/Buffer avec les légendes générées.

**6. Boucler (c'est là que la machine apprend)** : chaque semaine, exporte tes stats depuis
Metricool dans un fichier `stats.csv` (colonnes conseillées : `date, reseau, accroche, vues,
abonnes_gagnes, clics, inscriptions`), puis :
```bash
python machine/generer.py --stats stats.csv
```
L'IA analyse ce qui a marché et adapte la semaine suivante.

## En option : automatisation complète

- **Génération auto chaque dimanche** : pousse ce dépôt sur GitHub, ajoute ta clé dans
  *Settings → Secrets and variables → Actions → New secret* (`ANTHROPIC_API_KEY`). Le workflow
  `.github/workflows/hebdo.yml` génère la semaine tout seul chaque dimanche à 18h.
- **Publication auto Instagram** : passe ton compte Instagram en compte *Professionnel*, relie-le à
  une Page Facebook, crée une app sur developers.facebook.com, récupère `INSTAGRAM_ACCOUNT_ID` et un
  `META_ACCESS_TOKEN` (permissions `instagram_basic`, `instagram_content_publish`), mets-les dans
  `.env`. Ajoute une colonne `url_image` (lien public de l'image) dans le CSV, puis :
  ```bash
  python machine/publier_instagram.py sorties/<semaine>/calendrier.csv
  ```
  Ça publie les posts Instagram prévus aujourd'hui.

## Ce qu'il ne faut PAS faire

Pas de bots qui suivent/désabonnent en masse, pas de DM automatiques, pas d'achat d'abonnés.
Instagram et TikTok les détectent, réduisent ta portée et finissent par bannir le compte.
Ce système fait l'inverse : beaucoup de contenu utile, régulier, et amélioré chaque semaine
grâce aux chiffres. C'est la seule façon de grandir qui dure.
