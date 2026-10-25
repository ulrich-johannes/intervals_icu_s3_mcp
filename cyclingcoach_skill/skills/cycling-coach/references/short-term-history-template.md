# Short-Term History — template

> Lives in Coach MCP as the variable `short_term_history`. This is the rolling ~3-month state store and session log — it replaces what used to be intervals.icu calendar notes. It is the primary continuity mechanism between sessions: read it first, every time. Read the current version fresh every session; don't assume the copy in context is current.

**Last updated:** _(YYYY-MM-DD)_
**Window:** entries older than ~3 months should be trimmed from this record and, if notable, summarised into `long_term_history` instead (see `references/cycling-coach-memory.md` for the exact sequence).

> **This file doubles as the live-data cache.** The topmost dated entry's "Load state" block (CTL/ATL/TSB, HRV, RHR, sleep, readiness) is not just a historical record — it's checked *before* pulling fresh data from intervals.icu on any given day, to avoid re-pulling the same numbers repeatedly. See "Live-data caching policy" in `references/cycling-coach-memory.md` for the exact rule. Don't add a second, separate place to store "current" values — that would create two sources of truth for the same numbers and risk them drifting apart.

---

## Weekly load summary (rolling ~12 weeks)

| Week of | TSS | Hours | Key session | Notes |
|---|---|---|---|---|
| | | | | |

## Wellness trend (rolling ~4 weeks)

| Week of | HRV avg | RHR avg | Sleep avg | Notes |
|---|---|---|---|---|
| | | | | |

## Daily / session log (most recent first)

> One entry per daily review or significant session. This is the coach-note format from SKILL.md — write it every session without being asked, don't show it to the athlete verbatim unless they ask for it.

### _(DATE)_

**Load state**
- CTL: _(X)_ | ATL: _(Y)_ | TSB: _(Z)_
- HRV: _(X ms)_ (_trend_)
- RHR: _(X bpm)_
- Sleep: _(h:mm)_
- Readiness: _(score or text)_

**Yesterday**
- Session: _(type + brief description)_
- Execution: _(✅ / ⚠️ / ❌)_
- Key numbers: _(NP, IF, TSS, duration)_
- Metrics: _(fixed Metrics line from SKILL.md → Workout analysis; every field, `–` if not applicable)_
- Flags: _(any issues)_

**Today's prescription**
- Session type:
- Target:
- Power targets:
- Duration / TSS estimate:
- Fueling plan:
- Key focus:

**Flags & carry-forwards**
- _(ongoing watch items)_

**Next 48h outlook**
- _(brief note)_

---

_Repeat one dated block per entry, most recent first._
