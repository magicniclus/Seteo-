  // Commentaire : la bulle arrive, le mot-clé se tape lettre par lettre, la réponse tombe
  const sortie = D.duree - 0.3;
  tl.fromTo(el("com"), { autoAlpha: 0, scale: 0.75 }, { autoAlpha: 1, scale: 1, duration: 0.22, ease: "back.out(2)" }, 0.15);
  for (let k = 0; k < D.lettres; k++)
    tl.fromTo(el("c" + k), { opacity: 0 }, { opacity: 1, duration: 0.02, ease: "none" }, 0.45 + k * D.frappe);
  tl.fromTo(el("rep"), { autoAlpha: 0, scale: 0.75 }, { autoAlpha: 1, scale: 1, duration: 0.22, ease: "back.out(2)" }, D.reponse);
  va(el("com"), { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -30 }, 0.25, sortie, "power2.in");
  va(el("rep"), { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -30 }, 0.25, sortie, "power2.in");
