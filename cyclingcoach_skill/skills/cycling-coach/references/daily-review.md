# Daily review & planning — reference

This file covers the mechanics of the daily check-in: what to pull, how to parse state, what to write back. The state store itself (`short_term_history`) and the read/write mechanics for Coach MCP are covered in `references/cycling-coach-memory.md` — read that first if you haven't already this session. This file covers the coaching logic that runs on top of it.

---

## Fetching state at the start of a daily review

By the time you reach a daily review, the Coach MCP protocol (SKILL.md + `references/cycling-coach-memory.md`) should already have given you the current `short_term_history`. From it, extract:

- Last session's prescription vs execution
- Any flags (fatigue, injury watch, nutrition debt, morale)
- The 48h outlook that was written at the end of that entry

If `short_term_history` couldn't be read this session (Coach MCP unreachable), proceed without state but say so explicitly, and ask the athlete to confirm how the last session went rather than guessing.

---

## Data pulls for a daily review

**First, check whether a pull is even needed.** Look at the topmost dated entry already read from `short_term_history`. If it's dated today, its Load state block already has current CTL/ATL/TSB and wellness values — use those and skip this whole table, per the Live-data caching policy in `references/cycling-coach-memory.md`. Only proceed with the pulls below if that entry is stale (not today's date) or the athlete is asking about something specific it doesn't cover.

When a pull is actually needed, pull these in order; proceed if any fail (degrade gracefully):

| Data source | MCP call | What you need |
|-------------|----------|---------------|
| intervals.icu fitness | `icu_get_fitness_summary` | CTL, ATL, TSB today, plus ramp rate |
| intervals.icu wellness (**the only** wellness source — this connector has no device cross-check) | `icu_get_wellness_for_date` (today) / `icu_get_wellness_data` (range, for the baseline) | HRV, RHR, sleep, readiness; request ≥ 60 days on the first pull of a day so the baseline can be computed |
| intervals.icu recent activity | `icu_get_activities_by_date` | Last 7 days TSS, session types |

If HRV is absent (not recorded on this platform), note that explicitly and rely on RHR, sleep, TSB and subjective feel — there's no second wellness source to fall back on anymore.

The same single-source approach applies in the dashboard (`references/dashboard.md`).

---

## Interpreting wellness signals

### HRV

Single-day HRV is noisy. Decisions rest on the **7-day rolling average** compared with the athlete's **normal range** (60-day mean ± 0.5 SD of daily values; if < 30 days of data exist, use ±7 % around the available mean and say the baseline is provisional). Always use the same measurement (overnight average from the same device). Don't mix sources.

| Signal | Interpretation | Action |
|---|---|---|
| 7-day avg within normal range | Balanced | Proceed as planned |
| 7-day avg below normal range | Accumulated fatigue / stress | Amber flag. Cut volume, keep at most one quality session until it returns to range |
| 7-day avg below range for 5+ days and falling | Overreaching signal | Red flag. Recovery days, review the last 2 weeks of load |
| 7-day avg **above** normal range during heavy load, especially with rising RHR or poor sleep | Possible parasympathetic saturation, not "super-recovered" | Treat as a watch item, not a green light for extra intensity |
| Today's reading > 20 % below 7-day avg | Acute disturbance (bad night, alcohol, illness onset, travel) | Counts as one flag in the verdict. Ask about context before acting on it |

High HRV alone is never a reason to *add* intensity beyond the plan.

### Resting HR

- RHR elevated >5 bpm above the athlete's personal baseline: a recovery signal. Do not add intensity.
- RHR elevated >8 bpm: strong recovery signal; only Z1/Z2.
- RHR at or below baseline: cleared for normal training.

### Sleep

- < 5 h last night: no VO2max/threshold regardless of other signals. Z2 or sweet spot at most.
- < 6 h last night, or < 7 h for 3+ nights running: one flag in the verdict below.
- 6–7 h: can train; don't schedule an FTP test.
- 7–8 h+: normal training.

### Combining signals into a readiness verdict

Don't pick a single metric and ignore the others. Count flags: HRV (either HRV row above), RHR > 5 bpm above baseline, sleep < 6 h (or < 7 h for 3+ nights running), illness symptoms, and TSB below the phase-appropriate floor. That floor is −30 in a loading week (per SKILL.md's PMC danger zone), where −10 to −25 is normal productive fatigue, and −15 in a recovery or taper week.

- **Green** (0 flags): proceed as planned
- **Amber** (1 flag): proceed but cut volume 15–25 %. Keep the planned intensity ceiling and don't extend reps
- **Red** (≥ 2 flags, illness symptoms, or the HRV overreaching row): rest or Z1/Z2 only, no structured work

The verdict must appear explicitly in the daily review response.

---

## Session prescription logic

After the readiness verdict, match the prescription to the phase, the plan, and today's verdict:

1. Check `training_plan` (from Coach MCP) for what's scheduled this week. If today isn't explicitly planned, fall back to the last `short_term_history` entry's "next 48h outlook".
2. Check days to next event (from `athlete_profile`). Apply taper logic if < 10 days out (see SKILL.md load management section).
3. Apply the readiness modifier:
   - Green: full prescription
   - Amber: reduce volume (e.g., 3 × 10 min threshold → 2 × 10 min), same intensity ceiling
   - Red: Z2 or Z1 only, regardless of what the plan says

State the session with full interval format (see SKILL.md). Never vague ("do some riding"). Even a Z2 day gets a duration, a power target range, and a TSS estimate.

---

## Fueling brief format

For every session prescription, include a fueling brief:

```
Pre-ride: [what to eat, when — e.g., "2h before: 80g oats + 20g protein; 30 min before: 1 banana"]
On bike: [g/hr target + specific product or format — e.g., "60 g/hr → 1 gel every 30 min + 500ml drink with 40g carbs/hr"]
Post-ride (within 30 min): [g protein + g carbs]
Next meal (within 2h): [emphasis — carb-forward vs protein-forward depending on next day's session]
```

Adjust to the session duration. Z2 rides < 90 min: no on-bike fueling needed. Threshold or VO2max sessions any length: pre-load with 1–2h meal; have carbs available even for short sessions.

---

## Writing the entry back

After generating the response, prepend the structured entry to the top of `short_term_history`'s current content and write the whole result back with `state_update` — see `references/cycling-coach-memory.md`. Since `state_update` replaces the full value, this does mean composing the new full text (new entry + everything already there) before writing, not a true partial-insert — but no merging or reconciliation is needed beyond that concatenation.

**The entry is never shown verbatim to the athlete unless requested.** Summarise conversationally. It exists for machine parsing in the next session, not for human reading.

Use the exact format from SKILL.md / `references/short-term-history-template.md`, including the **Metrics** line for the previous day's ride (SKILL.md → Workout analysis). Fill every field and use `–` for not-applicable. The EF baseline is computed from these lines.

---

## Edge cases

**No HRV data**: proceed using TSB + subjective report. State explicitly that HRV is missing and that the readiness verdict is less reliable.

**Athlete overrides the verdict**: if an athlete says "I know HRV is down but I want to do intervals", acknowledge it, adjust the prescription conservatively (shorter reps, same intensity), and note the override in the Short-Term History entry's flags section.

**Day before a race**: readiness verdict is moot. The session is openers by definition (< 45 min: 2–3 × 3 min @ threshold or 4–5 × 1 min at VO2max pace, the rest Z2; consistent with SKILL.md → Taper timing). Focus the response on tomorrow: sleep, fueling, logistics, race plan.

**Extended no-entry gap** (athlete hasn't checked in for 3+ days): don't reconstruct state from guesses. Pull `icu_get_activities_by_date` and `icu_get_fitness_summary` to see what actually happened, then build the state from raw data. Tell the athlete what you found, and write a catch-up entry that's honest about the gap rather than fabricating daily entries for the missing days.
