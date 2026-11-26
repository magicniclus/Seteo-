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

  // Mise en scène « vitrine » : le carré du haut. À son arrivée, il grandit, ses deux plaques se
  // déplient derrière lui et les coins de viseur se posent. Ensuite il respire à peine (il flotte, les
  // plaques tournent d'un rien, le point de l'onglet clignote). À chaque nouveau plan : fondu court,
  // petit éclair et battement du cadre. Il s'efface avant le carton de fin (sauf s'il va jusqu'au bout).
  if (D.vitrine) {
    const V = D.vitrine, $ = (id) => document.getElementById(id);
    const boite = $("vitrine"), cadre = $("vitrine-cadre"), coins = $("vitrine-coins"), eclair = $("vitrine-eclair");
    const p1 = $("vitrine-plaque-1"), p2 = $("vitrine-plaque-2"), onglet = $("vitrine-onglet"), point = $("vitrine-point");
    const t0 = V.d, debut = t0 < 0.05;   // présent dès la première image : il s'y met en place
    const sortie = V.reste ? D.duree : V.f - 0.35;
    const entre = (cible, de, a, duree, t, ease) =>
      tl.fromTo(cible, de, Object.assign({ duration: duree, ease: ease, immediateRender: debut }, a), t);
    gsap.set(boite, { autoAlpha: debut ? 1 : 0 });
    tl.set(boite, { autoAlpha: 1 }, t0);
    entre(boite, { scale: 0.9, rotate: -3 }, { scale: 1, rotate: 0 }, 0.7, t0, "back.out(1.6)");
    entre(p1, { x: 0, y: 0, rotate: 0 }, { x: -24, y: 22, rotate: -3 }, 0.6, t0 + 0.12, "power3.out");
    entre(p2, { x: 0, y: 0, rotate: 0 }, { x: 24, y: -18, rotate: 2.5 }, 0.6, t0 + 0.2, "power3.out");
    entre(coins, { scale: 1.14, autoAlpha: 0 }, { scale: 1, autoAlpha: 1 }, 0.5, t0 + 0.25, "power2.out");
    if (onglet) entre(onglet, { y: -16 }, { y: 0 }, 0.5, t0 + 0.05, "back.out(2)");
    // la respiration : des allers-retours entiers (il revient au repos avant de partir)
    const calme = t0 + 0.9;
    const respire = (cible, de, a, periode) => {
      let fois = Math.floor((sortie - calme) / periode);
      fois -= fois % 2;
      if (cible && fois >= 2)
        tl.fromTo(cible, de, Object.assign({ duration: periode, ease: "sine.inOut", yoyo: true, repeat: fois - 1, immediateRender: false }, a), calme);
    };
    respire(boite, { y: 0 }, { y: -10 }, 1.8);
    respire(p1, { rotate: -3 }, { rotate: -1.6 }, 2.6);
    respire(p2, { rotate: 2.5 }, { rotate: 3.7 }, 3.1);
    respire(point, { autoAlpha: 1 }, { autoAlpha: 0.25 }, 0.6);
    V.plans.forEach((p, k) => {
      const plan = $(p.id), avant = V.plans[k - 1], apres = V.plans[k + 1];
      if (k === 0) {
        gsap.set(plan, { autoAlpha: debut ? 1 : 0 });
        tl.set(plan, { autoAlpha: 1 }, p.d);
      } else {
        va(plan, { autoAlpha: 0, scale: 1.08 }, { autoAlpha: 1, scale: 1 }, 0.35, p.d, "power2.out");
        va(eclair, { autoAlpha: 0 }, { autoAlpha: 0.3 }, 0.08, p.d, "none");
        va(eclair, { autoAlpha: 0.3 }, { autoAlpha: 0 }, 0.3, p.d + 0.08, "power1.out");
        va(cadre, { scale: 1 }, { scale: 1.025 }, 0.14, p.d, "power2.out");
        va(cadre, { scale: 1.025 }, { scale: 1 }, 0.4, p.d + 0.14, "back.out(2)");
        va(coins, { scale: 1.08 }, { scale: 1 }, 0.45, p.d, "power3.out");
      }
      if (apres || !V.reste) tl.set(plan, { autoAlpha: 0 }, p.cache);
      if (p.legende) {
        const legende = $(p.legende);
        if (!avant || avant.legende !== p.legende)
          va(legende, { autoAlpha: 0, x: -24 }, { autoAlpha: 1, x: 0 }, 0.45, p.d + (k === 0 ? 0.35 : 0.2), "back.out(1.8)");
        if (apres && apres.legende !== p.legende)
          va(legende, { autoAlpha: 1, x: 0 }, { autoAlpha: 0, x: -16 }, 0.2, p.f - 0.2, "power2.in");
      }
    });
    if (!V.reste) {
      va(boite, { scale: 1, rotate: 0, autoAlpha: 1 }, { scale: 0.88, rotate: 2, autoAlpha: 0 }, 0.35, V.f - 0.35, "power2.in");
      tl.set(boite, { autoAlpha: 0 }, V.f);
    }
  }

  // Mise en scène « partage » : le haut de l'écran. À l'arrivée, la barre de titre descend et la carte
  // monte (déjà là à la première image). Un nouveau titre chasse l'ancien vers le haut ; un nouveau plan
  // arrive en fondu avec un petit « tap » de l'écran ; pastille et étiquette changent s'il le faut.
  // Les encarts sautent par-dessus le coin de la carte et leur nombre monte jusqu'à sa valeur.
  // Tout repart juste avant le carton de fin (sauf si ça va jusqu'au bout).
  if (D.partage) {
    const P = D.partage, $ = (id) => document.getElementById(id);
    const titre = $("partage-titre"), carte = $("partage-carte"), ecran = $("partage-ecran");
    const icone = $("partage-icone"), point = $("partage-point");
    const t0 = P.d, debut = t0 < 0.05;
    const sortie = P.reste ? D.duree : P.f - 0.35;
    const entre = (cible, de, a, duree, t, ease) =>
      tl.fromTo(cible, de, Object.assign({ duration: duree, ease: ease, immediateRender: debut }, a), t);
    entre(titre, { y: -26, scale: 0.97 }, { y: 0, scale: 1 }, 0.55, t0, "back.out(1.8)");
    entre(carte, { y: 46, scale: 0.95 }, { y: 0, scale: 1 }, 0.65, t0 + 0.05, "back.out(1.5)");
    entre(icone, { rotate: -14, scale: 0.8 }, { rotate: 0, scale: 1 }, 0.6, t0 + 0.15, "back.out(2.6)");
    // le point de l'en-tête clignote doucement (allers-retours entiers)
    let fois = Math.floor((sortie - t0 - 0.8) / 0.7);
    fois -= fois % 2;
    if (point && fois >= 2)
      tl.fromTo(point, { autoAlpha: 1 }, { autoAlpha: 0.25, duration: 0.7, ease: "sine.inOut", yoyo: true, repeat: fois - 1, immediateRender: false }, t0 + 0.8);

    P.titres.forEach((x, k) => {
      const el = $(x.id);
      if (k === 0) {
        gsap.set(el, { autoAlpha: debut ? 1 : 0 });
        tl.set(el, { autoAlpha: 1 }, x.d);
      } else {
        va(el, { autoAlpha: 0, y: 34 }, { autoAlpha: 1, y: 0 }, 0.38, x.d + 0.08, "back.out(1.7)");
        va(icone, { rotate: -12, scale: 1.18 }, { rotate: 0, scale: 1 }, 0.45, x.d + 0.05, "back.out(2.4)");
      }
      if (k + 1 < P.titres.length) va(el, { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -30 }, 0.22, x.f - 0.06, "power2.in");
    });

    P.plans.forEach((p, k) => {
      const plan = $(p.id), avant = P.plans[k - 1], apres = P.plans[k + 1];
      if (k === 0) {
        gsap.set(plan, { autoAlpha: debut ? 1 : 0 });
        tl.set(plan, { autoAlpha: 1 }, p.d);
      } else {
        va(plan, { autoAlpha: 0, scale: 1.06 }, { autoAlpha: 1, scale: 1 }, 0.32, p.d, "power2.out");
        va(ecran, { scale: 1 }, { scale: 0.975 }, 0.1, p.d, "power2.out");
        va(ecran, { scale: 0.975 }, { scale: 1 }, 0.4, p.d + 0.1, "back.out(2.2)");
      }
      if (apres || !P.reste) tl.set(plan, { autoAlpha: 0 }, p.cache);
      // pastille (en haut à droite) : elle saute ; étiquette (en bas à gauche) : elle glisse
      [["badge", { scale: 0.4 }, { scale: 1 }, "back.out(2.6)", 0.45], ["legende", { x: -30 }, { x: 0 }, "back.out(1.8)", 0.55]]
        .forEach(([cle, de, a, ease, retard]) => {
          if (!p[cle]) return;
          const el = $(p[cle]);
          if (!avant || avant[cle] !== p[cle])
            va(el, Object.assign({ autoAlpha: 0 }, de), Object.assign({ autoAlpha: 1 }, a), 0.42, p.d + (k === 0 ? retard : 0.12), ease);
          if (apres && apres[cle] !== p[cle])
            va(el, Object.assign({ autoAlpha: 1 }, a), Object.assign({ autoAlpha: 0 }, de), 0.18, p.f - 0.16, "power2.in");
        });
    });

    P.encarts.forEach((x) => {
      const el = $(x.id);
      va(el, { autoAlpha: 0, scale: 0.7, rotate: -6, y: 30 }, { autoAlpha: 1, scale: 1, rotate: 0, y: 0 }, 0.5, x.d, "back.out(1.7)");
      if (x.compteur) {
        const valeur = $(x.id + "-valeur"), etat = { v: 0 };
        const ecrire = () => {
          const n = String(Math.round(etat.v)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
          valeur.textContent = x.compteur.avant + n + x.compteur.apres;
        };
        tl.fromTo(etat, { v: 0 }, { v: x.compteur.valeur, duration: 0.8, ease: "power2.out", onUpdate: ecrire, immediateRender: false }, x.d + 0.12);
      }
      if (!x.avec_carte) {
        va(el, { autoAlpha: 1, scale: 1 }, { autoAlpha: 0, scale: 0.85 }, 0.22, x.f - 0.22, "power2.in");
        tl.set(el, { autoAlpha: 0 }, x.f);
      } else if (!P.reste) {
        va(el, { autoAlpha: 1, scale: 1 }, { autoAlpha: 0, scale: 0.85 }, 0.3, P.f - 0.35, "power2.in");
        tl.set(el, { autoAlpha: 0 }, P.f);
      }
    });

    if (!P.reste) {
      va(titre, { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -24 }, 0.3, P.f - 0.35, "power2.in");
      va(carte, { autoAlpha: 1, scale: 1 }, { autoAlpha: 0, scale: 0.94 }, 0.35, P.f - 0.35, "power2.in");
      tl.set([titre, carte], { autoAlpha: 0 }, P.f);
    }
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
    tl.set(boite, { autoAlpha: 0 }, b.cache || b.f);
  });

  tl.set({}, {}, D.duree); // la timeline dure exactement la vidéo
  if (typeof window.PH_EXTRAS === "function") window.PH_EXTRAS(tl, va); // sur mesure (extras.html)

  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
})();
