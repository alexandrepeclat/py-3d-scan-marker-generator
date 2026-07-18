# ============================================================
# Générateur de dômes de référence pour scan 3D
# ============================================================
# Basé sur : https://download.revopoint3d.com/support/download/accessories/marker-block-kit-quickstartguide-en-v1.1-20250117.pdf
# Objectif :
# Générer des répartitions de pastilles sur des dômes 3D
# servant de points de référence pour un scanner.
#
# Le dôme correspond à un demi-icosaèdre tronqué vu depuis
# son sommet.
#
#
# Nomenclature des faces :
#
# Vue depuis le dessus du dôme.
# Pour chaque étage :
#   - on commence par la face située à midi
#   - puis on tourne dans le sens horaire
#
#
# Symboles :
#
#   h = face hexagone
#   p = face pentagone
#   x = face portant une pastille
#
#
# Structure utilisée :
#
#
# Sommet (non affiché) :
#
#             h
#             x
#
# Une pastille est toujours présente au sommet.
#
#
# Milieu :
#
#             h - p - h - p - h - p
#             0       1       2
#
# Règle :
#   exactement 2 des 3 hexagones du milieu reçoivent une
#   pastille.
#
#
# Bas :
#
#             p - h - h - p - h - h - p - h - h
#             0   1 2   3   4 5   6   7 8
#
# Règle :
#   - une pastille dans chaque groupe h-h
#   - une pastille supplémentaire sur un pentagone
#
#
# Exemple :
#
# Milieu :
#
#             x-p-h-p-x-p
#
# signifie :
#             hexagone milieu 0 marqué
#             hexagone milieu 1 vide
#             hexagone milieu 2 marqué
#
#
# Bas :
#
#             p-x-h-p-h-x-p-h-x
#
# signifie :
#             groupe 1 : premier hexagone marqué
#             groupe 2 : deuxième hexagone marqué
#             groupe 3 : deuxième hexagone marqué
#             + pentagone marqué
#
#
# Le seed fixe permet de retrouver exactement les mêmes
# configurations lors d'une exécution ultérieure.
#
# ============================================================

            
        


import argparse
import math
import random
from itertools import combinations


# ==============================
# Paramètres
# ==============================

SEED = 12345

_parser = argparse.ArgumentParser(description="Génère des dômes de référence pour scan 3D.")
_parser.add_argument(
    "-n", "--nb-domes",
    type=int,
    default=10,
    help="Nombre de dômes à générer (défaut : 10, max : 24 dômes physiquement distincts).",
)
_args = _parser.parse_args()

NB_DOMES = _args.nb_domes

random.seed(SEED)


# ==============================
# Génération de toutes les
# configurations valides
# ==============================
#
# Le dôme est composé de 3 "branches" identiques en
# structure (1 hexagone du milieu + 1 groupe p-h-h du bas),
# disposées avec une symétrie de rotation d'ordre 3.
#
# Numéroter les branches 0/1/2 dépend uniquement d'où on
# commence à lire le dôme : deux configurations qui sont des
# rotations l'une de l'autre décrivent donc le MÊME dôme
# physique. Pour choisir des dômes qui se ressemblent
# vraiment le moins possible, il faut donc :
#   1) dédupliquer par orbite de rotation (pas juste par
#      tuple identique),
#   2) parmi les dômes physiquement distincts, choisir ceux
#      qui maximisent la distance mutuelle minimale, en
#      tenant compte du fait que l'orientation relative de
#      deux dômes n'est jamais connue à l'avance.

def generate_all_configs():

    configs = []

    for middle_marked in combinations(range(3), 2):
        middle = ["h", "h", "h"]
        for i in middle_marked:
            middle[i] = "x"

        for hex_choices in (
            (a, b, c)
            for a in (0, 1)
            for b in (0, 1)
            for c in (0, 1)
        ):
            for pentagon in (0, 3, 6):
                bottom = [
                    "p", "h", "h",
                    "p", "h", "h",
                    "p", "h", "h"
                ]

                for group_index, choice in enumerate(hex_choices):
                    start = 1 + group_index * 3
                    bottom[start + choice] = "x"

                bottom[pentagon] = "x"

                configs.append((tuple(middle), tuple(bottom)))

    return configs


def rotate(config, k):
    """Tourne le dôme de k branches (k dans 0, 1, 2)."""

    middle, bottom = config

    branches = [
        (middle[i], bottom[3 * i], bottom[3 * i + 1], bottom[3 * i + 2])
        for i in range(3)
    ]
    branches = branches[k:] + branches[:k]

    new_middle = tuple(b[0] for b in branches)
    new_bottom = tuple(v for b in branches for v in b[1:])

    return new_middle, new_bottom


def marked_vector(config):
    """Vecteur binaire : 1 si la face porte une pastille."""

    middle, bottom = config
    return tuple(1 if v == "x" else 0 for v in middle + bottom)


def canonical(config):
    """Représentant unique de l'orbite de rotation d'un dôme."""

    return min(rotate(config, k) for k in range(3))


def hamming(a, b):
    return sum(x != y for x, y in zip(a, b))


def orientation_free_distance(config_a, config_b):
    """
    Différence entre 2 dômes en tenant compte du fait que leur
    orientation relative n'est pas connue à l'avance : on prend
    la rotation qui les rapproche le plus, donc le pire cas de
    confusion possible entre les deux.
    """

    va = marked_vector(config_a)

    return min(
        hamming(va, marked_vector(rotate(config_b, k)))
        for k in range(3)
    )


# ==============================
# Sélection des dômes les plus
# différents entre eux
# ==============================

def min_pairwise_distance(indices, dist):
    return min(dist[i][j] for i, j in combinations(indices, 2))


def rank_by_diversity(dist):
    """
    Classe tous les dômes du plus au moins "utile" à garder, du
    premier au dernier, via un ajout glouton par plus grande
    distance minimale (farthest-point). Contrairement à une
    sélection optimisée pour un NB_DOMES précis (avec échanges
    locaux), cet ordre ne dépend pas du nombre final demandé :
    prendre les N premiers de ce classement pour N=10 donne
    exactement les mêmes dômes que les 10 premiers d'un
    classement pour N=20. C'est ce qui garantit que la sortie
    reste cohérente quand on change -n.
    """

    n = len(dist)
    indices = list(range(n))
    random.shuffle(indices)  # pour varier les ex-aequo, reproductible via SEED

    # Amorce : la paire la plus éloignée
    i0, j0 = max(combinations(indices, 2), key=lambda p: dist[p[0]][p[1]])
    order = [i0, j0]

    # Ajout glouton : à chaque étape, le dôme qui maximise sa
    # distance minimale aux dômes déjà classés
    while len(order) < n:
        remaining = [i for i in indices if i not in order]
        next_index = max(
            remaining,
            key=lambda i: min(dist[i][s] for s in order)
        )
        order.append(next_index)

    return order


# ==============================
# Format d'affichage
# ==============================

def format_dome(config):

    middle, bottom = config

    middle_text = f"{middle[0]}-p-{middle[1]}-p-{middle[2]}-p"
    bottom_text = "-".join(bottom)

    return middle_text, bottom_text


# ==============================
# Géométrie réelle du dôme (SVG)
# ==============================
# Le dôme est un icosaèdre tronqué (ballon de foot) coupé en
# 2 par un plan perpendiculaire à un axe passant par 2
# hexagones opposés. On calcule ses vraies coordonnées 3D, on
# garde la moitié supérieure (16 faces : 1 sommet + 6 milieu +
# 9 bas) et on projette à plat, vue du dessus. Les faces
# partagent réellement leurs arêtes (vraie tessellation, pas
# une approximation), et le sommet, un hexagone du milieu et
# son pentagone du bas sont toujours alignés en ligne droite
# à midi (propriété géométrique exacte du solide, vérifiée
# analytiquement).

_PHI = (1 + 5 ** 0.5) / 2

_ICOSA_VERTICES = [
    (-1, _PHI, 0), (1, _PHI, 0), (-1, -_PHI, 0), (1, -_PHI, 0),
    (0, -1, _PHI), (0, 1, _PHI), (0, -1, -_PHI), (0, 1, -_PHI),
    (_PHI, 0, -1), (_PHI, 0, 1), (-_PHI, 0, -1), (-_PHI, 0, 1),
]

_ICOSA_FACES = [
    (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
    (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
    (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
    (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
]


def _v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v_scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _v_lerp(a, b, t):
    return _v_add(a, _v_scale(_v_sub(b, a), t))


def _v_norm(a):
    length = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    return (a[0] / length, a[1] / length, a[2] / length)


def _v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _v_cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _build_truncated_icosahedron():
    """Troncature exacte : chaque triangle -> hexagone, chaque sommet -> pentagone."""

    faces = {}

    for idx, (a, b, c) in enumerate(_ICOSA_FACES):
        A, B, C = _ICOSA_VERTICES[a], _ICOSA_VERTICES[b], _ICOSA_VERTICES[c]
        points = [
            _v_lerp(A, B, 1 / 3), _v_lerp(A, B, 2 / 3),
            _v_lerp(B, C, 1 / 3), _v_lerp(B, C, 2 / 3),
            _v_lerp(C, A, 1 / 3), _v_lerp(C, A, 2 / 3),
        ]
        centroid = _v_norm(tuple(sum(p[k] for p in points) / 6 for k in range(3)))
        faces[("h", idx)] = {"points": points, "centroid": centroid, "kind": "hex"}

    for vi in range(12):
        V = _ICOSA_VERTICES[vi]
        neighbors = {
            x
            for face in _ICOSA_FACES if vi in face
            for x in face if x != vi
        }

        v_dir = _v_norm(V)
        ref = (1, 0, 0) if abs(v_dir[0]) < 0.9 else (0, 1, 0)
        u = _v_norm(_v_cross(v_dir, ref))
        w = _v_cross(v_dir, u)

        by_angle = []
        for ni in neighbors:
            point = _v_lerp(V, _ICOSA_VERTICES[ni], 1 / 3)
            rel = _v_sub(point, V)
            angle = math.atan2(_v_dot(rel, w), _v_dot(rel, u))
            by_angle.append((angle, point))
        by_angle.sort(key=lambda t: t[0])

        points = [p for _, p in by_angle]
        centroid = _v_norm(tuple(sum(p[k] for p in points) / 5 for k in range(3)))
        faces[("p", vi)] = {"points": points, "centroid": centroid, "kind": "pent"}

    return faces


def _shared_edge(face_a, face_b, precision=4):
    def key(p):
        return tuple(round(c, precision) for c in p)

    pts_a = {key(p) for p in face_a["points"]}
    pts_b = {key(p) for p in face_b["points"]}
    return len(pts_a & pts_b) >= 2


def _resolve_dome_geometry():
    """
    Choisit une face hexagone comme sommet, extrait les 16
    faces de l'hémisphère (sommet + milieu + bas), et associe
    chaque index de nos structures de données (middle[i],
    bottom[i]) à sa vraie face géométrique, orientée pour
    qu'un hexagone du milieu (et son pentagone du bas) soit
    toujours à midi.
    """

    faces = _build_truncated_icosahedron()

    apex_id = ("h", 0)
    pole = faces[apex_id]["centroid"]

    ranked = sorted(faces, key=lambda fid: -_v_dot(faces[fid]["centroid"], pole))
    hemisphere = set(ranked[:16])

    middle = {
        fid for fid in hemisphere
        if fid != apex_id and _shared_edge(faces[apex_id], faces[fid])
    }
    bottom = hemisphere - {apex_id} - middle
    middle_hexagons = sorted(fid for fid in middle if fid[0] == "h")

    ref = (1, 0, 0) if abs(pole[0]) < 0.9 else (0, 1, 0)
    u = _v_norm(_v_cross(pole, ref))
    w = _v_cross(pole, u)

    def raw_angle(fid):
        centroid = faces[fid]["centroid"]
        rel = _v_sub(centroid, _v_scale(pole, _v_dot(centroid, pole)))
        return math.atan2(_v_dot(rel, w), _v_dot(rel, u))

    theta0 = raw_angle(middle_hexagons[0])

    def rel_angle(fid):
        angle = (raw_angle(fid) - theta0) % (2 * math.pi)
        return 0.0 if angle > 2 * math.pi - 1e-6 else angle

    middle_order = sorted(middle, key=rel_angle)

    # Un tri purement angulaire donne directement p-h-h-p-h-h-p-h-h en
    # lecture horaire réelle (vérifié : le pentagone de chaque groupe
    # est exactement aligné avec l'hexagone du milieu correspondant).
    # Grouper plutôt par adjacence réelle avec l'hexagone du milieu
    # donnerait un ordre h-p-h (le pentagone est entre ses 2 hexagones
    # voisins, pas suivi par eux) : ça décale le texte par rapport au
    # rendu visuel.
    bottom_order = sorted(bottom, key=rel_angle)

    def project(point, scale_factor):
        rel = _v_sub(point, _v_scale(pole, _v_dot(point, pole)))
        a = _v_dot(rel, u)
        b = _v_dot(rel, w)
        a2 = a * math.cos(theta0) + b * math.sin(theta0)
        b2 = -a * math.sin(theta0) + b * math.cos(theta0)
        return (b2 * scale_factor, -a2 * scale_factor)

    slots: dict = {"apex": apex_id}
    for j, fid in enumerate(middle_order):
        slots[("middle", j)] = fid
    for j, fid in enumerate(bottom_order):
        slots[("bottom", j)] = fid

    return faces, slots, project


_DOME_FACES, _DOME_SLOTS, _project = _resolve_dome_geometry()


def dome_svg(config, cx, cy, scale=90):
    middle, bottom = config

    marks: dict = {"apex": True}
    middle_ring = [middle[0], "p", middle[1], "p", middle[2], "p"]
    for j, value in enumerate(middle_ring):
        marks[("middle", j)] = value == "x"
    for j, value in enumerate(bottom):
        marks[("bottom", j)] = value == "x"

    parts = []

    for slot, face_id in _DOME_SLOTS.items():
        face = _DOME_FACES[face_id]

        projected = [_project(p, scale) for p in face["points"]]
        points = " ".join(f"{cx + x:.1f},{cy + y:.1f}" for x, y in projected)
        parts.append(f'<polygon points="{points}" fill="white" stroke="black" stroke-width="1.5" />')

        if marks[slot]:
            # Centre du disque = moyenne des points déjà projetés du
            # polygone (et non le centroïde 3D, normalisé sur la
            # sphère unité donc à une échelle différente des points
            # du polygone, ce qui décalait le disque hors de la face).
            px = sum(x for x, _ in projected) / len(projected)
            py = sum(y for _, y in projected) / len(projected)
            parts.append(f'<circle cx="{cx + px:.1f}" cy="{cy + py:.1f}" r="7" fill="black" />')

    return "\n".join(parts)


def build_domes_svg(domes, path):
    cols = 5
    cell_w, cell_h = 340, 380
    center_y_local = 190

    rows = -(-len(domes) // cols)  # division entière arrondie au sup.
    width = cols * cell_w
    height = rows * cell_h

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="sans-serif">'
    ]

    for index, dome in enumerate(domes):
        col = index % cols
        row = index // cols

        cx = col * cell_w + cell_w / 2
        cy = row * cell_h + center_y_local

        svg_parts.append(
            f'<text x="{cx:.1f}" y="{cy - 160:.1f}" text-anchor="middle" '
            f'font-size="16">Dôme {index + 1}</text>'
        )
        svg_parts.append(dome_svg(dome, cx, cy))

    svg_parts.append("</svg>")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))


# ==============================
# Génération
# ==============================

all_configs = generate_all_configs()
distinct_configs = sorted({canonical(c) for c in all_configs})

if NB_DOMES > len(distinct_configs):
    raise ValueError(
        f"NB_DOMES={NB_DOMES} dépasse le nombre de dômes "
        f"réellement distincts ({len(distinct_configs)})."
    )

n = len(distinct_configs)
dist = [
    [
        orientation_free_distance(distinct_configs[i], distinct_configs[j])
        for j in range(n)
    ]
    for i in range(n)
]

diversity_order = rank_by_diversity(dist)
selected_indices = diversity_order[:NB_DOMES]
domes = [distinct_configs[i] for i in selected_indices]


# ==============================
# Affichage final
# ==============================

print(
    f"{len(all_configs)} configurations valides, "
    f"{len(distinct_configs)} dômes physiquement distincts "
    f"(symétrie de rotation)."
)
print(
    f"Distance minimale garantie entre les {NB_DOMES} dômes "
    f"choisis : {min_pairwise_distance(selected_indices, dist)} faces."
)
print()

for number, dome in enumerate(domes, 1):

    middle, bottom = format_dome(dome)

    print(f"Dôme {number}")
    print(middle)
    print(bottom)
    print()


# ==============================
# Matrice des distances
# ==============================
# Distance = nb de faces dont l'état (avec/sans pastille)
# diffère, dans le pire cas d'alignement relatif (cf.
# orientation_free_distance). Plus c'est élevé, moins les
# deux dômes risquent d'être confondus.

header = "     " + "".join(f"{j + 1:>4}" for j in range(NB_DOMES))
print(header)

for row, i in enumerate(selected_indices, 1):
    cells = "".join(
        f"{dist[i][k]:>4}" if row != col + 1 else "   ."
        for col, k in enumerate(selected_indices)
    )
    print(f"{row:>4} {cells}")


# ==============================
# Export graphique
# ==============================

svg_path = "domes.svg"
build_domes_svg(domes, svg_path)

print()
print(f"Représentation graphique : {svg_path}")