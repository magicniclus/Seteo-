# Machine d'acquisition : Portail Habitat

Le système de la vidéo de Melvynx (« J'ai laissé l'IA gérer mon Instagram pendant 2 semaines »),
refait pour Portail Habitat. Melvynx est passé de 1 000 à 10 000 abonnés et a récupéré 3 771 emails
en 2 semaines avec cette boucle :

```
 1. CERVEAU IA        CLAUDE.md : qui tu es, comment tu parles
        │
 2. OUTLIERS          chaque matin : les vidéos qui explosent dans ta niche (outliers.py)
        │               + chaque dimanche : la semaine complète (generer.py)
        ▼
 3. TOURNAGE          /prompteur : script qui défile + caméra qui enregistre
        │
 4. MONTAGE           Claude Code + le skill montage-video (Remotion) -> vidéo 9:16
        │
 5. PUBLICATION       publier_instagram.py (3 à 12 posts/jour) ; TikTok via Metricool
        │
 6. ACQUISITION       « Commente DEVIS »  ->  DM automatique avec le lien
                      -> /ressource/devis : prénom + email -> INSCRIT GRATUIT Portail Habitat
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
| `machine/generer.py` | Semaine complète, tous réseaux + une ressource gratuite par mot-clé |
| `machine/publier_instagram.py` | Publie les reels et images à l'heure prévue |
| `serveur/app.py` | Commentaire -> DM, réponses IA aux DM, pages d'inscription, stats, prompteur |
| `.claude/skills/montage-video/` | Le skill que Claude Code utilise pour monter tes vidéos |
| `.github/workflows/hebdo.yml` | Lance outliers chaque matin et la semaine chaque dimanche, tout seul |

## Ce qu'il faut installer, et où

| Quoi | Où | Pourquoi |
|---|---|---|
| **Python 3.11+** | Ton ordi : https://www.python.org/downloads/ (Windows : coche « Add to PATH ») | Fait tourner la machine |
| **Node.js 20+** | Ton ordi : https://nodejs.org | Pour Claude Code et le montage (Remotion) |
| **Claude Code** | Ton ordi : `npm install -g @anthropic-ai/claude-code`, puis `claude` dans le dossier | Le monteur et le développeur IA |
| **ffmpeg** | Ton ordi : https://ffmpeg.org/download.html | Traitement vidéo |
| **Clé API Anthropic** | https://console.anthropic.com → API Keys (quelques € de crédit) | Le cerveau des scripts |
| **Compte Meta Developer** | https://developers.facebook.com | Publication, commentaires et DM Instagram |
| **Un serveur (VPS)** | Hetzner, OVH, Scaleway : ~5 €/mois, Ubuntu | Tourne 24h/24 : DM, pages, publication (c'est le « Hermès » de la vidéo) |
| **Un sous-domaine** | Chez ton hébergeur de domaine, ex. `machine.portail-habitat.fr` → IP du serveur | L'adresse des liens envoyés en DM |
| **Metricool** (facultatif) | https://metricool.com | Programmer TikTok / Shorts / LinkedIn + exporter les stats |

## Mise en route

**1. Sur ton ordi, dans le dossier du projet :**
```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # puis remplis .env
```

**2. Remplis `config/marque.yaml` et `CLAUDE.md`** : URL, cible, promesse, ton. Ajoute 10 à 30
comptes Instagram pros de ta niche (FR et US) dans `comptes_a_surveiller`.

**3. Génère ta première semaine :**
```bash
python machine/generer.py
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
machine.portail-habitat.fr {
    reverse_proxy 127.0.0.1:8000
}
```
Puis dans l'app Meta → Webhooks → Instagram : URL `https://machine.portail-habitat.fr/webhook/instagram`,
token de vérification = `META_VERIFY_TOKEN`, abonne-toi à **comments** et **messages**.

Ajoute les tâches automatiques (`crontab -e`) :
```
*/15 * * * * cd ~/machine && git pull -q && .venv/bin/python machine/publier_instagram.py
```
(Pense à lancer uvicorn en service permanent avec `systemd` ou `tmux` pour qu'il tourne 24h/24.)

**6. Tourne, monte, publie :**
- Ouvre `https://machine.portail-habitat.fr/prompteur/<lundi>/<numéro>` sur ton téléphone ou ton
  ordi : le script défile, tu enregistres, le rush se télécharge.
- Mets le rush dans `rushs/`, lance `claude` dans le dossier et dis :
  *« Monte le post 3 de la semaine avec le rush rushs/xxx.webm »*. Claude utilise le skill
  `montage-video`, tu fais tes retours, il refait une V2.
- Mets la vidéo en ligne (lien public), colle le lien dans `url_media` du CSV : elle part à l'heure prévue.
- TikTok / Shorts / LinkedIn : importe le CSV dans Metricool.

**7. Regarde et boucle :** `https://machine.portail-habitat.fr/stats?cle=<STATS_KEY>` montre,
par mot-clé, les DM envoyés, les ouvertures, les inscriptions et la conversion. Chaque semaine,
exporte tes stats dans `stats.csv` et lance `python machine/generer.py --stats stats.csv`.

**8. Pilote automatique :** pousse le dépôt sur GitHub et ajoute dans *Settings → Secrets and
variables → Actions* : `ANTHROPIC_API_KEY`, `INSTAGRAM_ACCOUNT_ID`, `META_ACCESS_TOKEN`. Le workflow
cherche les outliers chaque matin et prépare la semaine chaque dimanche.

## Brancher les inscrits sur Portail Habitat

Chaque inscription est enregistrée sur le serveur et envoyée à `PORTAIL_HABITAT_WEBHOOK_URL` :
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
