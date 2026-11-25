# Cerveau IA : Portail Travaux

Ce fichier est lu automatiquement par Claude Code et par tous les scripts de la machine.
C'est ce qui fait que l'IA « te connaît ». Mets-le à jour dès que tu apprends quelque chose.

## Qui on est
- Marque : Portail Travaux. Voir `config/marque.yaml` pour l'URL, la cible et la promesse.
- Le site n'est pas encore en ligne (novembre 2026) : pas de plans du site dans les vidéos pour l'instant.
- On aide les particuliers à réussir leurs projets de logement (travaux, rénovation, achat,
  aides, artisans de confiance).
- Objectif de chaque contenu : faire gagner des abonnés, puis transformer les abonnés en
  **inscrits gratuits sur Portail Travaux**.

## Comment on parle
- Tutoiement, phrases courtes, concret, chiffres réalistes (fourchettes, jamais de faux chiffres).
- Un peu d'humour, jamais de ton vendeur lourd.
- En DM : comme un pote qui s'y connaît. « Avec plaisir ! », « Top, je t'envoie ça ».

## Le mécanisme d'acquisition
- Chaque vidéo finit par : « Commente <MOT> et je t'envoie <la ressource> en DM. »
- Le DM contient le lien `/ressource/<mot>` : prénom + email → inscription gratuite → accès.
- TikTok, Shorts et Facebook ne permettent pas le DM automatique : là on dit
  « Le lien est dans ma bio, tape <MOT> ».

## À quoi on ressemble
- L'univers visuel des vidéos (couleurs, police, sous-titres, cartes) est dans `config/da.yaml`
  et `config/univers/`. Toute vidéo montée le respecte : c'est ce qui fait qu'on nous reconnaît.
- Le montage se fait avec le skill `montage-video`. Les extraits courts qui ponctuent une vidéo
  (gags de vieux films, extraits qu'on fournit) : skill `ponctuations`, banque dans `montage/ponctuations/`.
- Une vidéo sur un chantier précis, avec sa maquette 3D faite dans l'outil Dessin du site (zoom sur
  une pièce, vue large ou vue extérieure) : skill `video-chantier`. La maquette doit être crédible
  (douche dans un angle, cuisine avec plan de travail continu et passages, lit tête au mur).

## Règles
- On peut reprendre le **concept et le hook** d'une vidéo qui marche, jamais son design, ses
  images ou son texte mot pour mot. On refait tout à notre sauce avec notre expertise.
- Pas de promesses juridiques ou financières fermes : on renvoie vers un pro si besoin.

## Ce qu'on a appris (à compléter chaque semaine)
- Montage (25/11/2026) : pas de détourage de la personne, le rendu a été jugé affreux. Les
  animations prennent tout l'écran (`mise_en_scene: plein`) ; variante acceptée : la personne dans
  un cadre en bas, l'animation au-dessus (`cadre`).
- (colle ici les hooks et formats qui ont le mieux marché)
