"""The 21 aimags and Ulaanbaatar as a second map level: shapes dissolved from the soums, and each aimag's score
as its soums' risk weighted by their herds, the same aggregation validate uses for the aimag rho."""
import json
import sys

import shapely

from pipeline.boundaries import load_soums
from pipeline.export import SITE, feature, soum_shapes
from pipeline.nso import sheep_units
from pipeline.score import risk_class


def dissolve(soums: list[dict]) -> dict[str, object]:
    by: dict[str, list] = {}
    for s in soums:
        by.setdefault(s["aimag_pcode"], []).append(s["geom"])
    return {a: shapely.union_all(g) for a, g in by.items()}


def herd_weights(soums: list[dict], herds: dict, census: int) -> dict[str, float]:
    """Each soum's census herd in sheep units, the weight its risk carries in its aimag."""
    out = {}
    for s in soums:
        su = sheep_units(herds.get((s["pcode"], census, "stock"), {}))
        if su:
            out[s["pcode"]] = su
    return out


def summary(soums: list[dict], rows: dict[str, dict], weights: dict[str, float]) -> dict[str, dict]:
    """Per aimag: herd-weighted mean risk, its class, and how many soums fall in each class."""
    out: dict[str, dict] = {}
    acc: dict[str, list[float]] = {}
    for s in soums:
        a = out.setdefault(s["aimag_pcode"], {"risk": None, "risk_class": None, "counts": [0] * 5, "n": 0})
        r = rows.get(s["pcode"], {})
        if r.get("risk_class") is not None:
            a["counts"][r["risk_class"]] += 1
            a["n"] += 1
        w = weights.get(s["pcode"], 0.0)
        if r.get("risk") is not None and w > 0:
            t = acc.setdefault(s["aimag_pcode"], [0.0, 0.0])
            t[0], t[1] = t[0] + r["risk"] * w, t[1] + w
    for a, (num, den) in acc.items():
        out[a]["risk"] = round(num / den, 4)
        out[a]["risk_class"] = risk_class(out[a]["risk"])  # the class of the number the page shows
    return out


def write_shapes() -> None:
    """Dissolved from the soums as the map draws them, so an aimag border lies exactly on soum borders."""
    shapes = soum_shapes()
    soums = [{**s, "geom": shapes[s["pcode"]]} for s in load_soums()]
    first = {}
    for s in soums:
        first.setdefault(s["aimag_pcode"], s)
    feats = [feature(g, {"pcode": a, "name_mn": first[a]["aimag_mn"], "name_en": first[a]["aimag_en"],
                         "is_ub": first[a]["is_ub"]}, simplify=False) for a, g in dissolve(soums).items()]
    out = SITE / "aimags.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, separators=(",", ":")))
    print(f"{out}: {len(feats)} aimags, {out.stat().st_size / 1e6:.2f} MB")


def write_scores(label: str, rows: dict[str, dict], herds: dict, census: int, site=SITE) -> None:
    soums = load_soums()
    (site / f"aimag_{label}.json").write_text(json.dumps(summary(soums, rows, herd_weights(soums, herds, census))))


def check() -> None:
    from shapely.geometry import box
    soums = [{"pcode": "A1", "aimag_pcode": "X", "geom": box(0, 0, 1, 1)},
             {"pcode": "A2", "aimag_pcode": "X", "geom": box(1, 0, 2, 1)},
             {"pcode": "B1", "aimag_pcode": "Y", "geom": box(5, 5, 6, 6)}]
    shapes = dissolve(soums)
    assert set(shapes) == {"X", "Y"} and abs(shapes["X"].area - 2.0) < 1e-9, shapes
    rows = {"A1": {"risk": 1.0, "risk_class": 4}, "A2": {"risk": -1.0, "risk_class": 0},
            "B1": {"risk": None, "risk_class": None}}
    s = summary(soums, rows, {"A1": 3.0, "A2": 1.0, "B1": 2.0})
    assert s["X"]["risk"] == 0.5 and s["X"]["risk_class"] == 3, s  # (3*1 - 1*1) / 4; 0.5 opens "high"
    assert s["X"]["counts"] == [1, 0, 0, 0, 1] and s["X"]["n"] == 2, s
    assert s["Y"] == {"risk": None, "risk_class": None, "counts": [0, 0, 0, 0, 0], "n": 0}, s
    herds = {("A1", 2025, "stock"): {"camel": 0, "horse": 0, "cattle": 0, "sheep": 2.0, "goat": 0},
             ("A2", 2024, "stock"): {"camel": 0, "horse": 0, "cattle": 0, "sheep": 9.0, "goat": 0}}
    assert herd_weights(soums, herds, 2025) == {"A1": 2.0}, "only the census asked for weighs"
    edge = summary(soums, {"A1": {"risk": 0.49996, "risk_class": 2}}, {"A1": 1.0})["X"]
    assert edge["risk"] == 0.5 and edge["risk_class"] == 3, edge  # the class read from the number shown
    print("aimags check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else write_shapes()
