# FTP improvement — methodology

The athlete's primary goal is to raise FTP. This is the working framework for training structure, weekly sessions, and block planning. Load numbers (ramp rate, weekly TSS, taper) are defined once in SKILL.md → Load management; this file does not redefine them.

---

## What raises FTP

The evidence (summarised under "Evidence basis" at the end) supports three building blocks, in this order of priority:

1. **Low-intensity volume (Z1–Z2)**: most of the riding time. It builds mitochondrial density, capillarisation, fat oxidation and durability. It's the platform, and the thing easy days must not drift away from.
2. **Constant high-intensity work (HIT, ~2 sessions/week in loading weeks)**: VO2max-type intervals are part of **every** build block, not a plateau-breaker held in reserve. Well-executed HIT raises threshold power as well as VO2max. The clearest trial signal is that plans *without* high-intensity work underperform.
3. **Heavy-domain work (sweet spot / threshold / moderate-intensity intervals)**: the third quality session. It is effective for lactate-threshold power and fatigue resistance. Sweet spot (88–94 % FTP) specifically is a **practice-validated heuristic, not a trial-validated prescription**: no controlled trial has tested that band as such.

Default loading week for the athlete (8–12 h): **2 HIT + 1 heavy-domain session + Z2 fill**. In weeks with heavy life stress, an amber readiness trend, or < 7 h available: **1 HIT + 1 heavy-domain**. Never drop HIT entirely for a whole block unless it's a deliberate base or recovery phase.

The limiter diagnosis below shifts the **emphasis** (which HIT format, how much heavy-domain work, how much Z2), not whether HIT is present.

---

## Diagnose the limiter (do this before choosing a block focus)

Pull `icu_get_power_curves` (90 d). Compare against the FTP recorded in `athlete_profile`:

| Signal | Reading | Likely limiter → block emphasis |
|---|---|---|
| 5-min power / FTP | < ~1.15 | FTP close to its aerobic ceiling → **HIT emphasis**: both quality slots HIT-type, heavy-domain session shortened or alternate weeks |
| 5-min power / FTP | > ~1.25 | Big ceiling, low fraction used → **heavy-domain emphasis**: longest heavy-domain format progression, HIT stays at 1–2/week, consider a 1-week moderate-intensity block |
| 5-min power / FTP | 1.15–1.25 | Balanced → default 2 HIT + 1 heavy-domain |
| 20- or 60-min power after X kJ vs fresh | **Not checkable with this connector** — no durability/fatigue-curve tool. Don't substitute a guess for this row; drop it from the diagnosis rather than reading a limiter from missing data. | — |
| Pw:HR decoupling on qualifying long Z2 rides (same env, computed per SKILL.md via `icu_get_activity_streams` + `ride_metrics()`) | repeatedly > 5 % | Aerobic base or fueling → **Z2 volume, fueling practice** (rule out heat/indoor first) |
| Time-in-zone history (last 4–8 weeks) | lots of Z3, little Z2 or ≥ Z5 | "Grey zone" drift → **make easy days easy again**, then restore HIT |
| HIT sessions in the last 4–6 weeks | < 1/week on average | Missing stimulus → **restore HIT before changing anything else** |

These ratios are heuristics, not laws. The 5-min ratio needs a genuine recent maximal 5-min effort. If the curve has none, say the ratio is unreliable rather than reading a fake limiter from it. State the diagnosis and its evidence in the block goal in `training_plan`.

---

## Intensity distribution

Measure distribution by **time in zone**, not by session count: a "hard day" is still mostly warm-up, recoveries and cool-down.

For the athlete's typical 8–12 h/week, default to a **pyramidal** distribution:

| Share of weekly ride time | Target |
|---|---|
| Z1–Z2 | ~75–80 % |
| Heavy domain (Z3 upper / sweet spot / Z4) | ~10 % |
| Severe domain (Z5+, HIT work intervals) | ~10 % |

**Why pyramidal, stated honestly:** the best current synthesis (Rosenblat, Seiler et al. 2025, IPD network meta-analysis) finds no overall difference between polarised and pyramidal, with a subgroup signal favouring pyramidal for recreational athletes. That subgroup finding is hypothesis-generating, not proof. **Polarised is not inferior and does not require more volume**: training volume was not associated with larger gains in the cycling meta-analysis (Cove et al. 2025). Pick one model per block, write it in the block goal, and check actual time-in-zone against it weekly. The common failure isn't picking the wrong model. It's easy days drifting into Z3 and HIT disappearing.

---

## Block structure

A typical productive block:

- **Loading weeks (2–3)**: 2 HIT + 1 heavy-domain session plus Z2 fill (1 + 1 in heavy life weeks). Weekly TSS from the CTL formula in SKILL.md at a ramp of 2–5/week.
- **Recovery week (1)**: ~50–60 % of the loading weeks' TSS (practitioner convention, not trial-derived), with one short HIT session to keep the feel. TSB returns toward 0 or slightly positive. eFTP often pops here as fatigue masking lifts.

Masters athletes, or anyone with high life stress, often do better on 2 : 1 than 3 : 1. Decide from the athlete's own response (HRV trend, how the third loading week actually went), and note what works in `long_term_history`.

**Hard days hard, easy days easy.** Never schedule two quality sessions back-to-back unless it's a deliberate block (e.g. a camp weekend) with recovery planned afterward.

---

## Progression rules

Progress **one variable at a time**, in this order:

1. **Time in zone per session** (e.g. sweet spot 2 × 15 → 2 × 20 → 3 × 20 → 2 × 30 → 1 × 60 min).
2. **Rep length at the same intensity** (fewer, longer reps with the same total).
3. **Intensity**: only once the longest planned format is completed with ✅ execution and a stable HR creep across reps.

Rules of thumb:
- Add ~10–15 % time-in-zone per week in a loading block. Don't add time *and* watts in the same week.
- If a session's execution grades ⚠️/❌ twice in a row (per SKILL.md thresholds), don't progress. Hold, or step back one level, and check recovery before blaming fitness.
- **HIT progresses by volume of work first** (e.g. 30/15 3 × 13 → 3 × 15 → 4 × 13; 4 × 8 → 5 × 8 → 6 × 8), then by the +2 % calibration step in the HIT section. Never both in the same week.
- Use `icu_search_intervals` to anchor progression to what the athlete has actually done, not to what the template says comes next.

---

## Session library

TSS estimates below assume a ~15-min warm-up and ~10-min cool-down in Z1–Z2.

### Heavy domain: sweet spot (heuristic, see above)

| Level | Main set | Time in zone | Session TSS (approx.) |
|---|---|---|---|
| Entry | 3 × 10 min @ 88–92 %, 5 min easy | 30 min | ~60–70 |
| Intermediate | 3 × 15 min @ 90–94 %, 5 min easy (or 2 × 20) | 40–45 min | ~75–85 |
| Advanced | 2 × 30 min @ 90 % or 4 × 15 min @ 92–94 % | 60 min | ~100–110 |
| Extension | 1 × 60–90 min @ 88–90 % within a long ride | 60–90 min | ride-dependent |

### Heavy domain: moderate-intensity intervals (MIT)

- **5–7 × 10–14 min @ 90 % FTP** (range 88–93 %), 2–3 min easy. This is the format used in the Norwegian moderate-intensity trials, which improved power at 4 mmol lactate by ~4–4.5 % in well-trained cyclists. The trials paced by RPE 14–15 ("hard but controlled"). Here the %FTP target is used, with HR creep as the check.

### Threshold

- **Standard**: 2 × 20 min @ 95–100 %, 10 min easy (~80–90 TSS). Progress toward 3 × 15 or 2 × 25 before raising watts.
- **Over-unders**: 3–4 sets of 6–9 min alternating 1 min @ 105–110 % / 2 min @ 90–95 %, 5 min easy between sets. Count them as **threshold work, not a VO2max stimulus**: low-amplitude variation adds no time near VO2max. They're useful for races with repeated surges (attacks, punchy terrain, crosswinds). Check `athlete_profile` for whether the current target event demands this.
- Threshold work should leave the rider tired but not destroyed. If every threshold session is a survival exercise, FTP is set too high or recovery is short. Check the HR creep and the readiness verdict before cutting watts.

### High-intensity (VO2max-type) intervals

**Prescribe in % FTP, as fixed watt targets.** Every HIT session gets concrete watts from the FTP in `athlete_profile`, and execution is graded against that target with the normal ±3 % rule (SKILL.md → Fixed thresholds). Note: the trials themselves paced these formats as "highest power sustainable across all reps". A fixed %FTP is the more reproducible choice, but because a 20-min FTP can sit several percent off an individual's true threshold, the targets are **calibrated from the data** (rule below), not left static.

| Format | Prescription (% FTP) | Evidence | Use |
|---|---|---|---|
| **30/15s (Rønnestad)** | 3 sets × 13 × (30 s @ **120 %** / 15 s @ ~50 %), 3 min easy between sets. Calibration range 115–130 %. 15-s recoveries **active easy pedalling, not coasting**. Progress to 3 × 15 or 4 × 13 | Strongest cycling-specific longitudinal support (larger VO2max and 40-min power gains than 4 × 5 min), but small, well-trained, mostly male samples | Default HIT session A |
| **4–6 × 8 min** (Seiler 4 × 8) | **103 %** (range 100–106 %), 2–3 min easy | Beat 4 × 4 and 4 × 16 in recreational cyclists (small RCT) | Default HIT session B, especially early in a block |
| **5 × 5 min with surges** | 5–6 × 5 min @ **103 %** with three 30-s surges @ **125 %** per rep (at 0:30, 2:00, 3:30), 2–3 min easy | More time ≥ 90 % VO2max than steady reps, **acute data only** | HIT session B variant |
| **4–5 × 4–5 min** | **110 %** (range 106–115 %), first 30 s of each rep @ 120 %, recovery 2–4 min | Solid, but lost to 30/15 in Rønnestad's trials | Occasional variant |
| **Climbing VO2 5–6 × 3 min** | **115 %** (range 112–120 %) on a sustained climb, 3 min easy | Short reps accumulate little time near VO2max in less-trained riders | Occasional, event-specific (climbing races per `athlete_profile`) only |

**Calibration rule (per format, based on the data, not feel):**
- Start each format at the default % above.
- All reps ✅, set trend "holding", HR creep ≤ ~5 bpm in two consecutive sessions of that format → raise the target by **+2 % FTP** next time.
- ❌ (settled mean > 8 % under target, "fading" > 5 %, or reps cut) in two consecutive sessions **with a green readiness verdict** → lower the target by **−3 %**. With amber/red readiness it's fatigue: keep the target, fix recovery.
- Record the current calibrated % per format in `training_plan` (block field "Weekly quality structure"), so the next session starts from it. Never move FTP itself because of HIT calibration.

- **Dose**: ~2 HIT sessions/week in loading weeks is the evidence-typical dose. A third adds little and costs recovery. Never within 48 h of a key event.
- **Format differences are smaller than consistency.** A well-executed mesocycle of almost any sensible HIT format works. Doing it every week matters more than picking the perfect protocol. Rotate formats every block to keep execution fresh.
- Judge HIT by settled power held across the set, not by whether HR hits a number.

### Endurance (Z2)

- **Long Z2**: 2–5 h at 60–75 % FTP, steady. Ideally outdoors with terrain. Fuel it (SKILL.md carb table). An under-fueled long ride trains durability poorly and inflates decoupling.
- **Durability ride**: long Z2 with a 20–40 min sweet-spot or tempo effort in the last hour (after ≥ 1,500–2,000 kJ). It targets the fatigued curve directly and is the most useful long-ride variant for an FTP-focused rider.
- **Tempo-spiced Z2**: long ride with 1–2 × 20 min at 80–85 % folded in. Use sparingly. It's the easiest way to drift into grey-zone training.

### Recovery

- **Easy spin**: 30–60 min, < 55 % FTP. Goal: blood flow, not stimulus.
- **Off**: legitimately off the bike. Use it.

---

## Strength training

Heavy strength work (≥ ~80 % 1RM: e.g. squats, leg press, split squats, deadlifts; 3–4 sets of 4–6 reps, full recovery), added to rather than replacing riding. A 2025 meta-analysis found a **moderate effect on time-trial and time-to-exhaustion performance** but no significant effect on VO2max, with low certainty of evidence. So it's worth offering, not worth insisting on.

- **Base/off-season**: 2 sessions/week.
- **Build**: 1 maintenance session/week, ≥ 48 h before key interval sessions, never the day before.
- **Race/taper weeks**: drop it or keep one light session early in the week.

Ask whether the athlete does any. If not, suggest it once per off-season, not every week. Record it in `athlete_profile` → Constraints.

---

## How to know FTP is actually rising

- **eFTP from intervals.icu** rises consistently for > 2 weeks — note this connector's tools don't expose an eFTP field; this only works when the athlete pastes their own intervals.icu dashboard/screenshot showing it. Don't claim to be tracking eFTP proactively between pastes.
- **Power-curve PBs** in the 20- and 60-min regions
- **Settled power at the same HR** in comparable sessions (`icu_search_intervals`, matched on duration/intensity) creeps up
- **20-min test** done fresh, after a real warm-up and a real all-out effort. New FTP ≈ 0.95 × 20-min power. The individual error vs the true threshold is large (limits of agreement around ±9 %), so treat test FTP as an estimate.
- **Critical-power check**: two maximal efforts (e.g. 3 and 12 min, same session or on separate fresh days), computed from the two points by hand (standard two-point CP model: CP = (t₂·P₂ − t₁·P₁) / (t₂ − t₁)) — this connector's `icu_get_power_curves` doesn't return a CP-model field itself, only the raw curve, so the two efforts have to be pulled and the model applied explicitly, not assumed to come back pre-computed. If CP and test FTP disagree by > ~5 %, say so. If sweet-spot or threshold sessions feel inconsistent (some trivial, some impossible), suspect the anchor before the athlete.
- **Ramp test** if preferred: best 1-min power × 0.75 ≈ FTP. It is less specific to long-form FTP and tends to overestimate riders with a big anaerobic capacity. Use it as a direction check.
- **Subjective**: sessions at the old FTP feel meaningfully easier. Real, but not enough on its own.

FTP changes are proposed with evidence and written to `athlete_profile` only after the athlete confirms (SKILL.md → FTP and profile updates).

## Re-testing cadence

Test FTP every 4–8 weeks, ideally at the end of a recovery week (TSB ≥ 0). Don't test mid-block, because fatigue masks the true number. If eFTP and the power curve are rising on their own, formal testing is less critical.

---

## When FTP plateaus

If 6+ weeks of consistent loading hasn't moved eFTP:

1. **Check HIT consistency first.** Count HIT sessions over the last 6 weeks from the Metrics lines (`type=VO2`). If it's < 1/week on average, restore 2/week before anything else. This is the most common hidden cause.
2. **Re-run the limiter diagnosis** and shift emphasis accordingly.
3. **Check recovery**: sleep, life stress, HRV trend, total TSS vs the CTL formula. Chronic overreaching feels like a training plateau.
4. **Check base and distribution**: if Z2 volume shrank or easy days drifted into Z3, fix that.
5. **Vary the stimulus**: a new HIT format (see table), durability rides, or one **1-week moderate-intensity block** (below). Change the format, not just the watts.
6. **Check the FTP anchor**: a plateau in eFTP with rising comparable-session power may just be a stale or mis-set FTP (CP check above).
7. **Body composition**: only if the athlete has stated it as a goal (SKILL.md → Body composition). Never a default lever, and never during a build or within 3 weeks of a target event.

### Concentrated blocks (optional, with caution)

- **1-week moderate-intensity block**: 6 MIT sessions (5–7 × 10–14 min @ 88–93 % FTP) in 7 days, then ~6 easy days. It improved 4-mmol power vs regular training in a randomised crossover of well-trained cyclists. Use at most once every 8–12 weeks, only with a green readiness trend, good sleep and no illness in the prior weeks.
- **HIT shock weeks** (e.g. five 30/15 sessions in 6 days): equivocal evidence, and high dropout in the trials (respiratory infections, "excessive total load"). Don't use them for this athlete unless explicitly requested and recovery is excellent.
- Neither block nor traditional periodisation has been shown to be superior over 8–12 weeks. The default stays traditional 3 : 1 (or 2 : 1) loading.

---

## Recovery is part of training

Adaptation happens during recovery, not during the ride. If sleep is short, life stress is high, or nutrition is off, adaptation suffers. Factor in recovery state, not just session prescription.

Signs the athlete needs more recovery, not more training:

- Resting HR > 5 bpm above baseline for several days
- 7-day HRV average below the athlete's normal range (see `references/daily-review.md`)
- HR suppressed at familiar power (can't get HR up in intervals) or unusually high at familiar power
- Settled power fading in intervals that were previously ✅
- Motivation drop, sleep disruption, mood
- TSB below −20 for > 2 weeks without a planned recovery week

Tell the athlete this honestly when you see it.

---

## Evidence basis (what the rules above rest on)

| Claim | Evidence strength | Key sources |
|---|---|---|
| Polarised ≈ pyramidal overall. Slight pyramidal edge for recreational athletes | Moderate (IPD network meta-analysis; subgroup is hypothesis-generating) | Rosenblat, Seiler et al., *Sports Med* 2025; Silva Oliveira et al., *Sports Med* 2024 |
| More volume ≠ larger gains in trained cyclists (over typical 6–12-week interventions) | Moderate (cycling meta-analysis) | Cove et al., *J Sci Med Sport* 2025 |
| Plans without HIT underperform; HIT raises threshold power | Moderate (trials where the comparator had zero HIT) | Neal 2013; Stöggl & Sperlich 2014; Rønnestad 2015 |
| 30/15 > 4 × 5 min | Moderate (small, well-trained samples; gap narrows under self-pacing) | Rønnestad 2015/2020/2021; Appelhans et al. 2025 |
| 4 × 8 min (maximal sustainable in the trial; ~100–106 % FTP here) works well for recreational cyclists | Low–moderate (small RCT) | Seiler et al. 2013 |
| Moderate-intensity interval blocks raise 4-mmol power | Moderate (randomised crossover, n = 30) | Mølmen et al., *MSSE* 2025; Rønnestad et al., *EJSS* 2025 |
| Sweet spot 88–94 % FTP as a specific band | None direct (coaching convention) | — |
| 20-min FTP ≈ threshold for an individual | Weak (wide individual limits of agreement) | Borszcz et al., *IJSPP* 2019 |
| Heavy strength training improves TT performance | Low certainty (meta-analysis) | Llanos-Lagos et al., *Eur J Appl Physiol* 2025 |

**What this evidence doesn't settle for this athlete:** almost all interval-format trials used well-trained, mostly male riders (VO2max ~65–74) in Norwegian labs. Applying them to an 8–12 h/week amateur is extrapolation. The trials showing "HIT beats threshold" compared against arms with **zero** HIT. They prove that some HIT beats none, not that 2 HIT/week beats 1 HIT + 2 heavy-domain sessions. Short-intervention meta-analyses also say little about long-term durability, which is why Z2 volume stays the foundation here despite the "volume isn't associated with gains" finding. Treat the athlete's own response (Metrics lines, comparable efforts, eFTP) as the tiebreaker, and record what works in `long_term_history`.
