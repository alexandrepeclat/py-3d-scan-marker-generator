# ============================================================
# Reference dodecahedron generator for 3D scanning
# ============================================================
# Same idea as the dome generator (3d-scan-marker-generator-
# dome.py), but for a full regular dodecahedron (12 pentagonal
# faces) instead of half a truncated icosahedron.
#
#
# Structure:
#
# The dodecahedron is shown as 2 separate flat views (top and
# bottom), each showing 1 pole face plus the ring of 5 faces
# around it:
#
#   apex   (1 face, always marked)
#   upper  (5 faces, ring around the apex, shown in the top view)
#   lower  (5 faces, ring around the bottom, shown in the bottom view)
#   bottom (1 face, always marked)
#
# For each ring: start at 12 o'clock, then move clockwise.
#
#
# Symbols:
#
#   p = pentagon face
#   x = face carrying a marker
#
#
# Rule (applied independently to the upper ring and to the
# lower ring):
#
#   each ring carries EITHER
#     - 2 markers, never adjacent, OR
#     - 3 markers, never 3 adjacent in a row
#       (this forces exactly one adjacent pair: a cycle of 5
#       can't fit 3 mutually non-adjacent positions)
#
#
# Example:
#
#             x-p-x-p-p
#
# means: position 0 marked, 1 empty, 2 marked, 3 empty, 4 empty
# (a valid 2-marker, non-adjacent pattern).
#
#
# Two-view convention:
#
# The bottom view shows the object as if physically rotated
# 180° about the horizontal axis running through the apex
# face's own reference vertex (the one placed at 12 o'clock in
# the top view). Checked against a real dodecahedron: with
# this specific axis, the bottom face ends up with the same
# edge orientation as the apex face (not inverted).
#
#
# Choosing which dodecahedra to display:
#
# There are 100 raw (upper, lower) combinations, but only 20
# physically distinct dodecahedra once rotational symmetry is
# removed (a dodecahedron has 5-fold rotational symmetry about
# the apex-bottom axis). Domes are ranked using 4 criteria, in
# this order:
#
#   1. Marker count: most markers first (8, then 7, then 6),
#      for the most visible reference points during a scan.
#
#   2. On a tie: marker coverage, same rationale as the dome
#      generator (see 3d-scan-marker-generator-dome.py) —
#      smallest maximum angular gap between 2 consecutive
#      markers, so no side is left without a visible marker.
#
#   3. Still tied: maximum mutual distance from the other
#      dodecahedra already picked within the same tier, so they
#      look as different from each other as possible.
#
#   4. Still tied: alphabetical order of the generated text, for
#      a fully deterministic result.
#
# ============================================================

import argparse
import math
from itertools import combinations

from mathutils import cross, dot, normalize, project_to_plane, scale, shared_edge, sub


# ==============================
# Parameters
# ==============================

_parser = argparse.ArgumentParser(description="Generate reference dodecahedra for 3D scanning.")
_parser.add_argument(
    "-n", "--nb-domes",
    type=int,
    default=None,
    help="Number of dodecahedra to generate (default: all 20 physically distinct ones).",
)
_args = _parser.parse_args()

NB_DOMES = _args.nb_domes  # resolved to the max once distinct_configs is known


# ==============================
# Generating all valid
# configurations
# ==============================

def _ring_patterns():
    # All valid marking patterns for one ring of 5 faces: either
    # 2 markers with no two adjacent, or 3 markers with no 3 in a
    # row. Returns a list of tuples of marked positions (0-4).

    n = 5

    def is_adjacent(a, b):
        return (a - b) % n in (1, n - 1)

    patterns = []
    for combo in combinations(range(n), 2):
        if not is_adjacent(*combo):
            patterns.append(combo)

    for combo in combinations(range(n), 3):
        marked = set(combo)
        has_run_of_3 = any(all((c + i) % n in marked for i in range(3)) for c in range(n))
        if not has_run_of_3:
            patterns.append(combo)

    return patterns


def generate_all_configs():

    patterns = _ring_patterns()
    configs = []

    for upper_marked in patterns:
        upper = tuple("x" if i in upper_marked else "p" for i in range(5))

        for lower_marked in patterns:
            lower = tuple("x" if i in lower_marked else "p" for i in range(5))
            configs.append((upper, lower))

    return configs


def rotate(config, k):
    # Rotate the dodecahedron by k face-steps (k in 0..4).

    upper, lower = config
    return upper[k:] + upper[:k], lower[k:] + lower[:k]


def marked_vector(config):
    # Binary vector: 1 if the face carries a marker.

    upper, lower = config
    return tuple(1 if v == "x" else 0 for v in upper + lower)


def canonical(config):
    # Unique representative of a dodecahedron's rotation orbit.

    return min(rotate(config, k) for k in range(5))


def hamming(a, b):
    return sum(x != y for x, y in zip(a, b))


def orientation_free_distance(config_a, config_b):
    # Difference between 2 dodecahedra, accounting for the fact
    # that their relative orientation isn't known in advance: use
    # whichever rotation brings them closest together, i.e. the
    # worst-case mix-up between the two.

    va = marked_vector(config_a)

    return min(
        hamming(va, marked_vector(rotate(config_b, k)))
        for k in range(5)
    )


# ==============================
# Picking the domes that differ
# the most from each other
# ==============================

def min_pairwise_distance(indices, dist):
    return min(dist[i][j] for i, j in combinations(indices, 2))


def rank_by_diversity(indices, dist):
    # Ranks the given dodecahedra (indices into distinct_configs,
    # already sorted alphabetically) from most to least "worth
    # keeping", via greedy farthest-point insertion. See
    # 3d-scan-marker-generator-dome.py for the full rationale:
    # same algorithm, no randomness, alphabetically-first wins on
    # a tie, and a prefix of this ranking never changes when more
    # dodecahedra are requested.

    ordered = sorted(indices)

    if len(ordered) <= 1:
        return ordered

    # Seed: the farthest pair
    i0, j0 = max(combinations(ordered, 2), key=lambda p: dist[p[0]][p[1]])
    order = [i0, j0]

    # Greedy growth: at each step, add the dodecahedron that
    # maximizes its minimum distance to the ones already ranked
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

    upper, lower = config
    return "-".join(upper), "-".join(lower)


# ==============================
# Real dodecahedron geometry (SVG)
# ==============================
# The dodecahedron is built as the dual of the icosahedron: each
# icosahedron face becomes a dodecahedron vertex, and each
# icosahedron vertex (5 faces meeting there) becomes a
# dodecahedron pentagon, its 5 vertices angle-sorted around that
# icosahedron vertex's own direction.

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


def _build_dodecahedron():
    dodeca_verts = []
    for (a, b, c) in _ICOSA_FACES:
        A, B, C = _ICOSA_VERTICES[a], _ICOSA_VERTICES[b], _ICOSA_VERTICES[c]
        centroid = normalize(tuple((A[k] + B[k] + C[k]) / 3 for k in range(3)))
        dodeca_verts.append(centroid)

    dodeca_faces = []
    for vi in range(12):
        V = _ICOSA_VERTICES[vi]
        touching = [i for i, f in enumerate(_ICOSA_FACES) if vi in f]

        v_dir = normalize(V)
        ref = (1, 0, 0) if abs(v_dir[0]) < 0.9 else (0, 1, 0)
        u = normalize(cross(v_dir, ref))
        w = cross(v_dir, u)

        def angle(face_i, v_dir=v_dir, u=u, w=w):
            p = dodeca_verts[face_i]
            rel = sub(p, scale(v_dir, dot(p, v_dir)))
            return math.atan2(dot(rel, w), dot(rel, u))

        touching.sort(key=angle)
        dodeca_faces.append(touching)

    return dodeca_verts, dodeca_faces


def _resolve_dome_geometry():
    # Picks a face as apex, finds its antipodal bottom face, the
    # ring of 5 faces adjacent to each, and maps each index of our
    # data structures (upper[i], lower[i]) to its real geometric
    # face. Orientation: the apex's own reference vertex (its
    # first vertex) is placed at 12 o'clock in the top view; the
    # bottom view uses the same horizontal axis, flipped (see
    # header comment).

    dodeca_verts, dodeca_faces = _build_dodecahedron()

    def face_points(face_idx):
        return [dodeca_verts[i] for i in dodeca_faces[face_idx]]

    def face_centroid(face_idx):
        pts = face_points(face_idx)
        return normalize(tuple(sum(p[k] for p in pts) / len(pts) for k in range(3)))

    ranked = sorted(range(12), key=lambda i: -dot(face_centroid(i), face_centroid(0)))
    apex_idx = ranked[0]
    bottom_idx = ranked[-1]
    pole = face_centroid(apex_idx)

    upper = [i for i in ranked[1:6] if shared_edge(face_points(apex_idx), face_points(i))]
    lower = [i for i in ranked[6:11] if shared_edge(face_points(bottom_idx), face_points(i))]
    assert len(upper) == 5 and len(lower) == 5

    ref_vertex = dodeca_verts[dodeca_faces[apex_idx][0]]
    rel0 = sub(ref_vertex, scale(pole, dot(ref_vertex, pole)))
    u = normalize(rel0)
    w = cross(pole, u)
    theta0 = math.atan2(dot(rel0, w), dot(rel0, u))  # 0 by construction, kept for clarity

    def raw_angle(face_idx):
        c = face_centroid(face_idx)
        rel = sub(c, scale(pole, dot(c, pole)))
        return math.atan2(dot(rel, w), dot(rel, u))

    def rel_angle(face_idx):
        a = (raw_angle(face_idx) - theta0) % (2 * math.pi)
        return 0.0 if a > 2 * math.pi - 1e-6 else a

    upper_order = sorted(upper, key=rel_angle)
    lower_order = sorted(lower, key=rel_angle)

    def top_project(point, scale_factor):
        return project_to_plane(point, pole, u, w, rotation=theta0, scale_factor=scale_factor)

    def bottom_project(point, scale_factor):
        w_flipped = tuple(-c for c in w)
        return project_to_plane(point, pole, u, w_flipped, rotation=theta0, scale_factor=scale_factor)

    slots: dict = {"apex": apex_idx, "bottom": bottom_idx}
    for j, fid in enumerate(upper_order):
        slots[("upper", j)] = fid
    for j, fid in enumerate(lower_order):
        slots[("lower", j)] = fid

    # Azimuth (degrees, 0 = 12 o'clock, clockwise) of each ring
    # slot, excluding apex/bottom which have no meaningful azimuth
    # (they sit at the poles). Reused to evaluate marker spread.
    slot_azimuth = {
        key: math.degrees(rel_angle(fid))
        for key, fid in slots.items()
        if key not in ("apex", "bottom")
    }

    face_point_lists = {i: face_points(i) for i in range(12)}

    return face_point_lists, slots, top_project, bottom_project, slot_azimuth


_DOME_FACE_POINTS, _DOME_SLOTS, _top_project, _bottom_project, _SLOT_AZIMUTH = _resolve_dome_geometry()


def marked_slots(config):
    # Slot -> marker present or not, for this dodecahedron.

    upper, lower = config

    marks: dict = {"apex": True, "bottom": True}
    for j, value in enumerate(upper):
        marks[("upper", j)] = value == "x"
    for j, value in enumerate(lower):
        marks[("lower", j)] = value == "x"

    return marks


def coverage_score(config):
    # Largest angular gap (degrees, around the pole) between 2
    # consecutive markers, excluding apex/bottom (always marked,
    # no meaningful azimuth at the poles). A large gap means a
    # side viewing angle with no marker visible at all. The
    # smaller the value, the more evenly the markers are spread
    # around the dodecahedron.

    marks = marked_slots(config)
    azimuths = sorted(
        _SLOT_AZIMUTH[slot] for slot, marked in marks.items()
        if marked and slot not in ("apex", "bottom")
    )

    count = len(azimuths)
    gaps = (
        (azimuths[(i + 1) % count] - azimuths[i]) % 360
        for i in range(count)
    )
    return max(gaps)


def marker_count(config):
    # Total number of markers on the dodecahedron, including the
    # apex and bottom (always marked) and the 2 rings (2 or 3
    # markers each) — ranges from 6 (2+2) to 8 (3+3).

    upper, lower = config
    return 2 + upper.count("x") + lower.count("x")


def _face_svg(face_idx, projector, cx, cy, scale_factor, marked):
    projected = [(cx + x, cy + y) for x, y in (projector(p, scale_factor) for p in _DOME_FACE_POINTS[face_idx])]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in projected)
    svg = f'<polygon points="{points}" fill="white" stroke="black" stroke-width="1.5" />'

    if marked:
        px = sum(x for x, _ in projected) / len(projected)
        py = sum(y for _, y in projected) / len(projected)
        svg += f'\n<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="black" />'

    return svg


def dome_svg(config, cx_top, cx_bottom, cy, scale_factor=80):
    marks = marked_slots(config)
    parts = []

    parts.append(_face_svg(_DOME_SLOTS["apex"], _top_project, cx_top, cy, scale_factor, marks["apex"]))
    for j in range(5):
        key = ("upper", j)
        parts.append(_face_svg(_DOME_SLOTS[key], _top_project, cx_top, cy, scale_factor, marks[key]))

    parts.append(_face_svg(_DOME_SLOTS["bottom"], _bottom_project, cx_bottom, cy, scale_factor, marks["bottom"]))
    for j in range(5):
        key = ("lower", j)
        parts.append(_face_svg(_DOME_SLOTS[key], _bottom_project, cx_bottom, cy, scale_factor, marks[key]))

    return "\n".join(parts)


def build_domes_svg(domes, path):
    cols = 4
    panel_gap = 165
    cell_w, cell_h = 400, 340
    center_y_local = 170

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

        cell_cx = col * cell_w + cell_w / 2
        cy = row * cell_h + center_y_local
        cx_top = cell_cx - panel_gap / 2
        cx_bottom = cell_cx + panel_gap / 2

        svg_parts.append(
            f'<text x="{cell_cx:.1f}" y="{cy - 140:.1f}" text-anchor="middle" '
            f'font-size="16">Dodecahedron {index + 1}</text>'
        )
        svg_parts.append(
            f'<text x="{cx_top:.1f}" y="{cy - 120:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#666">top</text>'
        )
        svg_parts.append(
            f'<text x="{cx_bottom:.1f}" y="{cy - 120:.1f}" text-anchor="middle" '
            f'font-size="11" fill="#666">bottom</text>'
        )
        svg_parts.append(dome_svg(dome, cx_top, cx_bottom, cy))

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
        f"distinct dodecahedra ({len(distinct_configs)})."
    )

n = len(distinct_configs)
dist = [
    [
        orientation_free_distance(distinct_configs[i], distinct_configs[j])
        for j in range(n)
    ]
    for i in range(n)
]

# Final sort: first by marker count (most markers first, for the
# most visible reference points), then by coverage tier, then by
# distance within a tier, then alphabetically as a last resort
# (see the comment at the top of the file).
markers = [marker_count(cfg) for cfg in distinct_configs]
coverage = [round(coverage_score(cfg), 6) for cfg in distinct_configs]
tier_key = [(-markers[i], coverage[i]) for i in range(n)]

tiers: list = []
for i in sorted(range(n), key=lambda i: (tier_key[i], i)):
    if tiers and tier_key[tiers[-1][-1]] == tier_key[i]:
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
    f"{len(distinct_configs)} physically distinct dodecahedra "
    f"(rotational symmetry)."
)
print(
    f"Guaranteed minimum distance across the {NB_DOMES} chosen "
    f"dodecahedra: {min_pairwise_distance(selected_indices, dist)} faces."
)
print()

for number, dome in enumerate(domes, 1):

    upper, lower = format_dome(dome)

    print(f"Dodecahedron {number}")
    print(f"upper: {upper}")
    print(f"lower: {lower}")
    print()


# ==============================
# Distance matrix
# ==============================
# Distance = number of faces whose marked state differs, in the
# worst-case relative alignment (see orientation_free_distance).
# The higher, the less likely the two dodecahedra are to be
# confused.

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

svg_path = "dodecahedra.svg"
build_domes_svg(domes, svg_path)

print()
print(f"Graphical representation: {svg_path}")
