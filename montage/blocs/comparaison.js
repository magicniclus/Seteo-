  // Comparaison : les deux cartes s'ouvrent comme un livre, puis le verdict tombe
  tl.fromTo(el("g"), { autoAlpha: 0, x: -140, rotateY: 28 }, { autoAlpha: 1, x: 0, rotateY: 0, duration: 0.55, ease: DOUX }, 0.5);
  tl.fromTo(el("d"), { autoAlpha: 0, x: 140, rotateY: -28 }, { autoAlpha: 1, x: 0, rotateY: 0, duration: 0.55, ease: DOUX }, 0.64);
  if (D.gagnant) {
    const gagnant = el(D.gagnant), perdant = el(D.gagnant === "g" ? "d" : "g");
    va(perdant, { autoAlpha: 1, scale: 1 }, { autoAlpha: 0.45, scale: 0.94 }, 0.35, D.verdict);
    va(gagnant, { scale: 1 }, { scale: 1.05 }, 0.4, D.verdict, "back.out(2.4)");
    tl.fromTo(el("cadre"), { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.25, ease: "none" }, D.verdict);
    if (el("badge")) tl.fromTo(el("badge"), { autoAlpha: 0, y: 18, scale: 0.6 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.4, ease: "back.out(2.4)" }, D.verdict + 0.12);
  }
