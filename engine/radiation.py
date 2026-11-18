"""Incident radiation on the glazing grid with parametric shading.

Model per hour h and point p:
    I = (DNI*cos(theta) + circumsolar) * V_sun(p,h)      # beam + circumsolar
      + (isotropic + horizon)          * SVF_ratio(p)    # sky diffuse
      + albedo*GHI*0.5                 * GVF_ratio(p)    # ground reflected
V_sun: sun ray blocked or not by any shading rectangle.
SVF/GVF here are diffuse shading coefficients (unobstructed = 1): cosine &
solid-angle weighted Tregenza visibility relative to the clear façade.
Absolute sky view factor for tilt β is that ratio × (1+cos β)/2.
"""
import numpy as np

from .geometry import to_local


def tregenza_patches():
    bands = [(6, 30), (18, 30), (30, 24), (42, 24), (54, 18), (66, 12), (78, 6)]
    dirs, sa = [], []
    for alt, n in bands:
        a = np.deg2rad(alt)
        omega = 2 * np.pi * (np.sin(a + np.deg2rad(6)) - np.sin(a - np.deg2rad(6))) / n
        for j in range(n):
            az = 2 * np.pi * (j + 0.5) / n
            dirs.append([np.cos(a) * np.sin(az), np.cos(a) * np.cos(az), np.sin(a)])
            sa.append(omega)
    dirs.append([0, 0, 1]); sa.append(2 * np.pi * (1 - np.sin(np.deg2rad(84))))
    return np.array(dirs), np.array(sa)


def blocked(points, dirs, quads, chunk=2048):
    """Boolean (N_points, N_dirs): True where a ray hits any rectangle."""
    N, M = len(points), len(dirs)
    out = np.zeros((N, M), dtype=bool)
    if not quads or M == 0:
        return out
    P = points.astype(np.float64)
    for q in quads:
        O, u, v = (np.asarray(q[k], float) for k in ("O", "u", "v"))
        w = np.cross(u, v)
        uu, vv = u @ u, v @ v
        if uu < 1e-12 or vv < 1e-12:
            continue
        num = (O - P) @ w               # (N,)
        Pu, Pv = (P - O) @ u, (P - O) @ v
        for s in range(0, M, chunk):
            D = dirs[s:s + chunk]
            den = D @ w                  # (m,)
            with np.errstate(divide="ignore", invalid="ignore"):
                t = num[:, None] / den[None, :]
                a = (Pu[:, None] + t * (D @ u)[None, :]) / uu
                b = (Pv[:, None] + t * (D @ v)[None, :]) / vv
            hit = (t > 1e-6) & (a >= 0) & (a <= 1) & (b >= 0) & (b <= 1)
            out[:, s:s + chunk] |= hit
    return out


def compute(scene, comps, facade_az):
    pts, quads = scene["points"], scene["quads"]
    n = np.array([0.0, 1.0, 0.0])  # local normal

    # --- beam ---
    sun_local = to_local(comps["sun_vec"], facade_az)
    cos_t = np.clip(sun_local @ n, 0, None)
    beam = comps["dni"] * cos_t + comps["circ"]            # (H,)
    front = cos_t > 0
    vis_sun = np.ones((len(pts), len(beam)))
    if front.any():
        vis_sun[:, front] = ~blocked(pts, sun_local[front], quads)
    vis_sun[:, ~front] = 1.0  # beam is ~0 anyway (circumsolar handled by Perez)

    # --- sky + ground view ratios ---
    pdirs, sa = tregenza_patches()
    sky_local = to_local(pdirs, facade_az)
    w_sky = sa * np.clip(sky_local @ n, 0, None)
    gnd_local = sky_local * np.array([1, 1, -1])
    w_gnd = sa * np.clip(gnd_local @ n, 0, None)
    svf = 1 - (blocked(pts, sky_local, quads) * w_sky).sum(1) / w_sky.sum()
    gvf = 1 - (blocked(pts, gnd_local, quads) * w_gnd).sum(1) / w_gnd.sum()

    # --- integrate ---
    shaded = (vis_sun @ beam + svf * comps["iso"].sum() + gvf * comps["ground"].sum()) / 1000
    unshaded = np.full(len(pts), (beam.sum() + comps["iso"].sum() + comps["ground"].sum()) / 1000)

    hourly_shaded = beam * vis_sun.mean(0) + comps["iso"] * svf.mean() + comps["ground"] * gvf.mean()
    hourly_unshaded = beam + comps["iso"] + comps["ground"]

    months = np.arange(1, 13)
    m = comps["month"]
    monthly_s = np.array([hourly_shaded[m == k].sum() for k in months]) / 1000
    monthly_u = np.array([hourly_unshaded[m == k].sum() for k in months]) / 1000

    return {
        "shaded": shaded, "unshaded": unshaded, "svf": svf, "gvf": gvf,
        "hours": comps["hours"], "hourly_shaded": hourly_shaded,
        "hourly_unshaded": hourly_unshaded,
        "monthly_shaded": monthly_s, "monthly_unshaded": monthly_u,
        "beam_share": beam.sum() / max(hourly_unshaded.sum(), 1e-9),
    }
