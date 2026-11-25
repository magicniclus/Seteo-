// Agencement crédible d'une pièce : où poser chaque équipement pour que la maquette ressemble à un
// vrai projet. Tout est posé au millimètre contre un mur, à l'équerre, avec les dégagements d'usage :
//   - salle de bains : douche ou baignoire calée dans un angle, loin de la porte ; 70 cm libres devant
//     la vasque, 60 cm devant les WC et 20 cm de chaque côté ; rien dans le débattement de la porte ;
//   - cuisine : meubles bas bord à bord (plan de travail continu), évier sous la fenêtre,
//     lave-vaisselle contre l'évier, 60 cm de plan entre l'évier et la plaque, hotte au-dessus de la
//     plaque, réfrigérateur en bout de ligne, 90 cm de passage devant, îlot seulement s'il reste
//     1 m de passage de chaque côté ; triangle évier-plaque-réfrigérateur vérifié par l'outil du site ;
//   - chambre : tête de lit contre un mur, chevets de part et d'autre, 60 cm de passage ;
//   - séjour : canapé contre un mur, table basse devant, meuble télé en face.
// Ce qui ne tient pas sans tricher est laissé de côté, avec un avertissement.
//
// Repères : millimètres ; x vers la droite, y vers le bas. `Rect` = faces intérieures des murs.
// Côtés : fond = mur du haut du plan, devant = mur du bas (celui que la caméra regarde par-dessus).

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Tout = any;
export interface Pt { x: number; y: number }
export interface Rect { x0: number; y0: number; x1: number; y1: number }
export type Cote = 'fond' | 'droite' | 'devant' | 'gauche';
/** Ouverture sur un côté de la pièce : intervalle le long du mur, depuis son début (haut ou gauche). */
export interface Baie { cote: Cote; de: number; a: number; porte: boolean; allege: number; /** profondeur à garder libre devant (défaut : la largeur de la porte, son débattement) */ debat?: number }
interface Pose { id: string; cote: Cote | null; rect: Rect; libre: Rect | null; h: number; alt: number; objetId: string }

const COTES: Cote[] = ['fond', 'droite', 'devant', 'gauche'];
const ROTATION: Record<Cote, number> = { fond: 0, droite: 900, devant: 1800, gauche: 2700 };
const touche = (a: Rect, b: Rect, jeu = 0) =>
  a.x0 < b.x1 + jeu - 1 && b.x0 < a.x1 + jeu - 1 && a.y0 < b.y1 + jeu - 1 && b.y0 < a.y1 + jeu - 1;
const dedans = (a: Rect, b: Rect) => a.x0 >= b.x0 - 1 && a.y0 >= b.y0 - 1 && a.x1 <= b.x1 + 1 && a.y1 <= b.y1 + 1;
const centre = (r: Rect): Pt => ({ x: (r.x0 + r.x1) / 2, y: (r.y0 + r.y1) / 2 });
const ecart = (a: Pt, b: Pt) => Math.hypot(a.x - b.x, a.y - b.y);

export class Piece {
  poses: Pose[] = [];
  alertes: string[] = [];
  /** Contour réel de la pièce quand elle n'est pas rectangulaire (pièce en L) : une table peut aller dans l'autre partie. */
  contour: Pt[] | null = null;
  constructor(
    private d: Tout,
    private ctx: { nouvelId: (p: string) => string },
    public niveau: Tout,
    public r: Rect,
    public baies: Baie[],
    /** Côtés du rectangle sans mur (pièce en L) : on n'y adosse rien. */
    public ouverts: Cote[] = [],
  ) {}

  longueur(c: Cote) { return c === 'fond' || c === 'devant' ? this.r.x1 - this.r.x0 : this.r.y1 - this.r.y0; }
  profondeur(c: Cote) { return c === 'fond' || c === 'devant' ? this.r.y1 - this.r.y0 : this.r.x1 - this.r.x0; }

  /** Rectangle au sol d'un objet de largeur l et de profondeur p, posé contre le côté c à l'abscisse s. */
  emprise(c: Cote, s: number, l: number, p: number, recul = 0): Rect {
    const { x0, y0, x1, y1 } = this.r;
    if (c === 'fond') return { x0: x0 + s, y0: y0 + recul, x1: x0 + s + l, y1: y0 + recul + p };
    if (c === 'devant') return { x0: x0 + s, y0: y1 - recul - p, x1: x0 + s + l, y1: y1 - recul };
    if (c === 'gauche') return { x0: x0 + recul, y0: y0 + s, x1: x0 + recul + p, y1: y0 + s + l };
    return { x0: x1 - recul - p, y0: y0 + s, x1: x1 - recul, y1: y0 + s + l };
  }

  /** Zones où une porte s'ouvre : rien ne s'y pose. */
  get debattements(): Rect[] {
    return this.baies.filter((b) => b.porte).map((b) => this.emprise(b.cote, b.de - 50, b.a - b.de + 100, (b.debat ?? b.a - b.de) + 50));
  }
  get portes(): Pt[] {
    return this.baies.filter((b) => b.porte).map((b) => centre(this.emprise(b.cote, b.de, b.a - b.de, 10)));
  }
  /** Une fenêtre du côté c recouvre-t-elle l'intervalle [s, s + l] ? Renvoie sa hauteur d'allège, sinon rien. */
  fenetreSur(c: Cote, s: number, l: number): number | null {
    const f = this.baies.find((b) => !b.porte && b.cote === c && b.de < s + l - 30 && b.a > s + 30);
    return f ? f.allege : null;
  }
  porteSur(c: Cote, s: number, l: number): boolean {
    return this.baies.some((b) => b.porte && b.cote === c && b.de < s + l && b.a > s);
  }
  mur(c: Cote): string | undefined {
    const { x0, y0, x1, y1 } = this.r;
    const m = this.niveau.murs.find((w: Tout) => {
      const horizontal = Math.abs(w.a.y - w.b.y) < 5;
      const demi = w.epaisseur / 2 + 30;
      if (c === 'fond' || c === 'devant') {
        const y = c === 'fond' ? y0 : y1;
        return horizontal && Math.abs(w.a.y - y) <= demi && Math.min(w.a.x, w.b.x) < x1 && Math.max(w.a.x, w.b.x) > x0;
      }
      const x = c === 'gauche' ? x0 : x1;
      return !horizontal && Math.abs(w.a.x - x) <= demi && Math.min(w.a.y, w.b.y) < y1 && Math.max(w.a.y, w.b.y) > y0;
    });
    return m?.id;
  }

  /**
   * Un emplacement est-il possible ? L'objet reste dans la pièce, hors des débattements de porte,
   * à `jeu` mm au moins des objets déjà posés, pas devant une fenêtre s'il est trop haut, et la
   * zone `libre` devant lui (dégagement) ne contient aucun objet. Il ne mord pas non plus sur le
   * dégagement des objets déjà là.
   */
  possible(c: Cote, s: number, l: number, p: number, o: { libre?: number; jeu?: number; h?: number; alt?: number; sur?: string[]; flottant?: boolean } = {}): boolean {
    const rect = this.emprise(c, s, l, p);
    if ((this.ouverts.includes(c) && !o.flottant) || !dedans(rect, this.r)) return false;
    if (this.debattements.some((z) => touche(rect, z))) return false;
    if (this.porteSur(c, s, l)) return false;
    const [alt, h] = [o.alt ?? 0, o.h ?? 900];
    const allege = this.fenetreSur(c, s, l);
    if (allege !== null && alt + h > allege + 50 && alt < 2100) return false;
    for (const q of this.poses) {
      const superposes = alt >= q.alt + q.h || q.alt >= alt + h;     // l'un au-dessus de l'autre (hotte, meuble haut)
      if (superposes || o.sur?.includes(q.id)) continue;
      if (touche(rect, q.rect, o.jeu ?? 0)) return false;
      // un objet mince au mur (sèche-serviettes) ne gêne pas le passage devant son voisin
      if (q.libre && p > 150 && touche(rect, q.libre)) return false;
    }
    if (o.libre) {
      const zone = this.emprise(c, s, l, o.libre, p);
      if (!dedans(zone, this.r)) return false;
      if (this.poses.some((q) => q.alt < 900 && touche(zone, q.rect))) return false;
    }
    return true;
  }

  /** Pose l'objet du catalogue contre le côté c, à l'abscisse s, dos au mur. */
  poser(id: string, c: Cote, s: number, o: { libre?: number } = {}): Pose | null {
    const cat = this.d.objetDuCatalogue(id);
    if (!cat) throw new Error(`Objet inconnu du catalogue : ${id}`);
    const { l, p, h } = cat.dimensions;
    const rect = this.emprise(c, s, l, p);
    const objetId = this.ctx.nouvelId('obj');
    const apercu = this.d.objetAPoser(this.niveau, id, centre(rect), { aimant: false, id: objetId });
    if (!apercu) return null;
    const mur = this.mur(c);
    const objet = { ...apercu.objet, rotation: ROTATION[c], ...(mur && cat.contreMur ? { accrocheMurId: mur } : {}) };
    this.niveau = { ...this.niveau, objets: [...this.niveau.objets, objet] };
    const pose: Pose = { id, cote: c, rect, libre: o.libre ? this.emprise(c, s, l, o.libre, p) : null, h: h || 2000, alt: cat.altitude ?? 0, objetId };
    this.poses.push(pose);
    return pose;
  }

  /** Pose un objet libre (table, îlot) : son rectangle au sol, tourné d'un quart si `quart`. */
  poserLibre(id: string, rect: Rect, quart = false): Pose | null {
    const cat = this.d.objetDuCatalogue(id);
    if (!cat) throw new Error(`Objet inconnu du catalogue : ${id}`);
    const objetId = this.ctx.nouvelId('obj');
    const apercu = this.d.objetAPoser(this.niveau, id, centre(rect), { aimant: false, id: objetId });
    if (!apercu) return null;
    this.niveau = { ...this.niveau, objets: [...this.niveau.objets, { ...apercu.objet, rotation: quart ? 900 : 0 }] };
    const pose: Pose = { id, cote: null, rect, libre: null, h: cat.dimensions.h || 900, alt: cat.altitude ?? 0, objetId };
    this.poses.push(pose);
    return pose;
  }
  tourner(pose: Pose, rotation: number) {
    this.niveau = { ...this.niveau, objets: this.niveau.objets.map((x: Tout) => (x.id === pose.objetId ? { ...x, rotation } : x)) };
  }

  /**
   * Cherche le meilleur emplacement le long des murs : tous les 5 cm, on garde celui qui respecte
   * les règles (`possible`) et obtient la meilleure note. `marge` : distance minimale aux murs
   * perpendiculaires (20 cm de chaque côté d'un WC).
   */
  placer(
    id: string,
    regles: { libre?: number; jeu?: number; marge?: number; cotes?: Cote[]; flottant?: boolean; note: (c: Cote, s: number, rect: Rect) => number },
  ): Pose | null {
    const cat = this.d.objetDuCatalogue(id);
    if (!cat) throw new Error(`Objet inconnu du catalogue : ${id}`);
    const { l, p, h } = cat.dimensions;
    let meilleur: { c: Cote; s: number; note: number } | null = null;
    for (const c of regles.cotes ?? COTES) {
      const fin = this.longueur(c) - l - (regles.marge ?? 0);
      const pas: number[] = [];
      for (let s = regles.marge ?? 0; s <= fin + 0.5; s += 50) pas.push(s);
      if (fin >= (regles.marge ?? 0)) pas.push(fin);
      for (const s of pas) {
        if (!this.possible(c, s, l, p, { libre: regles.libre, jeu: regles.jeu, h: h || 2000, alt: cat.altitude ?? 0, flottant: regles.flottant })) continue;
        const note = regles.note(c, s, this.emprise(c, s, l, p));
        if (!meilleur || note > meilleur.note) meilleur = { c, s, note };
      }
    }
    if (!meilleur) {
      this.alertes.push(`« ${id} » ne tient pas dans la pièce en respectant les dégagements : laissé de côté.`);
      return null;
    }
    return this.poser(id, meilleur.c, meilleur.s, { libre: regles.libre });
  }

  /** Le rectangle est-il tout entier dans la pièce (son contour réel s'il est connu) ? */
  contient(rect: Rect): boolean {
    if (!this.contour) return dedans(rect, this.r);
    return [[rect.x0, rect.y0], [rect.x1, rect.y0], [rect.x0, rect.y1], [rect.x1, rect.y1]]
      .every(([x, y]) => this.d.pointDansPolygone({ x: Math.min(Math.max(x!, -1e9), 1e9), y: y! }, this.contour) || this.surLeBord({ x: x!, y: y! }));
  }
  private surLeBord(p: Pt): boolean {
    const c = this.contour!;
    return c.some((a, i) => {
      const b = c[(i + 1) % c.length]!;
      const dans = (v: number, u: number, w: number) => v >= Math.min(u, w) - 1 && v <= Math.max(u, w) + 1;
      return (Math.abs(a.x - b.x) < 1 && Math.abs(p.x - a.x) < 1 && dans(p.y, a.y, b.y)) || (Math.abs(a.y - b.y) < 1 && Math.abs(p.y - a.y) < 1 && dans(p.x, a.x, b.x));
    });
  }
  /** Longueur d'une emprise le long du côté c, et son abscisse de départ. */
  le_long(c: Cote, rect: Rect): number { return c === 'fond' || c === 'devant' ? rect.x1 - rect.x0 : rect.y1 - rect.y0; }
  abscisse(c: Cote, rect: Rect): number { return c === 'fond' || c === 'devant' ? rect.x0 - this.r.x0 : rect.y0 - this.r.y0; }
  loinDeLaPorte(rect: Rect): number {
    const portes = this.portes;
    return portes.length ? Math.min(...portes.map((p) => ecart(p, centre(rect)))) : 0;
  }
  dansUnAngle(c: Cote, s: number, l: number): boolean { return s < 1 || s > this.longueur(c) - l - 1; }
  /** Le côté d'en face. */
  enFace(c: Cote): Cote { return COTES[(COTES.indexOf(c) + 2) % 4]!; }
}

const EAU = ['douche-italienne', 'douche-grande', 'douche-angle', 'douche-niche', 'douche-cabine', 'baignoire', 'baignoire-180', 'baignoire-angle', 'baignoire-douche', 'baignoire-ilot'];
const estEau = (id: string) => EAU.includes(id);
const estVasque = (id: string) => id.includes('vasque');
const estWc = (id: string) => id.startsWith('wc');

/** Salle de bains, salle d'eau, WC : l'ordre de pose suit l'encombrement (le plus gros d'abord). */
export function agencerBain(piece: Piece, equipements: string[]): void {
  const ordre = [...equipements].sort((a, b) => rang(a) - rang(b));
  let eau: Pose | null = null;
  for (const id of ordre) {
    if (estEau(id)) {
      // Dans un angle, le plus loin possible de la porte ; de préférence au fond.
      const pose = piece.placer(id, {
        libre: 600,
        note: (c, s, rect) =>
          (piece.dansUnAngle(c, s, piece.le_long(c, rect)) ? 5000 : 0) + piece.loinDeLaPorte(rect) + (c === 'fond' ? 300 : 0),
      });
      eau ??= pose;
    } else if (estVasque(id)) {
      // 70 cm libres devant ; de préférence sur le même mur que la douche, à 10 cm d'elle, sinon au fond.
      piece.placer(id, {
        libre: 700,
        jeu: 100,
        note: (c, s, rect) =>
          (eau && eau.cote === c ? 1500 - Math.min(1500, distanceBords(rect, eau.rect)) : 0) +
          (c === 'fond' ? 600 : 0) +
          piece.loinDeLaPorte(rect) / 4,
      });
    } else if (estWc(id)) {
      // 20 cm de chaque côté, 60 cm devant ; plutôt sur un mur de côté, jamais nez à nez avec la porte.
      piece.placer(id, {
        libre: 600,
        jeu: 200,
        marge: 200,
        note: (c, s, rect) => {
          const face = piece.baies.some((b) => b.porte && b.cote === piece.enFace(c) && b.de < s + 380 && b.a > s);
          return (c === 'gauche' || c === 'droite' ? 800 : 0) - (face ? 1500 : 0) + piece.loinDeLaPorte(rect) / 3;
        },
      });
    } else if (id === 'seche-serviettes') {
      // À portée de main en sortant de la douche ou du bain.
      piece.placer(id, {
        jeu: 50,
        note: (_c, _s, rect) => (eau ? 3000 - ecart(centre(rect), centre(eau.rect)) : piece.loinDeLaPorte(rect)),
      });
    } else {
      // Lave-linge, meuble : contre un mur, de préférence dans un angle.
      piece.placer(id, { libre: 600, note: (c, s, rect) => (piece.dansUnAngle(c, s, piece.le_long(c, rect)) ? 500 : 0) + piece.loinDeLaPorte(rect) / 4 });
    }
  }
}
const rang = (id: string) => (estEau(id) ? 0 : estVasque(id) ? 1 : estWc(id) ? 2 : id === 'seche-serviettes' ? 9 : 5);
function distanceBords(a: Rect, b: Rect): number {
  const dx = Math.max(0, Math.max(a.x0, b.x0) - Math.min(a.x1, b.x1));
  const dy = Math.max(0, Math.max(a.y0, b.y0) - Math.min(a.y1, b.y1));
  return Math.hypot(dx, dy);
}

/**
 * Cuisine en ligne le long d'un mur : réfrigérateur en bout, plan de travail, évier, lave-vaisselle
 * contre l'évier, 60 cm de plan au moins, plaque et hotte, un dernier meuble au bout. Les meubles bas
 * sont bord à bord. `fenetre` : largeur d'une fenêtre à réserver au-dessus de l'évier (aucun meuble
 * haut n'y va). Renvoie l'abscisse du centre de l'évier, ou rien si la ligne ne tient pas.
 * L'îlot ne se pose que s'il reste 1 m de passage côté cuisine et 90 cm de l'autre côté.
 */
export function agencerCuisine(
  piece: Piece,
  equipements: string[],
  d: Tout,
  o: { cote?: Cote; fenetre?: number; essai?: boolean } = {},
): { evier: number | null } {
  const dims = (id: string) => d.objetDuCatalogue(id)?.dimensions ?? { l: 600, p: 600, h: 870 };
  const role = (id: string) => d.objetDuCatalogue(id)?.cuisine as string | undefined;
  const demandes = [...equipements];
  const prendre = (test: (id: string) => boolean): string | null => {
    const i = demandes.findIndex(test);
    return i < 0 ? null : demandes.splice(i, 1)[0]!;
  };
  const frigo = prendre((id) => role(id) === 'frigo');
  const evier = prendre((id) => role(id) === 'evier') ?? 'evier-120';
  const plaque = prendre((id) => role(id) === 'plaque') ?? 'plaque-60';
  const laveVaisselle = prendre((id) => id === 'lave-vaisselle');
  const hotte = prendre((id) => id.startsWith('hotte') && id !== 'hotte-ilot');
  const four = prendre((id) => id === 'four');
  const ilot = prendre((id) => id.startsWith('ilot'));
  const hauts = demandes.filter((id) => role(id) === 'haut');
  const bas = demandes.filter((id) => role(id) === 'bas' && d.objetDuCatalogue(id)?.contreMur);
  const autres = demandes.filter((id) => !hauts.includes(id) && !bas.includes(id));

  // La ligne, dans l'ordre. Entre l'évier et la plaque : le lave-vaisselle puis un meuble de 60
  // (ou le four, encastré sous le plan), soit 60 cm de plan de travail au moins.
  const c: Cote = o.cote ?? 'fond';
  const ligne: string[] = [];
  if (frigo) ligne.push(frigo);
  ligne.push(bas.shift() ?? 'meuble-bas-60', evier);
  if (laveVaisselle) ligne.push(laveVaisselle);
  ligne.push(four ?? bas.shift() ?? 'meuble-bas-60', plaque, bas.shift() ?? 'meuble-bas-40');
  const total = () => ligne.reduce((t, id) => t + dims(id).l, 0);
  const longueurMur = piece.longueur(c);
  const dire = (m: string) => { if (!o.essai) piece.alertes.push(m); };
  // Trop long pour le mur : on retire d'abord le meuble du bout, puis celui d'avant l'évier.
  const fixes = [evier, plaque, frigo, laveVaisselle, four];
  while (total() > longueurMur) {
    const bout = ligne.length - 1;
    const i = !fixes.includes(ligne[bout]!) ? bout : ligne.indexOf(evier) - 1;
    if (i < 0 || fixes.includes(ligne[i]!)) break;
    dire(`Cuisine : « ${ligne[i]} » retiré, le mur (${(longueurMur / 1000).toFixed(2)} m) est trop court pour toute la ligne.`);
    ligne.splice(i, 1);
  }
  if (total() > longueurMur) {
    dire(`Cuisine : la ligne (${(total() / 1000).toFixed(2)} m) ne tient pas sur ${(longueurMur / 1000).toFixed(2)} m de mur. Agrandis la pièce ou retire un élément.`);
    return { evier: null };
  }
  // Les meubles bas restants complètent la ligne tant qu'il y a la place.
  while (bas.length && total() + dims(bas[0]!).l <= longueurMur) ligne.push(bas.shift()!);
  // Pas de plan de travail à côté de la plaque ou de l'évier : on en glisse un à la mesure de la
  // place qui reste (80, 60, 40 ou 30 cm), d'abord au bout de la ligne, puis entre le
  // réfrigérateur et l'évier.
  const plan = (id: string | undefined) => !!id && role(id) === 'bas' && id !== 'lave-vaisselle' && id !== four;
  for (const ou of ['bout', 'debut'] as const) {
    const manque = ou === 'bout' ? !plan(ligne.at(-1)) : !plan(ligne[ligne.indexOf(evier) - 1]);
    const taille = [800, 600, 400, 300].find((l) => total() + l <= longueurMur);
    if (!manque || !taille) continue;
    if (ou === 'bout') ligne.push(`meuble-bas-${taille / 10}`);
    else ligne.splice(ligne.indexOf(evier), 0, `meuble-bas-${taille / 10}`);
  }
  // Essai à blanc : chaque élément tient-il (porte, débattement, fenêtre devant un meuble trop haut) ?
  let s = 0;
  for (const id of ligne) {
    const cat = dims(id);
    if (!piece.possible(c, s, cat.l, cat.p, { libre: 900, h: cat.h, sur: ligne })) {
      dire(`Cuisine : « ${id} » ne tient pas à sa place sur ce mur (porte, fenêtre ou passage de 90 cm).`);
      return { evier: null };
    }
    s += cat.l;
  }
  if (o.essai) return { evier: 1 };
  s = 0;
  let centreEvier: number | null = null;
  let posePlaque: Pose | null = null;
  const posesBas: Pose[] = [];
  for (const id of ligne) {
    const pose = piece.poser(id, c, s, { libre: 900 });
    if (pose && role(id) !== 'frigo') posesBas.push(pose);
    if (id === evier && centreEvier === null) centreEvier = s + dims(id).l / 2;
    if (id === plaque && !posePlaque) posePlaque = pose;
    s += dims(id).l;
  }
  if (o.fenetre && centreEvier !== null)
    piece.baies.push({ cote: c, de: centreEvier - o.fenetre / 2, a: centreEvier + o.fenetre / 2, porte: false, allege: 950 });
  // Hotte centrée au-dessus de la plaque ; meubles hauts au-dessus des meubles bas, hors hotte et hors fenêtre.
  if (posePlaque) {
    const h = hotte ?? 'hotte-60';
    const lh = dims(h).l;
    const milieu = piece.abscisse(c, posePlaque.rect) + piece.le_long(c, posePlaque.rect) / 2;
    piece.poser(h, c, Math.min(Math.max(0, milieu - lh / 2), longueurMur - lh));
  }
  for (const id of hauts) {
    const cat = d.objetDuCatalogue(id);
    const place = posesBas.find((q) => q.id !== evier && q.id !== plaque
      && piece.possible(c, piece.abscisse(c, q.rect), cat.dimensions.l, cat.dimensions.p, { h: cat.dimensions.h, alt: cat.altitude ?? 1450 }));
    if (place) piece.poser(id, c, piece.abscisse(c, place.rect));
    else dire(`Cuisine : pas de place pour « ${id} » au-dessus du plan de travail.`);
  }
  // Îlot : parallèle à la ligne, 1 m de passage côté cuisine, 90 cm de l'autre côté et aux deux bouts.
  if (ilot) {
    const { l, p } = dims(ilot);
    const y0 = piece.r.y0 + 600 + 1000;
    const largeur = piece.r.x1 - piece.r.x0;
    const rect = { x0: piece.r.x0 + (largeur - l) / 2, y0, x1: piece.r.x0 + (largeur + l) / 2, y1: y0 + p };
    const tient = c === 'fond' && largeur >= l + 1800 && rect.y1 + 900 <= piece.r.y1 && !piece.debattements.some((z) => touche(rect, z, 200));
    if (tient) piece.poserLibre(ilot, rect);
    else dire(`Cuisine : pas d'îlot, la pièce est trop petite pour garder le passage (il faut ${((l + 1800) / 1000).toFixed(1)} × ${((600 + 1000 + p + 900) / 1000).toFixed(1)} m au moins pour « ${ilot} »).`);
  }
  for (const id of autres) piece.placer(id, { libre: 600, note: (_c, _s, rect) => piece.loinDeLaPorte(rect) });
  const triangle = d.triangleActivite(piece.niveau);
  if (triangle && triangle.conseil !== 'bon')
    dire(`Cuisine : triangle évier-plaque-réfrigérateur ${triangle.conseil === 'trop_petit' ? 'trop serré' : 'trop grand'} (${(triangle.perimetre / 1000).toFixed(1)} m ; conseillé : 3,6 à 7,9 m).`);
  return { evier: centreEvier };
}

/** Chambre : lit tête au mur (pas sous la fenêtre, pas sur le mur de la porte), chevets, armoire. */
export function agencerChambre(piece: Piece, equipements: string[], d: Tout): void {
  const reste = [...equipements];
  const lit = reste.find((id) => id.startsWith('lit-')) ?? 'lit-160';
  const chevets = reste.filter((id) => id === 'chevet').length;
  const l = d.objetDuCatalogue(lit).dimensions.l;
  // 60 cm de passage de chaque côté (les chevets s'y logent), 70 cm au pied.
  const pose = piece.placer(lit, {
    libre: 700,
    marge: 600,
    note: (c, s, rect) => {
      const milieu = (piece.longueur(c) - l) / 2;
      const sousFenetre = piece.fenetreSur(c, s, l) !== null;
      const murDePorte = piece.baies.some((b) => b.porte && b.cote === c);
      return 2000 - Math.abs(s - milieu) - (sousFenetre ? 1500 : 0) - (murDePorte ? 2500 : 0) + piece.loinDeLaPorte(rect) / 5;
    },
  });
  if (pose?.cote) {
    const s = pose.cote === 'fond' || pose.cote === 'devant' ? pose.rect.x0 - piece.r.x0 : pose.rect.y0 - piece.r.y0;
    const lc = d.objetDuCatalogue('chevet').dimensions;
    const places = [s - lc.l, s + l].slice(0, chevets);
    for (const sc of places) if (piece.possible(pose.cote, sc, lc.l, lc.p, { h: lc.h })) piece.poser('chevet', pose.cote, sc);
  }
  for (const id of reste.filter((x) => x !== lit && x !== 'chevet'))
    piece.placer(id, { libre: 700, note: (c, s, rect) => (piece.dansUnAngle(c, s, piece.le_long(c, rect)) ? 400 : 0) - piece.loinDeLaPorte(rect) / 6 + (pose && c === piece.enFace(pose.cote!) ? 600 : 0) });
}

/** Séjour : canapé contre le plus long mur libre, table basse à 40 cm devant, meuble télé en face, table à manger à l'écart. */
export function agencerSejour(piece: Piece, equipements: string[], d: Tout): void {
  const reste = [...equipements];
  const tirer = (test: (id: string) => boolean) => {
    const i = reste.findIndex(test);
    return i < 0 ? null : reste.splice(i, 1)[0]!;
  };
  const canape = tirer((id) => id.startsWith('canape'));
  const basse = tirer((id) => id.startsWith('table-basse'));
  const tele = tirer((id) => id === 'meuble-tv');
  const table = tirer((id) => id.startsWith('table-') && !id.startsWith('table-basse'));
  const chaises = reste.filter((id) => id === 'chaise').length;
  let sofa: Pose | null = null;
  if (canape) {
    const lc = d.objetDuCatalogue(canape).dimensions.l;
    sofa = piece.placer(canape, {
      libre: 1000,
      marge: 100,
      flottant: true,       // dans une pièce en L, le canapé peut tourner le dos à l'autre partie
      note: (c, s, rect) => piece.longueur(c) / 4 - Math.abs(s - (piece.longueur(c) * 0.3 - lc / 2)) / 2 + piece.loinDeLaPorte(rect) / 6 - (piece.fenetreSur(c, s, lc) !== null ? 300 : 0),
    });
  }
  if (sofa?.cote && basse) {
    const b = d.objetDuCatalogue(basse).dimensions;
    const cs = centre(sofa.rect);
    const horizontal = sofa.cote === 'fond' || sofa.cote === 'devant';
    const sens = sofa.cote === 'fond' || sofa.cote === 'gauche' ? 1 : -1;
    const avance = (horizontal ? sofa.rect.y1 - sofa.rect.y0 : sofa.rect.x1 - sofa.rect.x0) / 2 + 400 + b.p / 2;
    const c = horizontal ? { x: cs.x, y: cs.y + sens * avance } : { x: cs.x + sens * avance, y: cs.y };
    const rect = horizontal ? { x0: c.x - b.l / 2, y0: c.y - b.p / 2, x1: c.x + b.l / 2, y1: c.y + b.p / 2 } : { x0: c.x - b.p / 2, y0: c.y - b.l / 2, x1: c.x + b.p / 2, y1: c.y + b.l / 2 };
    if (dedans(rect, piece.r) && !piece.poses.some((q) => touche(rect, q.rect))) piece.poserLibre(basse, rect, !horizontal);
  }
  if (tele) {
    const lt = d.objetDuCatalogue(tele).dimensions.l;
    const face = sofa?.cote ? piece.enFace(sofa.cote) : null;
    const axe = sofa ? (sofa.cote === 'fond' || sofa.cote === 'devant' ? centre(sofa.rect).x - piece.r.x0 : centre(sofa.rect).y - piece.r.y0) : 0;
    piece.placer(tele, {
      note: (c, s) => (face && c === face ? 3000 - Math.abs(s + lt / 2 - axe) : 0),
    });
  }
  // Table à manger : celle demandée, sinon une plus petite si elle ne tient pas.
  for (const essai of table ? [table, 'table-4', 'table-ronde'].filter((x, i, a) => a.indexOf(x) === i) : []) {
    if (tableAManger(piece, essai, sofa, chaises, d)) {
      if (essai !== table) piece.alertes.push(`Séjour : « ${table} » ne tient pas avec le passage autour, remplacée par « ${essai} ».`);
      break;
    }
    if (essai === 'table-ronde') piece.alertes.push(`Séjour : pas la place pour une table à manger avec le passage autour.`);
  }
  for (const id of reste.filter((x) => x !== 'chaise'))
    piece.placer(id, { note: (c, s, rect) => (piece.dansUnAngle(c, s, piece.le_long(c, rect)) ? 500 : 0) + piece.loinDeLaPorte(rect) / 8 });
}

/** Une table et ses chaises, le plus loin possible du canapé, 70 cm libres autour, 80 cm des murs. */
function tableAManger(piece: Piece, table: string, sofa: Pose | null, chaises: number, d: Tout): boolean {
  {
    const t = d.objetDuCatalogue(table).dimensions;
    let meilleur: { rect: Rect; note: number } | null = null;
    // 70 cm autour de la table pour tirer une chaise et passer ; 80 cm des murs. Dans une pièce en L,
    // la table peut aller dans l'autre partie que celle du canapé.
    const cadre = piece.contour
      ? { x0: Math.min(...piece.contour.map((p) => p.x)), y0: Math.min(...piece.contour.map((p) => p.y)), x1: Math.max(...piece.contour.map((p) => p.x)), y1: Math.max(...piece.contour.map((p) => p.y)) }
      : piece.r;
    for (let x = cadre.x0 + 800; x + t.l + 800 <= cadre.x1; x += 100)
      for (let y = cadre.y0 + 800; y + t.p + 800 <= cadre.y1; y += 100) {
        const rect = { x0: x, y0: y, x1: x + t.l, y1: y + t.p };
        const zone = { x0: x - 700, y0: y - 700, x1: x + t.l + 700, y1: y + t.p + 700 };
        if (!piece.contient({ x0: x - 800, y0: y - 800, x1: x + t.l + 800, y1: y + t.p + 800 })) continue;
        if (piece.poses.some((q) => touche(zone, q.rect)) || piece.debattements.some((z) => touche(zone, z))) continue;
        const note = sofa ? ecart(centre(rect), centre(sofa.rect)) : 0;
        if (!meilleur || note > meilleur.note) meilleur = { rect, note };
      }
    if (meilleur) {
      piece.poserLibre(table, meilleur.rect);
      // Les chaises, dossier vers l'extérieur, réparties sur les deux longs côtés.
      const ch = d.objetDuCatalogue('chaise').dimensions;
      const n = Math.min(chaises || 4, table === 'table-6' ? 6 : 4);
      const parCote = Math.ceil(n / 2);
      const r = meilleur.rect;
      for (let i = 0; i < n; i++) {
        const haut = i < parCote;
        const k = (haut ? i : i - parCote) + 0.5;
        const cx = r.x0 + ((r.x1 - r.x0) * k) / parCote;
        const cy = haut ? r.y0 - ch.p / 2 + 150 : r.y1 + ch.p / 2 - 150;
        const pose = piece.poserLibre('chaise', { x0: cx - ch.l / 2, y0: cy - ch.p / 2, x1: cx + ch.l / 2, y1: cy + ch.p / 2 });
        if (pose && !haut) piece.tourner(pose, 1800);
      }
      return true;
    }
    return false;
  }
}

/** Équipement courant d'une pièce quand la fiche n'en donne pas. */
export const PAR_DEFAUT: Record<string, string[]> = {
  salle_de_bain: ['baignoire', 'vasque', 'seche-serviettes'],
  salle_d_eau: ['douche-italienne', 'vasque', 'seche-serviettes'],
  wc: ['wc-suspendu'],
  cuisine: ['refrigerateur', 'meuble-bas-60', 'evier-120', 'lave-vaisselle', 'meuble-bas-60', 'plaque-60', 'hotte-60', 'meuble-bas-40'],
  chambre: ['lit-160', 'chevet', 'chevet', 'armoire'],
  sejour: ['canape-3', 'table-basse', 'meuble-tv', 'table-6', 'chaise', 'chaise', 'chaise', 'chaise'],
  bureau: ['bureau', 'bibliotheque'],
};

/** Aiguille vers la bonne règle d'après le type de pièce. Renvoie l'abscisse de l'évier (cuisine) ou rien. */
export function agencer(piece: Piece, type: string, equipements: string[] | undefined, d: Tout): { evier: number | null } {
  const liste = equipements ?? PAR_DEFAUT[type] ?? [];
  if (type === 'cuisine') {
    // Le mur le plus long qui accueille la ligne entière ; sinon sans lave-vaisselle ; sinon l'essentiel.
    const listes = [liste, liste.filter((id) => id !== 'lave-vaisselle'), ['refrigerateur', 'evier-120', 'plaque-60', 'hotte-60']];
    const cotes = (['fond', 'droite', 'gauche', 'devant'] as Cote[]).sort((a, b) => piece.longueur(b) - piece.longueur(a));
    for (const l of listes)
      for (const c of cotes)
        if (agencerCuisine(piece, l, d, { cote: c, essai: true }).evier !== null) {
          if (l !== liste) piece.alertes.push(`Cuisine : la pièce est petite, ligne réduite (${l.join(', ')}).`);
          return agencerCuisine(piece, l, d, { cote: c });
        }
    piece.alertes.push('Cuisine : aucun mur ne peut recevoir une ligne de cuisine (porte, fenêtre basse ou pièce trop petite).');
    return { evier: null };
  }
  if (type === 'salle_de_bain' || type === 'salle_d_eau' || type === 'wc' || type === 'buanderie') agencerBain(piece, liste);
  else if (type === 'chambre') agencerChambre(piece, liste, d);
  else if (type === 'sejour') agencerSejour(piece, liste, d);
  else for (const id of liste) piece.placer(id, { libre: 600, note: (c, s, rect) => (piece.dansUnAngle(c, s, piece.le_long(c, rect)) ? 500 : 0) + piece.loinDeLaPorte(rect) / 5 });
  return { evier: null };
}
