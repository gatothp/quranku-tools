import json

with open("bbox/p003.json") as f:
    boxes = json.load(f)["boxes"]

with open("bbox_ayat/p003.json") as f:
    results = json.load(f)["boxes"]

print("Ayah assignments and markers:")
for b in boxes[:12]:
    r = next((r for r in results if r["ayat"] == b["ayat"]), None)
    if r:
        print(f"  Ayah {b['ayat']:>2}: marker_y={b['y']:>4}, line={r['line']:>2}, strips={len(r['strips'])}")

print("\nStrip details for ayahs 8-10:")
for ayat_num in [8, 9, 10]:
    r = next((r for r in results if r["ayat"] == ayat_num), None)
    if r:
        print(f"\n  Ayah {ayat_num}:")
        for s in r['strips']:
            print(f"    Strip on line {s['line']}: y={s['y']}, x={s['x']}, w={s['width']}")
