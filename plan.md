# ZudRisk: what next

Written 2026-11-12, after the round below worked through the 2026-11-08 list in its order. Each idea that changes the
score or the model carries the rule that decides it, fixed before the run.

## Next

### 1. Turn on GitHub Pages (one setting)

- **Why.** The workflow is in (`.github/workflows/pages.yml`), but Pages serves nothing until it is switched on.
- **What.** In the repository on GitHub: Settings -> Pages -> Build and deployment -> Source: **GitHub Actions**.
  Then Actions -> Pages -> Run workflow, or push anything under `site/`. The site appears at
  <https://sarul72.github.io/ZudRisk/>.
- **Needs from you.** The click, signed in as Sarul72.

### 2. Run the daily iron-dzud test

- **Why.** The code is in (`pipeline.thaw`); the data is not, because it needs the CDS account.
- **What.** `uv run python -m pipeline.thaw --fetch`, then `uv run python -m pipeline.thaw`.
- **Decision rule.** Kept only if, added to the model, held-out soum rho and AUC both rise (now 0.372 and 0.745).
  If kept: `z_thaw` joins `FEATURES` in `pipeline.model` before `past_mortality`, and hindcast runs again.
- **Effort.** 100 CDS requests, two to six hours of download. The outcome is uncertain.

### 3. Daily update on Windows

- **Why.** The launchd agent was for the Mac. The project now lives on a Windows PC.
- **What.** The `schtasks` line in README ("Monthly outlook update"). `pipeline.update` now commits and pushes
  `site/data` itself after it publishes a stage.
- **Needs from you.** One `git push` by hand first, so Git keeps the GitHub sign-in.

## Done in this round (2026-11-12)

| Idea | Outcome |
|---|---|
| Publish online | Pages workflow serving `site/`; `pipeline.update` commits and pushes `site/data` after a new stage. Pages still needs the setting above. |
| Colour the map by chance | Soum and aimag maps coloured by the chance of losses >= 5 % (six steps, <5 % to >=50 %), legend in both languages, classes one click away. A stage with Brier skill <= 0 keeps the classes; none has. |
| Herd composition in the model | Held-out soum rho 0.372 -> 0.352, AUC 0.745 -> 0.732. Both fell, so not used (`pipeline.herdmix`). |
| A chance for each aimag | Fitted on the 525 aimag-winters per stage. Held-out Brier skill: Oct 0.05, Nov 0.21, Dec 0.20, Jan 0.25, Feb 0.23, Mar 0.23. Shown in the aimag popup, the aimag table and the map. |
| Iron dzud from daily data | Code and test in (`pipeline.thaw`); waiting for the CDS download (Next, 2). |
| Header on 1280-1600 px screens | The subtitle had shrunk to a narrow column (header 311 px at 1400 px); it now wraps to its own row (132 px). |

## Done in the round before (2026-11-08)

| Idea | Outcome | Commit |
|---|---|---|
| Train the model on the 2000/01-2010/11 aimag-winters too | AUC rose 0.727 -> 0.745; rho fell 0.380 -> 0.372. The fixed score still ranks better. | `1f6f642` |
| SEAS5 seasonal forecast in the October stage | It lowered that stage's skill (soum rho 0.221 -> 0.090). Tested, not used. | `a9193e1` |
| Iron dzud from monthly melt and rain on snow | No relation to losses (rho 0.02-0.05). Tested, not used. | `58f672a` |
| Risk as a chance of losses of 5 % or more | Shown in the soum popup. Brier skill runs from 0.037 (Oct) to 0.121 (Jan). | `f9d1b54` |
| Daily outlook update | `pipeline.update` and a launchd agent, installed on the Mac | `8bd2169` |
| Phone-sized controls and readable charts | Header 271 -> 167 px on a phone; no control under 44 px | `283f65a` |
