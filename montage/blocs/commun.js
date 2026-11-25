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
  if (scene) {
    tl.fromTo(scene, { autoAlpha: 1, yPercent: 100 }, { autoAlpha: 1, yPercent: 0, duration: 0.45, ease: "power4.out" }, 0);
    va(scene, { yPercent: 0 }, { yPercent: -100 }, 0.36, D.duree - 0.36, "power3.in");
  }
  if (el("sur")) montrer(el("sur"), 0.22);
  if (el("titre")) montrer(el("titre"), 0.32);
