  // Barres : la ligne arrive, la barre pousse jusqu'à sa valeur, le chiffre claque
  D.lignes.forEach(function (ligne, k) {
    montrer(el("b" + k), ligne.t, { y: 24 });
    tl.fromTo(el("p" + k), { scaleX: 0 }, { scaleX: 1, duration: 0.75, ease: DOUX }, ligne.t + 0.1);
    tl.fromTo(el("v" + k), { scale: 0.5 }, { scale: 1, duration: 0.4, ease: "back.out(2.2)" }, ligne.t + 0.45);
  });
