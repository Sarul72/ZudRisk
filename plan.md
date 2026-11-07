# ZudRisk: what next

Written 2026-11-08, after v0.5 and the follow-ups listed under "Done in this round". The ideas are ranked, and the
first is the recommended one. Each idea that changes the score or the model carries the rule that decides it. The
rule is fixed before the run, as it was for the earlier ideas.

## Next

### 1. Publish the site online (GitHub Pages)

- **Why.** The site lives only on this Mac, so nobody else can open it.
- **What.**
  - A GitHub repository, with Pages serving `site/`.
  - `pipeline.update` commits and pushes `site/data` after it publishes a stage.
- **Needs from you.** The GitHub account, and the choice to make the repository and the site public.
- **Watch.**
  - `site/data` is 14 MB; Pages allows 1 GB.
  - Nothing under `data/raw/` and no credential is ever committed.
- **Effort.** About an hour.

### 2. Colour the map by chance, not class

- **Why.** The chance of losses of 5 % or more appears only in the soum popup. The map still shows five classes.
- **What.**
  - A sequential scale in percent, read from `site/data/calibration.json`.
  - A legend in both languages.
  - The classes kept as an option.
- **Decision rule.** A stage whose held-out Brier skill is 0 or below keeps the classes.
- **Effort.** About an hour.

### 3. Herd composition in the model

- **Why.** Species differ in how they come through a dzud. The model sees only the herd's size in sheep units.
- **What.** Each species' share of the soum's census becomes a feature in `pipeline.model`. The data is already in
  `data/derived/livestock.csv`.
- **Decision rule.** Kept only if held-out soum rho and AUC both rise. They are now 0.372 and 0.745.
- **Effort.** One to two hours.

### 4. A chance for each aimag

- **Why.** The aimag view shows a herd-weighted risk but no chance. The soum calibration does not carry over to an
  aimag mean.
- **What.** `pipeline.calibrate` is fitted again on the 525 aimag-winters (2000/01-2024/25), and the result goes in
  the aimag popup.
- **Decision rule.** Shown only where held-out Brier skill is above 0.
- **Effort.** About an hour.

### 5. Iron dzud from daily data

- **Why.**
  - The monthly test found nothing (README, "Tested and not used").
  - A crust is a one-day thaw, which a monthly mean hides.
- **What.** ERA5-Land daily maximum temperature and snow depth for Nov-Feb, counted as thaw days on snow per soum.
- **Decision rule.** The same as for the monthly test: kept only if held-out soum rho and AUC both rise.
- **Effort.** About 125 CDS requests, which take two to six hours to download. The outcome is uncertain.

## Done in this round

| Idea | Outcome | Commit |
|---|---|---|
| Train the model on the 2000/01-2010/11 aimag-winters too | AUC rose 0.727 -> 0.745; rho fell 0.380 -> 0.372. The fixed score still ranks better. | `1f6f642` |
| SEAS5 seasonal forecast in the October stage | It lowered that stage's skill (soum rho 0.221 -> 0.090). Tested, not used. | `a9193e1` |
| Iron dzud from monthly melt and rain on snow | No relation to losses (rho 0.02-0.05). Tested, not used. | `58f672a` |
| Risk as a chance of losses of 5 % or more | Shown in the soum popup. Brier skill runs from 0.037 (Oct) to 0.121 (Jan). | `f9d1b54` |
| Daily outlook update | `pipeline.update` and a launchd agent, installed on this Mac | `8bd2169` |
| Phone-sized controls and readable charts | Header 271 -> 167 px on a phone; no control under 44 px | `283f65a` |
