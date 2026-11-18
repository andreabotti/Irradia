"""Climate handling: EPW parsing (ladybug), sun positions (ladybug Sunpath),
analysis periods (ladybug AnalysisPeriod) and Perez sky decomposition (pvlib)."""
import io
import os
import tempfile
import zipfile

import numpy as np
import pvlib
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.epw import EPW
from ladybug.location import Location
from ladybug.sunpath import Sunpath


def load_epw_bytes(data: bytes) -> dict:
    """Parse EPW (or a .zip containing one) into plain arrays (cache-friendly)."""
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".epw")]
            if not names:
                raise ValueError("The zip file does not contain an .epw file.")
            data = z.read(names[0])
    fd, path = tempfile.mkstemp(suffix=".epw")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    try:
        epw = EPW(path)
        dni = np.array(epw.direct_normal_radiation.values, dtype=float)
        dhi = np.array(epw.diffuse_horizontal_radiation.values, dtype=float)
        ghi = np.array(epw.global_horizontal_radiation.values, dtype=float)
        loc = epw.location
    finally:
        os.remove(path)
    if len(dni) != 8760:  # leap-year EPWs: drop 29 Feb (hours 1416-1439)
        keep = np.r_[0:1416, 1440:len(dni)]
        dni, dhi, ghi = dni[keep], dhi[keep], ghi[keep]
    return {
        "city": loc.city, "country": loc.country,
        "latitude": loc.latitude, "longitude": loc.longitude,
        "time_zone": loc.time_zone, "elevation": loc.elevation,
        "dni": dni, "dhi": dhi, "ghi": ghi,
    }


def sun_positions(clim: dict) -> dict:
    """Sun altitude/azimuth/vector-to-sun for every hour (mid-hour), world XYZ
    (x = east, y = north, z = up)."""
    loc = Location(clim["city"], "", clim["country"], clim["latitude"],
                   clim["longitude"], clim["time_zone"], clim["elevation"])
    sp = Sunpath.from_location(loc)
    alt = np.empty(8760); azi = np.empty(8760); vec = np.empty((8760, 3))
    for h in range(8760):
        s = sp.calculate_sun_from_hoy(h + 0.5)
        alt[h], azi[h] = s.altitude, s.azimuth
        v = s.sun_vector_reversed
        vec[h] = (v.x, v.y, v.z)
    return {"alt": alt, "azi": azi, "vec": vec}


def period_hours(st_month, st_day, st_hour, end_month, end_day, end_hour) -> np.ndarray:
    ap = AnalysisPeriod(st_month, st_day, st_hour, end_month, end_day, end_hour)
    return np.array([int(h) for h in ap.hoys]) % 8760


def sky_components(clim, sun, hours, facade_az, albedo):
    """Per-hour irradiance components on an unobstructed vertical surface.
    Returns only hours with the sun above the horizon (night diffuse ignored)."""
    hours = np.asarray(hours)
    hours = hours[sun["alt"][hours] > 0.5]
    zen = np.clip(90.0 - sun["alt"][hours], 0, 89.5)
    azi = sun["azi"][hours]
    dni, dhi, ghi = clim["dni"][hours], clim["dhi"][hours], clim["ghi"][hours]
    doy = hours // 24 + 1
    dni_extra = pvlib.irradiance.get_extra_radiation(doy)
    am = pvlib.atmosphere.get_relative_airmass(zen)
    comp = pvlib.irradiance.perez(90.0, facade_az, dhi, dni, np.asarray(dni_extra),
                                  zen, azi, np.asarray(am), return_components=True)
    def _get(key):  # pvlib >=0.11 prefixes keys with "poa_"
        return np.asarray(comp[f"poa_{key}"] if f"poa_{key}" in comp else comp[key], dtype=float)
    circ = np.nan_to_num(_get("circumsolar"))
    iso = np.nan_to_num(_get("isotropic") + _get("horizon"))
    iso = np.clip(iso, 0, None)
    ground = albedo * ghi * 0.5  # vertical surface view factor to ground = 0.5
    cum_days = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    month = np.searchsorted(cum_days, hours // 24, side="right")  # 1..12
    return {
        "hours": hours, "month": month, "dni": dni,
        "circ": circ, "iso": iso, "ground": ground,
        "sun_vec": sun["vec"][hours],
    }
