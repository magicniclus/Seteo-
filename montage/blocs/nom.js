  // Bandeau nom : l'étiquette tombe, le nom monte, le trait se tire ; puis tout repart
  const fin = D.duree - 0.45;
  tl.fromTo(el("role"), { yPercent: -110 }, { yPercent: 0, duration: 0.42, ease: "back.out(2)" }, 0.1);
  tl.fromTo(el("nom"), { autoAlpha: 0, y: 34 }, { autoAlpha: 1, y: 0, duration: 0.45, ease: "back.out(1.5)" }, 0.3);
  tl.fromTo(el("trait"), { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power4.out" }, 0.48);
  va(el("trait"), { scaleX: 1 }, { scaleX: 0 }, 0.3, fin, "power2.in");
  va(el("nom"), { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -16 }, 0.3, fin + 0.04, "power2.in");
  va(el("role"), { yPercent: 0 }, { yPercent: -110 }, 0.3, fin + 0.06, "power2.in");
