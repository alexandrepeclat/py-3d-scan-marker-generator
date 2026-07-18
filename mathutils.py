# ============================================================
# Generic 3D vector and polyhedron-projection helpers.
# ============================================================
# Not tied to any specific solid: reusable for building and
# projecting any polyhedron (truncated icosahedron, other
# Platonic/Archimedean solids, etc.), not just the dome.
#
# Vectors are plain (x, y, z) tuples.

import math


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def lerp(a, b, t):
    return add(a, scale(sub(b, a), t))


def normalize(a):
    length = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    return (a[0] / length, a[1] / length, a[2] / length)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def shared_edge(points_a, points_b, precision=4):
    # Two faces share an edge if at least 2 of their vertices coincide
    # (within floating-point precision).
    def key(p):
        return tuple(round(c, precision) for c in p)

    set_a = {key(p) for p in points_a}
    set_b = {key(p) for p in points_b}
    return len(set_a & set_b) >= 2


def project_to_plane(point, pole, u, w, rotation=0.0, scale_factor=1.0):
    # Orthographic projection of `point` onto the plane perpendicular to
    # `pole`, using (u, w) as the in-plane basis, then rotated by
    # `rotation` radians so that angle 0 lands at the top of the screen
    # and increasing angle reads clockwise (screen y grows downward).
    rel = sub(point, scale(pole, dot(point, pole)))
    a = dot(rel, u)
    b = dot(rel, w)
    a2 = a * math.cos(rotation) + b * math.sin(rotation)
    b2 = -a * math.sin(rotation) + b * math.cos(rotation)
    return (b2 * scale_factor, -a2 * scale_factor)
