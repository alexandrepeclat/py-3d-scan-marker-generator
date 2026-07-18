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

            
        


import random
from itertools import combinations


# ==============================
# Paramètres
# ==============================

SEED = 12345
NB_DOMES = 10

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


def select_diverse(count, dist):

    n = len(dist)
    indices = list(range(n))
    random.shuffle(indices)  # pour varier les ex-aequo, reproductible via SEED

    # Amorce : la paire la plus éloignée
    i0, j0 = max(combinations(indices, 2), key=lambda p: dist[p[0]][p[1]])
    selected = [i0, j0]

    # Ajout glouton : à chaque étape, le dôme qui maximise sa
    # distance minimale aux dômes déjà choisis
    while len(selected) < count:
        remaining = [i for i in indices if i not in selected]
        next_index = max(
            remaining,
            key=lambda i: min(dist[i][s] for s in selected)
        )
        selected.append(next_index)

    # Amélioration locale : on essaie d'échanger chaque dôme
    # choisi contre un dôme non choisi si ça augmente la
    # distance minimale globale de l'ensemble.
    improved = True
    while improved:
        improved = False
        current = min_pairwise_distance(selected, dist)

        for pos in range(len(selected)):
            for candidate in indices:
                if candidate in selected:
                    continue

                trial = selected[:pos] + selected[pos + 1:] + [candidate]
                trial_min = min_pairwise_distance(trial, dist)

                if trial_min > current:
                    selected = trial
                    current = trial_min
                    improved = True
                    break

            if improved:
                break

    return selected


# ==============================
# Format d'affichage
# ==============================

def format_dome(config):

    middle, bottom = config

    middle_text = f"{middle[0]}-p-{middle[1]}-p-{middle[2]}"
    bottom_text = "-".join(bottom)

    return middle_text, bottom_text


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

selected_indices = select_diverse(NB_DOMES, dist)
selected_indices.sort(key=lambda i: distinct_configs[i])
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