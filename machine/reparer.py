"""Répare une vidéo arrivée coupée (étape 0 du montage, seulement si besoin).

Symptôme : ffprobe ou transcrire.py répond « error reading header » ou « moov atom not found ».
Une pièce jointe trop lourde est parfois tronquée à l'envoi : il lui manque sa fin, où le fichier
range son index. Si la coupure tombe dans l'index (fichier à peine trop gros), l'image et le son
sont entiers : on les relit directement dans les données et on refait un fichier propre.
Si la coupure tombe dans les données elles-mêmes, c'est irréparable : il faut redemander la vidéo
par un lien (Dropbox, Google Drive).

Limites : vidéo H.264 à une tranche par image (ce que sortent les téléphones et ffmpeg), son AAC.

Usage :
    python machine/reparer.py video-coupee.mov rushs/video-reparee.mp4
"""
import struct, sys, subprocess
import numpy as np
import av

source, sortie = sys.argv[1], sys.argv[2]
d = open(source, "rb").read()

# --- atomes de tête
pos, mdat = 0, None
while pos + 8 <= len(d):
    taille, nom = struct.unpack(">I4s", d[pos:pos + 8])
    if nom == b"mdat": mdat = (pos + 8, pos + taille)
    if nom == b"moov": moov = pos
    if taille < 8: break
    pos += taille
debut, fin = mdat
assert fin <= len(d), "les données elles-mêmes sont coupées : irréparable"

# --- ce qui reste de l'index : réglages du codec vidéo et cadence
i = d.find(b"avcC", moov)
avcc = d[i + 4:i - 4 + struct.unpack(">I", d[i - 4:i])[0]]
long_nal = (avcc[4] & 3) + 1
p, sps_pps = 6, []
for _ in range(avcc[5] & 31):
    n = struct.unpack(">H", avcc[p:p + 2])[0]; sps_pps.append(avcc[p + 2:p + 2 + n]); p += 2 + n
nb_pps = avcc[p]; p += 1
for _ in range(nb_pps):
    n = struct.unpack(">H", avcc[p:p + 2])[0]; sps_pps.append(avcc[p + 2:p + 2 + n]); p += 2 + n
j = d.find(b"mdhd", moov); echelle, duree = struct.unpack(">II", d[j + 16:j + 24])
j = d.find(b"stts", moov); nb_images, delta = struct.unpack(">II", d[j + 12:j + 20])
ips = echelle / delta
print(f"vidéo : {nb_images} images attendues, {ips:.3f} i/s, {duree / echelle:.2f} s, longueur NAL {long_nal}")

def nal(p):
    """Longueur totale (préfixe compris) si une unité H.264 commence en p, sinon 0.
    Signatures strictes (encodeur x264, une tranche par image) pour ne jamais prendre du son pour de l'image :
    longueur plausible, entête de tranche, première tranche de l'image, type de tranche, jeu de paramètres 0."""
    if p + 8 > fin: return 0
    L = int.from_bytes(d[p:p + long_nal], "big")
    if L < 3 or L > 400000 or p + long_nal + L > fin: return 0
    h, a, b = d[p + long_nal], d[p + long_nal + 1], d[p + long_nal + 2]
    if h in (0x65, 0x45, 0x25) and a == 0x88 and b & 0x80: return long_nal + L          # image clé
    if h in (0x41, 0x61, 0x21, 0x01) and a in (0x9A, 0x9B, 0x9E, 0x9F): return long_nal + L  # P ou B
    if h == 0x06 and a == 0x05 and L < 4096: return long_nal + L                         # informations de l'encodeur
    return 0

video = bytearray()
for x in sps_pps: video += b"\x00\x00\x00\x01" + x
sons, images, p = [], 0, debut
while p < fin:
    n = nal(p)
    if n:
        if d[p + long_nal] & 0x1F in (1, 5): images += 1
        video += b"\x00\x00\x00\x01" + d[p + long_nal:p + n]
        p += n
    else:  # du son : on avance jusqu'au prochain début d'image plausible
        q = p + 1
        while q < fin and not nal(q): q += 1
        sons.append(d[p:q]); p = q
print(f"images retrouvées : {images} ; blocs de son : {len(sons)} ({sum(map(len, sons))} octets)")
open(sortie + ".h264", "wb").write(video)

# --- le son : AAC brut, réglages inconnus -> on essaie les plus courants et on garde celui qui se décode
def essai(freq, canaux, limite=None):
    idx = {48000: 3, 44100: 4, 32000: 5, 24000: 6, 22050: 7}[freq]
    asc = bytes([(2 << 3) | (idx >> 1), ((idx & 1) << 7) | (canaux << 3)])
    c = av.CodecContext.create("aac", "r"); c.extradata = asc
    pcm, erreurs, trames = [], 0, 0
    for bloc in sons[:limite]:
        try:
            for f in c.decode(av.Packet(bloc)):
                trames += 1
                a = f.to_ndarray()
                pcm.append(a if a.ndim == 2 else a[None, :])
        except Exception:
            erreurs += 1
    return pcm, erreurs, trames

meilleur = None
for freq in (44100, 48000, 32000, 24000, 22050):
    for canaux in (1, 2):
        pcm, erreurs, trames = essai(freq, canaux, 120)
        ecart = abs(trames * (len(sons) / 120) * 1024 / freq - duree / echelle)
        print(f"  essai {freq} Hz, {canaux} canal(aux) : {trames} trames, {erreurs} erreurs sur 120 blocs, écart de durée estimé {ecart:.1f} s")
        note = (erreurs, ecart)
        if meilleur is None or note < meilleur[0]: meilleur = (note, freq, canaux)
_, freq, canaux = meilleur
pcm, erreurs, trames = essai(freq, canaux)
son = np.concatenate(pcm, axis=1)
print(f"son retenu : {freq} Hz, {canaux} canal(aux), {trames} trames, {erreurs} erreurs, {son.shape[1] / freq:.2f} s")
son = son[:, 1024:]                         # l'amorce de l'encodeur AAC, que l'index disait de sauter
brut = (np.clip(son.T, -1, 1) * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-framerate", f"{ips:.6f}", "-i", sortie + ".h264",
                "-f", "s16le", "-ar", str(freq), "-ac", str(son.shape[0]), "-i", "-",
                "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-shortest", sortie], input=brut, check=True)
print("écrit :", sortie)
