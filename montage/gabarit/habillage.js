// Habillage (GSAP) : accroche, chiffres, carton de fin, barre de progression.
(function () {
  const D = __DONNEES__;
  const tl = gsap.timeline({ paused: true });
  const REBOND = "back.out(1.7)";
  const va = (cible, de, a, duree, t, ease) =>
    tl.fromTo(cible, de, Object.assign({ duration: duree, ease: ease || "power3.out", immediateRender: false }, a), t);

  // Cartes : l'accroche est là dès la toute première image (c'est elle qui arrête le pouce)
  D.cartes.forEach((c) => {
    const fond = document.getElementById(c.id).firstElementChild;
    if (c.d <= 0.05) tl.fromTo(fond, { autoAlpha: 1, scale: 1.05 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: "power3.out" }, 0);
    else tl.fromTo(fond, { autoAlpha: 0, y: 50, scale: 0.9 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.36, ease: REBOND }, c.d);
    va(fond, { autoAlpha: 1, y: 0, scale: 1 }, { autoAlpha: 0, y: -40, scale: 0.96 }, 0.22, c.f - 0.22, "power2.in");
    tl.set(fond, { autoAlpha: 0 }, c.f);
    if (c.compteur) { // le chiffre « monte » jusqu'à sa valeur
      const valeur = fond.firstElementChild;
      const etat = { v: 0 };
      const ecrire = () => {
        const n = String(Math.round(etat.v)).replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0"); // espace insécable des milliers
        valeur.textContent = c.compteur.avant + n + c.compteur.apres;
      };
      tl.fromTo(etat, { v: 0 }, { v: c.compteur.valeur, duration: 0.7, ease: "power2.out", onUpdate: ecrire }, c.d + 0.1);
    }
  });

  // Carton de fin : il monte, puis la pastille du mot-clé « respire » à intervalle régulier
  if (D.fin) {
    const fond = document.getElementById("fin").firstElementChild;
    const mot = document.getElementById("fin-mot");
    tl.fromTo(fond, { autoAlpha: 0, y: 120, scale: 0.92 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.45, ease: REBOND }, D.fin.d);
    tl.fromTo(mot, { scale: 0.6 }, { scale: 1, duration: 0.5, ease: "back.out(2.4)" }, D.fin.d + 0.18);
    for (let t = D.fin.d + 1.0; t + 0.7 < D.duree; t += 0.9) {
      va(mot, { scale: 1 }, { scale: 1.06 }, 0.3, t, "sine.inOut");
      va(mot, { scale: 1.06 }, { scale: 1 }, 0.3, t + 0.3, "sine.inOut");
    }
  }

  const barre = document.getElementById("barre-plein");
  if (barre) tl.fromTo(barre, { scaleX: 0 }, { scaleX: 1, duration: D.duree, ease: "none" }, 0);

  tl.set({}, {}, D.duree);
  window.__timelines = window.__timelines || {};
  window.__timelines["habillage"] = tl;
})();
