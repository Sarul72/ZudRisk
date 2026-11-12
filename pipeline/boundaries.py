"""Soum boundaries from OCHA COD-AB (NSO source, CC BY-IGO), trimmed to the fields the pipeline uses."""
import ast
import functools
import json
import sys
import zipfile
from pathlib import Path

from shapely.geometry import shape

from pipeline.http import download

COD_URL = (
    "https://data.humdata.org/dataset/a9b0a8a6-cb14-448e-b35c-aa5eb51b0557/resource/"
    "de6b11d3-767d-449f-99fc-80c5b4e9abe3/download/mng_admin_boundaries.geojson.zip"
)
RAW = Path("data/raw/cod_mng.zip")
OUT = Path("data/derived/soums.geojson")
UB_PCODE = "MN11"


def is_aimag_centre(soum: dict) -> bool:
    """NSO numbers each aimag's centre soum 01 (Dalanzadgad MN4601, Baruun-Urt MN2201, ...); Ulaanbaatar is apart."""
    return not soum["is_ub"] and soum["pcode"].endswith("01")


def trim(props: dict) -> dict:
    return {
        "pcode": props["adm2_pcode"],
        "aimag_pcode": props["adm1_pcode"],
        "aimag_mn": props["adm1_name1"],
        "aimag_en": props["adm1_name"],
        "name_mn": props["adm2_name1"],
        "name_en": props["adm2_name"],
        "area_km2": props["area_sqkm"],
        "is_ub": props["adm1_pcode"] == UB_PCODE,
    }


@functools.cache
def _parsed() -> tuple[dict, ...]:
    return tuple({**f["properties"], "geom": shape(f["geometry"])} for f in json.loads(OUT.read_text(encoding="utf-8"))["features"])


def load_soums() -> list[dict]:
    """Parsed once per process; each caller gets fresh dicts over the shared (immutable) shapes."""
    return [dict(s) for s in _parsed()]


def main() -> None:
    if not RAW.exists():
        download(COD_URL, RAW)
    with zipfile.ZipFile(RAW) as z:
        fc = json.loads(z.read("mng_admin2.geojson"))
    feats = [{"type": "Feature", "properties": trim(f["properties"]), "geometry": f["geometry"]}
             for f in fc["features"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(feats)} soums, {sum(f['properties']['is_ub'] for f in feats)} UB")


def unnamed_encodings(src: str) -> list[int]:
    """Lines with text-mode file I/O that leaves the encoding to the locale (cp1252 on Windows, which breaks Cyrillic)."""
    bad = []
    for n in ast.walk(ast.parse(src)):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)) or any(k.arg == "encoding" for k in n.keywords):
            continue
        mode = n.args[0].value if n.args and isinstance(n.args[0], ast.Constant) else None if n.args else "r"
        is_path_open = n.func.attr == "open" and isinstance(mode, str) and "b" not in mode and not (
            isinstance(n.func.value, ast.Name) and n.func.value.id == "z")  # zip members are bytes
        if n.func.attr in ("read_text", "write_text") or is_path_open or (
                n.func.attr == "run" and any(k.arg == "text" for k in n.keywords)):
            bad.append(n.lineno)
    return bad


def check() -> None:
    assert unnamed_encodings('Path("a").read_text()\nPath("a").open("w")\nsubprocess.run(["git"], text=True)') == [1, 2, 3]
    assert unnamed_encodings('Path("a").read_text(encoding="utf-8")\nz.open("x.shp")\nPath("a").open("rb")') == []
    bad = {f.name: lines for f in sorted(Path(__file__).parent.glob("*.py"))
           if (lines := unnamed_encodings(f.read_text(encoding="utf-8")))}
    assert not bad, f"text I/O without encoding=\"utf-8\": {bad}"
    ub = trim({"adm2_pcode": "MN1101", "adm2_name": "Baganuur", "adm2_name1": "Багануур",
               "adm1_pcode": "MN11", "adm1_name": "Ulaanbaatar", "adm1_name1": "Улаанбаатар",
               "area_sqkm": 51.5, "version": "v01"})
    soum = trim({"adm2_pcode": "MN4804", "adm2_name": "Adaacag", "adm2_name1": "Адаацаг",
                 "adm1_pcode": "MN48", "adm1_name": "Dundgovi", "adm1_name1": "Дундговь",
                 "area_sqkm": 3321.9, "version": "v01"})
    assert soum == {"pcode": "MN4804", "aimag_pcode": "MN48", "aimag_mn": "Дундговь",
                    "aimag_en": "Dundgovi", "name_mn": "Адаацаг", "name_en": "Adaacag",
                    "area_km2": 3321.9, "is_ub": False}, soum
    assert ub["is_ub"] is True
    first, again = load_soums(), load_soums()
    assert first[0]["geom"] is again[0]["geom"], "the boundaries file is parsed once per process"
    first[0]["pcode"] = "changed"
    assert again[0]["pcode"] != "changed" and load_soums()[0]["pcode"] != "changed", "each caller gets its own dicts"
    print("boundaries check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
