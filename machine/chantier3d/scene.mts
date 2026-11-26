// Construit la maquette d'un chantier avec le code de l'outil Dessin du site (paquet `core`).
// Lancé par machine/chantier3d.py avec le `tsx` du site :
//   SITE_PORTAIL=<dossier du site> <site>/node_modules/.bin/tsx machine/chantier3d/scene.mts <fiche.json>
// Écrit sur la sortie standard : { scene, reperes } — la scène au format de l'éditeur, et les
// repères utiles à la caméra (centre et taille de la maison, de chaque pièce).
//
// Tout est en mètres dans la fiche, en millimètres dans la scène. L'axe x va vers la droite du
// plan, l'axe y vers le bas : la façade « de devant » (celle que la caméra voit) est en bas du plan.
import { readFileSync } from 'node:fs';
import { agencer, agencerCuisine, PAR_DEFAUT, Piece, type Baie, type Cote, type Rect } from './agencement.mts';

const site = process.env.SITE_PORTAIL;
if (!site) throw new Error('SITE_PORTAIL manque (dossier du site).');
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const d: any = await import(`${site}/packages/core/src/dessin/index.ts`);

type Pt = { x: number; y: number };
type Paire = [number, number];
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Tout = any;

// --catalogue : ce qu'on peut écrire dans une fiche (objets, ouvertures, pièces, toits, piscines, modèles)
if (process.argv[2] === '--catalogue') {
  const parCategorie: Record<string, string[]> = {};
  for (const o of d.CATALOGUE_OBJETS) (parCategorie[o.categorie] ??= []).push(`${o.id} (${o.dimensions.l / 10}×${o.dimensions.p / 10} cm)`);
  process.stdout.write(
    JSON.stringify({
      modeles: d.MODELES.map((m: Tout) => `${m.id} : ${m.detail}`),
      pieces: Object.keys(d.LIBELLES_PIECE),
      ouvertures: Object.keys(d.CATALOGUE_OUVERTURES),
      toits: Object.keys(d.LIBELLES_TOITURE),
      piscines: Object.keys(d.LIBELLES_FORME_PISCINE),
      objets: parCategorie,
    }),
  );
  process.exit(0);
}

const fiche = JSON.parse(readFileSync(process.argv[2]!, 'utf8'));
let compteur = 0;
const ctx = { nouvelId: (p: string) => `${p}_${String(++compteur).padStart(6, '0')}` };
const mm = (v: number) => Math.round(v * 1000);
const P = ([x, y]: Paire): Pt => ({ x: mm(x), y: mm(y) });
const etape = <T,>(r: { ok: boolean; data?: T; message?: string; code?: string }, quoi: string): T => {
  if (!r.ok) throw new Error(`${quoi} : ${r.message ?? r.code}`);
  return r.data as T;
};
/** Essaie une pose facultative : si l'outil la refuse (pas la place), on garde le niveau tel quel. */
const tenter = (n: Tout, f: () => { ok: boolean; data?: Tout }): Tout => {
  try {
    const r = f();
    return r.ok ? r.data : n;
  } catch {
    return n;
  }
};

const SOLS: Record<string, [string, string, string]> = {
  sejour: ['parquet', 'pa-chene-clair', 'decalee'],
  chambre: ['parquet', 'pa-chene-naturel', 'decalee'],
  bureau: ['parquet', 'pa-noyer', 'decalee'],
  couloir: ['parquet', 'pa-chene-clair', 'decalee'],
  entree: ['parquet', 'pa-chene-clair', 'decalee'],
  dressing: ['parquet', 'pa-chene-naturel', 'decalee'],
  cuisine: ['carrelage', 'ca-gris-60', 'droite'],
  salle_de_bain: ['carrelage', 'ca-gris-60', 'droite'],
  salle_d_eau: ['carrelage', 'ca-gris-60', 'droite'],
  wc: ['carrelage', 'ca-gris-60', 'droite'],
  buanderie: ['carrelage', 'ca-gris-60', 'droite'],
};
const PIECES_D_EAU = new Set(['salle_de_bain', 'salle_d_eau']);

const boite = (pts: Pt[]) => {
  const xs = pts.map((p) => p.x);
  const ys = pts.map((p) => p.y);
  return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
};
const longueur = (m: Tout) => Math.hypot(m.b.x - m.a.x, m.b.y - m.a.y);
const milieu = (m: Tout): Pt => ({ x: (m.a.x + m.b.x) / 2, y: (m.a.y + m.b.y) / 2 });
const revetement = ([famille, materiauId, pose]: [string, string, string]) => ({ famille, materiauId, pose });

/** Sol de chaque pièce d'après son type, faïence dans les pièces d'eau. */
function revetir(n: Tout): Tout {
  for (const piece of n.pieces) {
    const sol = SOLS[piece.type];
    if (sol)
      n = tenter(n, () =>
        d.appliquerRevetement(n, { genre: 'piece', pieceId: piece.id, surface: 'sol' }, revetement(sol)),
      );
    if (PIECES_D_EAU.has(piece.type))
      n = tenter(n, () =>
        d.revetirMursDeLaPiece(n, piece.id, { famille: 'faience', materiauId: 'fa-metro', pose: 'droite' }),
      );
  }
  return n;
}

/** Ouverture posée sur le mur le plus proche du point. */
function ouvrir(n: Tout, point: Pt, type: string): Tout {
  const cible = d.murSousLePoint(n.murs, point, 400);
  if (!cible) return n;
  return tenter(n, () => d.poserOuverture(n, { murId: cible.mur.id, type, centre: cible.distanceDepuisA }, ctx));
}

/** Meuble posé près du point (l'outil le cale contre le mur), retiré s'il chevauche un voisin. */
function meubler(n: Tout, id: string, point: Pt, tour?: number): Tout {
  if (!d.objetDuCatalogue(id)) throw new Error(`Objet inconnu du catalogue : ${id}`);
  let suite = tenter(n, () => d.poserObjet(n, { catalogueId: id, position: point }, ctx));
  if (suite === n) return n;
  const pose = suite.objets.at(-1);
  if (tour) suite = tenter(suite, () => d.tournerObjet(suite, pose.id, tour));
  // la hotte se pose exprès au-dessus de la plaque : seuls les autres chevauchements comptent
  const gene = id.startsWith('hotte')
    ? false
    : d.collisions(suite).some((c: Tout) => JSON.stringify(c).includes(pose.id));
  return gene ? n : suite;
}

/** Le contour d'une pièce sans ses points alignés (un mur droit = une seule arête). */
function sommets(contour: Pt[]): Pt[] {
  return contour.filter((p, i) => {
    const a = contour[(i - 1 + contour.length) % contour.length]!;
    const b = contour[(i + 1) % contour.length]!;
    return Math.abs((p.x - a.x) * (b.y - p.y) - (p.y - a.y) * (b.x - p.x)) > 1;
  });
}

/** Chaque arête de chaque pièce, rapportée au mur qui la porte : intervalle [t0, t1] depuis l'extrémité a du mur. */
function aretesSurMurs(n: Tout): { piece: Tout; mur: Tout; t0: number; t1: number }[] {
  const res: { piece: Tout; mur: Tout; t0: number; t1: number }[] = [];
  for (const piece of n.pieces) {
    const c = sommets(piece.contour);
    c.forEach((p, i) => {
      const q = c[(i + 1) % c.length]!;
      const horizontal = Math.abs(p.y - q.y) < 5;
      if (!horizontal && Math.abs(p.x - q.x) >= 5) return;
      for (const m of n.murs) {
        if (Math.abs(m.a.y - m.b.y) < 5 !== horizontal) continue;
        const demi = m.epaisseur / 2 + 10;
        if (horizontal ? Math.abs(m.a.y - p.y) > demi : Math.abs(m.a.x - p.x) > demi) continue;
        const t = (pt: Pt) => (horizontal ? (pt.x - m.a.x) * Math.sign(m.b.x - m.a.x) : (pt.y - m.a.y) * Math.sign(m.b.y - m.a.y));
        const [t0, t1] = [Math.max(0, Math.min(t(p), t(q))), Math.min(longueur(m), Math.max(t(p), t(q)))];
        if (t1 - t0 > 300) res.push({ piece, mur: m, t0, t1 });
      }
    });
  }
  return res;
}

const VIE = ['sejour', 'entree', 'couloir'];
const FENETRES: Record<string, string> = {
  sejour: 'fenetre_double', cuisine: 'fenetre_double', chambre: 'fenetre_double', bureau: 'fenetre_double',
  salle_de_bain: 'fenetre', salle_d_eau: 'fenetre', buanderie: 'fenetre', dressing: 'fenetre',
};

/**
 * Portes et fenêtres d'un niveau, pièce par pièce, comme dans une vraie maison :
 *  - chaque pièce a UNE porte, qui donne sur la pièce de vie (séjour, entrée, couloir), dans un
 *    angle (15 cm du mur) pour laisser le reste du mur aux meubles ; jamais de chambre en enfilade
 *    si on peut l'éviter ; la cuisine s'ouvre sur le séjour par un passage libre ;
 *  - une fenêtre par pièce, centrée sur son plus long mur extérieur ; pas de fenêtre dans un WC ;
 *  - au rez-de-chaussée, la porte d'entrée dans l'angle de la façade de devant et une baie vitrée
 *    sur le séjour.
 */
function ouverturesAuto(n: Tout, rdc = true): Tout {
  const aretes = aretesSurMurs(n);
  const exterieur = boite(n.murs.filter((m: Tout) => m.type === 'mur').flatMap((m: Tout) => [m.a, m.b]));
  const poser = (mur: Tout, type: string, centre: number) => {
    n = tenter(n, () => d.poserOuverture(n, { murId: mur.id, type, centre }, ctx));
  };
  const largeur = (type: string) => d.CATALOGUE_OUVERTURES[type].largeur as number;
  // Portes intérieures
  for (const piece of n.pieces) {
    if (VIE.includes(piece.type)) continue;
    let choix: { mur: Tout; u0: number; u1: number; rang: number } | null = null;
    for (const a of aretes.filter((x) => x.piece === piece && x.mur.type === 'cloison'))
      for (const b of aretes.filter((x) => x.mur === a.mur && x.piece !== piece)) {
        const [u0, u1] = [Math.max(a.t0, b.t0), Math.min(a.t1, b.t1)];
        if (u1 - u0 < 950) continue;
        const rang = VIE.includes(b.piece.type) ? 3 : b.piece.type === 'cuisine' ? 2 : b.piece.type === 'chambre' ? 0 : 1;
        if (!choix || rang > choix.rang || (rang === choix.rang && u1 - u0 > choix.u1 - choix.u0)) choix = { mur: a.mur, u0, u1, rang };
      }
    if (!choix) {
      console.error(`Pas de mur commun où mettre la porte de la pièce « ${piece.type} » : elle reste sans porte.`);
      continue;
    }
    if (choix.rang === 0) console.error(`La pièce « ${piece.type} » n'est accessible que par une chambre : revois les cloisons.`);
    const type = piece.type === 'cuisine' ? 'ouverture_libre' : 'porte';
    const l = largeur(type);
    poser(choix.mur, type, choix.u1 - choix.u0 >= l + 300 ? choix.u0 + 150 + l / 2 : (choix.u0 + choix.u1) / 2);
  }
  // Fenêtres, porte d'entrée, baie vitrée
  let entree = !rdc;
  const ordre = [...n.pieces].sort((a: Tout, b: Tout) => VIE.indexOf(b.type) - VIE.indexOf(a.type));
  for (const piece of ordre) {
    const dehors = aretes.filter((x) => x.piece === piece && x.mur.type === 'mur').sort((a, b) => b.t1 - b.t0 - (a.t1 - a.t0));
    const devant = dehors.find((x) => Math.abs(x.mur.a.y - x.mur.b.y) < 5 && Math.abs(x.mur.a.y - exterieur.y1) < 150);
    let fenetres = 0;
    if (devant && VIE.includes(piece.type) && !entree) {
      // La porte d'entrée dans l'angle, la baie vitrée centrée sur ce qui reste de façade.
      const lp = largeur('porte_entree');
      poser(devant.mur, 'porte_entree', devant.t0 + 400 + lp / 2);
      entree = true;
      const [r0, r1] = [devant.t0 + 400 + lp + 600, devant.t1 - 400];
      if (piece.type === 'sejour' && r1 - r0 >= largeur('baie_coulissante')) {
        poser(devant.mur, 'baie_coulissante', (r0 + r1) / 2);
        fenetres++;
      }
    }
    const type = FENETRES[piece.type];
    if (!type) continue;
    for (const a of dehors) {
      if (a === devant && VIE.includes(piece.type)) continue;
      if (fenetres >= (piece.type === 'sejour' ? 3 : 1)) break;
      const l = a.t1 - a.t0;
      const choix = l >= largeur(type) + 800 ? type : l >= largeur('fenetre') + 500 ? 'fenetre' : null;
      if (!choix) continue;
      poser(a.mur, choix, (a.t0 + a.t1) / 2);
      fenetres++;
    }
  }
  return n;
}

/** Le plus grand rectangle qui tient dans une pièce (elle-même si elle est rectangulaire). */
function plusGrandRectangle(contour: Pt[]): Rect {
  const tri = (v: number[]) => [...new Set(v)].sort((a, b) => a - b);
  const [xs, ys] = [tri(contour.map((p) => p.x)), tri(contour.map((p) => p.y))];
  const plein = (i: number, j: number) => d.pointDansPolygone({ x: (xs[i]! + xs[i + 1]!) / 2, y: (ys[j]! + ys[j + 1]!) / 2 }, contour);
  let meilleur: Rect | null = null;
  let aire = 0;
  for (let i0 = 0; i0 < xs.length - 1; i0++)
    for (let i1 = i0 + 1; i1 < xs.length; i1++)
      for (let j0 = 0; j0 < ys.length - 1; j0++)
        for (let j1 = j0 + 1; j1 < ys.length; j1++) {
          let tout = true;
          for (let i = i0; i < i1 && tout; i++) for (let j = j0; j < j1 && tout; j++) tout = plein(i, j);
          const a = (xs[i1]! - xs[i0]!) * (ys[j1]! - ys[j0]!);
          if (tout && a > aire) [meilleur, aire] = [{ x0: xs[i0]!, y0: ys[j0]!, x1: xs[i1]!, y1: ys[j1]! }, a];
        }
  const b = boite(contour);
  return meilleur ?? { x0: b.x0, y0: b.y0, x1: b.x1, y1: b.y1 };
}

/** Les côtés du rectangle qui ne longent pas un mur de la pièce sur presque toute leur longueur (pièce en L). */
function cotesOuverts(contour: Pt[], r: Rect): Cote[] {
  const c = sommets(contour);
  const couvert = (horizontal: boolean, fixe: number, de: number, a: number) => {
    let total = 0;
    c.forEach((p, i) => {
      const q = c[(i + 1) % c.length]!;
      if (horizontal ? Math.abs(p.y - fixe) > 5 || Math.abs(q.y - fixe) > 5 : Math.abs(p.x - fixe) > 5 || Math.abs(q.x - fixe) > 5) return;
      const [u, v] = horizontal ? [Math.min(p.x, q.x), Math.max(p.x, q.x)] : [Math.min(p.y, q.y), Math.max(p.y, q.y)];
      total += Math.max(0, Math.min(v, a) - Math.max(u, de));
    });
    return total / (a - de);
  };
  const ouverts: Cote[] = [];
  if (couvert(true, r.y0, r.x0, r.x1) < 0.95) ouverts.push('fond');
  if (couvert(true, r.y1, r.x0, r.x1) < 0.95) ouverts.push('devant');
  if (couvert(false, r.x0, r.y0, r.y1) < 0.95) ouverts.push('gauche');
  if (couvert(false, r.x1, r.y0, r.y1) < 0.95) ouverts.push('droite');
  return ouverts;
}

/** Les ouvertures d'un niveau qui donnent sur une pièce rectangulaire : sur quel côté, de où à où. */
function baiesDe(n: Tout, r: Rect): Baie[] {
  const baies: Baie[] = [];
  for (const o of n.ouvertures) {
    const m = n.murs.find((w: Tout) => w.id === o.murId);
    if (!m) continue;
    const l = longueur(m);
    const [ux, uy] = [(m.b.x - m.a.x) / l, (m.b.y - m.a.y) / l];
    const a = { x: m.a.x + ux * o.position, y: m.a.y + uy * o.position };
    const b = { x: a.x + ux * o.largeur, y: a.y + uy * o.largeur };
    const demi = m.epaisseur / 2 + 40;
    const cat = d.CATALOGUE_OUVERTURES[o.type] ?? { allege: 0 };
    const porte = (cat.allege ?? 0) < 300;
    const sur = (cote: Cote, de: number, jusqua: number, longueurCote: number) => {
      const [x, y] = [Math.max(0, Math.min(de, jusqua)), Math.min(longueurCote, Math.max(de, jusqua))];
      // une baie ou une porte coulissante ne débat pas : 60 cm de passage suffisent devant
      const glisse = /coulissante|galandage|ouverture_libre|arche/.test(o.type);
      if (y - x > 100) baies.push({ cote, de: x, a: y, porte, allege: cat.allege ?? 0, ...(glisse ? { debat: 600 } : {}) });
    };
    if (Math.abs(uy) < 0.01) {
      if (Math.abs(a.y - r.y0) <= demi) sur('fond', a.x - r.x0, b.x - r.x0, r.x1 - r.x0);
      else if (Math.abs(a.y - r.y1) <= demi) sur('devant', a.x - r.x0, b.x - r.x0, r.x1 - r.x0);
    } else if (Math.abs(ux) < 0.01) {
      if (Math.abs(a.x - r.x0) <= demi) sur('gauche', a.y - r.y0, b.y - r.y0, r.y1 - r.y0);
      else if (Math.abs(a.x - r.x1) <= demi) sur('droite', a.y - r.y0, b.y - r.y0, r.y1 - r.y0);
    }
  }
  return baies;
}

const dire = (alertes: string[]) => alertes.forEach((a) => console.error(a));

/**
 * Meubles de chaque pièce, posés selon les règles d'agencement (agencement.mts). Une maison sans
 * pièce « cuisine » reçoit une cuisine ouverte dans le séjour, sur le premier mur où elle tient.
 * "equipements" dans la fiche d'une maison : l'équipement voulu par type de pièce
 * ({"cuisine": [..., "ilot"]}), à la place de l'équipement courant ; il vaut aussi pour la cuisine
 * ouverte du séjour.
 */
function meublesAuto(n: Tout): Tout {
  const voulus: Record<string, string[]> = fiche.equipements ?? {};
  const sansCuisine = !n.pieces.some((p: Tout) => p.type === 'cuisine');
  for (const piece of [...n.pieces]) {
    if (!PAR_DEFAUT[piece.type]) continue;
    const r = plusGrandRectangle(piece.contour);
    const p = new Piece(d, ctx, n, r, baiesDe(n, r), cotesOuverts(piece.contour, r));
    if (sommets(piece.contour).length > 4) p.contour = piece.contour;
    if (piece.type === 'sejour' && sansCuisine && n.type !== 'etage') {
      // Cuisine ouverte : la ligne complète si elle tient sur un mur, sinon une ligne courte.
      const courte = ['refrigerateur', 'evier-120', 'meuble-bas-60', 'plaque-60', 'hotte-60'];
      let faite = false;
      for (const liste of [voulus.cuisine ?? PAR_DEFAUT.cuisine!, courte]) {
        const cote = (['fond', 'droite', 'gauche', 'devant'] as Cote[]).find(
          (c) => agencerCuisine(p, liste, d, { cote: c, essai: true }).evier !== null,
        );
        if (!cote) continue;
        agencerCuisine(p, liste, d, { cote });
        faite = true;
        break;
      }
      if (!faite) p.alertes.push('Aucun mur du séjour ne peut recevoir une cuisine : la maison est sans cuisine. Écris le plan à la main ("plan") ou prends un modèle avec cuisine.');
    }
    agencer(p, piece.type, voulus[piece.type], d);
    n = p.niveau;
    dire(p.alertes);
  }
  return n;
}

/** Aménagement écrit à la main dans la fiche (cloisons, pièces, ouvertures, objets), en mètres. */
function amenager(n: Tout, plan: Tout): Tout {
  for (const [a, b] of plan.cloisons ?? [])
    n = etape(d.ajouterMur(n, { a: P(a), b: P(b), type: 'cloison' }, ctx), 'cloison');
  for (const [point, type] of plan.pieces ?? []) {
    const piece = n.pieces.find((x: Tout) => d.pointDansPolygone(P(point), x.contour));
    if (!piece) throw new Error(`Aucune pièce sous le point ${point} (${type}).`);
    n = etape(d.typerPiece(n, piece.id, type), `pièce ${type}`);
  }
  n = revetir(n);
  // Seulement les cloisons et les pièces : portes, fenêtres et meubles posés d'office, selon les règles.
  // "ouvertures_en_plus" : des ouvertures ajoutées à celles d'office (une deuxième baie...), avant les
  // meubles, qui en tiennent compte.
  if (!plan.ouvertures && !plan.objets) {
    n = ouverturesAuto(n);
    for (const [point, type] of plan.ouvertures_en_plus ?? []) {
      const avant = n;
      n = ouvrir(n, P(point), type);
      if (n === avant) console.error(`  ⚠ « ${type} » refusée en ${point} : pas de mur là, ou la place est prise (porte, fenêtre, angle).`);
    }
    return meublesAuto(n);
  }
  for (const [point, type] of plan.ouvertures ?? []) n = ouvrir(n, P(point), type);
  for (const [id, point, tour] of plan.objets ?? []) n = meubler(n, id, P(point), tour);
  return n;
}

/** Murs extérieurs d'une forme (rectangle ou L), avec la pièce détectée. */
function coque(base: Tout, forme: Tout): Tout {
  const murs = etape<Tout[]>(
    d.mursDepuisForme(forme, { epaisseur: 200, hauteur: base.hauteurSousPlafond, nouvelId: ctx.nouvelId }),
    'murs',
  );
  return { ...base, murs, pieces: d.synchroniserPieces([], d.detecterPieces(murs), () => ctx.nouvelId('p')) };
}

/** Terrasse, piscine, allée, arbres, clôture : placés d'office autour de la maison, ou aux points donnés. */
/** Les ouvertures d'un type posées sur la façade de devant : centre x et largeur, en mm. */
function surFacade(n: Tout, types: string[], yFacade: number): { x: number; l: number }[] {
  return n.ouvertures
    .filter((o: Tout) => types.includes(o.type))
    .map((o: Tout) => {
      const m = n.murs.find((w: Tout) => w.id === o.murId);
      if (!m || Math.abs(m.a.y - m.b.y) > 5 || Math.abs(m.a.y - yFacade) > 150) return null;
      const sens = Math.sign(m.b.x - m.a.x);
      return { x: m.a.x + sens * (o.position + o.largeur / 2), l: o.largeur };
    })
    .filter(Boolean);
}

/**
 * L'extérieur, placé comme dans une vraie parcelle : l'allée mène à la porte d'entrée, la terrasse
 * est devant la baie vitrée (ou la porte-fenêtre) du séjour, la piscine au-delà de la terrasse, du
 * côté opposé à l'entrée. `true` place d'office ; des points ([[x, y], [x, y]], en mètres) placent à la main.
 */
function exterieur(n: Tout, e: Tout, marge: number): Tout {
  const b = boite(n.murs.flatMap((m: Tout) => [m.a, m.b]));
  const l = b.x1 - b.x0;
  const facade = b.y1 + 100;                       // nu extérieur de la façade de devant
  const porte = surFacade(n, ['porte_entree'], b.y1)[0];
  const baie = surFacade(n, ['baie_coulissante', 'porte_fenetre'], b.y1)[0];
  // Allée : 1,20 m de large, de la porte d'entrée jusqu'au bord de la parcelle.
  const xp = porte?.x ?? b.x0 + l * 0.2;
  const allee = e.allee === true ? [{ x: xp - 600, y: facade }, { x: xp + 600, y: b.y1 + marge }] : e.allee ? [P(e.allee[0]), P(e.allee[1])] : null;
  if (allee) n = tenter(n, () => d.ajouterAllee(n, allee[0], allee[1]));
  // Terrasse : devant la baie, 1 m de plus de chaque côté, 3,50 m de profondeur ; jamais sur l'allée.
  let terrasse: { x0: number; x1: number; y1: number } | null = null;
  if (e.terrasse) {
    let [a, c] =
      e.terrasse === true
        ? [{ x: (baie?.x ?? b.x0 + l * 0.65) - (baie?.l ?? 2400) / 2 - 1000, y: facade }, { x: (baie?.x ?? b.x0 + l * 0.65) + (baie?.l ?? 2400) / 2 + 1000, y: facade + 3500 }]
        : [P(e.terrasse[0]), P(e.terrasse[1])];
    if (allee && e.terrasse === true) {
      const [g, dr] = [Math.min(allee[0].x, allee[1].x), Math.max(allee[0].x, allee[1].x)];
      if (a.x < dr + 300 && c.x > g - 300) {
        if ((baie?.x ?? 0) > xp) a = { ...a, x: Math.max(a.x, dr + 300) };
        else c = { ...c, x: Math.min(c.x, g - 300) };
      }
    }
    a = { ...a, x: Math.max(a.x, b.x0 - marge + 500) };
    c = { ...c, x: Math.min(c.x, b.x1 + marge - 500) };
    const avant = n.exterieur.terrasses.length;
    n = tenter(n, () => d.ajouterTerrasse(n, a, c, ctx, { aimant: false }));
    if (n.exterieur.terrasses.length > avant) terrasse = { x0: Math.min(a.x, c.x), x1: Math.max(a.x, c.x), y1: Math.max(a.y, c.y) };
  }
  if (e.piscine) {
    const forme = e.piscine === true ? 'rectangle' : typeof e.piscine === 'string' ? e.piscine : e.piscine[1] ?? 'rectangle';
    let point: Pt;
    if (Array.isArray(e.piscine)) point = P(e.piscine[0]);
    else {
      // Au-delà de la terrasse (2 m de plage), centrée sur elle ; sinon du côté opposé à l'entrée.
      const taille = { rectangle: [8000, 4000], ronde: [4000, 4000], ovale: [7000, 3500], haricot: [7000, 3500], L: [8000, 5000], couloir: [15000, 2500], hors_sol: [5000, 3000] }[forme as 'rectangle'] ?? [8000, 4000];
      const devant = (terrasse?.y1 ?? facade + 1500) + 2000 + taille[1]! / 2;
      const cx = terrasse ? (terrasse.x0 + terrasse.x1) / 2 : xp < b.x0 + l / 2 ? b.x1 - taille[0]! / 2 : b.x0 + taille[0]! / 2;
      point = devant + taille[1]! / 2 <= b.y1 + marge - 800
        ? { x: Math.min(Math.max(cx, b.x0 - marge + taille[0]! / 2 + 800), b.x1 + marge - taille[0]! / 2 - 800), y: devant }
        : { x: xp < b.x0 + l / 2 ? b.x1 + 2000 + taille[0]! / 2 : b.x0 - 2000 - taille[0]! / 2, y: b.y1 - taille[1]! / 2 };
      if (!Array.isArray(e.piscine) && point.y === devant && allee) {
        const [g, dr] = [Math.min(allee[0].x, allee[1].x), Math.max(allee[0].x, allee[1].x)];
        if (point.x - taille[0]! / 2 < dr + 800 && point.x + taille[0]! / 2 > g - 800)
          point = { ...point, x: xp < (b.x0 + b.x1) / 2 ? dr + 800 + taille[0]! / 2 : g - 800 - taille[0]! / 2 };
      }
    }
    const avant = n.exterieur.piscines.length;
    n = tenter(n, () => d.ajouterPiscine(n, point, forme, ctx));
    if (n.exterieur.piscines.length === avant) console.error('La piscine ne tient pas sur la parcelle à cet endroit : agrandis "parcelle" ou donne sa place.');
  }
  // Les arbres restent derrière et à droite : devant à gauche, ils cacheraient la maison à la caméra.
  const coins: Pt[] = [
    { x: b.x0 - marge * 0.55, y: b.y0 - marge * 0.5 },
    { x: b.x1 + marge * 0.55, y: b.y0 - marge * 0.5 },
    { x: b.x0 + l * 0.5, y: b.y0 - marge * 0.6 },
    { x: b.x1 + marge * 0.7, y: b.y0 + (b.y1 - b.y0) * 0.35 },
  ];
  const arbres: Pt[] = Array.isArray(e.arbres) ? e.arbres.map(P) : coins.slice(0, Number(e.arbres ?? 0));
  for (const a of arbres) n = tenter(n, () => d.ajouterVegetal(n, a, 'arbre', ctx, { aimant: false }));
  if (e.cloture) {
    const type = e.cloture === true ? 'grillage' : e.cloture;
    const m = marge - 100;
    const ouverture = allee ? [allee[0].x - 200, allee[1].x + 200] : [b.x0, b.x0];
    const tour: Pt[] = [
      { x: ouverture[1]!, y: b.y1 + m },
      { x: b.x1 + m, y: b.y1 + m },
      { x: b.x1 + m, y: b.y0 - m },
      { x: b.x0 - m, y: b.y0 - m },
      { x: b.x0 - m, y: b.y1 + m },
      { x: ouverture[0]!, y: b.y1 + m },
    ];
    let id: string | undefined;
    for (let i = 1; i < tour.length; i++) {
      const r = d.tracerCloture(n, { ...(id ? { id } : {}), a: tour[i - 1], b: tour[i], type }, ctx);
      if (!r.ok) break;
      const { elementId, ...suite } = r.data;
      id = elementId;
      n = suite;
    }
  }
  return n;
}

// ----- La scène
let scene: Tout;
const ext = fiche.exterieur ?? {};
// Parcelle : 6 m autour de la maison ; 10,5 m avec une piscine (terrasse, 2 m de plage, bassin devant).
const marge = mm(ext.parcelle ?? (ext.piscine ? 10.5 : 6));

if (fiche.piece) {
  // Une pièce seule, posée comme une maquette : pour montrer une salle de bains, une cuisine...
  const p = fiche.piece;
  const s = d.nouvelleScene(ctx.nouvelId);
  // largeur et profondeur sont celles de la pièce, de mur à mur : les murs (20 cm) s'ajoutent autour
  const [L, H] = [mm(p.largeur) + 400, mm(p.profondeur) + 400];
  let n = coque(s.niveaux[0], { forme: 'rectangle', largeur: L, profondeur: H });
  n = etape(d.typerPiece(n, n.pieces[0].id, p.type), 'pièce');
  n = revetir(n);
  const r: Rect = { x0: 200, y0: 200, x1: L - 200, y1: H - 200 };
  // La porte : sur le mur de devant, à 15 cm de l'angle gauche (à droite si "porte_a_droite").
  const typePorte = typeof p.porte === 'string' ? p.porte : 'porte';
  const lp = d.CATALOGUE_OUVERTURES[typePorte].largeur;
  const sp = p.porte_a_droite ? r.x1 - r.x0 - 150 - lp : 150;
  n = ouvrir(n, { x: r.x0 + sp + lp / 2, y: H - 100 }, typePorte);
  const piece = new Piece(d, ctx, n, r, [{ cote: 'devant', de: sp, a: sp + lp, porte: true, allege: 0 }]);
  const typeFenetre = p.fenetre === false ? null : typeof p.fenetre === 'string' ? p.fenetre : 'fenetre';
  const lf = typeFenetre ? d.CATALOGUE_OUVERTURES[typeFenetre].largeur : 0;
  const voulus: Tout[] = p.equipements ?? PAR_DEFAUT[p.type] ?? [];
  const auto: string[] = voulus.filter((e: Tout) => !Array.isArray(e));
  const { evier } = p.type === 'cuisine' ? agencerCuisine(piece, auto, d, { fenetre: lf || undefined }) : agencer(piece, p.type, auto, d);
  n = piece.niveau;
  // Un équipement donné avec son point ([id, [x, y]]) va où la fiche le dit, tel quel.
  for (const [id, point, tour] of voulus.filter((e: Tout) => Array.isArray(e))) n = meubler(n, id, P(point), tour);
  if (typeFenetre) {
    // Cuisine : au-dessus de l'évier. Ailleurs : au fond, sinon sur un côté, là où rien de haut
    // (douche, colonne, armoire) n'est devant, et de préférence sur un pan de mur nu.
    let place: { cote: Cote; s: number } | null = evier !== null ? { cote: 'fond', s: evier - lf / 2 } : null;
    for (const nu of [true, false]) {
      if (place) break;
      for (const cote of ['fond', 'droite', 'gauche'] as Cote[]) {
        const long = piece.longueur(cote);
        const essais = [0.5, 0.35, 0.65, 0.25, 0.75].map((k) => long * k - lf / 2).filter((x) => x >= 200 && x + lf <= long - 200);
        const libre = essais.find((x) => !piece.poses.some((q) => q.cote === cote
          && piece.abscisse(cote, q.rect) < x + lf + 100 && piece.abscisse(cote, q.rect) + piece.le_long(cote, q.rect) > x - 100
          && (nu || q.alt + q.h > 900)));
        if (libre !== undefined) { place = { cote, s: libre }; break; }
      }
    }
    if (place) {
      const c = place.s + lf / 2;
      const point = place.cote === 'fond' ? { x: r.x0 + c, y: 100 } : place.cote === 'droite' ? { x: L - 100, y: r.y0 + c } : { x: 100, y: r.y0 + c };
      n = ouvrir(n, point, typeFenetre);
    } else piece.alertes.push('Pas de pan de mur libre pour la fenêtre : la pièce est sans fenêtre.');
  }
  dire(piece.alertes);
  scene = { ...s, niveaux: [n] };
} else {
  const m = fiche.maison ?? 'demo';
  if (m === 'demo') scene = etape(d.sceneDemo(ctx), 'maison de démonstration');
  else {
    if (typeof m === 'string') {
      scene = etape(d.sceneModele(m, ctx), `modèle ${m}`);
    } else {
      const s = d.nouvelleScene(ctx.nouvelId);
      const forme =
        (m.forme ?? 'rectangle') === 'rectangle'
          ? { forme: 'rectangle', largeur: mm(m.largeur), profondeur: mm(m.profondeur) }
          : { forme: m.forme, largeur: mm(m.largeur), profondeur: mm(m.profondeur), decoupe: { largeur: mm(m.decoupe[0]), profondeur: mm(m.decoupe[1]) } };
      let n = coque(s.niveaux[0], forme);
      if (!fiche.plan && n.pieces[0]) n = etape(d.typerPiece(n, n.pieces[0].id, 'sejour'), 'pièce');
      scene = { ...s, niveaux: [n] };
    }
    // Aménagement : celui de la fiche s'il y en a un, sinon l'automatique.
    let rdc = scene.niveaux[0];
    rdc = fiche.plan ? amenager(rdc, fiche.plan) : meublesAuto(ouverturesAuto(revetir(rdc)));
    rdc = exterieur(rdc, ext, marge);
    scene = { ...scene, niveaux: [rdc, ...scene.niveaux.slice(1).map((n: Tout) => meublesAuto(ouverturesAuto(revetir(n), false)))] };
    scene = etape(d.parcelleAutour(scene, marge), 'parcelle');
    if (fiche.etage && scene.niveaux.length === 1) {
      const { niveauId, ...avec } = etape<Tout>(d.ajouterNiveau(scene, { type: 'etage', copierMurs: true }, ctx), 'étage');
      scene = { ...avec, niveaux: avec.niveaux.map((n: Tout) => (n.id === niveauId ? ouverturesAuto(revetir(n), false) : n)) };
    }
    if (fiche.toit !== false) scene = etape(d.toitureAutomatique(scene, fiche.toit ?? 'deux_pans'), 'toit');
  }
}

// ----- Les repères pour la caméra (mêmes calculs que la vue 3D du site : cadre du niveau, marge de 3 m)
const rdc = scene.niveaux[0];
const e = rdc.exterieur;
const points: Pt[] = [
  ...rdc.murs.flatMap((m: Tout) => [m.a, m.b]),
  ...e.terrasses.flatMap((t: Tout) => t.contour),
  ...e.allees.flat(),
  ...e.clotures.flatMap((c: Tout) => c.points),
  ...e.piscines.flatMap((p: Tout) => d.contourPiscine(p)),
  ...e.vegetation.flatMap((v: Tout) => [
    { x: v.position.x - v.diametre / 2, y: v.position.y - v.diametre / 2 },
    { x: v.position.x + v.diametre / 2, y: v.position.y + v.diametre / 2 },
  ]),
];
const MARGE = 3000;
const bb = boite(points);
const cadre = { x: bb.x0 - MARGE, y: bb.y0 - MARGE, l: Math.max(bb.x1 - bb.x0 + 2 * MARGE, 12_000), h: Math.max(bb.y1 - bb.y0 + 2 * MARGE, 10_000) };
const toit = d.toit3D(rdc);
const hauteur = toit ? Math.max(...toit.pans.flat().map((p: Tout) => p.z)) - rdc.altitude : 2500;
const maison = boite(rdc.murs.flatMap((m: Tout) => [m.a, m.b]));
const reperes = {
  // la maison seule (sans le jardin) : pour la vue large de l'intérieur
  contenu: {
    centre: [(maison.x0 + maison.x1) / 2000, (maison.y0 + maison.y1) / 2000],
    rayon: Math.hypot(maison.x1 - maison.x0, maison.y1 - maison.y0, 2500) / 2000,
  },
  cadre: {
    centre: [(cadre.x + cadre.l / 2) / 1000, (cadre.y + cadre.h / 2) / 1000],
    rayon: Math.max(4, Math.hypot(cadre.l - 6000, cadre.h - 6000, hauteur) / 2000),
  },
  niveaux: scene.niveaux.map((n: Tout) => ({ id: n.id, nom: n.nom, type: n.type })),
  pieces: scene.niveaux.flatMap((n: Tout, i: number) =>
    n.pieces.map((p: Tout) => {
      const b = boite(p.contour);
      return {
        niveau: i,
        niveauId: n.id,
        type: p.type,
        nom: p.nom ?? d.LIBELLES_PIECE[p.type],
        centre: [(b.x0 + b.x1) / 2000, (b.y0 + b.y1) / 2000],
        rayon: Math.hypot(b.x1 - b.x0, b.y1 - b.y0) / 2000,
        surface: Math.round(((b.x1 - b.x0) * (b.y1 - b.y0)) / 1e5) / 10,
      };
    }),
  ),
  objets: scene.niveaux.reduce((t: number, n: Tout) => t + n.objets.length, 0),
};
process.stdout.write(JSON.stringify({ scene, reperes }));
