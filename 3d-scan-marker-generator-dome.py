# ============================================================
# Reference dome generator for 3D scanning
# ============================================================
# Based on: https://download.revopoint3d.com/support/download/accessories/marker-block-kit-quickstartguide-en-v1.1-20250117.pdf
#
# Goal:
# Generate marker layouts on 3D domes used as reference points
# for a scanner.
#
# The dome is a truncated icosahedron, halved, viewed from its
# apex.
#
#
# Face naming:
#
# Viewed from above the dome.
# For each tier:
#   - start with the face at 12 o'clock
#   - then move clockwise
#
#
# Symbols:
#
#   h = hexagon face
#   p = pentagon face
#   x = face carrying a marker
#
#
# Structure used:
#
#
# Apex (not displayed):
#
#             h
#             x
#
# A marker is always present at the apex.
#
#
# Middle tier:
#
#             h - p - h - p - h - p
#             0       1       2
#
# Rule:
#   exactly 2 of the 3 middle hexagons carry a marker.
#
#
# Bottom tier:
#
#             p - h - h - p - h - h - p - h - h
#             0   1 2   3   4 5   6   7 8
#
# Rule:
#   - one marker in each h-h group
#   - one additional marker on a pentagon
#
#
# Example:
#
# Middle tier:
#
#             x-p-h-p-x-p
#
# means:
#             middle hexagon 0 marked
#             middle hexagon 1 empty
#             middle hexagon 2 marked
#
#
# Bottom tier:
#
#             p-x-h-p-h-x-p-h-x
#
# means:
#             group 1: first hexagon marked
#             group 2: second hexagon marked
#             group 3: second hexagon marked
#             + pentagon marked
#
#
# Choosing which domes to display:
#
# With these rules, there are 72 valid configurations, i.e. 24
# physically distinct domes once rotational symmetry is
# removed (see below). The program never displays more domes
# than requested, and always ranks them in the same order
# (from "best" to "worst"), using 3 criteria applied in this
# order:
#
#   1. Marker spread ("coverage"): smallest maximum angular
#      gap between 2 consecutive markers around the dome.
#      Goal: no side of the dome should ever be left without a
#      visible marker during a scan. This criterion only takes
#      a handful of possible values (domes are often tied).
#
#   2. On a coverage tie: maximum mutual distance from the
#      other domes already picked within that same tier, to
#      get domes that look as different from each other as
#      possible (see below).
#
#   3. If still tied: alphabetical order of the generated text
#      (e.g. "h-p-x-p-x-p" / "p-h-x-p-x-h-x-x-h"), for a fully
#      deterministic result.
#
# This order never depends on the number of domes requested
# (-n): the first N domes shown with -n 10 are always exactly
# the first N of a -n 20, etc.
#
# ============================================================

import argparse
import math
from itertools import combinations

from mathutils import cross, dot, lerp, normalize, project_to_plane, scale, shared_edge, sub


# ==============================
# Parameters
# ==============================

_parser = argparse.ArgumentParser(description="Generate reference domes for 3D scanning.")
_parser.add_argument(
    "-n", "--nb-domes",
    type=int,
    default=None,
    help="Number of domes to generate (default: all 24 physically distinct domes).",
)
_args = _parser.parse_args()

NB_DOMES = _args.nb_domes  # resolved to the max once distinct_configs is known


# ==============================
# Generating all valid
# configurations
# ==============================
#
# The dome is made of 3 branches, identical in structure (1
# middle hexagon + 1 p-h-h bottom group), arranged with 3-fold
# rotational symmetry.
#
# Numbering the branches 0/1/2 depends only on where you start
# reading the dome: two configurations that are rotations of
# each other describe the SAME physical dome. To pick domes
# that truly look as different as possible, we therefore need
# to:
#   1) deduplicate by rotation orbit (not just identical
#      tuples),
#   2) among the physically distinct domes, pick the ones that
#      maximize the minimum mutual distance, accounting for
#      the fact that the relative orientation of two domes is
#      never known in advance.

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
    # Rotate the dome by k branches (k in 0, 1, 2).

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
    # Binary vector: 1 if the face carries a marker.

    middle, bottom = config
    return tuple(1 if v == "x" else 0 for v in middle + bottom)


def canonical(config):
    # Unique representative of a dome's rotation orbit.

    return min(rotate(config, k) for k in range(3))


def hamming(a, b):
    return sum(x != y for x, y in zip(a, b))


def orientation_free_distance(config_a, config_b):
    # Difference between 2 domes, accounting for the fact that
    # their relative orientation isn't known in advance: use
    # whichever rotation brings them closest together, i.e. the
    # worst-case mix-up between the two.

    va = marked_vector(config_a)

    return min(
        hamming(va, marked_vector(rotate(config_b, k)))
        for k in range(3)
    )


# ==============================
# Picking the domes that differ
# the most from each other
# ==============================

def min_pairwise_distance(indices, dist):
    return min(dist[i][j] for i, j in combinations(indices, 2))


def rank_by_diversity(indices, dist):
    # Ranks the given domes (indices into distinct_configs,
    # already sorted alphabetically) from most to least "worth
    # keeping", via greedy farthest-point insertion (always add
    # the dome with the largest minimum distance to the ones
    # already picked). Unlike a selection optimized for one
    # specific NB_DOMES (with local swaps), this order doesn't
    # depend on the final count requested: taking the first N of
    # this ranking for N=10 gives exactly the same domes as the
    # first 10 of a ranking for N=20. That's what keeps the
    # output consistent when -n changes.
    #
    # No randomness: on a distance tie, the alphabetically first
    # dome (smallest index) always wins, making the result fully
    # deterministic and reproducible.

    ordered = sorted(indices)

    if len(ordered) <= 1:
        return ordered

    # Seed: the farthest pair
    i0, j0 = max(combinations(ordered, 2), key=lambda p: dist[p[0]][p[1]])
    order = [i0, j0]

    # Greedy growth: at each step, add the dome that maximizes
    # its minimum distance to the domes already ranked
    while len(order) < len(ordered):
        remaining = [i for i in ordered if i not in order]
        next_index = max(
            remaining,
            key=lambda i: min(dist[i][s] for s in order)
        )
        order.append(next_index)

    return order


# ==============================
# Display format
# ==============================

def format_dome(config):

    middle, bottom = config

    middle_text = f"{middle[0]}-p-{middle[1]}-p-{middle[2]}-p"
    bottom_text = "-".join(bottom)

    return middle_text, bottom_text


# ==============================
# Real dome geometry (SVG)
# ==============================
# The dome is a truncated icosahedron (soccer ball) cut in half
# by a plane perpendicular to an axis through 2 opposite
# hexagons. We compute its real 3D coordinates, keep the upper
# half (16 faces: 1 apex + 6 middle + 9 bottom) and project it
# flat, viewed from above. Faces genuinely share their edges
# (real tessellation, not an approximation), and the apex, a
# middle hexagon and its bottom pentagon are always aligned in
# a straight line at 12 o'clock (an exact geometric property of
# the solid, verified analytically).

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


def _build_truncated_icosahedron():
    # Exact truncation: each triangle -> hexagon, each vertex -> pentagon.

    faces = {}

    for idx, (a, b, c) in enumerate(_ICOSA_FACES):
        A, B, C = _ICOSA_VERTICES[a], _ICOSA_VERTICES[b], _ICOSA_VERTICES[c]
        points = [
            lerp(A, B, 1 / 3), lerp(A, B, 2 / 3),
            lerp(B, C, 1 / 3), lerp(B, C, 2 / 3),
            lerp(C, A, 1 / 3), lerp(C, A, 2 / 3),
        ]
        centroid = normalize(tuple(sum(p[k] for p in points) / 6 for k in range(3)))
        faces[("h", idx)] = {"points": points, "centroid": centroid, "kind": "hex"}

    for vi in range(12):
        V = _ICOSA_VERTICES[vi]
        neighbors = {
            x
            for face in _ICOSA_FACES if vi in face
            for x in face if x != vi
        }

        v_dir = normalize(V)
        ref = (1, 0, 0) if abs(v_dir[0]) < 0.9 else (0, 1, 0)
        u = normalize(cross(v_dir, ref))
        w = cross(v_dir, u)

        by_angle = []
        for ni in neighbors:
            point = lerp(V, _ICOSA_VERTICES[ni], 1 / 3)
            rel = sub(point, V)
            angle = math.atan2(dot(rel, w), dot(rel, u))
            by_angle.append((angle, point))
        by_angle.sort(key=lambda t: t[0])

        points = [p for _, p in by_angle]
        centroid = normalize(tuple(sum(p[k] for p in points) / 5 for k in range(3)))
        faces[("p", vi)] = {"points": points, "centroid": centroid, "kind": "pent"}

    return faces


def _resolve_dome_geometry():
    # Picks a hexagon face as the apex, extracts the 16 faces of
    # the hemisphere (apex + middle + bottom), and maps each
    # index of our data structures (middle[i], bottom[i]) to its
    # real geometric face, oriented so that a middle hexagon
    # (and its bottom pentagon) is always at 12 o'clock.

    faces = _build_truncated_icosahedron()

    apex_id = ("h", 0)
    pole = faces[apex_id]["centroid"]

    ranked = sorted(faces, key=lambda fid: -dot(faces[fid]["centroid"], pole))
    hemisphere = set(ranked[:16])

    middle = {
        fid for fid in hemisphere
        if fid != apex_id and shared_edge(faces[apex_id]["points"], faces[fid]["points"])
    }
    bottom = hemisphere - {apex_id} - middle
    middle_hexagons = sorted(fid for fid in middle if fid[0] == "h")

    ref = (1, 0, 0) if abs(pole[0]) < 0.9 else (0, 1, 0)
    u = normalize(cross(pole, ref))
    w = cross(pole, u)

    def raw_angle(fid):
        centroid = faces[fid]["centroid"]
        rel = sub(centroid, scale(pole, dot(centroid, pole)))
        return math.atan2(dot(rel, w), dot(rel, u))

    theta0 = raw_angle(middle_hexagons[0])

    def rel_angle(fid):
        angle = (raw_angle(fid) - theta0) % (2 * math.pi)
        return 0.0 if angle > 2 * math.pi - 1e-6 else angle

    middle_order = sorted(middle, key=rel_angle)

    # A purely angular sort directly gives p-h-h-p-h-h-p-h-h in
    # true clockwise reading (verified: each group's pentagon is
    # exactly aligned with its corresponding middle hexagon).
    # Grouping instead by real adjacency to the middle hexagon
    # would give an h-p-h order (the pentagon sits between its 2
    # neighboring hexagons, not followed by them): that would
    # shift the text out of sync with the rendered image.
    bottom_order = sorted(bottom, key=rel_angle)

    def project(point, scale_factor):
        return project_to_plane(point, pole, u, w, rotation=theta0, scale_factor=scale_factor)

    slots: dict = {"apex": apex_id}
    for j, fid in enumerate(middle_order):
        slots[("middle", j)] = fid
    for j, fid in enumerate(bottom_order):
        slots[("bottom", j)] = fid

    # Azimuth (degrees, 0 = 12 o'clock, clockwise) of each slot,
    # excluding the apex which has no meaningful azimuth (it
    # sits at the pole). Reused to evaluate marker spread.
    slot_azimuth = {
        key: math.degrees(rel_angle(fid))
        for key, fid in slots.items()
        if key != "apex"
    }

    return faces, slots, project, slot_azimuth


_DOME_FACES, _DOME_SLOTS, _project, _SLOT_AZIMUTH = _resolve_dome_geometry()


def marked_slots(config):
    # Slot -> marker present or not, for this dome.

    middle, bottom = config

    marks: dict = {"apex": True}
    middle_ring = [middle[0], "p", middle[1], "p", middle[2], "p"]
    for j, value in enumerate(middle_ring):
        marks[("middle", j)] = value == "x"
    for j, value in enumerate(bottom):
        marks[("bottom", j)] = value == "x"

    return marks


def coverage_score(config):
    # Largest angular gap (degrees, around the pole) between 2
    # consecutive markers, excluding the apex (always marked,
    # with no meaningful azimuth since it sits at the pole). A
    # large gap means a side viewing angle with no marker
    # visible at all. The smaller the value, the more evenly the
    # markers are spread around the dome.

    marks = marked_slots(config)
    azimuths = sorted(
        _SLOT_AZIMUTH[slot] for slot, marked in marks.items()
        if marked and slot != "apex"
    )

    count = len(azimuths)
    gaps = (
        (azimuths[(i + 1) % count] - azimuths[i]) % 360
        for i in range(count)
    )
    return max(gaps)


def dome_svg(config, cx, cy, scale_factor=90):
    marks = marked_slots(config)

    parts = []

    for slot, face_id in _DOME_SLOTS.items():
        face = _DOME_FACES[face_id]

        projected = [_project(p, scale_factor) for p in face["points"]]
        points = " ".join(f"{cx + x:.1f},{cy + y:.1f}" for x, y in projected)
        parts.append(f'<polygon points="{points}" fill="white" stroke="black" stroke-width="1.5" />')

        if marks[slot]:
            # Disc center = average of the polygon's already
            # projected points (not the 3D centroid, which is
            # normalized onto the unit sphere and therefore at a
            # different scale than the polygon's own points,
            # which used to push the disc off the face).
            px = sum(x for x, _ in projected) / len(projected)
            py = sum(y for _, y in projected) / len(projected)
            parts.append(f'<circle cx="{cx + px:.1f}" cy="{cy + py:.1f}" r="7" fill="black" />')

    return "\n".join(parts)


def build_domes_svg(domes, path):
    cols = 5
    cell_w, cell_h = 340, 380
    center_y_local = 190

    rows = -(-len(domes) // cols)  # ceiling division
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
            f'font-size="16">Dome {index + 1}</text>'
        )
        svg_parts.append(dome_svg(dome, cx, cy))

    svg_parts.append("</svg>")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))


# ==============================
# Generation
# ==============================

all_configs = generate_all_configs()
distinct_configs = sorted({canonical(c) for c in all_configs})

if NB_DOMES is None:
    NB_DOMES = len(distinct_configs)
elif NB_DOMES > len(distinct_configs):
    raise ValueError(
        f"NB_DOMES={NB_DOMES} exceeds the number of physically "
        f"distinct domes ({len(distinct_configs)})."
    )

n = len(distinct_configs)
dist = [
    [
        orientation_free_distance(distinct_configs[i], distinct_configs[j])
        for j in range(n)
    ]
    for i in range(n)
]

# Final sort: first by coverage tier, then by distance within a
# tier, then alphabetically as a last resort (see the comment at
# the top of the file).
coverage = [round(coverage_score(cfg), 6) for cfg in distinct_configs]

tiers: list = []
for i in sorted(range(n), key=lambda i: (coverage[i], i)):
    if tiers and coverage[tiers[-1][-1]] == coverage[i]:
        tiers[-1].append(i)
    else:
        tiers.append([i])

diversity_order = []
for tier in tiers:
    diversity_order += rank_by_diversity(tier, dist)

selected_indices = diversity_order[:NB_DOMES]
domes = [distinct_configs[i] for i in selected_indices]


# ==============================
# Final display
# ==============================

print(
    f"{len(all_configs)} valid configurations, "
    f"{len(distinct_configs)} physically distinct domes "
    f"(rotational symmetry)."
)
print(
    f"Guaranteed minimum distance across the {NB_DOMES} chosen "
    f"domes: {min_pairwise_distance(selected_indices, dist)} faces."
)
print()

for number, dome in enumerate(domes, 1):

    middle, bottom = format_dome(dome)

    print(f"Dome {number}")
    print(middle)
    print(bottom)
    print()


# ==============================
# Distance matrix
# ==============================
# Distance = number of faces whose marked state differs, in the
# worst-case relative alignment (see orientation_free_distance).
# The higher, the less likely the two domes are to be confused.

header = "     " + "".join(f"{j + 1:>4}" for j in range(NB_DOMES))
print(header)

for row, i in enumerate(selected_indices, 1):
    cells = "".join(
        f"{dist[i][k]:>4}" if row != col + 1 else "   ."
        for col, k in enumerate(selected_indices)
    )
    print(f"{row:>4} {cells}")


# ==============================
# Graphical export
# ==============================

svg_path = "domes.svg"
build_domes_svg(domes, svg_path)

print()
print(f"Graphical representation: {svg_path}")
