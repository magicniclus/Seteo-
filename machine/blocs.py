"""Les blocs : des animations prêtes à l'emploi, posées dans une vidéo par la clé "blocs" du plan.

Ils s'inspirent du catalogue HyperFrames (https://hyperframes.heygen.com/catalog) : on en a repris
les mouvements, refaits au format vertical et dans la DA (couleurs, police, zones sûres).
Styles et animations : montage/blocs/<nom>.css et .js. Ici, on fabrique les balises et les données.

Un bloc « plein » remplace l'image par une scène plein écran (la voix et les sous-titres continuent) ;
un bloc « calque » se pose par-dessus la prise (le visage reste visible).

Chaque fabrique reçoit le bloc tel qu'écrit dans plan.json et un contexte :
    c["id"]      identifiant unique (préfixe de tous les id HTML)
    c["debut"]   début du bloc dans la vidéo ; c["duree"] sa durée
    c["T"]       convertit un repère ("m34" ou des secondes) en secondes de la vidéo
    c["media"]   copie une image dans le projet et rend son adresse
et renvoie (balises HTML, données pour l'animation).
"""

import html
import re
import sys

e = html.escape
COCHE = "M6 46 L30 72 L80 8"
CROIX = "M12 12 L74 68 M74 12 L12 68"


def accent(texte: str, c: dict) -> str:
    """Texte sûr pour le HTML ; les *astérisques* passent en couleur d'accent."""
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(c["typo"](texte)))


def entete(b: dict, c: dict) -> str:
    sur = f'<span id="{c["id"]}-sur" class="sur-titre">{e(c["typo"](b["sur_titre"]))}</span>' if b.get("sur_titre") else ""
    titre = f'<h2 id="{c["id"]}-titre" class="titre">{accent(b["titre"], c)}</h2>' if b.get("titre") else ""
    return sur + titre


def scene(c: dict, contenu: str) -> str:
    # "devant" : la personne détourée reste au premier plan, le contenu tient au-dessus de sa tête
    if c.get("devant"):
        return f'\n    <div id="{c["id"]}-scene" class="scene scene--devant"><div class="scene__contenu">{contenu}</div></div>'
    return f'\n    <div id="{c["id"]}-scene" class="scene"><div class="scene__contenu">{contenu}</div></div>'


def instants(lignes: list, c: dict, premier: float, pas: float) -> list[float]:
    """L'instant (local au bloc) où chaque ligne apparaît : son repère "quand", sinon en cascade."""
    temps = []
    for k, ligne in enumerate(lignes):
        if isinstance(ligne, dict) and "quand" in ligne:
            t = c["T"](ligne["quand"]) - c["debut"]
        else:
            t = premier + k * pas
        temps.append(round(min(max(t, 0.45), max(c["duree"] - 0.9, 0.45)), 3))
    return temps


def liste(b: dict, c: dict):
    """Liste à cocher : 2 à 4 lignes. signe : coche (défaut), croix (erreurs) ou numero."""
    lignes = [l if isinstance(l, dict) else {"texte": l} for l in b["lignes"]]
    if not 1 <= len(lignes) <= 4:
        sys.exit("plan.json : un bloc « liste » prend 1 à 4 lignes (au-delà, on ne lit plus).")
    signe = b.get("signe", "coche")
    plus_long = max(len(l["texte"]) for l in lignes)
    dense = len(lignes) == 4
    taille = (72 if plus_long <= 18 else 62 if plus_long <= 24 else 54) - (10 if dense else 0)
    rangs = ""
    for k, l in enumerate(lignes):
        if signe == "numero":
            dessin = str(k + 1)
        else:
            dessin = (f'<svg viewBox="0 0 86 80"><path id="{c["id"]}-s{k}" pathLength="100" '
                      f'd="{CROIX if signe == "croix" else COCHE}"/></svg>')
        detail = f'<span class="liste__detail">{e(c["typo"](l["detail"]))}</span>' if l.get("detail") else ""
        rangs += (f'<li id="{c["id"]}-l{k}" class="liste__ligne"><span class="liste__signe">{dessin}</span>'
                  f'<span class="liste__texte" style="font-size:{taille}px">{accent(l["texte"], c)}{detail}</span></li>')
    balises = scene(c, entete(b, c) + f'<ul class="liste{" liste--dense" if dense else ""}">{rangs}</ul>')
    return balises, {"lignes": [{"t": t} for t in instants(lignes, c, 0.95, 0.75)]}


def barres(b: dict, c: dict):
    """Barres horizontales : 2 à 4 lignes {nom, valeur, texte}. La plus forte prend l'accent."""
    lignes = b["lignes"]
    if not 2 <= len(lignes) <= 4:
        sys.exit("plan.json : un bloc « barres » prend 2 à 4 lignes.")
    maxi = max(float(l["valeur"]) for l in lignes) or 1
    fort = b.get("fort", max(range(len(lignes)), key=lambda k: float(lignes[k]["valeur"])))
    rangs = ""
    for k, l in enumerate(lignes):
        largeur = max(8, round(float(l["valeur"]) / maxi * 100))
        rangs += (f'<div id="{c["id"]}-b{k}" class="barre{" barre--forte" if k == fort else ""}">'
                  f'<div class="barre__tete"><span class="barre__nom">{e(c["typo"](l["nom"]))}</span>'
                  f'<span id="{c["id"]}-v{k}" class="barre__valeur">{e(c["typo"](str(l.get("texte", l["valeur"]))))}</span></div>'
                  f'<div class="barre__piste"><div id="{c["id"]}-p{k}" class="barre__plein" style="width:{largeur}%"></div></div></div>')
    balises = scene(c, entete(b, c) + f'<div class="barres{" barres--dense" if len(lignes) == 4 else ""}">{rangs}</div>')
    return balises, {"lignes": [{"t": t} for t in instants(lignes, c, 0.85, 0.5)]}


def comparaison(b: dict, c: dict):
    """Deux cartes l'une sous l'autre {titre, valeur, note} : "gauche" est celle du haut,
    "droite" celle du bas. gagnant : "gauche", "droite" ou rien."""
    gagnant = {"gauche": "g", "droite": "d"}.get(b.get("gagnant"))
    cartes = ""
    for cote, cle in (("g", "gauche"), ("d", "droite")):
        x = b[cle]
        valeur = c["typo"](str(x["valeur"]))
        taille = min(120, int(470 / (0.62 * max(len(valeur), 3))))
        note = f'<span class="duel__note">{e(c["typo"](x["note"]))}</span>' if x.get("note") else ""
        verdict = ""
        if cote == gagnant:
            verdict = f'<span id="{c["id"]}-cadre" class="duel__cadre"></span>'
            if b.get("badge", "Le bon choix"):
                verdict += (f'<span class="duel__rang"><span id="{c["id"]}-badge" class="duel__badge">'
                            f'{e(b.get("badge", "Le bon choix"))}</span></span>')
        cartes += (f'<div id="{c["id"]}-{cote}" class="duel__carte"><span class="duel__texte">'
                   f'<span class="duel__titre">{e(c["typo"](x["titre"]))}</span>{note}</span>'
                   f'<span class="duel__valeur" style="font-size:{taille}px">{e(valeur)}</span>{verdict}</div>')
    verdict_t = c["T"](b["verdict"]) - c["debut"] if "verdict" in b else min(2.0, c["duree"] - 1.2)
    balises = scene(c, entete(b, c) + f'<div class="duel">{cartes}</div>')
    return balises, {"gagnant": gagnant, "verdict": round(max(verdict_t, 1.3), 3)}


def avant_apres(b: dict, c: dict):
    """Deux photos : celle d'après balaie celle d'avant. "quand" : l'instant de la bascule."""
    avant = c["media"](b["avant"], f'{c["id"]}-avant')
    apres = c["media"](b["apres"], f'{c["id"]}-apres')
    bascule = c["T"](b["quand"]) - c["debut"] if "quand" in b else c["duree"] * 0.4
    cadre = (f'<div id="{c["id"]}-cadre" class="aa"><img class="aa__image" src="{e(avant)}" alt="">'
             f'<span class="aa__etiquette aa__etiquette--avant">{e(b.get("etiquette_avant", "Avant"))}</span>'
             f'<div id="{c["id"]}-apres" class="aa__apres"><img class="aa__image" src="{e(apres)}" alt="">'
             f'<span id="{c["id"]}-etq" class="aa__etiquette aa__etiquette--apres">{e(b.get("etiquette_apres", "Après"))}</span></div>'
             f'<div id="{c["id"]}-trait" class="aa__trait"></div></div>')
    balises = scene(c, entete(b, c) + cadre)
    return balises, {"bascule": round(min(max(bascule, 0.9), c["duree"] - 1.6), 3), "balayage": 0.9, "largeur": 920}


def commentaire(b: dict, c: dict):
    """Une bulle « commentaire » où le mot-clé se tape, puis la réponse de la marque. Calque."""
    texte = b.get("texte") or c["mot_cle"]
    if not texte:
        sys.exit("plan.json : le bloc « commentaire » a besoin d'un \"texte\" ou d'un \"mot_cle\".")
    lettres = "".join(f'<span id="{c["id"]}-c{k}" class="c">{e(ch)}</span>' for k, ch in enumerate(texte))
    marque = " ".join(c["marque"]).title()
    initiales = "".join(m[0] for m in c["marque"])[:2].upper()
    pseudo = b.get("pseudo", "toi")
    frappe = 0.07
    balises = (f'\n    <div class="fil">'
               f'<div id="{c["id"]}-com" class="fil__bulle"><span class="fil__avatar">{e(pseudo[:1].upper())}</span>'
               f'<span><span class="fil__nom">{e(pseudo)}</span><span class="fil__texte">{lettres}</span></span></div>'
               f'<div id="{c["id"]}-rep" class="fil__bulle fil__bulle--marque"><span class="fil__avatar">{e(initiales)}</span>'
               f'<span><span class="fil__nom">{e(marque)}</span>'
               f'<span class="fil__texte">{e(c["typo"](b.get("reponse", "Je t’envoie ça en DM")))}</span></span></div></div>')
    return balises, {"lettres": len(texte), "frappe": frappe, "reponse": round(0.45 + len(texte) * frappe + 0.45, 3)}


def nom(b: dict, c: dict):
    """Bandeau « qui parle » : un nom et un rôle. Calque, à poser dans les premières secondes."""
    role = (f'<span class="bandeau__cache"><span id="{c["id"]}-role" class="bandeau__role">{e(c["typo"](b["role"]))}</span></span>'
            if b.get("role") else f'<span id="{c["id"]}-role"></span>')
    balises = (f'\n    <div class="bandeau">{role}<span id="{c["id"]}-nom" class="bandeau__nom">{e(b["nom"])}</span>'
               f'<span id="{c["id"]}-trait" class="bandeau__trait"></span></div>')
    return balises, {}


def demande(b: dict, c: dict):
    """La fiche d'une demande de travaux : 2 à 6 champs {nom, valeur}. Un champ {"flou": true} est
    masqué : sa vraie valeur n'entre jamais dans la vidéo, même si elle est donnée dans le plan."""
    champs = b["champs"]
    if not 2 <= len(champs) <= 6:
        sys.exit("plan.json : un bloc « demande » prend 2 à 6 champs.")
    rangs = ""
    for k, ch in enumerate(champs):
        if ch.get("flou"):
            # texte de remplacement : même silhouette (lettres -> x, chiffres -> 0), rien de réel
            modele = str(ch.get("valeur") or "Xxxxxxx Xxxxxxxx")
            faux = re.sub(r"[^\W\d_]", "x", re.sub(r"\d", "0", modele))[:22]
            valeur = f'<span class="fiche__valeur fiche__valeur--floue">{e(faux)}</span>'
        else:
            valeur = f'<span class="fiche__valeur">{accent(str(ch["valeur"]), c)}</span>'
        rangs += (f'<div id="{c["id"]}-ch{k}" class="fiche__champ"><span class="fiche__nom">{e(c["typo"](ch["nom"]))}</span>'
                  f'{valeur}</div>')
    balises = scene(c, entete(b, c) + f'<div id="{c["id"]}-fiche" class="fiche">{rangs}</div>')
    return balises, {"champs": [{"t": t} for t in instants(champs, c, 0.7, 0.3)]}


# nom du bloc -> (fabrique, type, durée par défaut en secondes)
BLOCS = {
    "liste": (liste, "plein", 7.0),
    "barres": (barres, "plein", 6.0),
    "comparaison": (comparaison, "plein", 6.0),
    "avant_apres": (avant_apres, "plein", 5.0),
    "demande": (demande, "plein", 6.0),
    "commentaire": (commentaire, "calque", 4.0),
    "nom": (nom, "calque", 3.5),
}
