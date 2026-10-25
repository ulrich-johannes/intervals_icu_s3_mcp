# Workout & training data analysis — reference

**Authority:** the single-session analysis protocol (sources per metric, thresholds, decoupling qualification, Metrics line, FTP-update rule) lives in **SKILL.md → Workout & training data analysis**. This file adds file parsing, metric definitions, technique and climbing notes, and the multi-week review. Where anything here seems to differ from SKILL.md, SKILL.md wins. Fix this file rather than following the difference.

---

## Sources you'll see

### intervals.icu (preferred for anything synced)

Use the tools named in SKILL.md's source table. Don't re-derive what they already return. Dashboard pastes/screenshots typically contain CTL/ATL/TSB, weekly TSS, eFTP, power curve, activity list and zone distribution. Treat pasted numbers as the athlete's view and cross-check against the tools when it matters.

### Ride files (FIT / GPX / TCX / CSV) not in intervals.icu

- **FIT**: the gold standard (power, HR, cadence, GPS, altitude, temperature). `scripts/ride_metrics.py` reads it directly via `fitdecode`.
- **TCX**: XML with power/HR/cadence/GPS. Parse with `lxml` or `xml.etree`.
- **GPX**: GPS first; extensions may hold HR/cadence/power. Often no power at all.
- **CSV**: platform-specific, usually one row per sample.

### Pasted descriptions

Take them at face value. Ask for power numbers only if they're missing and matter to the question.

---

## Parsing ride files

Install `fitdecode` (it installs as a wheel). `fitparse` frequently fails to build in this environment. If it's really needed, install it with `SETUPTOOLS_USE_DISTUTILS=stdlib pip install fitparse --break-system-packages`.

```bash
pip install fitdecode --break-system-packages
python3 scripts/ride_metrics.py ride.fit --ftp <FTP> --weight <kg> [--indoor] [--temp <°C>]
```

For GPX/TCX/CSV: resample to 1 Hz (power gaps → 0, HR gaps → NaN), then `from ride_metrics import ride_metrics` and pass the arrays.

```python
import gpxpy
with open('ride.gpx') as f:
    gpx = gpxpy.parse(f)
for track in gpx.tracks:
    for seg in track.segments:
        for pt in seg.points:
            # pt.time, pt.elevation; HR/cadence/power live in pt.extensions (TrackPointExtension)
            pass
# TCX: xml.etree.ElementTree with namespace http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2
```

Never dump raw streams into the conversation, and never compute metrics by reading them.

---

## Metric definitions (what the script and the tools compute)

| Metric | Definition |
|---|---|
| NP | 4th root of the mean of (30-s rolling average power)⁴ |
| IF | NP / FTP |
| TSS | duration_s × NP × IF / (FTP × 3600) × 100 |
| VI | NP / average power |
| kJ | Σ power (W·s) / 1000. ≈ kcal expended at ~24 % gross efficiency, so a useful energy check |
| EF | NP / average HR |
| Pw:HR decoupling | (EF₁ − EF₂) / EF₁ × 100, where EF per half = avg power / avg HR. Reported only for qualifying rides (SKILL.md) |
| HR creep (interval sets) | avg HR of last rep − avg HR of first rep at similar settled power, in bpm |
| Elevation gain | sum of positive altitude deltas after 3–5-sample smoothing (GPS noise) |
| VAM | vertical metres climbed per hour on a climb segment |

There is **one** HR-drift concept for steady rides (decoupling) and **one** for interval sets (HR creep). Don't introduce a third ("HR at constant power +5 %" etc.).

---

## Technique observations

With cadence data:
- Note cadence by zone. Self-selected cadence is individual. Flag changes versus the athlete's own norm more than deviations from a textbook number.
- Z4/Z5 work below ~75 rpm when not deliberately prescribed (force intervals) usually means grinding. It shifts load to the muscles and speeds up local fatigue.
- Climbs below ~65–70 rpm at threshold suggest over-gearing. Check gearing in `athlete_profile` → Equipment before calling it a technique fault.

With GPS on known climbs: this connector has no dedicated climb-segment/VAM tool. If elevation and power streams are both present (`icu_get_activity_streams`), average power and climb duration for that stretch can still be read directly and compared against the athlete's own previous efforts on the same climb — don't compute a VAM figure yourself from altitude deltas in context, and don't fall back to generic category benchmarks (e.g. "3.5–4.0 W/kg ≈ Cat 3") either; they're too coarse to be useful for one athlete.

---

## Multi-week / dashboard review

When the athlete shares a dashboard or asks "how am I doing":

1. **CTL trajectory and ramp**: classify with the ramp table in SKILL.md → Load management (one definition, used everywhere).
2. **TSB pattern**: does it cycle (build → recover → build) or sit chronically below −20 (red flag)?
3. **eFTP trajectory**: flat eFTP across a build block means volume without enough stimulus, or the wrong stimulus for the limiter (re-run the diagnosis in `references/ftp-training.md`).
4. **Intensity distribution by time in zone**: compare with the block's stated model (pyramidal or polarised, `references/ftp-training.md`). Flag grey-zone drift.
5. **Weekly consistency**: planned vs actual TSS/hours in `training_plan`'s ledger. Bumpy weeks build less fitness than steady ones.
6. **Durability trend**: not available with this connector — `icu_get_power_curves` has no fatigue/kJ parameter. Skip this item rather than estimating it.
7. **EF trend**: median EF of qualifying rides from the Metrics lines in `short_term_history`, indoor and outdoor separately. Only call a trend with ≥ 3 data points per setting.
8. **Time to A-race vs CTL plan**: check target events in `athlete_profile`. Where should CTL peak relative to those dates, and where is it now?

---

## Common patterns and what they mean

- **TSB < −20 for > 2 weeks without a recovery week** → likely overreaching. Insert a recovery week.
- **TSB > +10 during a build block** → under-loading. Build potential is being lost.
- **CTL flat despite lots of riding** → too easy (no stimulus), or intensity isn't captured (HR-only rides, missing power).
- **5-min power / FTP ≥ ~1.25 and 20–60-min PBs lagging** → big ceiling, low utilisation. Shift emphasis toward heavy-domain work while keeping HIT (`references/ftp-training.md`).
- **5-min power / FTP ≤ ~1.15** → FTP is pressing against the ceiling. Shift emphasis to HIT (both quality slots).
- **Fewer than ~1 HIT session/week over the last 4–6 weeks** → the most likely reason for a flat eFTP. Restore HIT before diagnosing anything subtler.
- **20-min power up ≥ 5 W vs the 60-day best, from a genuine effort** → probable FTP rise. Propose an update per SKILL.md (athlete confirms).
- **Decoupling > 5 % on a qualifying long Z2 ride** → first check heat, indoor cooling and fueling (carbs/h vs the SKILL.md table). Only when those are clean and it repeats across ≥ 2–3 rides, read it as limited aerobic durability.
- **Strong climbs relative to FTP** (long climbs at or near FTP late in rides) → good fatigue resistance. Confirm against a few comparable climbs over time rather than inferring from one — there's no durability-curve tool on this connector to cross-check against.
- **VI > 1.10 on a supposed steady ride** → surging. Work on pacing discipline, especially early in group rides.
- **Settled power fading across VO2 reps and HR not rising** → likely fatigue (HR suppression). Check the readiness verdict before blaming the prescription.

---

## When the data quality is poor

- **GPS only (no power, no HR)**: distance, elevation and speed only. Say so and ask for a power file. Don't fake TSS from speed and elevation.
- **Optical HR**: EF and decoupling are unreliable. Report them with a caveat or as `–`, and note `hr_src=optical` in the Metrics line.
- **Fragmented files / autopause artefacts**: skip NP, decoupling and drift. They need continuous streams.
- **Power dropouts or implausible spikes** (single-second values far above the athlete's 5-s best): flag them. Exclude from best-effort claims.
