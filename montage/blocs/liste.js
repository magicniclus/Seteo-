  // Liste : chaque ligne glisse quand elle est dite, puis son signe se dessine
  D.lignes.forEach(function (ligne, k) {
    montrer(el("l" + k), ligne.t, { x: -50 });
    const trace = el("s" + k);
    if (trace) dessiner(trace, ligne.t + 0.18, 0.4);
  });
