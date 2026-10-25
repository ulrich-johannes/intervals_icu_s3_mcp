# Target events & schedule planning — framework

This is a **methodology**, not a data file — it holds no dates, no race names, no specific athlete data. All of that lives in `athlete_profile` in Coach MCP, under "Target events & schedule". Use this file for *how to think about* a race or non-race event; use the Coach MCP record for *what the actual events are*.

Two categories of event live in `athlete_profile`:

1. **Races** (A/B priority) — things to peak for
2. **Non-race schedule events** — vacations, work travel, family commitments, anything that constrains or creates training opportunity without being a race

Both matter for planning. A week where the athlete is on a non-riding family trip needs the same forward-planning treatment as a taper week — just with a different shape.

---

## Capturing a new event

When the athlete mentions a new target race or a life event (vacation, work trip, etc.) that will affect training, **write it to `athlete_profile` in the same turn**, not at the end of the session. Losing a mentioned event because the conversation ended before the usual end-of-session write is a bigger cost than one extra targeted edit. Ask for whatever structured detail you need (see templates below) but don't block on getting every field — capture what you have and fill gaps later.

---

## Analysing a race's demands

When a race is added or the athlete asks for prep advice, break the format down into physiological demands using this structure. Store the result in the race's entry in `athlete_profile`.

1. **Format** — mass start / time trial / stage race / gran fondo / criterium / gravel / other. Note anything structurally unusual (team components, seeding by a preliminary effort, closed vs open roads).
2. **Duration & intensity shape** — all-out short effort? Sustained sub-threshold? Repeated surges with recovery? A mix across a multi-hour event?
3. **Terrain** — flat/rolling/hilly/mountainous; if climbing-dominant, note the character of the decisive climb(s) (length, gradient, sustained vs stepped) since that's usually the actual pacing question.
4. **Group dynamics** — mass-start drafting and positioning demands are a real, trainable skill, distinct from raw power. Solo/TT-format events don't have this demand at all.
5. **Fueling window** — total duration determines carb/hr targets (see SKILL.md's intra-ride carbohydrate table) and whether pre-race and on-course fueling logistics need rehearsal.
6. **Environmental factors** — heat, altitude, cold/wet descents — anything that needs specific acclimation or kit planning.

From the demand breakdown, derive prep priorities using the FTP/session frameworks in `references/ftp-training.md` — match session type to the dominant demand (e.g. repeated surges → over-unders; sustained sub-threshold climbing → long sweet-spot/tempo blocks; a short all-out TT-style effort → threshold-pace time-trial rehearsal). Don't reach for a generic "do some threshold work" prescription — tie every session choice back to a named demand from the breakdown.

---

## Multiple A-races close together

When two A-races are close enough that full recovery + a full build between them isn't realistic (as a rule of thumb, under ~3–4 weeks apart), this is a genuine planning constraint — call it out explicitly rather than treating them as independent.

1. **Rank them.** One is usually the bigger physical or personal target. Ask the athlete if it's not obvious from context. The lesser event gets raced well, not tapered into deeply.
2. **Don't double-taper.** A full taper into the earlier, lower-priority race erodes the fitness the later race depends on. A short sharpening (openers, volume down modestly) is usually enough.
3. **Protect the recovery window after the first race.** The single biggest risk in a tight gap is adding meaningful load too soon after the first event because the athlete "feels okay." Be explicit about how many easy/off days come first before anything structured resumes.
4. **Use the gap length to size the second block.** A short gap (under ~2 weeks) leaves room for recovery and a light sharpening only — no real fitness gains happen there. A longer gap (3–4+ weeks) can fit one real (short) loading block before its own taper.

---

## Non-race schedule events

Vacations, work travel, and other life events aren't just gaps to plan around passively — classify them and plan accordingly:

- **No training access** (e.g. a non-cycling family trip): treat the week as a scheduled recovery/maintenance week in the forward plan rather than letting it silently create an unplanned CTL drop. If it lands during a build phase, consider shifting the block boundaries so it falls at a natural recovery point instead.
- **Reduced/unstructured access** (e.g. work travel with hotel-gym or occasional riding only): plan minimum-viable maintenance — what's the smallest weekly dose that holds fitness (typically 2–3 short sessions, one with some intensity) — rather than assuming normal volume or writing the week off entirely.
- **Training opportunity** (e.g. a cycling-focused trip, altitude, or a location with terrain the athlete doesn't have at home): this can be reframed as an informal camp — plan volume and intensity deliberately rather than just "riding a lot while there," and factor in the fatigue cost afterward the same way you would after any camp week.

Whichever category, the event should show up as a shaped week (or block of weeks) in `training_plan`'s forward plan — not just a mental note. When building or revising the forward plan, always check `athlete_profile`'s event list first so a vacation week doesn't silently get planned as a normal build week.

---

## When an event completes

Move it from "upcoming" to a brief completed-event entry (date, result/outcome, one-line takeaway) in `athlete_profile`. At season end, or whenever that section gets long, migrate the season's completed events into `long_term_history` as part of that year's summary rather than letting them accumulate indefinitely in the profile.
