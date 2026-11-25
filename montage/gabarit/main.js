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
  // (la personne détourée, si elle existe, suit exactement les mêmes zooms que la prise)
  const plan = [document.getElementById("plan"), document.getElementById("plan-detoure")].filter(Boolean);
  gsap.set(plan, { transformOrigin: "50% " + D.visageY * 100 + "%" });
  D.zooms.forEach((z, k) => {
    if (k === 0) tl.fromTo(plan, { scale: z.de }, { scale: z.a, duration: z.duree, ease: "none" }, z.t);
    else va(plan, { scale: z.de }, { scale: z.a }, z.duree, z.t, "none");
  });

  // Mise en scène « coin » : la personne détourée en bas, d'un côté puis de l'autre (coupe franche)
  if (D.coin) {
    const p = document.getElementById("personne");
    gsap.set(p, { x: D.coin.cotes[0].x, y: D.coin.y, scale: D.coin.s, transformOrigin: "0 0" });
    D.coin.cotes.forEach((c) =>
      tl.set(p, { x: c.x, y: D.coin.y, scale: D.coin.s, transformOrigin: "0 0", attr: { "data-cote": c.cote } }, c.t));
  }

  // Mots derrière la personne : un mot géant passe entre le décor et elle
  D.derriere.forEach((m) => {
    const mot = document.getElementById(m.id);
    tl.fromTo(mot, { autoAlpha: 0, scale: 0.7, y: 80 }, { autoAlpha: 1, scale: 1, y: 0, duration: 0.5, ease: "back.out(1.4)" }, m.d);
    va(mot, { autoAlpha: 1, scale: 1 }, { autoAlpha: 0, scale: 1.08 }, 0.3, m.f - 0.3, "power2.in");
    tl.set(mot, { autoAlpha: 0 }, m.f);
  });

  // la prise et la personne détourée bougent toujours ensemble
  const personne = document.getElementById("personne");
  const cadres = [document.getElementById("prise"), personne].filter(Boolean);

  // Blocs qui passent derrière la personne : le fond monte derrière elle, elle rétrécit vers le bas
  // pour laisser la place à l'animation, puis reprend sa taille juste avant que le fond reparte.
  // (un bloc met un instant à monter et à repartir ; un plan de coupe « derriere » change d'un coup)
  if (personne) D.devant.forEach((w) => {
    const bloc = w.genre !== "plan";
    va(personne, { scale: 1 }, { scale: w.echelle }, 0.42, w.d + (bloc ? 0.26 : 0.02), "power3.out");
    va(personne, { scale: w.echelle }, { scale: 1 }, 0.34, w.f - (bloc ? 0.72 : 0.36), "power3.inOut");
  });

  // Blocs « en cadre » : la prise rétrécit dans un cadre arrondi en bas de l'écran, l'animation occupe
  // le haut ; puis elle reprend tout l'écran (sauf si le bloc va jusqu'à la dernière image).
  const prise = document.getElementById("prise");
  D.cadres.forEach((w) => {
    const bord = document.getElementById(w.bord);
    const plein = { scale: 1, y: 0, clipPath: "inset(0px 0px 0px 0px round 0px)" };
    const petit = { scale: w.s, y: w.y, clipPath: w.clip };
    tl.set(prise, { zIndex: 4 }, w.d);            // au-dessus du bloc pendant le passage
    va(prise, plein, petit, 0.5, w.d + 0.04, "power3.inOut");
    tl.fromTo(bord, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.18, ease: "none" }, w.d + 0.48);
    if (w.reste) return;
    va(bord, { autoAlpha: 1 }, { autoAlpha: 0 }, 0.1, w.f - 0.72, "none");
    va(prise, petit, plein, 0.4, w.f - 0.64, "power3.inOut");
    tl.set(prise, { zIndex: 1 }, w.f);
    tl.set(bord, { autoAlpha: 0 }, w.f);
  });

  // 2. Plans de coupe
  D.broll.forEach((b) => {
    const boite = document.getElementById(b.id);
    const cadre = boite.firstElementChild;
    if (b.mode === "carte") {
      // (quand la personne passe dans son cadre, la carte attend qu'elle ait libéré le haut de l'écran)
      // une carte qui suit une autre bout à bout la remplace d'un coup (coupe franche), sans animation
      if (b.apres) tl.fromTo(boite, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.01, ease: "none" }, b.d);
      else tl.fromTo(boite, { autoAlpha: 0, y: -70, rotate: -2 }, { autoAlpha: 1, y: 0, rotate: 0, duration: 0.4, ease: "back.out(1.7)" }, b.d + (b.cadre ? 0.22 : 0));
      if (!b.suite) va(boite, { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -50 }, 0.22, b.f - 0.22, "power2.in");
      // la prise descend et rétrécit sous la carte (le visage reste visible), puis reprend sa place
      // (sauf si elle est déjà dans son cadre, en bas : voir les passages « en cadre » plus haut)
      const grand = { scale: 1, borderRadius: 0 }, petit = { scale: D.reduit, borderRadius: 64 };
      if (!b.cadre) {
        va(cadres, grand, petit, 0.4, b.d, "power3.out");
        va(cadres, petit, grand, 0.32, b.f - 0.32, "power3.inOut");
      }
    } else {
      // plein écran ou derrière la personne : apparition nette (deux plans « derriere » s'enchaînent sans trou) ;
      // dès la première image s'il commence avec la vidéo (c'est lui qu'on voit en premier)
      if (b.d < 0.05) {
        gsap.set(boite, { autoAlpha: 1 });
        tl.set(boite, { autoAlpha: 1 }, 0);
      } else tl.fromTo(boite, { autoAlpha: 0 }, { autoAlpha: 1, duration: b.mode === "derriere" || b.apres ? 0.02 : 0.1, ease: "none" }, b.d);
    }
    if (b.zoom !== false) tl.fromTo(cadre, { scale: 1.09 }, { scale: 1, duration: b.f - b.d, ease: "none" }, b.d);
    tl.set(boite, { autoAlpha: 0 }, b.f);
  });

  tl.set({}, {}, D.duree); // la timeline dure exactement la vidéo
  if (typeof window.PH_EXTRAS === "function") window.PH_EXTRAS(tl, va); // sur mesure (extras.html)

  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
})();
