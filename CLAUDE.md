# Cerveau IA : Portail Travaux

Ce fichier est lu automatiquement par Claude Code et par tous les scripts de la machine.
C'est ce qui fait que l'IA « te connaît ». Mets-le à jour dès que tu apprends quelque chose.

## Qui on est
- Marque : Portail Travaux. Voir `config/marque.yaml` pour l'URL, la cible et la promesse.
- Le site n'est pas encore en ligne (novembre 2026) : pour le montrer dans une vidéo, on filme une copie
  locale (`python machine/site_local.py demarrer`, données fictives seulement), jamais de vraie donnée.
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
- La vidéo d'un projet de travaux (numéro, ville, budgets, « propose ton devis ») : skill
  `video-projet`, à part. Derrière la personne, rien que le projet (maquettes 3D faites dans l'outil
  Dessin du site, fiche, budgets, appel) : pas d'extrait venu d'ailleurs, pas d'animation hors projet.
  La maquette doit être crédible (douche dans un angle, cuisine avec plan de travail continu et
  passages, lit tête au mur).

## Règles
- On peut reprendre le **concept et le hook** d'une vidéo qui marche, jamais son design, ses
  images ou son texte mot pour mot. On refait tout à notre sauce avec notre expertise.
- Pas de promesses juridiques ou financières fermes : on renvoie vers un pro si besoin.

## Ce qu'on a appris (à compléter chaque semaine)
- Montage (25/11/2026) : le premier détourage (personne rétrécie au milieu, modèle de HyperFrames)
  a été jugé affreux. Ce qui est demandé ensuite, pour présenter un projet : le contenu derrière
  la personne pendant toute la vidéo, elle détourée en bas de l'écran comme un présentateur, qui
  change de côté, avec des zooms (`mise_en_scene: coin`, détourage RobustVideoMatting). Autres
  versions acceptées : animations plein écran (`plein`) ou personne dans un cadre en bas (`cadre`).
- Montage (26/11/2026) : en `coin`, on le trouvait trop en bas. Variante demandée : lui détouré au
  centre, plus haut, et la 3D du projet dans un carré travaillé et légèrement animé au-dessus de lui
  (`mise_en_scene: vitrine`, skill `video-projet`).
- Montage (26/11/2026) : la mise en page préférée, d'après une vidéo de référence : l'écran coupé en
  deux, le contenu en haut sur fond bleu (barre de titre, carte, pastilles, encart qui déborde), lui
  en bas, les sous-titres en bandeau sur la couture (`mise_en_scene: partage`). À faire par défaut.
  En bas, sa VRAIE vidéo avec son décor, sur toute la largeur : le détourage sur fond transparent y
  a été jugé moche (« je veux plus le background transparent »).
- (colle ici les hooks et formats qui ont le mieux marché)
