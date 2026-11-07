"""NSO Mongolia livestock stock and adult losses per soum (PxWeb API, no login), joined to COD soums."""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from pipeline.boundaries import UB_PCODE, load_soums
from pipeline.http import get_json, post_json

BASE = "https://data.1212.mn/api/v1/en/NSO/Industry,%20service/Livestock/"
TABLES = {"stock": "DT_NSO_1001_021V1.px", "loss": "DT_NSO_1001_029V1.px"}
TYPES = {"1": "horse", "2": "cattle", "3": "camel", "4": "sheep", "5": "goat"}
# Sheep units per head: Nandintsetseg et al. 2018, Sci. Rep. 8:14769
SHEEP_UNITS = {"camel": 5, "horse": 7, "cattle": 6, "sheep": 1, "goat": 0.9}
YEARS = range(2000, 2026)
BATCH = 60
OUT = Path("data/derived/livestock.csv")
OUT_AIMAG = Path("data/derived/livestock_aimag.csv")


def norm(name: str) -> str:
    """Spelling-insensitive key: NSO and COD write the same soum with and without 'сум', spaces, hyphens."""
    s = name.strip().lower().replace("ё", "е")
    s = re.sub(r"\s+сум$", "", s)
    s = s.replace("гөвь", "говь")
    return re.sub(r"[\s\-]", "", s)


def sheep_units(by_type: dict[str, float]) -> float | None:
    if any(t not in by_type for t in SHEEP_UNITS):
        return None
    return sum(SHEEP_UNITS[t] * by_type[t] for t in SHEEP_UNITS)


def crosswalk(nso_regions: dict[str, str], soums: list[dict]) -> tuple[dict[str, str], list[str]]:
    """Map NSO 5-digit soum codes to COD pcodes by (aimag, soum) name; return unmatched NSO codes."""
    by_name = {(norm(s["aimag_mn"]), norm(s["name_mn"])): s["pcode"] for s in soums}
    xwalk, unmatched = {}, []
    for code, name in nso_regions.items():
        if len(code) != 5:
            continue
        key = (norm(nso_regions[code[:3]]), norm(name))
        if key in by_name:
            xwalk[code] = by_name[key]
        else:
            unmatched.append(code)
    taken = [p for p in xwalk.values()]
    if len(taken) != len(set(taken)):
        dup = sorted({p for p in taken if taken.count(p) > 1})
        raise ValueError(f"several NSO soums map to {dup}: their herds would overwrite each other")
    return xwalk, sorted(unmatched)


def aimag_crosswalk(nso_regions: dict[str, str], soums: list[dict]) -> dict[str, str]:
    """NSO 3-digit aimag codes to COD aimag pcodes by name; Ulaanbaatar is left out like everywhere else."""
    by_name = {norm(s["aimag_mn"]): s["aimag_pcode"] for s in soums if s["aimag_pcode"] != UB_PCODE}
    return {c: by_name[norm(t)] for c, t in nso_regions.items() if len(c) == 3 and norm(t) in by_name}


def parse(resp: dict, years: dict[str, str], xwalk: dict[str, str], kind: str) -> list[tuple]:
    rows = []
    for cell in resp["data"]:
        t, region, y = cell["key"]
        value = cell["values"][0]
        if t not in TYPES or region not in xwalk or value in ("..", ""):
            continue
        # PxWeb writes "-" for nil
        rows.append((xwalk[region], int(years[y]), kind, TYPES[t], 0.0 if value == "-" else float(value)))
    return rows


def main() -> None:
    meta = get_json(BASE + TABLES["stock"])
    var = {v["code"]: v for v in meta["variables"]}
    regions = dict(zip(var["Бүс"]["values"], var["Бүс"]["valueTexts"]))
    xwalk, unmatched = crosswalk(regions, load_soums())
    print(f"matched {len(set(xwalk.values()))}, unmatched NSO {unmatched}")
    rows = fetch(xwalk)
    write(OUT, "pcode", rows)
    print(f"{len(rows)} rows -> {OUT}; {fill_camel(_read(OUT))[1]} soum-years read camel '..' as 0")
    axwalk = aimag_crosswalk(regions, load_soums())
    print(f"aimags matched {len(axwalk)}")
    arows = fetch(axwalk)
    write(OUT_AIMAG, "aimag_pcode", arows)
    print(f"{len(arows)} rows -> {OUT_AIMAG}")


def fetch(xwalk: dict[str, str]) -> list[tuple]:
    codes = sorted(xwalk)
    rows = []
    for kind, table in TABLES.items():
        tmeta = get_json(BASE + table)
        yvar = next(v for v in tmeta["variables"] if v["code"] == "Он")
        years = {c: t for c, t in zip(yvar["values"], yvar["valueTexts"]) if int(t) in YEARS}
        for i in range(0, len(codes), BATCH):
            body = {"query": [
                {"code": "Малын төрөл", "selection": {"filter": "item", "values": list(TYPES)}},
                {"code": "Бүс", "selection": {"filter": "item", "values": codes[i:i + BATCH]}},
                {"code": "Он", "selection": {"filter": "item", "values": list(years)}},
            ], "response": {"format": "json"}}
            rows += parse(post_json(BASE + table, body), years, xwalk, kind)
    return rows


def write(path: Path, key: str, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([key, "year", "kind", "type", "thousand_head"])
        w.writerows(sorted(rows))


def fill_camel(herds: dict[tuple, dict[str, float]]) -> tuple[dict, int]:
    """NSO leaves camel as '..' where it later prints 0 (no camels in that soum, e.g. MN4101 in 2009 vs 2012).
    Reading that as missing would drop mostly northern, camel-free soums from every early winter."""
    n = 0
    for by_type in herds.values():
        if "camel" not in by_type and all(t in by_type for t in SHEEP_UNITS if t != "camel"):
            by_type["camel"] = 0.0
            n += 1
    return herds, n


def _read(path: Path) -> dict[tuple, dict[str, float]]:
    out: dict[tuple, dict[str, float]] = defaultdict(dict)
    with path.open() as f:
        for r in csv.reader(f):
            if r[1] != "year":
                out[(r[0], int(r[1]), r[2])][r[3]] = float(r[4])
    return dict(out)


def load_livestock() -> dict[tuple, dict[str, float]]:
    return fill_camel(_read(OUT))[0]


def load_livestock_aimag() -> dict[tuple, dict[str, float]]:
    """Keyed (aimag_pcode, year, kind); NSO's own aimag totals, the only losses it gives for 2010."""
    return fill_camel(_read(OUT_AIMAG))[0]


def check() -> None:
    assert norm("Баянхонгор сум") == norm("Баянхонгор")
    assert norm("Гурванбулаг") == norm("Гурван булаг")
    assert norm("Өмнөгөвь") == norm("Өмнөговь")
    assert norm("Баян-Өлгий") == "баянөлгий"
    assert abs(sheep_units({"camel": 1, "horse": 1, "cattle": 1, "sheep": 1, "goat": 1}) - 19.9) < 1e-9
    assert sheep_units({"camel": 1, "horse": 1}) is None
    sample = {"data": [
        {"key": ["4", "34801", "1"], "values": ["120.5"]},
        {"key": ["5", "34801", "1"], "values": [".."]},
        {"key": ["0", "34801", "1"], "values": ["999"]},
        {"key": ["4", "99999", "1"], "values": ["1"]},
    ]}
    rows = parse(sample, years={"1": "2024"}, xwalk={"34801": "MN4804"}, kind="stock")
    assert rows == [("MN4804", 2024, "stock", "sheep", 120.5)], rows
    dash = parse({"data": [{"key": ["3", "34801", "1"], "values": ["-"]}]}, {"1": "2024"}, {"34801": "MN4804"}, "stock")
    assert dash == [("MN4804", 2024, "stock", "camel", 0.0)], dash
    four = {"horse": 1.0, "cattle": 1.0, "sheep": 1.0, "goat": 1.0}
    filled, n = fill_camel({("A", 2009, "stock"): dict(four), ("B", 2009, "stock"): {"sheep": 1.0}})
    assert filled[("A", 2009, "stock")]["camel"] == 0.0 and n == 1
    assert "camel" not in filled[("B", 2009, "stock")]
    soums = [{"pcode": "MN8301", "aimag_pcode": "MN83", "aimag_mn": "Баян-Өлгий", "name_mn": "Өлгий"}]
    try:
        crosswalk({"183": "Баян-Өлгий", "18301": "Өлгий", "18399": "Өлгий сум"}, soums)
        raise AssertionError("two NSO codes on one soum must raise")
    except ValueError:
        pass
    assert aimag_crosswalk({"183": "Баян-Өлгий", "511": "Улаанбаатар", "18301": "Өлгий"}, soums) == {"183": "MN83"}
    print("nso check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
