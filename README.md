# Machine d'acquisition : Portail Travaux

Le système de la vidéo de Melvynx (« J'ai laissé l'IA gérer mon Instagram pendant 2 semaines »),
refait pour Portail Travaux. Melvynx est passé de 1 000 à 10 000 abonnés et a récupéré 3 771 emails
en 2 semaines avec cette boucle :

```
 1. CERVEAU IA        CLAUDE.md : qui tu es, comment tu parles
        │
 2. VEILLE            chaque matin : les vidéos qui explosent (outliers.py)
        │               + les tendances et les hooks du moment (tendances.py)
        │               + chaque dimanche : la semaine complète écrite par Claude (generer.py)
        ▼
 3. TOURNAGE          /studio -> /prompteur : le texte de Claude défile, tu t'enregistres,
        │               la prise part toute seule sur le serveur (rushs/)
        │             + ecrans.py filme le site Portail Travaux (plans de coupe 1080x1920)
        │
 4. MONTAGE           Claude Code + le skill montage-video : il transcrit, coupe les blancs et les
        │               ratés, pose sous-titres, chiffres, plans de coupe et carton « Commente <MOT> »
        │               dans ton univers visuel (config/da.yaml), puis relit sa vidéo et la corrige
        │
 5. PUBLICATION       publier_instagram.py (3 à 12 posts/jour) ; TikTok via Metricool
        │
 6. ACQUISITION       « Commente DEVIS »  ->  DM automatique avec le lien
                      -> /ressource/devis : prénom + email -> INSCRIT GRATUIT Portail Travaux
                      -> l'IA répond aux DM dans ton style
        │
 7. APPRENTISSAGE     /stats : conversion par mot-clé -> stats.csv -> la semaine suivante s'adapte
```

## Les fichiers

| Fichier | Rôle |
|---|---|
| `CLAUDE.md` | Le « cerveau IA » : identité, ton, règles. Lu par Claude Code et tous les scripts |
| `config/marque.yaml` | Ton URL, ta cible, ta promesse, les comptes à surveiller |
| `machine/outliers.py` | Trouve les vidéos à x3+ de leur moyenne et réécrit le script à ta sauce |
| `machine/tendances.py` | Scanne les hashtags Instagram et les Shorts YouTube : tendances + bibliothèque de hooks |
| `machine/ecrans.py` | Filme le site Portail Travaux en vertical (défilement, clics) pour tes vidéos |
| `machine/generer.py` | Semaine complète, tous réseaux + une ressource gratuite par mot-clé |
| `machine/publier_instagram.py` | Publie les reels et images à l'heure prévue |
| `serveur/app.py` | Commentaire -> DM, réponses IA aux DM, pages d'inscription, stats, studio, prompteur |
| `.claude/skills/montage-video/` | Le skill que Claude Code utilise pour monter tes vidéos |
| `config/da.yaml` + `config/univers/` | Ta DA : couleurs, police, sous-titres, rythme. Lue par tous les montages |
| `machine/reparer.py` | Répare une vidéo arrivée coupée à l'envoi, quand il ne lui manque que la fin |
| `machine/transcrire.py` | Rush → texte mot par mot (ElevenLabs Scribe, ou Whisper en local) |
| `machine/couper.py` | Enlève les blancs et les prises ratées, met la vidéo au format et la voix au bon niveau |
| `machine/broll.py` | Plans de coupe : vieux films du domaine public, Pexels, page web filmée, fichiers à toi ; et la banque de ponctuations (`montage/ponctuations/`) |
| `machine/site_local.py` | Lance une copie du site Portail Travaux sur la machine (émulateurs Firebase, données fictives) pour filmer son outil Dessin |
| `machine/chantier3d.py` | Maquette 3D d'un chantier faite avec l'outil Dessin du site (agencement selon les règles d'usage), filmée en zoom sur une pièce, en vue large ou en vue extérieure |
| `machine/monter.py` | Plan de montage + DA → vidéo (HyperFrames : du HTML animé rendu en MP4) |
| `machine/blocs.py` + `montage/blocs/` | Animations prêtes à l'emploi, reprises du catalogue HyperFrames et refaites dans ta DA : liste à cocher, barres, comparaison, avant/après, fiche de demande client (infos privées floutées), bulle de commentaire, bandeau nom |
| `machine/yeux.py` | Relit la vidéo finie : planche d'images, mesures du son, critique de Gemini |
| `montage/` | L'atelier : HyperFrames, le gabarit des vidéos, les polices, un dossier par vidéo |
| `.github/workflows/hebdo.yml` | Lance outliers + tendances chaque matin et la semaine chaque dimanche, tout seul |

## Ce qu'il faut installer, et où

| Quoi | Où | Pourquoi |
|---|---|---|
| **Python 3.11+** | Ton ordi : https://www.python.org/downloads/ (Windows : coche « Add to PATH ») | Fait tourner la machine |
| **Node.js 22+** | Ton ordi : https://nodejs.org | Pour Claude Code et le montage (HyperFrames) |
| **Claude Code** | Ton ordi : `npm install -g @anthropic-ai/claude-code`, puis `claude` dans le dossier | Le monteur et le développeur IA |
| **ffmpeg** | Ton ordi : https://ffmpeg.org/download.html | Traitement vidéo |
| **Clé API Anthropic** | https://console.anthropic.com → API Keys (quelques € de crédit) | Le cerveau des scripts |
| **Clé ElevenLabs** (facultatif) | https://elevenlabs.io → API Keys | Transcription Scribe, la plus précise en français. Sans elle : Whisper, gratuit, sur ta machine |
| **Clé Pexels** (facultatif) | https://www.pexels.com/api/ (gratuit) | Plans de coupe libres de droits |
| **Clé Gemini** (facultatif) | https://aistudio.google.com/apikey | Les « yeux » : Gemini regarde la vidéo montée et dit quoi corriger |
| **Clé API YouTube** | https://console.cloud.google.com → active « YouTube Data API v3 » → Identifiants → Clé API (gratuit) | Veille des Shorts les plus vus |
| **Compte Meta Developer** | https://developers.facebook.com | Publication, commentaires et DM Instagram |
| **Un serveur (VPS)** | Hetzner, OVH, Scaleway : ~5 €/mois, Ubuntu | Tourne 24h/24 : DM, pages, publication (c'est le « Hermès » de la vidéo) |
| **Un sous-domaine** | Chez ton hébergeur de domaine, ex. `machine.ton-domaine.fr` → IP du serveur | L'adresse des liens envoyés en DM |
| **Metricool** (facultatif) | https://metricool.com | Programmer TikTok / Shorts / LinkedIn + exporter les stats |

## Mise en route

**1. Sur ton ordi, dans le dossier du projet :**
```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-montage.txt   # montage : images + Whisper local
playwright install chromium        # le navigateur qui filme les pages web
(cd montage && npm install)        # HyperFrames, le moteur de montage
cp .env.example .env               # puis remplis .env
```

**2. Remplis `config/marque.yaml` et `CLAUDE.md`** : URL, cible, promesse, ton. Ajoute 10 à 30
comptes Instagram pros de ta niche (FR et US) dans `comptes_a_surveiller`, tes hashtags et tes
recherches YouTube, et les pages du site à filmer dans `pages_ecran`.

**3. Lance la veille, filme le site, puis génère ta première semaine :**
```bash
python machine/tendances.py        # tendances + hooks -> sorties/tendances/
python machine/outliers.py         # vidéos qui explosent -> sorties/outliers/
python machine/ecrans.py           # vidéos du site -> ecrans/*.mp4
python machine/generer.py          # la semaine, nourrie par la veille
```
→ `sorties/<lundi>/calendrier.md` (à lire), `calendrier.csv` (planning), et `ressources/*.json`
(une ressource gratuite par mot-clé).

**4. Connecte Instagram (Meta) :**
1. Passe ton compte Instagram en **compte professionnel** et relie-le à une **Page Facebook**.
2. Sur developers.facebook.com : *Créer une app* → type *Entreprise* → ajoute les produits
   **Instagram** et **Webhooks**.
3. Demande les permissions `instagram_basic`, `instagram_content_publish`,
   `instagram_manage_comments`, `instagram_manage_messages`, `pages_messaging`.
4. Récupère l'**ID du compte Instagram**, un **token d'accès longue durée** (de la Page) et le
   **secret de l'app** → mets-les dans `.env`.
5. Pour l'usage par le public, Meta demande une **vérification de l'app** (App Review). En
   attendant, tout marche avec ton propre compte en mode développement.

**5. Mets le serveur en ligne (VPS) :**
```bash
# sur le serveur
sudo apt install -y python3-venv git caddy
git clone <ton dépôt> machine && cd machine
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
nano .env                                    # mêmes valeurs que sur ton ordi
.venv/bin/uvicorn serveur.app:app --host 127.0.0.1 --port 8000
```
Caddy donne le HTTPS automatiquement. Mets dans `/etc/caddy/Caddyfile` :
```
machine.ton-domaine.fr {
    reverse_proxy 127.0.0.1:8000
}
```
Puis dans l'app Meta → Webhooks → Instagram : URL `https://machine.ton-domaine.fr/webhook/instagram`,
token de vérification = `META_VERIFY_TOKEN`, abonne-toi à **comments** et **messages**.

Ajoute les tâches automatiques (`crontab -e`) :
```
*/15 * * * * cd ~/machine && git pull -q && .venv/bin/python machine/publier_instagram.py
```
(Pense à lancer uvicorn en service permanent avec `systemd` ou `tmux` pour qu'il tourne 24h/24.)

**6. Tourne, monte, publie :**
- Ouvre `https://machine.ton-domaine.fr/studio?cle=<STATS_KEY>` sur ton téléphone (ajoute-le à
  l'écran d'accueil). Tu y vois les vidéos à tourner cette semaine (⏺ à faire, ✅ faite), les
  vidéos du site et les hooks du moment.
- Clique sur **Enregistrer** : le texte écrit par Claude défile sur l'écran, la caméra filme.
  À chaque **Stop**, la prise est envoyée sur le serveur dans `rushs/` (refais autant de prises
  que tu veux). Si le réseau coupe, la prise est téléchargée sur ton téléphone.
- Récupère les prises sur ton ordi : `rsync -av root@<ip-serveur>:machine/rushs/ rushs/`
- Lance `claude` dans le dossier et dis : *« Monte le post 3 de la semaine »*. Claude suit le
  skill `montage-video` (voir « Le montage automatique » plus bas). Tu fais tes retours, il refait une V2.
- Mets la vidéo en ligne (lien public), colle le lien dans `url_media` du CSV : elle part à l'heure prévue.
- TikTok / Shorts / LinkedIn : importe le CSV dans Metricool.

**7. Regarde et boucle :** `https://machine.ton-domaine.fr/stats?cle=<STATS_KEY>` montre,
par mot-clé, les DM envoyés, les ouvertures, les inscriptions et la conversion. Chaque semaine,
exporte tes stats dans `stats.csv` et lance `python machine/generer.py --stats stats.csv`.

**8. Pilote automatique :** pousse le dépôt sur GitHub et ajoute dans *Settings → Secrets and
variables → Actions* : `ANTHROPIC_API_KEY`, `INSTAGRAM_ACCOUNT_ID`, `META_ACCESS_TOKEN`. Le workflow
cherche les outliers chaque matin et prépare la semaine chaque dimanche.

## Le montage automatique

Tu te filmes au téléphone (à la verticale), tu donnes la vidéo à Claude Code (*« Monte cette vidéo,
mot-clé DEVIS »*, ou *« Monte le post 3 »* si elle vient du prompteur). Il enchaîne :

| Étape | Outil | Ce qui se passe |
|---|---|---|
| 1. Transcrire | `transcrire.py` : ElevenLabs Scribe ou Whisper | Chaque mot avec son début et sa fin |
| 2. Couper | `couper.py` : ffmpeg | Blancs et prises ratées enlevés, format vertical, voix au niveau des réseaux |
| 3. Planifier | Claude écrit `plan.json` | Corrections, accroche, chiffres, animations (blocs), plans de coupe, mots forts |
| 3 bis. Plans de coupe | `broll.py` : Internet Archive, Pexels, Playwright | Gags de vieux films (domaine public), vidéos libres de droits, pages web filmées, tes propres clips |
| 4. Monter | `monter.py` : HyperFrames | Sous-titres mot à mot, cartes, zooms, carton de fin, dans ta DA |
| 5. Regarder | `yeux.py` : planche d'images + Gemini | La vidéo est relue ; ce qui cloche est corrigé puis rendu de nouveau |

**Ta DA (ton univers)** est dans `config/da.yaml` et `config/univers/`. Trois univers sont proposés
(`atelier`, `chantier`, `plan`) : regarde-les avec `python machine/monter.py --planche --univers <nom>`
(image dans `montage/da/`), choisis-en un sur la ligne `univers:`, ou copie-en un pour créer le tien.

**À la main**, sans Claude :
```bash
python machine/transcrire.py rushs/2026-11-30-3-143012.webm
python machine/couper.py 2026-11-30-3 --retirer 5.4-10.9
# écris montage/projets/2026-11-30-3/plan.json (format : .claude/skills/montage-video/references/plan.md)
python machine/monter.py 2026-11-30-3 --apercu     # images clés à vérifier
python machine/monter.py 2026-11-30-3 --rendu      # -> montages/2026-11-30-3.mp4
python machine/yeux.py 2026-11-30-3                # relecture
```

**Deux mises en scène des animations**, au choix (`mise_en_scene` dans `config/da.yaml`, ou vidéo
par vidéo) : `plein`, l'animation remplace l'image quelques secondes ; `cadre`, tu restes à l'écran
dans un cadre arrondi en bas et l'animation s'affiche au-dessus. Rien n'est détouré.

**Ponctuations** (skill `ponctuations` : *« anime plus cette vidéo »*, *« trouve un extrait pour
cette phrase »*) : deux ou trois extraits de 2 à 3 s par vidéo (un gag de vieux film posé sur une
phrase), piochés dans la banque `montage/ponctuations/` (`python machine/broll.py banque`). Claude va
chercher lui-même les films du domaine public. Pour un extrait d'Instagram ou d'un film récent, c'est
toi qui lui donnes le fichier : un enregistrement d'écran suffit.

**Vidéo de chantier en 3D** (skill `video-chantier` : *« voilà un chantier : salle de bains de 6 m²,
douche à l'italienne, double vasque ; fais-moi un zoom sur la pièce »*) : Claude construit la maquette
avec l'outil Dessin de ton site (`python machine/site_local.py demarrer` le lance sur la machine,
avec des données fictives), l'aménage selon les règles d'usage et la filme selon le plan que tu
choisis : zoom sur une pièce, vue large de l'intérieur, ou vue extérieure avec le toit et le jardin.

**Clients** : une demande de travaux se montre soit en fiche redessinée (bloc `demande`), soit en
filmant ton outil avec `broll.py ecran --prive --flouter ...`. Dans les deux cas le nom, l'adresse,
le téléphone et l'e-mail sont masqués avant d'entrer dans la vidéo.

**Voix** : la machine n'ajoute jamais de voix. La seule voix d'une vidéo est la tienne.

**Extraits et droits** : la machine va chercher elle-même des images libres (Pexels, films du
domaine public sur Internet Archive) et filme des pages web. Un extrait de film récent ou la vidéo
d'un autre compte, c'est toi qui le fournis (un enregistrement d'écran suffit) : elle l'insère, mais
ne le télécharge pas à ta place, et te rappelle qu'un retrait pour droits d'auteur pénalise un compte.

## Brancher les inscrits sur Portail Travaux

Chaque inscription est enregistrée sur le serveur et envoyée à `PORTAIL_TRAVAUX_WEBHOOK_URL` :
```json
{"prenom": "Léa", "email": "lea@exemple.fr", "mot_cle": "devis", "source": "dm"}
```
Mets là l'adresse de l'API d'inscription de ton site, ou un scénario Zapier/Make/Brevo qui crée
le compte et envoie l'email de bienvenue.

## Les règles pour ne pas se faire bannir

- Le DM n'est envoyé **qu'aux gens qui commentent le mot-clé** (réponse privée officielle de Meta),
  et l'IA ne répond **qu'aux gens qui t'écrivent**. Pas de DM à froid, pas de follow/unfollow.
- Les outliers passent par l'API officielle (Business Discovery), pas par du scraping.
- On reprend le **concept et le hook** d'une vidéo qui marche, jamais son design ni son texte.
- Pas d'achat d'abonnés : ça tue la portée.
