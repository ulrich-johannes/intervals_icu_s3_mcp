"""Canonical ride metrics for the cycling-coach skill.

Use ONLY for uploaded ride files that are not in intervals.icu. For synced rides,
intervals.icu tools are the authoritative source (see SKILL.md).

Do not edit per session. Same 1-Hz inputs -> same outputs, always.
If a definition needs to change, change it here once and note it in SKILL.md.

Usage:
    python3 ride_metrics.py ride.fit --ftp 260 [--weight 72] [--indoor] [--temp 21]
or import ride_metrics() and pass 1-Hz lists/arrays.
"""
import argparse
import json

import numpy as np

ZONE_BOUNDS = [0, .55, .75, .90, 1.05, 1.20, 1.50, 99]   # 7-zone model, % FTP
ZONE_NAMES = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"]
DECOUPLING_MIN_S = 45 * 60      # qualification: >= 45 min
DECOUPLING_MAX_VI = 1.05        # qualification: steady ride only
HR_SPIKE_BPM_PER_S = 15         # larger 1-s jumps are sensor artefacts


def ride_metrics(power, hr, ftp, cadence=None, temp=None, indoor=None, weight=None):
    p = np.nan_to_num(np.asarray(power, float), nan=0.0)
    n = len(p)
    q = {"samples": n, "power_zero_pct": round(float((p == 0).mean() * 100), 1)}

    h = None
    if hr is not None:
        h = np.asarray(hr, float)
        bad = np.isnan(h) | (h < 40) | (h > 220)
        q["hr_dropout_pct"] = round(float(bad.mean() * 100), 1)
        h = np.where(bad, np.nan, h)
        h = np.where(np.abs(np.diff(h, prepend=h[0])) > HR_SPIKE_BPM_PER_S, np.nan, h)

    r30 = np.convolve(p, np.ones(30) / 30, mode="valid") if n >= 30 else p
    NP = float(np.mean(r30 ** 4) ** 0.25)
    avg = float(p.mean())
    IF = NP / ftp
    o = {
        "duration_min": round(n / 60, 1),
        "avg_w": round(avg),
        "np_w": round(NP),
        "if": round(IF, 3),
        "tss": round(n * NP * IF / (ftp * 3600) * 100, 1),
        "vi": round(NP / avg, 3) if avg else None,
        "kj": round(p.sum() / 1000),
    }
    if weight:
        o["np_wkg"] = round(NP / weight, 2)

    o["zones_min"] = {
        z: round(float(((p >= lo * ftp) & (p < hi * ftp)).sum()) / 60, 1)
        for z, lo, hi in zip(ZONE_NAMES, ZONE_BOUNDS, ZONE_BOUNDS[1:])
    }
    o["sweetspot_min"] = round(float(((p >= .88 * ftp) & (p < .94 * ftp)).sum()) / 60, 1)

    if h is not None and np.isfinite(h).sum() > 0.8 * n:
        m = n // 2
        ef = lambda a, z: np.nanmean(p[a:z]) / np.nanmean(h[a:z])
        e1, e2 = ef(0, m), ef(m, n)
        o["ef"] = round(float(NP / np.nanmean(h)), 3)
        o["decoupling_pct"] = round(float((e1 - e2) / e1 * 100), 1)
        o["decoupling_qualifies"] = bool(o["vi"] and o["vi"] < DECOUPLING_MAX_VI
                                         and n >= DECOUPLING_MIN_S)
    else:
        o["ef"] = o["decoupling_pct"] = None
        o["decoupling_qualifies"] = False

    if cadence is not None:
        c = np.asarray(cadence, float)
        c = c[c > 0]
        o["avg_cad"] = round(float(np.nanmean(c))) if c.size else None

    o["context"] = {"indoor": indoor, "temp_c": temp}
    o["quality"] = q
    return o


def load_fit_1hz(path):
    """Read a FIT file and resample power/HR/cadence to 1 Hz (gaps: power 0, HR NaN).

    Uses fitdecode (installs as a wheel: pip install fitdecode --break-system-packages).
    Falls back to fitparse, which may need SETUPTOOLS_USE_DISTUTILS=stdlib to install.
    """
    try:
        import fitdecode
        rows = []
        with fitdecode.FitReader(path) as fr:
            for fr_msg in fr:
                if isinstance(fr_msg, fitdecode.FitDataMessage) and fr_msg.name == "record":
                    rows.append({f.name: f.value for f in fr_msg.fields})
    except ImportError:
        from fitparse import FitFile
        rows = [r.get_values() for r in FitFile(path).get_messages("record")]
    rows = [r for r in rows if r.get("timestamp")]
    t0 = rows[0]["timestamp"]
    n = int((rows[-1]["timestamp"] - t0).total_seconds()) + 1
    pw, hr, cad = np.zeros(n), np.full(n, np.nan), np.zeros(n)
    for r in rows:
        i = int((r["timestamp"] - t0).total_seconds())
        pw[i] = r.get("power") or 0
        hr[i] = r.get("heart_rate") if r.get("heart_rate") is not None else np.nan
        cad[i] = r.get("cadence") or 0
    temps = [r["temperature"] for r in rows if r.get("temperature") is not None]
    return pw, hr, cad, (round(float(np.median(temps)), 1) if temps else None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("fit")
    ap.add_argument("--ftp", type=float, required=True)
    ap.add_argument("--weight", type=float)
    ap.add_argument("--indoor", action="store_true")
    ap.add_argument("--temp", type=float)
    a = ap.parse_args()
    pw, hr, cad, t = load_fit_1hz(a.fit)
    print(json.dumps(ride_metrics(pw, hr, a.ftp, cad, a.temp if a.temp is not None else t,
                                  a.indoor, a.weight), indent=1))
