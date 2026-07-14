"""
SCRIPT: 6-create-box-ayat.py
PURPOSE: Generate complete bounding boxes for each ayah (verse) based on ayah marker positions

INPUT:
  - User: Page number or range (e.g., "3" or "3-5")
  - JSON: bbox/p###.json - Contains marker positions from circle detection (script 5)
  - Image: Quran mushaf pages (jpg) from mushaf/ or madinah_v2 folder

LAYOUT RULES (Quran page, RTL):
  - Page has 15 lines, read top-to-bottom, right-to-left within each line
  - Each ayah marker (circle) indicates where that ayah ENDS
  - Marker has bounding box (x, y, width, height) defining its visual position

BOX GENERATION METHOD:
  1. Sort markers by surat then ayat (reading order)
  2. For each ayah, determine vertical span:
     - Start: line of previous marker (or 0 if first ayah)
     - End: line of current marker
  3. For each line in span, create one box with horizontal extent:
     - Previous-marker line: from prev_x to image_width (right side, RTL tail)
     - Current-marker line: from 0 to marker_x (left side, RTL head)
     - Middle lines: full width (0 to image_width)
  4. Special case: if prev and cur markers on the SAME line:
     - RIGHT box (prev_x → img_w) belongs to previous ayah
     - LEFT box  (0 → cur_x)     belongs to current ayah
  5. Clamp coordinates to image bounds

OUTPUT:
  - JSON: bbox_ayat/p###.json - Contains complete ayah boxes with:
    * id, surat, ayat, x, y, width, height
    * image_width, image_height (for reference)
  - Console: Box coordinates for each ayah
"""

import cv2
import json
import os
from pathlib import Path

os.makedirs("bbox_ayat", exist_ok=True)

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
    Build bounding boxes for ayahs using bbox marker positions (RTL layout).

    Each ayah number circle marks where that ayah ENDS.
    Reading order: right-to-left within a line, top-to-bottom across lines.

    On a shared line where prev and cur markers meet:
      - RIGHT part (prev_x → img_w): belongs to PREVIOUS ayah (its tail, read first RTL)
      - LEFT part  (0 → cur_x):      belongs to CURRENT ayah (its head, read second RTL)

    So for each ayah:
      - prev-marker line : LEFT portion (0 → prev_x)    ← current ayah starts here
      - middle lines     : full width (0 → img_w)
      - cur-marker line  : RIGHT portion (cur_x → img_w) ← current ayah ends here (RTL tail)
    """
    line_height = img_h / lines_per_page

    def marker_line(b):
        return int((b["y"] + b["height"] / 2) / line_height)

    sorted_boxes = sorted(boxes, key=lambda b: (b.get("surat", 0), b.get("ayat", 0)))

    results = []

    for idx, cur in enumerate(sorted_boxes):
        cur_line = marker_line(cur)
        cur_x    = cur["x"]

        if idx == 0:
            prev_line = -1
            prev_x    = 0   # no previous marker: start from left edge
        else:
            prev      = sorted_boxes[idx - 1]
            prev_line = marker_line(prev)
            prev_x    = prev["x"]

        # Determine start line
        if prev_line >= 0:
            if sorted_boxes[idx - 1]["x"] <= 0:
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
                # Shared line with previous ayah:
                # LEFT part (0 → prev_x) belongs to CURRENT ayah
                left_x  = 0
                right_x = max(0, prev_x)
            elif line_idx == cur_line:
                # Last line of current ayah:
                # RIGHT part (cur_x → img_w) belongs to CURRENT ayah (RTL tail)
                left_x  = cur_x
                right_x = img_w
            else:
                # Full-width middle line
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


# ── main ──────────────────────────────────────────────────────────────────────

def process_page(page_num):
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

    out_path = f"bbox_ayat/p{page_num:03d}.json"

    # Delete old JSON file to avoid lock/permission issues
    if Path(out_path).exists():
        try:
            Path(out_path).unlink()
        except Exception as e:
            print(f"⚠️  Could not delete {out_path}: {e}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"page": page_num,
                   "image_width": img_w,
                   "image_height": img_h,
                   "boxes": results}, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved → {out_path}")

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

    ok = sum(process_page(p) for p in page_range)
    print(f"\n✅ Done: {ok}/{len(page_range)} pages → bbox_ayat/")
