"""Parametric facade + shading geometry.

Local facade frame (metres):
    x = along the facade (to the right when seen from outside)
    y = outward normal
    z = up
Every shading element is a thin rectangle: origin O plus edge vectors u, v.
"""
import numpy as np


def _rad(a):
    return np.deg2rad(a)


def facade_frame(azimuth_deg):
    """Tangent and normal of the facade in world XYZ (x=E, y=N, z=up)."""
    a = _rad(azimuth_deg)
    n = np.array([np.sin(a), np.cos(a), 0.0])
    t = np.array([-np.cos(a), np.sin(a), 0.0])
    return t, n


def to_local(vecs, azimuth_deg):
    t, n = facade_frame(azimuth_deg)
    vecs = np.atleast_2d(vecs)
    return np.stack([vecs @ t, vecs @ n, vecs[:, 2]], axis=1)


def _range(start, end, spacing):
    if spacing <= 0 or end < start:
        return np.array([start])
    return np.arange(start, end + 1e-9, spacing)


def build_scene(p: dict) -> dict:
    W, H = p["facade_width"], p["facade_height"]
    win = {
        "x0": p["win_margin"], "x1": W - p["win_margin"],
        "z0": p["win_sill"], "z1": p["win_head"],
    }
    quads = []  # dicts: O, u, v, kind

    # Horizontal louvres (an overhang is a single louvre)
    hl = p["louvres"]
    if hl["on"]:
        th = _rad(hl["tilt"])
        for z in _range(hl["z_start"], hl["z_end"], hl["spacing"]):
            quads.append({
                "O": [win["x0"] - hl["ext"], hl["offset"], z],
                "u": [win["x1"] - win["x0"] + 2 * hl["ext"], 0, 0],
                "v": [0, hl["depth"] * np.cos(th), -hl["depth"] * np.sin(th)],
                "kind": "louvre"})

    oh = p["overhang"]
    if oh["on"]:
        th = _rad(oh["tilt"])
        z = win["z1"] + oh["gap"]
        quads.append({
            "O": [win["x0"] - oh["ext"], oh["offset"], z],
            "u": [win["x1"] - win["x0"] + 2 * oh["ext"], 0, 0],
            "v": [0, oh["depth"] * np.cos(th), -oh["depth"] * np.sin(th)],
            "kind": "overhang"})

    vf = p["fins"]
    if vf["on"]:
        ph = _rad(vf["angle"])
        z0, z1 = win["z0"] - vf["ext_bottom"], win["z1"] + vf["ext_top"]
        for x in _range(vf["x_start"], vf["x_end"], vf["spacing"]):
            quads.append({
                "O": [x, vf["offset"], z0],
                "u": [0, 0, z1 - z0],
                "v": [vf["depth"] * np.sin(ph), vf["depth"] * np.cos(ph), 0],
                "kind": "fin"})

    # Analysis grid on the glazing
    g = p["grid"]
    nx = max(1, int(round((win["x1"] - win["x0"]) / g)))
    nz = max(1, int(round((win["z1"] - win["z0"]) / g)))
    dx = (win["x1"] - win["x0"]) / nx
    dz = (win["z1"] - win["z0"]) / nz
    xs = win["x0"] + dx * (np.arange(nx) + 0.5)
    zs = win["z0"] + dz * (np.arange(nz) + 0.5)
    X, Z = np.meshgrid(xs, zs)
    pts = np.stack([X.ravel(), np.full(X.size, 1e-3), Z.ravel()], axis=1)

    return {
        "W": W, "H": H, "win": win, "quads": quads,
        "points": pts, "dx": dx, "dz": dz, "nx": nx, "nz": nz,
    }


def scene_to_obj(scene) -> str:
    """Wavefront OBJ of wall, glazing and shading (local frame, Z up)."""
    lines, vi = ["# facade-radiation export, local frame: x along, y out, z up"], 1

    def rect(O, u, v, name):
        nonlocal vi
        O, u, v = map(np.asarray, (O, u, v))
        for c in (O, O + u, O + u + v, O + v):
            lines.append("v %.4f %.4f %.4f" % tuple(c))
        lines.append(f"o {name}")
        lines.append(f"f {vi} {vi+1} {vi+2} {vi+3}")
        vi += 4

    w = scene["win"]
    rect([0, 0, 0], [scene["W"], 0, 0], [0, 0, scene["H"]], "wall")
    rect([w["x0"], 0.001, w["z0"]], [w["x1"] - w["x0"], 0, 0], [0, 0, w["z1"] - w["z0"]], "glazing")
    for i, q in enumerate(scene["quads"]):
        rect(q["O"], q["u"], q["v"], f"{q['kind']}_{i}")
    return "\n".join(lines)
