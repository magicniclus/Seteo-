// Sous-titres (GSAP) : chaque mot arrive quand il est dit ; le mot en cours passe sur la pastille.
(function () {
  const D = __DONNEES__;
  const tl = gsap.timeline({ paused: true });
  const va = (cible, de, a, duree, t, ease) =>
    tl.fromTo(cible, de, Object.assign({ duration: duree, ease: ease || "power3.out", immediateRender: false }, a), t);
  // Les deux états d'un mot : au repos (blanc cerné) et en cours (sur la pastille)
  const OMBRE = "0px 6px 22px rgba(0, 0, 0, 0.45)";
  const repos = { backgroundColor: D.accentVide, color: D.blanc, webkitTextStrokeColor: D.contour, textShadow: OMBRE };
  // sur une pastille claire, le texte foncé se lit sans contour ni ombre
  const enCours = { backgroundColor: D.accent, color: D.surAccent, webkitTextStrokeColor: D.contourActif,
                    textShadow: D.ombreActive ? OMBRE : "0px 0px 0px rgba(0, 0, 0, 0)" };
  const dit = (fort) => Object.assign({}, repos, fort ? { color: D.accentClair } : {});

  D.pages.forEach((p) => {
    const page = document.getElementById(p.id);
    tl.fromTo(page, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.02, ease: "none" }, p.d);
    tl.fromTo(page.firstElementChild, { scale: 0.9 }, { scale: 1, duration: 0.16, ease: "back.out(2.2)" }, p.d);
    p.mots.forEach((m, j) => {
      const mot = document.getElementById(p.id + "-" + j);
      const suivant = p.mots[j + 1];
      if (D.apparition === "mot_a_mot" && j > 0)
        tl.fromTo(mot, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.1, ease: "power3.out" }, Math.max(m.d - 0.03, p.d));
      if (D.motEnCours === "pastille") {
        va(mot, repos, enCours, 0.07, m.d);
        // une fois dit, le mot quitte la pastille ; un mot fort (chiffre, mot-clé) reste coloré
        if (suivant) va(mot, enCours, dit(m.fort), 0.09, suivant.d);
      } else {
        // (en bandeau, les mots au repos sont gris clair : seul le mot dit ressort)
        const calme = D.repos || D.blanc;
        va(mot, { color: calme }, { color: D.accent }, 0.07, m.d);
        if (suivant && !m.fort) va(mot, { color: D.accent }, { color: calme }, 0.09, suivant.d);
      }
      if (m.fort) va(mot, { scale: 1.22 }, { scale: 1 }, 0.3, m.d, "back.out(2.5)");
    });
    tl.set(page, { autoAlpha: 0 }, p.f); // l'écran disparaît net, quoi qu'il arrive
  });

  tl.set({}, {}, D.duree);
  window.__timelines = window.__timelines || {};
  window.__timelines["sous-titres"] = tl;
})();
