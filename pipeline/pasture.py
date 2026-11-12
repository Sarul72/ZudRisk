"""Usable pasture per soum, for the grazing-pressure denominator (plan.md, task Z3).

Grazing pressure is sheep units per km² of the whole soum, so a soum that is half lake or closed forest looks half as
grazed as it is. The Environmental Information Center's hayland and pasture map (Хадлан, бэлчээрийн зураг, eic.mn,
WFS layer geodb_haylandzone) splits the country into five rangeland zones: A high-mountain meadow and steppe, B
mountain forest, C steppe, D desert, and E "Бусад газар" (other land, 4.5 % of the country: large lakes, closed
forest and the like). Every zone but E is pasture by the map's own definition; its classes 1a-8a read "Ангилалгүй"
only because their sub-classes were not split, and they are tundra and forest pasture. So a soum's pasture is its
area less its share of zone E. The map is static and undated (uploaded 2020).

The rule, fixed before the run (2026-11-13): the pasture denominator is kept only if both the pre-registered pooled
soum rho (0.596, n 1683) and the every-soum-winter rho (0.434, n 4688) rise. The aimag rho (0.547) and the learned
model's held-out soum rho and AUC (0.372, 0.745) are reported, not decided on.

The map is read once over WFS (GML in EPSG:32648, WGS 84 / UTM 48N) and projected here with the standard library;
only the derived shares are published, citing EIC as Government Resolution 85 (2010) asks."""
import csv
import math
import re
import sys
from pathlib import Path

import shapely
from shapely.geometry import Polygon

WFS = ("https://eic.mn/cgi-bin/mapserver?map=/var/www/html/geodata/geodatainfo/maps/geo.map"
       "&SERVICE=WFS&VERSION=1.0.0&REQUEST=GetFeature&TYPENAME=geodb_haylandzone")
RAW = Path("data/raw/eic_haylandzone.gml")
OUT = Path("data/derived/soum_pasture.csv")
OTHER = "E"  # zoneengid of "Бусад газар / Other": the one zone that is not pasture

# WGS 84 and the UTM scale; zone 48N's central meridian is 105 E
A, F = 6378137.0, 1 / 298.257223563
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)
K0 = 0.9996


def utm_inverse(x: float, y: float, lon0: float = 105.0) -> tuple[float, float]:
    """WGS 84 UTM, northern hemisphere, to (lon, lat) in degrees (Snyder 1987, Map projections, eq. 8-18 to 8-25)."""
    x -= 500000.0
    mu = (y / K0) / (A * (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))
    p = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
         + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    c1, t1 = EP2 * math.cos(p) ** 2, math.tan(p) ** 2
    n1 = A / math.sqrt(1 - E2 * math.sin(p) ** 2)
    r1 = A * (1 - E2) / (1 - E2 * math.sin(p) ** 2) ** 1.5
    d = x / (n1 * K0)
    lat = p - (n1 * math.tan(p) / r1) * (d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * EP2) * d ** 4 / 24
                                         + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * EP2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = (d - (1 + 2 * t1 + c1) * d ** 3 / 6
           + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * EP2 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(p)
    return lon0 + math.degrees(lon), math.degrees(lat)


def _ring(coords: str) -> list[tuple[float, float]]:
    return [utm_inverse(*map(float, pt.split(","))) for pt in coords.split()]


def parse_zones(gml: str) -> dict[str, object]:
    """GML 2 from MapServer: each feature's zoneengid and its (multi)polygon, projected to lon/lat."""
    out = {}
    for feat in gml.split("<gml:featureMember>")[1:]:
        zid = re.search(r"<ms:zoneengid>([^<]*)</ms:zoneengid>", feat).group(1)
        polys = []
        for poly in re.findall(r"<gml:Polygon[^>]*>(.*?)</gml:Polygon>", feat, re.S):
            outer = re.search(r"<gml:outerBoundaryIs>.*?<gml:coordinates>([^<]*)</gml:coordinates>", poly, re.S).group(1)
            holes = re.findall(r"<gml:innerBoundaryIs>.*?<gml:coordinates>([^<]*)</gml:coordinates>", poly, re.S)
            polys.append(shapely.make_valid(Polygon(_ring(outer), [_ring(h) for h in holes])))
        out[zid] = shapely.union_all([out[zid], *polys]) if zid in out else shapely.union_all(polys)
    return out


def pasture_share(geom, other) -> float:
    """The share of a soum that is pasture: all of it but the map's "other land"."""
    return round(1 - geom.intersection(other).area / geom.area, 4)


def load_shares(path: Path = OUT) -> dict[str, float]:
    """pcode -> pasture share; an empty dict when the file is absent, which leaves the whole soum as its area."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {r["pcode"]: float(r["pasture_share"]) for r in csv.DictReader(f)}


def main() -> None:
    from pipeline.boundaries import load_soums
    if not RAW.exists():
        from pipeline.http import download
        download(WFS, RAW)
    zones = parse_zones(RAW.read_text(encoding="utf-8"))
    if OTHER not in zones or len(zones) != 5:
        sys.exit(f"expected the five zones A-E in {RAW}, got {sorted(zones)}")
    soums = load_soums()
    country = shapely.union_all([s["geom"] for s in soums])
    covered = shapely.union_all(list(zones.values())).intersection(country).area / country.area
    if covered < 0.99:
        sys.exit(f"the pasture map covers only {covered:.1%} of the soums: projection or file wrong")
    rows = [{"pcode": s["pcode"], "pasture_share": pasture_share(s["geom"], zones[OTHER])} for s in soums]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["pcode", "pasture_share"])
        w.writeheader()
        w.writerows(rows)
    low = sorted(rows, key=lambda r: r["pasture_share"])
    print(f"{OUT}: {len(rows)} soums, map covers {covered:.2%}; under 80 % pasture: "
          f"{sum(r['pasture_share'] < 0.8 for r in rows)}; least: " + ", ".join(f"{r['pcode']} {r['pasture_share']}" for r in low[:5]))


def check() -> None:
    # on the central meridian the inverse must give 105 E and the latitude whose meridian arc is y / k0:
    # the WGS 84 meridian arc to 45 N is 4 984 944.378 m (Snyder 1987, table 3; also GeographicLib)
    lon, lat = utm_inverse(500000.0, K0 * 4984944.378)
    assert abs(lon - 105.0) < 1e-9 and abs(lat - 45.0) < 1e-6, (lon, lat)
    lon0, lat0 = utm_inverse(0.0, 0.0)
    assert abs(lat0) < 1e-9 and lon0 < 105.0, (lon0, lat0)
    west, east = utm_inverse(400000.0, 5300000.0), utm_inverse(600000.0, 5300000.0)
    assert abs((105 - west[0]) - (east[0] - 105)) < 1e-9 and abs(west[1] - east[1]) < 1e-9, "symmetric about 105 E"

    gml = ("<wfs:FeatureCollection><gml:featureMember><ms:geodb_haylandzone><ms:msGeometry><gml:MultiPolygon><gml:polygonMember>"
           "<gml:Polygon><gml:outerBoundaryIs><gml:LinearRing><gml:coordinates>"
           "500000,5300000 510000,5300000 510000,5310000 500000,5310000 500000,5300000"
           "</gml:coordinates></gml:LinearRing></gml:outerBoundaryIs></gml:Polygon></gml:polygonMember></gml:MultiPolygon>"
           "</ms:msGeometry><ms:zoneengid>E</ms:zoneengid></ms:geodb_haylandzone></gml:featureMember></wfs:FeatureCollection>")
    z = parse_zones(gml)
    assert list(z) == ["E"] and abs(z["E"].bounds[0] - 105.0) < 1e-9, z
    from shapely.geometry import box
    assert pasture_share(box(0, 0, 4, 1), box(3, 0, 5, 1)) == 0.75
    assert pasture_share(box(0, 0, 1, 1), box(5, 5, 6, 6)) == 1.0
    assert load_shares(Path("no/such/file.csv")) == {}
    print("pasture check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
