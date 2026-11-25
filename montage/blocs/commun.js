// Début commun à tous les blocs. Le temps est local : 0 = l'instant où le bloc apparaît.
(function () {
  const D = __DONNEES__;
  const tl = gsap.timeline({ paused: true });
  const DOUX = "power3.out";
  const REBOND = "back.out(1.7)";
  const el = (suffixe) => document.getElementById(D.id + "-" + suffixe);
  // de -> a à l'instant t, sans rien toucher avant
  const va = (cible, de, a, duree, t, ease) =>
    tl.fromTo(cible, de, Object.assign({ duration: duree, ease: ease || DOUX, immediateRender: false }, a), t);
  // apparition simple d'un élément caché dans le CSS
  const montrer = (cible, t, de) =>
    tl.fromTo(cible, Object.assign({ autoAlpha: 0 }, de || { y: 30 }),
              { autoAlpha: 1, x: 0, y: 0, scale: 1, duration: 0.35, ease: DOUX }, t);
  // un trait qui se dessine (coche, croix, soulignement) : le tracé porte pathLength="100"
  const dessiner = (trace, t, duree) =>
    tl.fromTo(trace, { strokeDasharray: 100, strokeDashoffset: 100 },
              { strokeDashoffset: 0, duration: duree || 0.35, ease: "power1.inOut" }, t);

  // Scène plein écran : elle monte d'un bloc, puis repart par le haut
  const scene = el("scene");
  if (scene && D.place) {
    // La personne reste devant : on cherche la plus grande taille du contenu qui tient dans la hauteur
    // libre au-dessus de sa tête (D.place), et on le centre dans cette hauteur.
    const contenu = scene.firstElementChild;
    const large = contenu.offsetWidth;   // la largeur utile, entre les marges de côté
    const ajuster = () => {
      // à la taille k, le contenu se met en page sur large / k : plus on réduit, plus les lignes sont longues.
      // Il « tient » s'il ne dépasse ni en hauteur ni en largeur (un mot trop long pour sa ligne). Un décor
      // qui déborde exprès (le cadre du bon choix) dépasse autant à toutes les tailles : on le décompte.
      const depasse = () => contenu.scrollWidth - contenu.offsetWidth;
      contenu.style.width = (large / 0.45).toFixed(1) + "px";
      const decor = depasse();
      const tient = (k) => {
        contenu.style.width = (large / k).toFixed(1) + "px";
        return contenu.offsetHeight * k <= D.place && depasse() <= decor + 1;
      };
      let k = 1.2;   // un bloc court grossit un peu pour occuper la place, jamais plus
      if (!tient(k)) {
        let bas = 0.45, haut = k;
        for (let i = 0; i < 8; i++) { const m = (bas + haut) / 2; if (tient(m)) bas = m; else haut = m; }
        k = bas;
        tient(k);
      }
      contenu.style.transform = "translateY(" + Math.round((D.place - contenu.offsetHeight * k) / 2) + "px) scale(" + k.toFixed(3) + ")";
    };
    ajuster();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(ajuster);  // même mesure une fois la police chargée
  }
  if (scene) {
    tl.fromTo(scene, { autoAlpha: 1, yPercent: 100 }, { autoAlpha: 1, yPercent: 0, duration: 0.45, ease: "power4.out" }, 0);
    if (!D.reste) va(scene, { yPercent: 0 }, { yPercent: -100 }, 0.36, D.duree - 0.36, "power3.in");
  }
  if (el("sur")) montrer(el("sur"), 0.22);
  if (el("titre")) montrer(el("titre"), 0.32);
