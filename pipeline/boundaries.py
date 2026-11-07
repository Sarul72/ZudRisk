"""Soum boundaries from OCHA COD-AB (NSO source, CC BY-IGO), trimmed to the fields the pipeline uses."""
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


def load_soums() -> list[dict]:
    fc = json.loads(OUT.read_text())
    return [{**f["properties"], "geom": shape(f["geometry"])} for f in fc["features"]]


def main() -> None:
    if not RAW.exists():
        download(COD_URL, RAW)
    with zipfile.ZipFile(RAW) as z:
        fc = json.loads(z.read("mng_admin2.geojson"))
    feats = [{"type": "Feature", "properties": trim(f["properties"]), "geometry": f["geometry"]}
             for f in fc["features"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    print(f"{len(feats)} soums, {sum(f['properties']['is_ub'] for f in feats)} UB")


def check() -> None:
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
    print("boundaries check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
