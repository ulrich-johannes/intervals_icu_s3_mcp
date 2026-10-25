# Food analysis

When a food photo arrives, the job is to give the user **kcal, protein (g), fat (g), carbs (g)** that they can trust enough to log. They are calorie-tracking, not chasing perfection — so be useful and honest about uncertainty rather than fake-precise.

## Process

### 1. Identify what's on the plate

Name every visible component. If something is ambiguous (sauce, oil, dressing), say what you're assuming. If a component is hidden (under another item, behind the plate edge), flag it — don't silently ignore it.

### 2. Estimate portion sizes

Use visible reference points for scale:

- Standard cutlery (a dinner fork is ~20 cm; a teaspoon is ~5 ml; a tablespoon ~15 ml)
- Plate size (a standard dinner plate is ~26–28 cm)
- Hand size if a hand is visible (palm ≈ 100 g lean protein for an average adult)
- Bottles/cans of known size (a 0.33 L can, a 0.5 L bottle)
- Common items (a slice of bread is ~25–35 g, an egg ~50 g)

If there are no good scale references, say so and give a range rather than a single number.

### 3. Account for cooking method

Cooking method changes calories dramatically — usually because of added fat:

- Pan-fried / sautéed: assume ~1 tbsp oil (~120 kcal, 14 g fat) per portion unless clearly dry
- Deep-fried: more fat than you think — fries typically absorb 5–10 g oil per 100 g
- Grilled / steamed / boiled / baked dry: no added fat
- Buttered bread, dressed salads, mayo-based sauces: visible coating means significant fat — call it out

### 4. Compute macros

Use standard reference values (USDA or BLS / Bundeslebensmittelschlüssel level — both are fine):

- **Carbs**: 4 kcal/g
- **Protein**: 4 kcal/g
- **Fat**: 9 kcal/g
- **Alcohol** (relevant for beer/wine): 7 kcal/g — note that in Bavaria/Munich, a 0.5 L Helles is ~210 kcal, ~17 g carbs, no fat, no protein

Round to sensible numbers. Don't claim "37.4 g carbs" — the underlying estimate isn't that precise. Round protein/fat/carbs to nearest 1 g for small portions and nearest 5 g for meals; round kcal to nearest 10.

### 5. Output

Default to a compact table:

```
| Item | kcal | P (g) | F (g) | C (g) |
|---|---|---|---|---|
| Grilled chicken breast (~150 g) | 250 | 47 | 5 | 0 |
| Brown rice (~200 g cooked) | 230 | 5 | 2 | 48 |
| Steamed broccoli (~150 g) | 50 | 4 | 1 | 7 |
| Olive oil drizzle (~1 tbsp) | 120 | 0 | 14 | 0 |
| **Total** | **650** | **56** | **22** | **55** |
```

Below the table, in 1–2 sentences:

- Note any assumptions that materially affect the numbers (e.g., "I assumed the rice is plain brown; if it's pilaf or has butter, add ~50 kcal and 5 g fat")
- Note total uncertainty as a rough ±range ("ballpark ±10%")
- **Do not** volunteer fueling-strategy advice, ride-timing context, or coaching commentary unless the user asks. The default is: estimate the food, stop.

### When to expand beyond the table

If the user asks "is this good as a pre-ride breakfast" or "is this enough for my recovery", *then* switch into coach mode: connect the macros to the day's training. Typical anchors:

- **Pre-ride (2–3 h before)**: 1–3 g/kg carbs, low fat, low fiber, modest protein
- **Post-ride recovery (within ~1 h)**: 1–1.2 g/kg carbs + ~0.3 g/kg protein
- **Daily protein target for training cyclist**: ~1.6–2.0 g/kg bodyweight, spread across the day
- **Endurance training day total**: typically 5–8 g/kg carbs depending on volume
- **Hard interval / race day total**: 7–10 g/kg carbs

## Common pitfalls to avoid

- **Under-counting oils and dressings** — a "salad" with a heavy dressing can be 600 kcal. Look for shine/coating.
- **Confusing cooked vs raw weights** — 150 g cooked rice ≠ 150 g raw (raw is ~3× denser in carbs). Always estimate as served.
- **Misjudging portion of high-calorie items** — nuts, cheese, oils, peanut butter are very calorie-dense; small visual differences = big calorie differences. Be conservative (high) on these.
- **Missing hidden carbs** — breading, glazes, sauces, sugar in dressings.
- **Restaurant portions are larger than home portions** — if the photo is clearly a restaurant plate, weight your estimates upward.

## When the photo is genuinely unclear

If you can't see the food well, can't identify a component, or the photo is blurry, just say so and ask for more info or a better photo rather than guessing. A wrong number the user trusts is worse than no number.
