# Cycling Coach Memory record system — reference

This file covers the mechanics of the four-record persistent-memory system: where it lives, how to read it, and how to write updates using the real capabilities of the **Coach MCP** MCP tool (`state_create`, `state_list`, `state_get`, `state_update`, `state_delete`).

---

## Why this exists

Claude has no memory between sessions. All durable athlete state — profile, long-term history, short-term history, training plan — lives in **Coach MCP only**, as four named variables:

- `athlete_profile`
- `long_term_history`
- `short_term_history`
- `training_plan`

Nothing about the athlete's actual data is stored in this skill or in intervals.icu. intervals.icu stays purely a **live data source** (today's HRV, this week's TSS, this ride's power file) — never a place to persist coach state.

---

## This is a flat key-value store — every write replaces the whole value

Coach MCP has no element-level or partial-text edit. `state_update(var_name, content=...)` replaces the **entire** stored content for that variable; there is no equivalent of "insert this block at the top" or "replace just this one line" the way a document-editing connector would offer. That means the write pattern for every update is: **read the current full content, edit it in context (prepend an entry, change one field, delete a stale block), then write the complete result back in a single `state_update` call.**

This is simpler than it sounds, and simpler than an older Google-Drive-based version of this skill had to be: there's exactly **one key per record**, so there's no duplicate-file resolution, no folder-ownership disambiguation, and no `modifiedTime` guessing. Last write wins, cleanly, because there's only ever one copy.

Because each `state_update` call replaces the whole value, **batch all edits to one record into the single new content string you write back** — don't call `state_update` on the same `var_name` more than once in a turn.

---

## Locating and reading the records

At the start of any cycling-coach session:

1. `state_list` — lists variable names and descriptions (not content). 
   - **All four present** (`athlete_profile`, `long_term_history`, `short_term_history`, `training_plan`): proceed to read each.
   - **Empty, or some missing**: first run, or a partial first run. Create the missing ones from their templates (see First-run setup below); read the ones that already exist.
2. For each variable that exists, `state_get(var_name)` to read its full record — this returns `description`, `content`, and timestamps. The `content` field is the record's full markdown text.
3. There's no separate "check if I'll need to edit this" step the way an annotated read served for element IDs elsewhere — you always have the full text from `state_get`, and any edit is just producing a new full-text string.

---

## Writing updates

### The pattern, every time

1. `state_get` the variable if you haven't already this turn (you likely have, from the session-start read).
2. Compose the new full content in context: prepend a dated entry, edit one field, delete a stale table row, fold a section into another record — whatever the update is.
3. `state_update(var_name, content=<new full text>)`. Only pass `description` too if it's genuinely changed; omitted fields are left unchanged.

### Common cases

- **Prepend a new dated entry to `short_term_history`** (the common case, every daily review): take the current content, prepend the new entry block (see the format in SKILL.md's daily review section) above the existing entries, `state_update` with the combined text.
- **Prepend a new dated entry to `long_term_history`**: same pattern — check the file's existing convention (chronological vs. newest-first) before deciding where in the text the new entry goes.
- **Update one settled fact in `athlete_profile`** (new FTP, a new constraint, an updated running note): edit just that line or bullet in the text you read, leave everything else byte-for-byte the same, write the whole thing back.
- **Trim old entries from `short_term_history`**: remove entries older than ~3 months from the text before writing back. If any trimmed entry is genuinely notable, fold a one- or two-line summary into `long_term_history`'s content in the same turn (a separate `state_update` call, since it's a different `var_name`).
- **Revise `training_plan` when a block ends**: remove the completed block's forward-looking table from the text, add its summary row to the "past weeks" ledger section, add the new block's table, write the whole thing back.

---

## First-run setup

If `state_list` comes back **completely empty** — meaning nothing has ever been written to this athlete's storage bucket — this is a brand-new setup, not a transient error. Treat it as the trigger to start onboarding, not as something to quietly work around:

1. **Say so.** Tell the athlete plainly, in the same turn: no records were found in their store, and you're setting it up now. Don't create records silently and only mention it in passing.
2. **Pull what intervals.icu already has** before asking the athlete anything: `icu_get_athlete_profile` and `icu_get_sport_settings` for current FTP/zones, `icu_get_fitness_summary` for current CTL/ATL/TSB, `icu_get_upcoming_workouts`/`icu_get_calendar_events` for any races already on the calendar there.
3. **Ask the athlete directly** for the specific facts nothing can supply: name, age, height, years cycling, injury history, fueling tolerance, indoor setup/sensors, and any target events not already on the intervals.icu calendar. Don't invent placeholder values for these and move on — wait for the answer before writing them into `athlete_profile`.
4. For each of the four `var_name`s, `state_create(var_name, content=<template + whatever was pulled/answered>, description=<short description>)` using the matching template from this skill's `references/` folder (`athlete-profile-template.md`, `long-term-history-template.md`, `short-term-history-template.md`, `training-plan-template.md`). Fields you still don't have an answer for stay blank/placeholder in the template rather than guessed.

If `state_list` shows **some but not all** four variables (a partial prior run), only the missing ones need this treatment — read the existing ones normally and don't re-ask for facts already captured in them.

`state_create` fails if a variable with that name already exists and isn't deleted — if you get that error unexpectedly, `state_get` it instead; it likely already exists from an earlier session or a partial prior run.

---

## Live-data caching policy

Pulling CTL/ATL/TSB, wellness, and recent training history from intervals.icu on *every single request* is wasteful when the last pull might have happened minutes ago in the same conversation, or earlier the same day in a previous one. `short_term_history`'s topmost dated entry doubles as the cache for this data, so check it before reaching for a live pull.

### The threshold: same calendar day, not an hour count

**A cached Load state block is fresh if its entry's date matches today's date (Europe/Berlin, matching the athlete's Munich base) — otherwise it's stale.** This is a calendar-date rule, not an elapsed-time rule, and that's deliberate: Claude is told the current date at the start of a conversation but doesn't have reliable access to the current wall-clock time within it, so a rule like "fresh for 6 hours" can't actually be evaluated correctly — there's no trustworthy clock to check it against. "Same calendar day" only requires comparing two dates, which is something Claude can always do correctly.

### The check, every time a request would otherwise trigger a live pull

1. After reading `short_term_history` (already happening per the standard session start), look at the topmost dated entry in the log.
2. **Entry's date == today**: its Load state block (CTL, ATL, TSB, HRV, RHR, sleep, readiness) is current. Use those values directly. Skip `icu_get_fitness_summary` and `icu_get_wellness_for_date` entirely for this request.
3. **Entry's date < today, or the log is empty (first run)**: stale. Pull fresh data via the normal calls (see `references/daily-review.md`), and write the refreshed values as part of prepending today's new dated entry — this is one `state_update` call, not an extra one, since a new day's entry was going to be written anyway.

### The override: specific new data always wins over the cache

The date check governs whether to re-pull the *routine daily snapshot*. It's not a license to ignore something the athlete is explicitly telling you about. If the athlete mentions a ride, a weigh-in, or anything else that happened after today's entry was written — even if that entry's date is today — treat that specific thing as needing a fresh, targeted pull (e.g. `icu_get_activities_by_date` for a ride that isn't in the cached snapshot yet), regardless of what the date check says. The cache saves you from re-fetching the *same* answer twice, not from noticing new information.

### What this policy does and doesn't cover

- **Covered**: CTL/ATL/TSB, today's wellness (HRV/RHR/sleep/readiness), and the rolling recent-training-history summary — the specific data the daily review pulls fresh every time in the old design.
- **Not covered, and doesn't need a cache**: `athlete_profile` fields (FTP, zones, goals) — these already only update when a settled fact actually changes, per the read-edit-write sequence above; there's nothing to "re-pull" routinely. A specific activity's detailed metrics, once analyzed and logged into an entry's "Yesterday" / "Key numbers" / "Metrics" fields — that ride's data doesn't change after the fact, so there's no reason to ever re-fetch it once it's recorded; only pull `icu_get_activity_details` again if the athlete wants a deeper breakdown than what's already logged. The dashboard artifact (`references/dashboard.md`) — it pulls season-length trends and power curves that this daily cache was never scoped to hold; it can reuse today's cached Load state for its calendar view's most recent day, but everything else it needs is pulled fresh regardless of this policy.

---

## Migrating existing records to a newer template

Records created from older template versions keep their old structure. Templates only shape *new* records. When a record lacks a field the current template has (e.g. `training_plan` without "Limiter diagnosis"/"Intensity model", `athlete_profile` without "Sensors"/"Indoor setup", session entries without a "Metrics" line):

- Add the missing fields at the next write you were going to make anyway. Fill them from data you can pull, and ask the athlete only for what can't be pulled (sensors, indoor cooling, strength training).
- Replace content the current skill explicitly retired (e.g. the old adaptation trigger "VO2 session fails → drop FTP by ~10 W") and mention the change to the athlete in one line.
- Don't back-fill Metrics lines for past entries by estimating. The EF baseline starts from the first real Metrics line.

---

## Edge cases

**Coach MCP read fails or times out**: proceed using whatever live intervals.icu data you can pull, tell the athlete the records weren't reachable this session, and don't write anything back (you'd be writing from an incomplete picture and risk clobbering good data with a stale-context overwrite).

**The store was updated by a different conversation since you last read it**: unlike a document the athlete opens and edits directly, this store is only ever written through Claude — but the athlete may have run a cycling-coach session in a different conversation since this one started. Always `state_get` fresh at the start of a session rather than trusting anything from earlier in this conversation's context if meaningful time may have passed; don't assume your own last write here is still the latest state if there's any chance another session touched it first.

**A `var_name` you expect to exist comes back not-found from `state_get`**: check `state_list(include_deleted=true)` before recreating it — it may have been soft-deleted rather than never created. If it shows up deleted and that looks wrong, tell the athlete rather than silently recreating from a blank template over what might be recoverable.

**Composing a very large `short_term_history` write**: there's no element-level trimming here, so if the entry log has grown large, do the trim (see "Trim old entries" above) as part of composing the new content rather than after — don't write back a version that's still carrying entries well past the ~3-month window.
