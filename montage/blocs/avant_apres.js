  // Avant / après : un trait traverse l'image et découvre la photo d'après
  montrer(el("cadre"), 0.4, { y: 40 });
  const largeur = D.largeur;
  tl.fromTo(el("apres"), { clipPath: "inset(0% 100% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: D.balayage, ease: "sine.inOut" }, D.bascule);
  tl.fromTo(el("trait"), { autoAlpha: 1, x: 0 }, { autoAlpha: 1, x: largeur, duration: D.balayage, ease: "sine.inOut" }, D.bascule);
  tl.set(el("trait"), { autoAlpha: 0 }, D.bascule + D.balayage);
  tl.fromTo(el("etq"), { autoAlpha: 0, scale: 0.6 }, { autoAlpha: 1, scale: 1, duration: 0.35, ease: "back.out(2.2)" }, D.bascule + D.balayage * 0.45);
