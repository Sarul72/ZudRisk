# ZudRisk: aimag grouping + deferred minors (approved 2026-11-08: "Approve, build")

## A. Aimag grouping (user chose: Сум/Аймаг toggle)
1. pipeline/aimags.py: dissolve soums by aimag_pcode -> site/data/aimags.geojson (22: pcode, name_mn, name_en, is_ub).
   Aimag score = soum risk weighted by census stock SU (census_year of the stage), as validate's aimag rho;
   counts per class; UB unscored. Written per hindcast winter and for the outlook: site/data/aimag_<label>.json.
2. Site: header toggle "Сум | Аймаг" (aria-pressed). Aimag mode colours 22 aimags; popup risk, class, soum count per class.
   Soum mode draws aimag borders. Sidebar "Аймгууд" table sorted by risk; row click/Enter zooms to the aimag.

## B. Deferred minors
v0.3: depth-weighted density (rerun hindcast); ~/.cdsapirc missing url/key and submit without jobID -> RuntimeError;
valid_time units assert; snow-comparison.md 3 decimals.
v0.4: asof no-flag run; app.js render branches on the loaded view not sel.value; unseen() only for months after
data_through; esc pooled.n; bad/missing --through -> message; era5 falls back to cached files if CDS unreachable;
grid assert compares coordinates.

Order: B -> A pipeline -> site -> browser -> review -> commit.
