"""Official dzud designations by soum, for checking the Resolution 286 view (spec 2026-11-13, plan task 3).

NAMEM classifies soums under Resolution 286 every dekad, but publishes no table. A few releases name the soums in
running text, and two IFRC appeals reproduce them in tables. data/source/dzud_official_lists.csv holds those lists
as printed:
  - nema.gov.mn/post/151603 (2023-12-30) and /153062 (mid-February 2024);
  - zarig.mn/1327 (2023-01-26) and hunnu.mn/r/1209 (2023-02-27);
  - news.mn/r/2846354 (2026-01-27);
  - IFRC MDRMN006 (2016-12-26, dzud and near-dzud not split) and MDRMN011 (2020-01-12).
The research behind them: docs/research/official-dzud-lists.md.

Each list is one snapshot on one date, not the winter's whole story. A soum missing from a snapshot was not
assessed as dzud that day; that does not mean it never was that winter. Where a printed total differs from the
names given, the names are kept as given:
  - 2023-12-30 white: 80 names in 16 aimags against "81 in 17";
  - zarig.mn: 23 and 45 names, Baganuur in both lists;
  - hunnu.mn: 22 white names against "23", 42 near-dzud against "41" (a missing comma fixed: "Булган, Халхгол").
The two IFRC lists were rebuilt from scrambled PDF text (each province count and total checked); worth a look
against the PDFs before relying on a single soum.

This module matches the printed names to ZudRisk's soums (pcode) and writes data/derived/dzud_official.csv."""
import csv
import difflib
import re
import sys
from pathlib import Path

SRC = Path("data/source/dzud_official_lists.csv")
OUT = Path("data/derived/dzud_official.csv")
CATEGORIES = ("iron", "white", "white_moderate", "black", "dzud_any")
# names that differ from the boundary file's, beyond spelling: (aimag, printed, ZudRisk name)
ALIASES = {
    ("Хөвсгөл", "Khatgal"): "Алаг-Эрдэнэ",  # Khatgal is Alag-Erdene's centre
    ("Хэнтий", "Undurkhaan"): "Хэрлэн",  # the aimag centre's soum was renamed Kherlen
    ("Хэнтий", "Өндөрхаан"): "Хэрлэн",
    ("Дорнод", "Чулуухороот"): "Чулуунхороот",
    ("Дархан-Уул", "Хонго"): "Хонгор",
    ("Хэнтий", "Өлзийт"): "Хэрлэн",  # Kherlen's former name, as zarig.mn prints it: "Хэрлэн (Өлзийт)"
    ("Хэнтий", "Ulziit"): "Хэрлэн",
    ("Архангай", "Их-Тамир"): "Их тамир",
}
# Left unmatched on purpose: Bayan-Ulgii's Tsagaannuur (a soum since 2014, not in the boundary file, inside
# Ulaankhus there) and Ulaanbaatar's "Terelj" (not a district)
_LAT = str.maketrans({"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z",
                      "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "ө": "u", "п": "p",
                      "р": "r", "с": "s", "т": "t", "у": "u", "ү": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
                      "ш": "sh", "щ": "sh", "ъ": "", "ы": "ii", "ь": "i", "э": "e", "ю": "yu", "я": "ya"})


def latin_key(name: str) -> str:
    """A Mongolian name in IFRC's English spelling, letters only: Өндөрхангай -> undurkhangai."""
    return re.sub(r"[^a-z]", "", name.lower().translate(_LAT))


def ifrc_key(name: str) -> str:
    """An English spelling reduced the same way; IFRC writes Е as ye/e and Ү, У, Ө all as u."""
    k = re.sub(r"[^a-z]", "", name.lower())
    return "e" + k[2:] if k.startswith("ye") else k


def clean(printed: str) -> str:
    """Drop a former name in brackets: Ерөө (Бугант) -> Ерөө."""
    return re.sub(r"\s*\(.*?\)\s*", " ", printed).strip()


def match(aimag: str, printed: str, names: dict[str, str]) -> tuple[str | None, str]:
    """(pcode, how) for a printed soum in its aimag; names maps the aimag's ZudRisk names to pcodes."""
    if (aimag, printed) in ALIASES:
        return names.get(ALIASES[(aimag, printed)]), "alias"
    p = clean(printed)
    if (aimag, p) in ALIASES:
        return names.get(ALIASES[(aimag, p)]), "alias"
    if p in names:
        return names[p], "exact"
    if re.search(r"[a-z]", p, re.I):  # IFRC's English spelling
        key = ifrc_key(p)
        scored = sorted(((difflib.SequenceMatcher(None, key, ifrc_key(latin_key(n))).ratio(), n) for n in names), reverse=True)
        if scored and scored[0][0] >= 0.8 and (len(scored) < 2 or scored[0][0] > scored[1][0]):
            return names[scored[0][1]], "latin"
        return None, "none"
    # the last name before a verb carries a case ending: Түмэнцогтод, Халхголд, Баяндунд
    stems = [n for n in names if p.startswith(n) and len(p) - len(n) <= 3]
    if stems:
        return names[max(stems, key=len)], "suffix"
    close = difflib.get_close_matches(p, list(names), n=1, cutoff=0.85)
    return (names[close[0]], "close") if close else (None, "none")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from pipeline.boundaries import load_soums
    by_aimag: dict[str, dict[str, str]] = {}
    for s in load_soums():
        by_aimag.setdefault(s["aimag_mn"], {})[s["name_mn"]] = s["pcode"]
    with SRC.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    bad = [r for r in rows if r["category"] not in CATEGORIES or r["aimag"] not in by_aimag]
    if bad:
        sys.exit(f"unknown category or aimag: {bad[:3]}")
    out, unmatched, loose = [], [], []
    for r in rows:
        pcode, how = match(r["aimag"], r["soum"], by_aimag[r["aimag"]])
        out.append({**r, "pcode": pcode or "", "match": how})
        if pcode is None:
            unmatched.append(f"{r['as_of']} {r['aimag']} {r['soum']}")
        elif how in ("latin", "close"):
            name = next(n for n, pc in by_aimag[r["aimag"]].items() if pc == pcode)
            loose.append(f"{r['aimag']}: {r['soum']} -> {name}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, [*rows[0].keys(), "pcode", "match"])
        w.writeheader()
        w.writerows(out)
    print(f"{OUT}: {len(out)} rows, {len(out) - len(unmatched)} matched; unmatched: {unmatched}")
    print("matched by spelling, check: " + "; ".join(sorted(set(loose))))


def check() -> None:
    assert latin_key("Өндөрхангай") == "undurkhangai" and latin_key("Цэцэн-Уул") == "tsetsenuul"
    assert ifrc_key("Yeruu") == ifrc_key(latin_key("Ерөө")) == "eruu"
    names = {"Түмэнцогт": "A", "Халхгол": "B", "Баяндун": "C", "Ерөө": "D", "Хэрлэн": "E", "Өндөрхангай": "F",
             "Алаг-Эрдэнэ": "G", "Түвшинширээ": "H", "Баянхутаг": "I"}
    assert match("Сүхбаатар", "Түмэнцогтод", names) == ("A", "suffix")
    assert match("Дорнод", "Халхголд (Сүмбэр)", names) == ("B", "suffix")
    assert match("Дорнод", "Баяндунд", names) == ("C", "suffix")
    assert match("Сэлэнгэ", "Ерөө (Бугант)", names) == ("D", "exact")
    assert match("Хэнтий", "Undurkhaan", names) == ("E", "alias")
    assert match("Увс", "Undurkhangai", names) == ("F", "latin")
    assert match("Хөвсгөл", "Алаг-Эрдэнэ (Хатгал)", names) == ("G", "exact")
    assert match("Сүхбаатар", "Түвшинши", {"Түвшинширээ": "H"})[0] is None, "a cut name is not guessed"
    assert match("Хэнтий", "Атлантис", names) == (None, "none")
    print("official check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
