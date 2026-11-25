// Composition principale (GSAP) : zooms de la prise et plans de coupe.
// Règles HyperFrames : une timeline en pause, enregistrée sous l'identifiant de la composition ;
// des fromTo (justes même quand le rendu saute directement à une image) ; ni horloge, ni hasard,
// et jamais de lecture vidéo pilotée d'ici (ce sont les attributs data-* qui s'en chargent).
(function () {
  const D = __DONNEES__;
  const tl = gsap.timeline({ paused: true });
  // de -> a à l'instant t, sans rien toucher avant
  const va = (cible, de, a, duree, t, ease) =>
    tl.fromTo(cible, de, Object.assign({ duration: duree, ease: ease || "power3.out", immediateRender: false }, a), t);

  // 1. La prise : plan large / plan serré à chaque coupe, avec un léger zoom continu
  const plan = document.getElementById("plan");
  gsap.set(plan, { transformOrigin: "50% " + D.visageY * 100 + "%" });
  D.zooms.forEach((z, k) => {
    if (k === 0) tl.fromTo(plan, { scale: z.de }, { scale: z.a, duration: z.duree, ease: "none" }, z.t);
    else va(plan, { scale: z.de }, { scale: z.a }, z.duree, z.t, "none");
  });

  // 2. Plans de coupe
  D.broll.forEach((b) => {
    const boite = document.getElementById(b.id);
    const cadre = boite.firstElementChild;
    if (b.mode === "carte") {
      tl.fromTo(boite, { autoAlpha: 0, y: -70, rotate: -2 }, { autoAlpha: 1, y: 0, rotate: 0, duration: 0.4, ease: "back.out(1.7)" }, b.d);
      va(boite, { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -50 }, 0.22, b.f - 0.22, "power2.in");
    } else {
      tl.fromTo(boite, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.1, ease: "none" }, b.d);
    }
    tl.fromTo(cadre, { scale: 1.09 }, { scale: 1, duration: b.f - b.d, ease: "none" }, b.d);
    tl.set(boite, { autoAlpha: 0 }, b.f);
  });

  tl.set({}, {}, D.duree); // la timeline dure exactement la vidéo
  if (typeof window.PH_EXTRAS === "function") window.PH_EXTRAS(tl, va); // sur mesure (extras.html)

  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
})();
