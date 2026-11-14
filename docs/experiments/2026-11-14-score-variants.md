# Score variants: pre-registration (2026-11-14)

Written and committed before any variant is computed. The results go in a later commit, under "Results" below. Nothing
here changes the site or the published score until the owner decides.

## Baseline (as published)

- **Pre-registered pool:** soum-winters with losses in the pre-registered winters 2013/14, 2015/16, 2021/22, 2022/23,
  2023/24 (`hindcast.DZUD` plus the two calmest normal winters). Spearman ρ **0.600**, n = 1,683.
- **Every soum-winter:** 2011/12–2024/25. Spearman ρ **0.440**, n = 4,688.

Risk = Σ wₖ zₖ / Σ wₖ over the indicators present, with w = snow 0.41, cold 0.35, pressure 0.29, summer 0.24 (literature,
fixed before validation). The script must first reproduce both baseline numbers from `data/derived/indicators_*.csv`. If
it does not, it stops and reports why.

## Variants

**E1: snow and drought together.** A fifth term x = min(3, max(z_snow, 0) × max(z_summer, 0)). It is non-zero only when the
snow was deeper than normal *and* the summer worse than normal, the combination behind Resolution 286's dzud types. Weight
0.24, the smallest literature weight, so the new term cannot dominate. A soum missing either z gets no x (the term drops
out, as any absent indicator does).

**E2: how long the snow lay.** A fifth term z_days: the z-score of `snow_days` (snow-covered days, November–March) against
the soum's own winters 2001/02–2020/21. Same rules as the other indicators: population σ, clipped at ±3, needs at least
10 baseline winters. Weight 0.24, for the same reason as E1.

**E3: noise in small herds (a measurement check, not a model change).** The same published score, evaluated without the
smallest 10% of soum-winters by herd size (census sheep units before the winter), where a few deaths swing the percentage.
E3 never replaces the headline. It is reported beside it to show how much small herds move ρ.

## Decision rule

- **E1 and E2:** a variant is **kept** only if both the pre-registered ρ and the every-soum-winter ρ rise above 0.600 and
  0.440, rounded to 3 decimals. Otherwise it is **not used** and goes to README's "Tested and not used" with its numbers.
- A kept variant reaches the site only after the owner agrees, and only after the competition (2026-11-15).
- **E3:** no decision. It is reported only.
- Weights are not tuned after seeing results. If E1 and E2 both pass, they are not combined without a new pre-registration.
