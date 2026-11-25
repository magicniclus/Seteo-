  // Demande : la fiche se pose, puis ses champs arrivent un par un
  montrer(el("fiche"), 0.42, { y: 50 });
  D.champs.forEach(function (champ, k) {
    montrer(el("ch" + k), champ.t, { x: 40 });
  });
