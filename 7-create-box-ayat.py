"""
Create bounding boxes for complete ayahs (verses) based on marker positions.

Layout rules (Quran page, RTL):
- Page has 15 lines, read top-to-bottom, right-to-left within each line.
- Each ayah marker (circle number) indicates where that ayah ENDS.
- Each marker has a bounding box (x, y, width, height) that defines the marker's visual position.

Box generation:
- Each ayah spans vertically from the current marker's Y to the next marker's Y.
- For each line in that vertical range, create ONE box per ayah.
- Horizontal extent is determined by marker positions:
  - First line (where previous marker appears): from marker_right to img_width
  - Marker line (where current marker appears): from 0 to marker_x
  - Other lines: full width (0 to img_width)
"""

import cv2
import json
import os
from pathlib import Path

os.makedirs("ayat_boxes", exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def load_bbox(page_num):
    path = f"bbox/p{page_num:03d}.json"
    if not Path(path).exists():
        print(f"❌ Not found: {path}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("boxes", [])


def get_image(page_num):
    for p in [f"mushaf/p{page_num:03d}.jpg",
              f"D:\\apps\\android\\quran\\app\\src\\main\\assets\\files\\mushaf\\madinah_v2\\p{page_num:03d}.jpg"]:
        if Path(p).exists():
            img = cv2.imread(p)
            if img is not None:
                return img, p
    return None, None


# ── core algorithm ───────────────────────────────────────────────────────────

def build_ayah_boxes(boxes, img_h, img_w, lines_per_page=15):
    """
    Build bounding boxes for ayahs using bbox marker positions.

    Each ayah number circle marks where that ayah ENDS.
    - The circle BELONGS to the next ayah's rectangle (appears at its left boundary).
    - Vertical span: from the line the PREVIOUS marker is on, to the line THIS marker is on.
    - On the previous-marker line : box starts at prev_marker_x (left of prev circle) → full right
    - On the current-marker line  : box starts at 0 → cur_marker_x (left of cur circle)
    - On lines between            : full width
    """
    line_height = img_h / lines_per_page

    def marker_line(b):
        """Line index the centre of marker b sits on."""
        return int((b["y"] + b["height"] / 2) / line_height)

    # Sort markers by actual reading order: surat then ayat
    sorted_boxes = sorted(boxes, key=lambda b: (b.get("surat", 0), b.get("ayat", 0)))

    results = []

    for idx, cur in enumerate(sorted_boxes):
        cur_line = marker_line(cur)
        cur_x    = cur["x"]

        if idx == 0:
            prev_line = -1          # virtual line above page
            prev_x    = img_w       # no previous circle
        else:
            prev      = sorted_boxes[idx - 1]
            prev_line = marker_line(prev)
            prev_x    = prev["x"]

        # Lines this ayah covers:
        #   - If prev_line >= 0 and prev marker didn't consume the full line:
        #       start at prev_line (partial box from prev circle leftward)
        #   - Otherwise start at prev_line + 1
        #   - End at cur_line
        if prev_line >= 0:
            prev = sorted_boxes[idx - 1]
            # If previous marker was at left edge (x<=0), it consumed the whole line
            # so this ayah starts on the next line
            if prev["x"] <= 0:
                start_line = max(0, prev_line + 1)
            else:
                start_line = max(0, prev_line)
        else:
            start_line = 0
        end_line = cur_line

        if start_line > end_line:
            start_line = end_line

        for line_idx in range(start_line, end_line + 1):
            top_y    = line_idx * line_height
            bottom_y = (line_idx + 1) * line_height

            if line_idx == prev_line and idx > 0:
                # Previous-marker line: this ayah starts at left edge of prev circle
                left_x  = max(0, prev_x)
                right_x = img_w
            elif line_idx == cur_line:
                # Current-marker line: this ayah ends at left edge of cur circle
                left_x  = 0
                right_x = max(0, cur_x) if cur_x > 0 else img_w
            else:
                # Middle line: full width
                left_x  = 0
                right_x = img_w

            left_x  = max(0, min(img_w, left_x))
            right_x = max(0, min(img_w, right_x))

            if right_x > left_x:
                results.append({
                    "id":     cur["id"],
                    "surat":  cur.get("surat", 0),
                    "ayat":   cur.get("ayat", 0),
                    "x":      int(left_x),
                    "y":      int(top_y),
                    "width":  int(right_x - left_x),
                    "height": int(bottom_y - top_y),
                })

    return results


# ── visualisation ─────────────────────────────────────────────────────────────

def visualize(page_num, img, results):
    """Draw each ayah box as a red rectangle."""
    overlay = img.copy()

    for r in results:
        x = int(r["x"])
        y = int(r["y"])
        w = int(r["width"])
        h = int(r["height"])
        
        # Draw red rectangle
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Add ayah number label
        ayat = r.get("ayat", "?")
        cv2.putText(overlay, str(ayat),
                    (img.shape[1] - 40, y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 0, 0), 2)

    vis_path = f"ayat_boxes/p{page_num:03d}_visualization.jpg"
    if Path(vis_path).exists():
        try:
            Path(vis_path).unlink()
        except Exception as e:
            print(f"⚠️  Could not delete old visualization: {e}")
    cv2.imwrite(vis_path, overlay)
    print(f"📸 Visualization saved → {vis_path}")


# ── main ──────────────────────────────────────────────────────────────────────

def process_page(page_num, visualize_flag=True):
    print(f"\nProcessing page {page_num} ...")

    boxes = load_bbox(page_num)
    if boxes is None:
        return False

    img, img_path = get_image(page_num)
    if img is None:
        print(f"❌ Image not found for page {page_num}")
        return False

    img_h, img_w = img.shape[:2]
    print(f"   Image: {img_w}×{img_h}  |  Markers: {len(boxes)}")

    results = build_ayah_boxes(boxes, img_h, img_w, lines_per_page=15)

    for r in results:
        print(f"   Ayah {r['ayat']:>3}: box ({r['x']},{r['y']}) {r['width']}×{r['height']}")

    out_path = f"ayat_boxes/p{page_num:03d}.json"
    vis_path = f"ayat_boxes/p{page_num:03d}_visualization.jpg"

    # Delete old JSON file to avoid lock/permission issues
    if Path(out_path).exists():
        try:
            Path(out_path).unlink()
        except Exception as e:
            print(f"⚠️  Could not delete {out_path}: {e}")

    # Delete old visualization file
    if Path(vis_path).exists():
        try:
            Path(vis_path).unlink()
        except Exception as e:
            print(f"⚠️  Could not delete {vis_path}: {e}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"page": page_num,
                   "image_width": img_w,
                   "image_height": img_h,
                   "boxes": results}, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved → {out_path}")

    if visualize_flag:
        visualize(page_num, img, results)

    return True


if __name__ == "__main__":
    page_input = input("Enter page number or range (e.g., 3 or 3-5): ").strip()

    if "-" in page_input:
        try:
            s, e = map(int, page_input.split("-"))
            page_range = list(range(s, e + 1))
        except Exception:
            print("❌ Invalid range"); exit(1)
    else:
        try:
            page_range = [int(page_input)]
        except Exception:
            print("❌ Invalid page number"); exit(1)

    ok = sum(process_page(p, visualize_flag=True) for p in page_range)
    print(f"\n✅ Done: {ok}/{len(page_range)} pages → ayat_boxes/")
