# Dashboard artifact — reference

Build an interactive training dashboard as a published artifact (a self-contained page). Follow whatever artifact/design guidance the current environment provides, and load it before building. This is a real artifact with visual design stakes, not a quick chart.

**Trigger**: "show me my dashboard", "build/refresh my training dashboard", "give me the fitness page", or equivalent open requests to see the whole training picture visually.

**The bar for "done":** every chart in this spec ships with a computed, specific, written insight — not a caption that restates the axis labels. "CTL is 68" is not an insight. "CTL's climbed 6 points in two weeks but TSB is already at −18 with your race 9 days out — that's a fast ramp with limited room left to absorb load before you need to start coming down" is. If a chart doesn't have something like that attached, it isn't finished.

---

## The constraint that shapes everything here: this is a snapshot, not a live app

Artifacts render in a sandboxed iframe with no access to MCP servers — they cannot call intervals.icu or Coach MCP themselves. **All data has to be pulled by Claude via tool calls first, then embedded directly into the artifact's code as static data**, including every one of the written insights below — those are computed by Claude at build time and baked in as text, not derived client-side.

- Pull everything *before* writing the artifact file.
- Put a visible "Data as of [date]" note in the artifact so the athlete never mistakes a stale snapshot for live data.
- "Refreshing" means re-pulling data, recomputing every insight, and regenerating the embedded dataset — not editing display logic in place with the same stale numbers.
- Don't oversell this as real-time. This is a periodic check-in view.

---

## Data to pull

This touches a lot of endpoints. **Budget tool calls accordingly — this can easily run 15–30 calls.** Prefer aggregate/summary endpoints over iterating per-activity wherever one exists; only drop to per-activity calls for fields with no aggregate equivalent (decoupling, above-FTP work, zone-time detail). If intervals.icu tools are deferred in the current environment, load them (tool search) before first use. Two things on this list — the training plan and event list — cost nothing extra: they're already sitting in `training_plan` and `athlete_profile` from the normal session-start Coach MCP read, not a separate pull.

- **CTL/ATL/TSB**: `icu_get_fitness_chart`, trailing 90 days. Same-day value can come from the cache (`short_term_history`'s topmost entry, if dated today) per the Live-data caching policy — everything else in the 90-day window is historical and needs a real pull regardless of the cache.
- **Peak-power trend** (replaces an eFTP chart — this connector exposes no eFTP field): `icu_get_power_curves` at a fixed duration (20-min, the FTP-proxy duration) sampled periodically across the window, labeled explicitly as "20-min peak power," never called "eFTP." If the athlete pastes their own intervals.icu dashboard showing actual eFTP, that pasted number may be shown too, clearly attributed as athlete-supplied rather than pulled.
- **RHR / HRV / sleep**: `icu_get_wellness_data`, the only source (no device cross-check with this connector), trailing 90 days plus the 60 days before that for the HRV normal range. Today's value can come from the cache under the same rule as CTL/ATL/TSB.
- **Weekly activity aggregates** (moving time, distance, kJ, zone-time HR & power): trailing 8 weeks, from `icu_get_activities_by_date` aggregated per week; `icu_get_power_histogram`/`icu_get_hr_histogram` per activity for zone-time if the per-activity totals aren't already on the activity record.
- **Above-FTP work per activity**: `icu_get_power_histogram` per activity (time-in-zone above FTP), trailing 8 weeks, summed to weekly kJ. There is no W′-balance/extended-metrics tool on this connector — this histogram-based figure is a different, coarser measure (time above FTP, not W′ expenditure) and should be labeled as such.
- **Power curve**: two pulls — season-to-date (season start = the date recorded in `athlete_profile` if there is one, otherwise 1 January of the current year) and the equivalent calendar window one year earlier, via `icu_get_power_curves`.
- **Decoupling / EF**: first check the Metrics lines already in `short_term_history` (they carry `EF`, `dec`, `qual`, `env`). For rides not covered there: EF comes from `icu_get_activity_details`'s `efficiency_factor`; decoupling has no tool field at all on this connector — compute it via `icu_get_activity_streams` + the canonical `ride_metrics()` script (see SKILL.md's "Claude never eyeballs a metric"), not by recomputing it ad hoc. Trailing 90 days. **Only qualifying rides** count, defined once in SKILL.md: steady (VI < 1.05), ≥ 45 min continuous, complete HR, not a structured interval session. Keep indoor and outdoor as separate series.
- **Durability**: **not available with this connector** — drop chart 8's durability series (see below); `icu_get_power_curves` has no fatigue/kJ parameter.
- **Last 5 activities**: exactly 5, most recent first — from `icu_get_recent_activities` or `icu_get_activities_by_date`.
- **Training plan**: already loaded (`training_plan`'s forward-plan table).
- **Events**: already loaded (`athlete_profile`'s target events & schedule).

---

## Zone buckets: a 3-zone simplification, not the skill's 7-zone model

The skill's canonical framework is the 7-zone power model, and that stays the reference for prescribing sessions everywhere else. This dashboard's "3-Zone Distribution" is a deliberately coarser at-a-glance view — its whole point is answering "were my easy days actually easy," which a 7-way split doesn't do well. Map it from the 7-zone model, don't invent a separate system:

- **Easy** = Z1 + Z2
- **Moderate** = Z3 + Sweet Spot + Z4
- **Hard** = Z5 + Z6 + Z7

Compute separately for HR-based and power-based zones — the divergence between the two is itself signal (HR says "moderate" while power says "easy" = fatigue or heat), which is part of why both were asked for.

---

## Reference bands (reused from elsewhere in this skill — don't redefine these)

**TSB** (from SKILL.md's Load Management section):

| TSB | Color | Meaning |
|---|---|---|
| > +25 | Blue | Detrained / too much rest |
| +5 to +25 | Green | Fresh, race/peak-effort ready |
| −10 to +5 | Amber | Neutral, normal training |
| −30 to −10 | Orange | Fatigued, monitor |
| < −30 | Red | Overreached |

**Aerobic decoupling**, qualifying rides only (from SKILL.md → Fixed thresholds):

| Decoupling | Verdict |
|---|---|
| < 3% | ✅ Good |
| 3–5% | ⚠️ Acceptable |
| > 5% | ❌ Check heat/indoor, fueling, fatigue |
| > 8% | ❌ Investigate |

**HRV**: 7-day rolling average vs. normal range (60-day mean ± 0.5 SD), from `references/daily-review.md`:

| 7-day HRV avg | Verdict |
|---|---|
| Within normal range | Balanced |
| Below range | Accumulated fatigue — amber |
| Below range 5+ days and falling | Overreaching signal — red |
| Above range during heavy load | Watch item (possible saturation), not a green light |

Using these exact bands everywhere — chart shading, insight text, the daily review — is deliberate. A dashboard that colors a TSB of −15 differently than the daily review would silently contradicts itself and undermines trust in both.

---

## Locked chart specifications

Each chart below is fully specified: type, axes, series, reference lines, and which context layers (recent activities / plan / events) actually apply — not all four apply to all charts, and forcing them where they don't fit produces filler, not insight. Where an insight is duplicated across two places (e.g. "days to next race" appears both on the CTL chart and in the Events section), **compute it once and reuse the value** — don't recompute it twice and risk the two disagreeing.

### 1. Weekly stat cards — Moving Time, Distance, kJ
- **Type**: 3 stat cards, current week (Mon–Sun).
- **Each card shows**: this week's value, plus the delta vs. last week (▲/▼ with %). A bare number with no comparison is exactly the kind of non-insight this rewrite is meant to fix.
- **Context**: if `training_plan`'s forward-plan table has a row for this week, show the planned TSS/hours alongside actual and note over/under-delivery.
- **Insight** (below the cards, one line): call out whichever of the three (time/distance/kJ) diverges most from plan or from the athlete's own recent pattern, and say what it implies (e.g. under-delivered hours despite on-target kJ = shorter, harder rides than planned).

### 2. 3-zone distribution — weekly, HR and Power
- **Type**: two grouped bar charts side by side (HR-based, Power-based), X = day of current week, Y = minutes, 3 stacked segments per bar (Easy/Moderate/Hard).
- **Reference**: overlay the athlete's own trailing 4-week average distribution as a thin reference line, and state the current block's target distribution (pyramidal or polarised, as written in `training_plan`'s block goal per `references/ftp-training.md` → Intensity distribution). Compare against the block's own model, not a generic doctrine.
- **Context**: none of recent-activities/plan/events fit this one naturally — it's a pure this-week composition view.
- **Insight**: flag the day(s) that deviate most from the athlete's own baseline, and flag any day where the HR-based and power-based splits disagree (e.g. HR says "moderate," power says "easy") — that disagreement is itself the more interesting signal than either split alone.

### 3. Calendar grid — 7-day wellness + activity
- **Type**: 7-cell grid, current week. Each cell: date, sleep (h:mm), RHR (bpm), HRV status (colored per the HRV band table above), activity marker if a ride happened that day (TSS + type on hover/tap).
- **Context**: activities from the Last 5 Activities list that fall within this week appear as the day's marker — no separate pull needed, just cross-reference.
- **Insight**: flag any day whose readiness verdict (`references/daily-review.md`) was amber/red and note whether the training that day was adjusted accordingly.

### 4. Fitness/Fatigue/Form — CTL, ATL, TSB
- **Type**: line chart, X = date, trailing 90 days (shared X-axis range with charts 5 and 6, so the Fitness page reads as one coherent timeline). CTL solid line, ATL lighter/dashed line, TSB rendered as a colored band beneath both — colored per the TSB reference table, not a flat single color.
- **Context — events**: vertical reference line at each upcoming A-race date from `athlete_profile`, labeled with the race name.
- **Insight**: current TSB band + its verdict from the table, the 7-day trend direction (rising/falling), days to the next A-race, and — using the recent CTL ramp rate — whether the current trajectory plausibly lands in the green band by that date. This is the single most load-bearing insight on the whole dashboard; don't shortcut it to just "TSB is −12."

### 5. Peak-power tracker — 20-min best, periodic samples
- **Type**: line chart, same 90-day X-axis as chart 4, Y = watts. Horizontal reference line at the FTP currently recorded in `athlete_profile`. **Not an eFTP chart** — this connector exposes no eFTP field, so don't label it as one. It's the 20-min point of `icu_get_power_curves`, sampled periodically across the window.
- **Context — plan**: note the current block's stated goal (`training_plan`'s "Block goal") alongside the chart.
- **Insight**: is 20-min peak power tracking above, at, or below the recorded FTP × 1.05 (the usual 20-min-test relationship), and what the gap means — and does the trend direction match what the current block is supposed to be producing, or is it flat/declining despite a build block (worth surfacing plainly, not softened). If the athlete has separately pasted an actual eFTP reading from their own intervals.icu dashboard, that can be shown alongside as an athlete-supplied data point, clearly labeled as such rather than blended into this series.

### 6. RHR & HRV trend
- **Type**: two stacked line charts (RHR above, HRV below), same 90-day X-axis as charts 4–5. Each with a shaded rolling-7-day baseline band; HRV band additionally shaded per the HRV reference table above.
- **Insight**: current status per the HRV band table, direction of the baseline itself over the last 2–3 weeks (a rising baseline = genuine adaptation, a falling one = accumulating fatigue even if today's single reading looks fine), and what that implies for the near-term plan (tie to chart 4/7's read on current load).

### 7. Work vs. above-FTP work — weekly
- **Type**: grouped bar, X = week, trailing 8 weeks, Y = kJ. Two bars per week (total work, above-FTP work); show the above-FTP share as a data label on each bar rather than a second axis — a dual-axis chart here would be easy to misread.
- **Context — plan**: the current block's stated goal.
- **Insight**: flag weeks where the above-FTP share jumped disproportionately relative to total volume, and say whether that matches the block's goal (e.g. a VO2max-focused block should show this; a base-building block showing it unexpectedly is worth a direct comment, not a shrug).

### 8. Power-duration curve — this season vs. last year
- **Type**: line chart, X = duration on a log scale with gridlines at 5s/1min/5min/20min/60min, Y = watts. Two series: this season (solid), last year (muted/dashed). **No durability/fatigued-curve series** — this connector's `icu_get_power_curves` has no fatigue/kJ parameter, so don't add a third "after X kJ" line; a chart that used to carry one now just shows two.
- **Insight**: compute % change at each benchmark duration and state the single biggest gain and, if one exists, the biggest regression, by name and number. "20-minute power is up 4%, but 5-minute power is down 6% — the sustained-effort gains haven't come with a matching top-end" is the level of specificity expected here. Then add the limiter read: 5-min / FTP ratio, interpreted with `references/ftp-training.md` → Diagnose the limiter (its durability row is also marked not available), and whether the current block focus matches it.

### 9. Aerobic decoupling — 7-day moving average
- **Type**: line chart, X = date, trailing 90 days, Y = decoupling %, shaded per the decoupling reference table above.
- **Series**: indoor and outdoor as separate lines (indoor runs systematically higher from heat build-up). Plot individual qualifying rides as points; draw a rolling line only where ≥ 3 qualifying rides exist in the window.
- **Context — recent activities**: note which of the Last 5 Activities qualified (per the Data-to-pull definition). If fewer than 2–3 rides in the last week qualified, say so. A 7-day average built from one ride is noise, not a trend, and presenting it without that caveat would overstate confidence.
- **Insight**: trend direction and verdict from the reference table; an improving trend is real signal, but so is a flat-or-worsening one during a build block, and it should be named as clearly as the good version would be.

---

## Last 5 Activities

Exactly 5, most recent first. Per activity: date, type, headline, key metrics (NP, IF, TSS, duration, kJ), and a **condensed** coach takeaway — one sentence headline plus one or two sentences of substance (reuse the judgment and the Metrics line from SKILL.md's session analysis, not its full breakdown; that depth belongs in chat when the athlete asks about a specific ride). Where a ride is also referenced elsewhere on the dashboard (it's the latest decoupling data point, it set a power-curve best, it's today's calendar marker), say so — that's what turns a list into a dashboard instead of five disconnected rows.

---

## Upcoming Training Plan

Pull from `training_plan`'s forward-plan table: the next 2 weeks. Also surface today's/tomorrow's specific prescription from `short_term_history`'s topmost entry (the plan table is weekly-granularity; the daily entry has the specific next session). **Insight**: does the plan's stated shape for the coming weeks match what chart 4's TSB trajectory can actually absorb — if the plan calls for a build week but TSB is already deep in the orange/red band, say so plainly rather than presenting the plan as a given.

---

## Events

Pull from `athlete_profile`'s target events & schedule: upcoming races (A/B, with days-until) and upcoming non-race events (vacations, travel), sorted chronologically. For the nearest A-race, reuse (don't recompute) the readiness call already made in chart 4's insight — state it consistently in both places. For non-race events, note their planning classification (no training access / reduced access / opportunity, per `references/event-planning.md`) and whether `training_plan`'s forward plan already accounts for it or still needs adjusting.

---

## Building the artifact

- **Stack**: a single self-contained page with one charting library, following the environment's artifact/design guidance. This shouldn't look like a default chart-library demo.
- **Layout**: tabs for Calendar / Fitness / Compare / Plan & Events, with the Last 5 Activities list as a persistent section visible regardless of tab (it's cross-referenced from multiple charts, so it shouldn't be buried one tab away from them).
- **Insight callouts**: a single consistent visual treatment (a distinctly styled callout box, not just a stray paragraph) used under every chart, so the athlete's eye learns where to look for "what does this mean" versus "here's the data."
- **Data**: embed the pulled data and every precomputed insight as a plain JS object near the top of the file, with a `dataAsOf` date. No fetch calls inside the artifact — everything renders from what's embedded.
- **Design details**: consistent color palette built from the TSB/decoupling/HRV reference tables above (reuse those exact colors as the dashboard's semantic palette, don't invent a second color scheme); axis labels always carry units; tooltips on hover with exact values; consistent date formatting throughout (`DD MMM`).

---

## What this dashboard doesn't do

- It doesn't write anything back to Coach MCP. If an insight surfaced here is worth persisting (a multi-week decoupling trend, a plateaued eFTP), that's a judgment call for the normal coaching flow — update `athlete_profile` or `short_term_history` through the usual protocol in `references/cycling-coach-memory.md`; showing it on a dashboard doesn't count as recording it.
- It doesn't replace a full single-ride analysis. The Last 5 Activities blurbs are intentionally condensed; point the athlete back to a normal chat request for the full session analysis (SKILL.md) on any ride they want to dig into.
