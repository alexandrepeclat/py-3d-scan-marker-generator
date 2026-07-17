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


# ==============================
# Paramètres
# ==============================

SEED = 12345
NB_DOMES = 10

random.seed(SEED)



# ==============================
# Génération d'un dôme
# ==============================

def generate_dome():

    # --------------------------
    # Étage milieu :
    #
    # h-p-h-p-h-p
    #
    # Choisir exactement 2 hexagones
    # parmi les 3.
    # --------------------------

    middle = ["h", "h", "h"]

    for i in random.sample(range(3), 2):
        middle[i] = "x"



    # --------------------------
    # Étage bas :
    #
    # p-h-h-p-h-h-p-h-h
    #
    # Un hexagone marqué dans
    # chaque groupe h-h
    # + un pentagone marqué.
    # --------------------------

    bottom = [
        "p", "h", "h",
        "p", "h", "h",
        "p", "h", "h"
    ]


    # Un hexagone marqué par groupe
    for start in (1, 4, 7):

        position = random.choice(
            (start, start + 1)
        )

        bottom[position] = "x"


    # Un pentagone marqué
    pentagon = random.choice(
        (0, 3, 6)
    )

    bottom[pentagon] = "x"


    return middle, bottom



# ==============================
# Format d'affichage
# ==============================

def format_dome(dome):

    middle, bottom = dome


    # Ajout des pentagones intermédiaires
    middle_text = (
        middle[0]
        + "-p-"
        + middle[1]
        + "-p-"
        + middle[2]
    )


    bottom_text = "-".join(bottom)


    return middle_text, bottom_text



# ==============================
# Génération sans doublons
# ==============================

domes = set()


while len(domes) < NB_DOMES:

    dome = generate_dome()

    # Les listes deviennent des tuples
    # pour être comparables dans un set

    identifier = (
        tuple(dome[0]),
        tuple(dome[1])
    )

    domes.add(identifier)



# ==============================
# Affichage final
# ==============================

for number, dome in enumerate(sorted(domes), 1):

    middle, bottom = format_dome(dome)

    print(f"Dôme {number}")
    print(middle)
    print(bottom)
    print()