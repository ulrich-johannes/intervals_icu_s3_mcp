# icTrainer workout file authoring

The athlete's indoor trainer software is **icTrainer**. Workouts are delivered as a local downloadable file (create the file and hand it to the athlete as a download) — **not** via any intervals.icu tool, which icTrainer doesn't consume from directly (and this connector has no FIT-upload tool to push to intervals.icu anyway — see "Relationship to intervals.icu / FIT files" below). If the athlete also wants the session logged/tracked in intervals.icu, that's a separate, limited-capability path, not a substitute for the local file.

## Primary method (confirmed 2026-09-26): native `.ictx` ratio format

**Use this by default.** icTrainer has its own native workout format (`.ictx`, XML-based) with a `workoutStruct` field that encodes ramps and holds directly as **%FTP ratios**, not absolute watts. Because it's ratio-based, the athlete's dynamic FTP setting in icTrainer applies automatically — the same file keeps working as FTP changes, which is exactly the athlete's stated reason for pre-building a workout library ahead of progress.

This confirmation comes from 8 real `.ictx` files the athlete built and uploaded on 2026-09-26 (`Z2x130h60percent`, `SS5x15`, `SS5x20`, `SS5x20hart`, `SS5x5`, `5x5mitSurges`, `5x8vo2max`, `3x13x30-15`) — all functioning files from the athlete's own icTrainer install, not files Claude generated and independently verified against the app. Treat the structural rules below as well-evidenced but not Claude-tested; if a newly generated file renders incorrectly, that's new information to fold back in here.

### File structure

```xml
<?xml version="1.0" ?>
<icTrainer>
  <icTrainerExercise>
    <name>WorkoutName</name>
    <code></code>
    <version>9</version>
    <sportType>Road</sportType>
    <exerciseLevel>BEGINNER|ADVANCED</exerciseLevel>
    <exerciseType>ENDURANCE|POWER|HIIT</exerciseType>
    <workoutStruct>ratio;seg1;seg2;...</workoutStruct>
    <playlist></playlist>
    <lastUpdate>YYYY-MM-DD HH:MM</lastUpdate>
    <startImage></startImage>
    <maxLevelRatioDisplay>100|120|150</maxLevelRatioDisplay>
    <ratioExercise>true</ratioExercise>
    <author></author>
    <image></image>
    <containsVideo>false</containsVideo>
    <containsAudio>false</containsAudio>
    <sequence>
      <name>WarmUp</name>
      <loops>1</loops>
      <leg>
        <level>XS</level>
        <levelRatio>30</levelRatio>
        <levelRatioEnd>50</levelRatioEnd>
        <duration>05:00</duration>
        <rpm>80</rpm>
        <bpm>60</bpm>
        <bpmDefault>true</bpmDefault>
      </leg>
      <!-- more legs -->
    </sequence>
    <!-- more sequences: main set(s), CoolDown -->
  </icTrainerExercise>
</icTrainer>
```

### `workoutStruct` encoding

A semicolon-separated string, always starting with the literal `ratio`, then one token per phase:

```
<duration_seconds>-<%FTP>                  → flat hold
<duration_seconds>-<%FTP_start>-<%FTP_end> → ramp (linear from start to end)
```

This is a flat, redundant summary of the same data the `<sequence>`/`<leg>` blocks encode structurally — build both consistently; the `<sequence>` blocks are what icTrainer actually renders, `workoutStruct` mirrors it. When a `<sequence>` has `<loops>n</loops>` with multiple `<leg>` entries, the corresponding `workoutStruct` segment repeats that leg pattern n times in sequence (not as a single collapsed token) — e.g. 13 loops of a 30s/15s leg pair become 13 repeated `30-120;15-50` pairs in `workoutStruct`, laid out flat.

**`levelRatio` and `levelRatioEnd` are %FTP values** (e.g. `90` = 90% FTP, `108` = 108% FTP), not absolute watts. This is the mechanism that gives dynamic-FTP reuse.

### Worked example: warm-up pattern (consistent across the athlete's own files)

Every file the athlete built uses close to this same warm-up shape — worth reusing as the house style:

```
420-30-50;20-90;60-50;20-100;80-50
```

= 7 min ramp 30%→50% FTP, then two short activation spikes (20s @ 90%, 60s easy, 20s @ 100%, 80s easy) before the main set. Cooldowns are consistently a single ramp segment, e.g. `600-50-30` (10 min, 50%→30% FTP) or `300-50-30` (5 min).

### Worked example: interval set with recovery (30/15 format)

From the athlete's `3x13x30-15.ictx`, one set of 13 reps:

```xml
<sequence>
  <name>Hauptteil (wiederholend)</name>
  <loops>13</loops>
  <leg>
    <level>XXL</level>
    <levelRatio>120</levelRatio>
    <duration>00:30</duration>
    <rpm>80</rpm>
    <bpm>90</bpm>
    <bpmDefault>true</bpmDefault>
  </leg>
  <leg>
    <level>XS</level>
    <levelRatio>50</levelRatio>
    <duration>00:15</duration>
    <rpm>80</rpm>
    <bpm>60</bpm>
    <bpmDefault>true</bpmDefault>
  </leg>
</sequence>
```

followed by a separate 3-minute-easy sequence between the three sets of 13. The athlete's file duplicates this 13-loop sequence three times (once per set) rather than nesting an outer loop of 3 around an inner loop of 13 — icTrainer's format doesn't appear to support nested loops, so multi-set structures with different between-set recovery need one `<sequence>` per set.

### Worked example: reps with an embedded surge (5×5 with surges)

From `5x5mitSurges.ictx` — each 5-minute rep isn't flat, it has a surge inside it, built as 4 separate legs per loop iteration:

```xml
<sequence>
  <loops>5</loops>
  <leg><levelRatio>103</levelRatio><duration>02:30</duration>.../>
  <leg><levelRatio>125</levelRatio><duration>00:30</duration>.../>
  <leg><levelRatio>103</levelRatio><duration>02:00</duration>.../>
  <leg><levelRatio>50</levelRatio><duration>04:00</duration>.../>  <!-- recovery -->
</sequence>
```

i.e. base 103% for 2:30, a 30s surge to 125%, back to 103% for 2:00 (= 5:00 total work), then 4:00 recovery — all inside one `loops=5` sequence. **Note:** the athlete's file has one surge per rep; the training plan for this format specifies 3 surges per rep. If building this format from the plan spec rather than copying the athlete's file, extend the pattern to 3× (base/surge) per rep before the recovery leg — don't silently copy the athlete's simpler version as if it matches the plan.

### Sanity-checking a new file

- Cross-check `workoutStruct`'s total duration and the sum of all `<sequence>`/`<leg>` durations against the intended workout — they must describe the same thing twice, not diverge.
- `maxLevelRatioDisplay` should be ≥ the highest `levelRatio` used (100 for endurance-only files, 120–150 for anything with HIIT/surge work).
- `exerciseType` (ENDURANCE / POWER / HIIT) and `exerciseLevel` (BEGINNER / ADVANCED) are cosmetic/library-sorting fields in the athlete's own files — set them to whatever fits, they don't appear to affect playback.
- No requirement for one-row-per-minute or any minimum waypoint density — ramps interpolate correctly and holds stay flat with just a start/end pair, unlike the legacy ERG behavior below.

## Legacy method (superseded, kept for context only): raw `.erg` import

Before this file format was known to work, `.erg` (ERG-mode, absolute watts) was the fallback, and it had a real, separately-confirmed reliability problem: sparse waypoint files (two waypoints per phase) rendered incorrectly on this athlete's install in three different ways across iterations — a collapsed flat-hold, a silently dropped trailing row, an instant jump replacing a ramp. The only reliable fix found at the time was one explicit row per minute for the whole file, in absolute watts (not %FTP), which loses the dynamic-FTP-reuse property entirely.

**Don't use `.erg` by default now that the native `.ictx` ratio format is confirmed working** — it's strictly worse for this athlete (no dynamic FTP, needs far more rows, produces UI fragmentation). Keep this section only as a fallback if a future `.ictx` file is found not to import correctly, or if the athlete ever asks for an ERG file specifically (e.g. for a different piece of software).

If ever needed again, the ERG structure is:

```
[COURSE HEADER]
VERSION = 2
UNITS = ENGLISH
DESCRIPTION = <short description>
FILE NAME = <filename>.erg
MINUTES	WATTS
[END COURSE HEADER]
[COURSE DATA]
<time in minutes, decimal>	<power in watts, absolute>
...
[END COURSE DATA]
```
with one row per minute (rounded phase boundaries), ramps linearly interpolated, holds constant, and instant steps at interval boundaries (new phase's power starting exactly at the boundary minute, no interpolation across it).

## Relationship to intervals.icu / FIT files

If the athlete also wants the session tracked in intervals.icu (separate from riding it on icTrainer): this connector has no FIT-file-upload tool at all (`icu_bulk_create_manual_activities` is numeric-summary-only, no device/file upload, so it can't carry streams or support decoupling/EF analysis of that session). The athlete would need to upload the FIT file to intervals.icu themselves through intervals.icu directly, or settle for a bare manual summary entry via `icu_bulk_create_manual_activities`. Say this plainly rather than implying this connector can push a tracked file there; don't default to attempting either automatically — ask first, since icTrainer is the actual execution path and intervals.icu tracking is a secondary, now-limited record.
