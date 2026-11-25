# HyperFrames : ce qu'il faut savoir pour sortir du gabarit

HyperFrames (HeyGen, open source) transforme une page HTML en vidéo : le moteur ouvre la page dans
Chrome, la place image par image à l'instant voulu et encode le tout avec ffmpeg. La version est
figée dans `montage/package.json`. Doc : https://hyperframes.heygen.com/llms.txt (index des pages).

## Ce que `monter.py` écrit dans `montage/projets/<id>/`

```
index.html                    composition principale : la prise, les plans de coupe, la musique
compositions/sous-titres.html calque des sous-titres (sa propre timeline)
compositions/habillage.html   calque accroche / chiffres / carton de fin / signature / barre
assets/                       a-roll.mp4, plans de coupe, polices
lib/gsap.min.js               GSAP en local (aucun appel réseau pendant le rendu)
```

Ces fichiers sont régénérés à chaque `monter.py` : ne les modifie pas à la main, ce serait perdu.
On agit sur `plan.json`, sur `extras.html` (une vidéo) ou sur `montage/gabarit/` (toutes les vidéos).

## Les règles du moteur (sinon le rendu est faux)

1. **Le temps est dans le HTML** : un élément minuté porte `id`, `data-start`, `data-duration`
   (secondes). Les `<video>` avec son : `data-has-audio="true"` ; sans son : `muted`.
2. **Jamais de vidéo minutée dans un élément minuté.** Pour animer une vidéo, on l'enveloppe dans
   un `<div>` NON minuté et on anime l'enveloppe (c'est ce que fait le gabarit pour les plans de coupe).
3. **Une timeline GSAP en pause par composition**, enregistrée sous son identifiant :
   `window.__timelines["main"] = tl`. Pas de `play()`, pas de `currentTime`, pas de minuterie.
4. **Rien d'aléatoire ni d'horloge** : pas de `Math.random()`, `Date.now()`, `requestAnimationFrame`,
   `fetch`. Le rendu saute directement à n'importe quelle image, dans n'importe quel ordre.
5. **Des `fromTo`** plutôt que des `to` : les deux bouts sont écrits, donc justes après un saut.
   Plusieurs `fromTo` sur le même élément : `immediateRender: false` sur tous sauf le premier
   (la fonction `va()` du gabarit le fait).
6. **Un élément montré par la timeline** est caché dans le CSS (`opacity: 0; visibility: hidden`),
   révélé par un `fromTo` dont l'arrivée contient `autoAlpha: 1`, et éteint par un
   `tl.set(el, { autoAlpha: 0 }, fin)`.
7. **On anime des transformations** (`x`, `y`, `scale`, `rotate`) et l'opacité, pas `top`, `left`,
   `width`, `fontSize`.
8. Pas de sélecteur construit avec un gabarit de chaîne (`` `#${id}` ``) dans `querySelector` :
   `document.getElementById("carte-" + n)`.

## Vérifier

```bash
cd montage/projets/<id>
../../node_modules/.bin/hyperframes lint .                 # contrôle statique (fait par monter.py)
../../node_modules/.bin/hyperframes check .                # + exécution, mise en page, contrastes
../../node_modules/.bin/hyperframes snapshot . --at 3.2,7  # images à des instants précis
../../node_modules/.bin/hyperframes preview                # éditeur dans le navigateur (sur ton ordi)
```

Mets `HYPERFRAMES_NO_TELEMETRY=1` devant ces commandes (les scripts de `machine/` le font déjà).

## extras.html : une animation sur mesure pour UNE vidéo

Si `montage/projets/<id>/extras.html` existe, son contenu est inséré tel quel dans la composition
principale, au-dessus de la prise. Il contient des balises, un `<style>`, et une fonction
`window.PH_EXTRAS(tl, va)` qui ajoute ses animations à la timeline principale.
`va(cible, de, a, duree, instant, ease)` est le `fromTo` sûr du gabarit.

Exemple : une liste de trois points qui apparaissent un par un entre 6 s et 12 s.

```html
<div id="liste" class="liste">
  <p id="liste-1" class="liste__point">1. La dépose</p>
  <p id="liste-2" class="liste__point">2. L'évacuation des gravats</p>
  <p id="liste-3" class="liste__point">3. Les finitions</p>
</div>
<style>
  .liste { position: absolute; z-index: 6; left: var(--zone-cotes); right: var(--zone-cotes);
           top: calc(var(--zone-haut) + 20px); padding: 36px 44px; border-radius: 44px;
           background: var(--carte-fond); color: var(--carte-texte);
           font-weight: var(--graisse-titres); font-size: 54px; line-height: 1.25;
           opacity: 0; visibility: hidden; }
  .liste__point { opacity: 0; }
</style>
<script>
  window.PH_EXTRAS = function (tl, va) {
    const liste = document.getElementById("liste");
    tl.fromTo(liste, { autoAlpha: 0, y: 40 }, { autoAlpha: 1, y: 0, duration: 0.35, ease: "back.out(1.7)" }, 6);
    [6.3, 8.1, 9.9].forEach(function (t, k) {
      tl.fromTo(document.getElementById("liste-" + (k + 1)), { opacity: 0, x: -30 },
                { opacity: 1, x: 0, duration: 0.25, ease: "power3.out" }, t);
    });
    va(liste, { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -30 }, 0.22, 11.78, "power2.in");
    tl.set(liste, { autoAlpha: 0 }, 12);
  };
</script>
```

Utilise les variables de la DA (`--accent`, `--nuit`, `--carte-fond`, `--carte-texte`, `--police`,
`--graisse-titres`, `--zone-haut`...) : jamais de couleur écrite en dur. Relance
`python machine/monter.py <id> --apercu` et regarde le résultat avant de rendre.

Une animation qui resservira (liste, comparaison, avant/après) mérite d'entrer dans le gabarit
(`montage/gabarit/habillage.*` + une clé dans `plan.json`) plutôt que d'être recopiée.
