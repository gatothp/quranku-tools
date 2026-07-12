"""
Create expanded bounding boxes for complete ayahs (verses).

Layout rules (Quran page, RTL):
- Page has 15 lines, read top-to-bottom, right-to-left within each line.
- Each ayah marker (circle) sits ON the line where that ayah ENDS.
- An ayah's region starts right after the PREVIOUS ayah marker and ends at THIS ayah marker.

Box representation (simplified as list of line-strips):
  For each ayah, we produce a list of per-line rectangles that together cover
  the full ayah text. These are also stored as a bounding envelope for easy use.

Visual rule derived from reference images:
  - The PREVIOUS ayah's marker X position is the RIGHT boundary of THIS ayah's
    START portion (same line as previous marker).
  - On lines fully inside the ayah, the box is full-width.
  - On the last line (where THIS ayah's marker sits), the box goes from the
    RIGHT edge down to THIS marker's X (left boundary = 0, right = marker_x + marker_w).
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

def assign_lines(boxes, img_h, img_w, lines_per_page=15):
    """
    Assign markers to physical lines on the page.
    
    The page is divided into 15 equal-height lines.
    Each marker is assigned to the line containing its Y position.
    """
    if not boxes:
        return [0, img_h], {}

    # Calculate line height for 15 lines per page
    line_height = img_h / lines_per_page
    
    # Assign each marker to a line based on its Y position
    box_line = {}
    for b in boxes:
        line_idx = int(b["y"] / line_height)
        # Clamp to valid range
        line_idx = max(0, min(lines_per_page - 1, line_idx))
        box_line[b["id"]] = line_idx
    
    # Build line_tops array (top boundary of each line)
    line_tops = [i * line_height for i in range(lines_per_page + 1)]
    
    return line_tops, box_line


def build_ayah_boxes(boxes, img_h, img_w, lines_per_page=15):
    """
    Build bounding boxes for ayahs - ONE BOX PER LINE PER AYAH.
    
    Each ayah can span multiple lines and gets ONE BOX PER LINE.
    - If ayah spans lines 0-1, it gets 2 boxes: one on line 0, one on line 1
    - Each box covers the full width of its line (except when constrained by markers)
    - If multiple ayahs share a line, use marker X positions to split vertically
    
    Layout rules:
    - Ayah X ends where marker X is located
    - Ayah X starts after the previous ayah's marker
    - Shared line: split at marker X positions
    """
    line_tops, box_line = assign_lines(boxes, img_h, img_w, lines_per_page)

    # Sort by top-to-bottom, then right-to-left within line for reading order
    sorted_boxes = sorted(boxes, key=lambda b: (box_line[b["id"]], -b["x"]))

    # Group markers by line for easier processing
    markers_by_line = {}
    for box in sorted_boxes:
        line_idx = box_line[box["id"]]
        if line_idx not in markers_by_line:
            markers_by_line[line_idx] = []
        markers_by_line[line_idx].append(box)
    
    # Sort markers on each line by X position (left to right)
    for line_idx in markers_by_line:
        markers_by_line[line_idx].sort(key=lambda b: b["x"])

    results = []
    
    for idx, cur in enumerate(sorted_boxes):
        cur_line = box_line[cur["id"]]
        cur_marker_x = max(0, min(img_w, cur["x"]))
        
        # Get previous marker info
        if idx == 0:
            prev_line = -1
            prev_marker_x = img_w  # Right edge for RTL
        else:
            prev = sorted_boxes[idx - 1]
            prev_line = box_line[prev["id"]]
            prev_marker_x = max(0, min(img_w, prev["x"]))
        
        # Determine line range for this ayah
        # Ayah starts AFTER previous marker's line and ends at current marker's line
        if prev_line >= 0:
            start_line = prev_line + 1
        else:
            start_line = 0
        end_line = cur_line
        
        # Create one box per line this ayah spans
        for line_idx in range(start_line, end_line + 1):
            top_y = line_tops[line_idx]
            bottom_y = line_tops[line_idx + 1]
            
            # Determine horizontal extent for this line
            if line_idx == cur_line and line_idx in markers_by_line and len(markers_by_line[line_idx]) > 1:
                # Current marker line has multiple markers: use neighbor positions for split
                markers_on_line = markers_by_line[line_idx]
                cur_pos = None
                for pos, m in enumerate(markers_on_line):
                    if m["id"] == cur["id"]:
                        cur_pos = pos
                        break
                
                if cur_pos is not None:
                    if cur_pos > 0:
                        # There's a marker to the left of this one
                        left_marker_x = markers_on_line[cur_pos - 1]["x"]
                        left_x = left_marker_x
                    else:
                        # This is the leftmost marker on this line
                        left_x = 0
                    
                    if cur_pos < len(markers_on_line) - 1:
                        # There's a marker to the right of this one
                        right_marker_x = markers_on_line[cur_pos + 1]["x"]
                        right_x = right_marker_x
                    else:
                        # This is the rightmost marker on this line
                        right_x = img_w
                else:
                    # Shouldn't happen, but fallback to full width
                    left_x = 0
                    right_x = img_w
            elif line_idx == cur_line and prev_line == cur_line:
                # Current line has this marker and previous marker: split between them
                left_x = cur_marker_x
                right_x = prev_marker_x
            else:
                # Intermediate line or only marker on this line: full width
                left_x = 0
                right_x = img_w
            
            if right_x > left_x:  # Only add if valid width
                results.append({
                    "id":     cur["id"],
                    "surat":  cur.get("surat", 0),
                    "ayat":   cur.get("ayat", 0),
                    "x":      left_x,
                    "y":      top_y,
                    "width":  right_x - left_x,
                    "height": bottom_y - top_y,
                })
    
    results.sort(key=lambda r: (r["y"], -r["x"]))  # Sort by position top-to-bottom, right-to-left
    return results


# ── visualisation ─────────────────────────────────────────────────────────────

def visualize(page_num, img, results, line_tops):
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
    print(f"\n📖 Processing page {page_num} …")

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

    # Line tops for visualisation
    line_tops, _ = assign_lines(boxes, img_h, img_w)

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
        visualize(page_num, img, results, line_tops)

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
