"""Mongolia's natural zones (high mountain, taiga, forest steppe, steppe, desert steppe, desert) from the RESOLVE
Ecoregions 2017 polygons (Dinerstein et al. 2017, CC BY 4.0), each ecoregion assigned to its zone by name; and each
soum's zone as the one covering most of it. Read with the standard library: a shapefile is a few structs."""
import json
from collections import Counter
import struct
import sys
import zipfile
from pathlib import Path

import shapely
from shapely.geometry import LinearRing, Polygon

from pipeline.boundaries import load_soums
from pipeline.export import SITE, feature, soum_shapes

URL = "https://storage.googleapis.com/teow2016/Ecoregions2017.zip"
RAW = Path("data/raw/Ecoregions2017.zip")
BBOX = (87.0, 41.0, 120.5, 52.5)  # Mongolia with a margin; records outside are never parsed
ZONE_ORDER = ["mountain", "taiga", "forest_steppe", "steppe", "desert_steppe", "desert"]
# Each ecoregion touching Mongolia, by its RESOLVE name, to the zone of Mongolia's own physical geography
ZONES = {
    "Altai alpine meadow and tundra": "mountain",
    "Khangai Mountains alpine meadow": "mountain",
    "Sayan alpine meadows and tundra": "mountain",
    "Khangai Mountains conifer forests": "taiga",
    "Sayan montane conifer forests": "taiga",
    "Trans-Baikal conifer forests": "taiga",
    "Selenge-Orkhon forest steppe": "forest_steppe",
    "Daurian forest steppe": "forest_steppe",
    "Altai montane forest and forest steppe": "forest_steppe",
    "Mongolian-Manchurian grassland": "steppe",
    "Sayan Intermontane steppe": "steppe",
    "Eastern Gobi desert steppe": "desert_steppe",
    "Gobi Lakes Valley desert steppe": "desert_steppe",
    "Great Lakes Basin desert steppe": "desert_steppe",
    "Alashan Plateau semi-desert": "desert",
    "Junggar Basin semi-desert": "desert",
    "Taklimakan desert": "desert",  # a sliver where the two datasets' borders disagree, in the south-west Gobi
}


def zone_of(eco_name: str) -> str:
    if eco_name not in ZONES:
        raise KeyError(f"no natural zone for ecoregion {eco_name!r}: add it to ZONES")
    return ZONES[eco_name]


def polygon_of(content: bytes):
    """A shapefile polygon record (type 5) as one shapely geometry; clockwise rings are outer, the rest holes."""
    if struct.unpack_from("<i", content)[0] != 5:
        return None
    nparts, npts = struct.unpack_from("<2i", content, 36)
    parts = list(struct.unpack_from(f"<{nparts}i", content, 44)) + [npts]
    xy = struct.unpack_from(f"<{2 * npts}d", content, 44 + 4 * nparts)
    outers, holes = [], []
    for a, b in zip(parts, parts[1:]):
        ring = LinearRing([(xy[2 * i], xy[2 * i + 1]) for i in range(a, b)])
        (holes if ring.is_ccw else outers).append(shapely.make_valid(Polygon(ring)))
    return shapely.difference(shapely.union_all(outers), shapely.union_all(holes)) if holes else shapely.union_all(outers)


def _bbox_hits(content: bytes) -> bool:
    if struct.unpack_from("<i", content)[0] != 5:
        return False
    x0, y0, x1, y1 = struct.unpack_from("<4d", content, 4)
    return x0 <= BBOX[2] and x1 >= BBOX[0] and y0 <= BBOX[3] and y1 >= BBOX[1]


def iter_shp(f):
    f.read(100)
    while head := f.read(8):
        _, words = struct.unpack(">2i", head)
        yield f.read(2 * words)


def read_dbf(f):
    _, _, _, _, n, hdr_len, _ = struct.unpack("<4BIHH20x", f.read(32))
    fields = []
    for _ in range((hdr_len - 33) // 32):  # 32-byte descriptors, then the 0x0D terminator
        d = f.read(32)
        fields.append((d[:11].split(b"\0")[0].decode(), d[16]))
    f.read(hdr_len - 32 - 32 * len(fields))
    for _ in range(n):
        rec = f.read(1 + sum(ln for _, ln in fields))
        if rec[:1] == b"*":
            continue
        out, i = {}, 1
        for name, ln in fields:
            raw = rec[i:i + ln]
            try:
                out[name] = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                out[name] = raw.decode("latin-1").strip()
            i += ln
        yield out


def dominant(geom, zones: dict) -> tuple[str, float] | None:
    """The zone covering most of a soum, with its share of the soum's area."""
    shares = {z: geom.intersection(g).area / geom.area for z, g in zones.items()}
    best = max(shares, key=shares.get, default=None)
    return None if best is None or shares[best] == 0 else (best, round(shares[best], 3))


def ecoregions() -> list[tuple[str, object]]:
    """(ECO_NAME, geometry) for every ecoregion whose box touches Mongolia's."""
    if not RAW.exists():
        from pipeline.http import download
        download(URL, RAW)
    out = []
    with zipfile.ZipFile(RAW) as z, z.open("Ecoregions2017.shp") as shp, z.open("Ecoregions2017.dbf") as dbf:
        for content, row in zip(iter_shp(shp), read_dbf(dbf)):
            if _bbox_hits(content):
                out.append((row["ECO_NAME"], polygon_of(content)))
    return out


def main() -> None:
    soums = load_soums()
    country = shapely.union_all([s["geom"] for s in soums])
    inside = [(n, g.intersection(country)) for n, g in ecoregions() if g.intersects(country)]
    inside = [(n, g) for n, g in inside if g.area > 1e-6]
    missing = sorted({n for n, _ in inside if n not in ZONES})
    if missing:
        sys.exit(f"ecoregions in Mongolia with no zone: {missing}")
    zones = {z: shapely.union_all([g for n, g in inside if ZONES[n] == z]) for z in ZONE_ORDER
             if any(ZONES[n] == z for n, _ in inside)}
    feats = [feature(g, {"zone": z, "ecoregions": sorted({n for n, _ in inside if ZONES[n] == z})}) for z, g in zones.items()]
    (SITE / "zones.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
    by_soum = {s["pcode"]: dominant(s["geom"], zones) for s in soums}
    (SITE / "soum_zones.json").write_text(json.dumps(by_soum, separators=(",", ":")))
    total = country.area
    print("zones: " + ", ".join(f"{z} {g.area / total:.1%}" for z, g in zones.items()) +
          f"; soums by zone {dict(sorted(Counter(v[0] for v in by_soum.values() if v).items()))}")


def check() -> None:
    import io
    from shapely.geometry import box
    square = [(0, 0), (0, 4), (4, 4), (4, 0), (0, 0)]  # clockwise: an outer ring
    hole = [(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)]  # counter-clockwise: a hole
    pts = square + hole
    body = struct.pack("<i4d2i", 5, 0, 0, 4, 4, 2, len(pts)) + struct.pack("<2i", 0, 5) + \
        b"".join(struct.pack("<2d", x, y) for x, y in pts)
    g = polygon_of(body)
    assert abs(g.area - 12.0) < 1e-12, g.area  # 16 less the hole's 4
    assert polygon_of(struct.pack("<i", 0)) is None, "a null shape is skipped"

    fields = [(b"ECO_NAME", b"C", 20), (b"BIOME", b"N", 3)]
    head = struct.pack("<4BIHH20x", 3, 26, 1, 1, 1, 32 + 32 * len(fields) + 1, 1 + 23)
    desc = b"".join(n.ljust(11, b"\0") + t + b"\0" * 4 + bytes([ln]) + b"\0" * 15 for n, t, ln in fields)
    rec = b" " + "Gobi désert".encode("utf-8").ljust(20) + b" 13"
    rows = list(read_dbf(io.BytesIO(head + desc + b"\r" + rec + b"\x1a")))
    assert rows == [{"ECO_NAME": "Gobi désert", "BIOME": "13"}], rows

    assert zone_of("Khangai Mountains alpine meadow") == "mountain"
    assert zone_of("Mongolian-Manchurian grassland") == "steppe"
    try:
        zone_of("Atlantis reef")
        raise AssertionError("an ecoregion with no zone must be named, not dropped")
    except KeyError as e:
        assert "Atlantis reef" in str(e)

    zones = {"steppe": box(0, 0, 3, 1), "desert": box(3, 0, 4, 1)}
    assert dominant(box(0, 0, 4, 1), zones) == ("steppe", 0.75)
    assert dominant(box(10, 10, 11, 11), zones) is None
    print("zones check: ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
