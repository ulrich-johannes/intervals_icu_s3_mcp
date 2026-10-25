# Athlete Profile — template

> Lives in Coach MCP as the variable `athlete_profile`. This is the settled-facts record: things that don't change ride-to-ride. Day-to-day fitness state lives in `short_term_history`; the plan lives in `training_plan`; multi-year narrative lives in `long_term_history`. Read the current version fresh every session — never assume the copy in context is current.

**Last updated:** _(YYYY-MM-DD)_

---

## Athlete basics

- **Name / nickname:**
- **Age:** _(years)_
- **Height:** _(cm)_
- **Current bodyweight:** _(kg, with date — note recent low or trend if relevant, e.g. "78.0 kg (2026-05-15) — recent low 76.7 kg (2026-05-01)")_
- **Sex:** _(relevant for HR zones and recovery norms)_
- **Location:** Munich, DE — rolling/flat home terrain, weekend access to foothills and Alps
- **Years cycling seriously:** _(rough)_
- **Bike(s) raced/trained on:**

## Current performance baseline

- **FTP:** _(W)_ — source: _(TrainerRoad FTP / formal 20-min test / ramp test / threshold session like 3×18 min @ 95–100% / etc.)_, date: _(YYYY-MM-DD)_
  - *Note: intervals.icu eFTP can lag a TR or test FTP, especially after long-duration efforts (60+ min) feed the power curve — the algorithm maps those points conservatively. If both numbers exist, record both and which to trust, and watch for eFTP catching up after the next threshold session.*
- **W/kg at FTP:** _(at current weight; optionally also at race-low weight)_
- **Max HR:** _(bpm — measured peak preferred over 220-age estimate)_
- **Resting HR:** 7-day avg _(bpm)_; 60-day avg _(bpm)_
- **HRV (rMSSD) smoothed:** _(value — track drift vs the baseline at the start of the block; a 3+ point drop sustained over a week is signal)_
- **VO2max estimate:** _(intervals.icu unitless number, or formal mL/kg/min from lab test)_
- **Power profile ratio (5-min power / FTP):** _(value, date — input to the limiter diagnosis in `references/ftp-training.md`)_
- **Durability:** _(fatigued vs fresh 20-min power after the intervals.icu "after kJ" thresholds kj0/kj1 — note the kJ values configured)_
- **FTP change rule:** _new FTP values are written here only after the athlete confirms (SKILL.md → FTP and profile updates)_

### Power curve PBs (last ~90 days)

| Duration | Power (W) | W/kg | Date | Context |
|---|---|---|---|---|
| 5 s | | | | |
| 1 min | | | | |
| 5 min | | | | |
| 20 min | | | | |
| 60 min | | | | |

_Skip rows with no data. Add longer durations (3 h, 4 h) if recent long rides set them. The "Context" column matters — note if a number informs FTP, came from a race, or needs confirmation._

### Training zones (at FTP _XXX_ W — recalculate whenever FTP changes)

| Zone | Power (W) | % FTP | HR (bpm) |
|---|---|---|---|
| Z1 active recovery | | <55% | |
| Z2 endurance | | 56–75% | |
| Z3 tempo | | 76–90% | |
| SS sweet spot (overlay) | | 88–94% | |
| Z4 threshold | | 91–105% | |
| Z5 VO2max | | 106–120% | |
| Z6 anaerobic | | 121–150% | |
| Z7 neuromuscular | | >150% | |

## Target events & schedule

> Everything about what the athlete is training for, and what's competing for their training time, lives here. This skill holds no hardcoded event data anywhere else — see `references/event-planning.md` for the methodology used to fill this section in.

### Primary goal
_(e.g. "Raise FTP. Track via eFTP convergence to test FTP, plus explicit threshold or 20-min tests as opportunity allows.")_

### A-races

> One block per race. Use `references/event-planning.md` to derive the demand breakdown and prep priorities when a race is added.

#### _(Race name)_ — _(date)_, _(location)_
- **Status:** upcoming / completed
- **Format:** _(mass start / TT / stage race / gran fondo / etc. — structural detail: team components, seeding, closed/open roads)_
- **Course profile:** _(distance, elevation, key climbs/features)_
- **Demand breakdown:** _(duration & intensity shape, terrain, group dynamics, fueling window, environmental factors — see event-planning.md)_
- **Prep priorities:** _(session types tied to the demands above)_
- **Race-day execution notes:** _(pacing plan, fueling plan, logistics)_
- **If completed — outcome & lessons:** _(result, what worked, what didn't)_

### B-races / training events
_(Same structure, lighter weight — local Jedermann races, training camps used as races, etc.)_

### Upcoming non-race schedule events

> Vacations, work travel, family commitments — anything that constrains or creates training opportunity without being a race. See `references/event-planning.md` for how to classify and plan around these.

#### _(Event name)_ — _(date range)_, _(location)_
- **Type:** no training access / reduced-unstructured access / training opportunity
- **Expected impact:** _(e.g. "no structured work possible", "hotel gym only", "altitude camp opportunity")_
- **Planning note:** _(how the forward plan in `training_plan` should account for it)_

### Completed key events (this season)
_Major races and rides already in the legs — anchor durability and explain load shape. Migrate to `long_term_history` at season end._

## Constraints & history

- **Available training time:** _(typical hours/week; note if build vs recovery weeks differ)_
- **Recovery factors:** _(sleep average, job stress level, family demands)_
- **Injury / health history relevant to cycling:** _(knee, back, etc. — ongoing items only; full narrative history belongs in `long_term_history`)_
- **Known limiters:** _(e.g., "VO2max ceiling pulls FTP gains short", "fades after 4 h", "heat-sensitive")_
- **Known strengths:** _(e.g., "strong sub-threshold engine", "absorbs camp weeks well")_
- **Equipment notes:** _(climbing bike, gearing, aero kit, etc.)_
- **Sensors:** _(HR: chest strap / optical; power meter model, single/dual-sided — decides whether EF/decoupling are trustworthy)_
- **Indoor setup:** _(icTrainer + trainer model, cooling/fan, typical room temperature — indoor rides are compared only with indoor rides)_
- **Strength training:** _(none / what, how often — see `references/ftp-training.md` → Strength training)_

## Fueling baseline

- **Race-day target carbs/hr:** _(g/hr — 60–90 g/hr typical working range; tune from experience)_
- **Tested fueling tolerance:** _(highest sustained g/hr in a long event without GI issues)_
- **Hydration baseline:** _(ml/hr typical; sweat rate if measured)_
- **Known food preferences / restrictions:** _(allergies, gels vs real food, caffeine response)_
- **Race-week weight management:** _(default: stop aggressive deficits in race week; ride normally and fuel rides fully)_

## Coach's running notes

> Free-form. Observations the coach wants to remember that don't fit anywhere else and aren't tied to a specific date the way Short-Term History entries are. Dated entries. Good content here is the "why" behind decisions: data reconciliations, pattern recognition, things future-you would otherwise re-derive.

- _(YYYY-MM-DD)_ — _(observation)_
