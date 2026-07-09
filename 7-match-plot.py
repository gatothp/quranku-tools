import numpy as np
import cv2, json, os, openpyxl, subprocess, tempfile
from PIL import Image

# Prompt for page number
page_num = int(input("Enter page number (1-604): "))

IMAGE_PATH = f"mushaf/p{page_num:03d}.jpg"
TEMPLATE_PATH = "mushaf/circle.png"
MATCHED_JSON = f"matched_boxes_p{page_num}.json"
OUTPUT_JSON = f"circle_numbers_p{page_num}.json"
EXCEL_PATH = "files/quran.xlsx"

# Validate image exists
if not os.path.exists(IMAGE_PATH):
    print(f"❌ Image not found: {IMAGE_PATH}")
    exit(1)

print(f"\n📄 Processing page {page_num}...")
print(f"📸 Loading image: {IMAGE_PATH}")

# === STEP 1: DETECT CIRCLES USING TEMPLATE MATCHING ===
print("\n🔍 Detecting ayah circles...")

img = cv2.imread(IMAGE_PATH)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

template = cv2.imread(TEMPLATE_PATH, 0)
tw, th = template.shape[::-1]

scales = np.linspace(0.8, 1.2, 10)

results = []
seen = []

def extract_number_from_circle(gray_img, x, y, w, h):
    """Extract the Arabic number from circle using Tesseract"""
    try:
        roi = gray_img[max(0, y+h//4):min(gray_img.shape[0], y+3*h//4), 
                       max(0, x+w//4):min(gray_img.shape[1], x+3*w//4)]
        
        if roi.size < 10:
            return ""
        
        _, binary = cv2.threshold(255 - roi, 100, 255, cv2.THRESH_BINARY)
        
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tesseract_path):
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                cv2.imwrite(tmp.name, binary)
                try:
                    result = subprocess.run(
                        [tesseract_path, tmp.name, 'stdout', '-l', 'ara', '--psm', '8'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    text = result.stdout.strip()
                    os.unlink(tmp.name)
                    return text if text else ""
                except:
                    if os.path.exists(tmp.name):
                        os.unlink(tmp.name)
        
        return ""
    except:
        return ""

for scale in scales:
    resized = cv2.resize(gray, None, fx=scale, fy=scale)
    result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
    
    threshold = 0.3
    loc = np.where(result >= threshold)
    
    for pt in zip(*loc[::-1]):
        x = int(pt[0] / scale)
        y = int(pt[1] / scale)
        w = int(tw / scale)
        h = int(th / scale)
        
        # Expand bounding box by 40%
        expand = 1.4
        x = int(x - w * (expand - 1) / 2)
        y = int(y - h * (expand - 1) / 2)
        w = int(w * expand)
        h = int(h * expand)
        
        # Avoid duplicates
        too_close = False
        for (sx, sy) in seen:
            if abs(x - sx) < 20 and abs(y - sy) < 20:
                too_close = True
                break
        
        if too_close:
            continue
        
        seen.append((x, y))
        
        # Try to extract ayah number
        ayah_number = extract_number_from_circle(gray, x, y, w, h)
        
        results.append({
            "id": len(results) + 1,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "ayah_number": ayah_number
        })
        
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

# Save matched circles
with open(MATCHED_JSON, "w") as f:
    json.dump({"boxes": results}, f, ensure_ascii=False, indent=2)

detected_circles = len(results)
print(f"✅ Detected {detected_circles} circles")

# === STEP 2: VALIDATE AGAINST EXCEL ===
print("\n📊 Validating against Excel...")

try:
    wb = openpyxl.load_workbook(EXCEL_PATH)
    sheet = wb['hal-ayat']
    expected_ayat = None
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row[0] == page_num:
            expected_ayat = row[1]
            break
except Exception as e:
    print(f"⚠️  Could not load Excel file: {e}")
    expected_ayat = None

if expected_ayat:
    if detected_circles == expected_ayat:
        print(f"✅ Page {page_num}: {detected_circles} circles detected (matches {expected_ayat} ayat)")
    else:
        print(f"⚠️  Page {page_num}: {detected_circles} circles detected but {expected_ayat} ayat expected")
else:
    print(f"ℹ️  Page {page_num}: {detected_circles} circles detected")

# === STEP 3: INTERACTIVE EDITOR ===
print("\n✏️  Opening editor for manual number assignment...")

# Load boxes
with open(MATCHED_JSON, "r") as f:
    data = json.load(f)
    boxes = data["boxes"]

# Load and resize image for display
img_display = cv2.imread(IMAGE_PATH)
height, width = img_display.shape[:2]
scale = 650 / height
new_width = int(width * scale)
img_display = cv2.resize(img_display, (new_width, 650))
clone = img_display.copy()

# Scale boxes to match resized image
scaled_boxes = []
for box in boxes:
    scaled_boxes.append({
        "id": box["id"],
        "x": int(box["x"] * scale),
        "y": int(box["y"] * scale),
        "width": int(box["width"] * scale),
        "height": int(box["height"] * scale),
        "ayah_number": box.get("ayah_number", "")
    })

current_box_idx = 0
editing = False
number_input = ""

def draw_boxes():
    temp = clone.copy()
    for i, b in enumerate(scaled_boxes):
        x, y, w, h = b["x"], b["y"], b["width"], b["height"]
        color = (0, 255, 0) if i == current_box_idx else (100, 100, 100)
        cv2.rectangle(temp, (x, y), (x+w, y+h), color, 2)
        
        text = f"#{i+1}"
        if b["ayah_number"]:
            text += f" {b['ayah_number']}"
        cv2.putText(temp, text, (x, y-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    if editing:
        cv2.rectangle(temp, (20, 20), (400, 80), (200, 200, 200), -1)
        cv2.putText(temp, f"Circle #{current_box_idx + 1} - Enter Number: {number_input}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(temp, "(Press Enter to confirm, Backspace to delete, ESC to cancel)", (30, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    else:
        cv2.rectangle(temp, (20, 20), (600, 100), (50, 50, 50), -1)
        cv2.putText(temp, f"Page {page_num} - Circle {current_box_idx + 1}/{len(scaled_boxes)}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(temp, "E: Edit | W/P: Previous | N: Next | S: Save | ESC: Exit", (30, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return temp

cv2.namedWindow("Circle Editor")

print(f"✅ Loaded {len(scaled_boxes)} circles")
print()

while True:
    cv2.imshow("Circle Editor", draw_boxes())
    key = cv2.waitKey(1) & 0xFF
    
    if editing:
        if key == 13:  # Enter
            scaled_boxes[current_box_idx]["ayah_number"] = number_input
            editing = False
            number_input = ""
            print(f"Saved: Circle {current_box_idx + 1} = {scaled_boxes[current_box_idx]['ayah_number']}")
        elif key == 8:  # Backspace
            number_input = number_input[:-1]
        elif key == 27:  # ESC
            editing = False
            number_input = ""
        else:
            if key >= 32 and key < 127:
                number_input += chr(key)
    else:
        if key == ord("e"):
            number_input = scaled_boxes[current_box_idx]["ayah_number"]
            editing = True
        
        elif key == ord("w") or key == ord("p"):
            if current_box_idx > 0:
                current_box_idx -= 1
        
        elif key == ord("n"):
            if current_box_idx < len(scaled_boxes) - 1:
                current_box_idx += 1
        
        elif key == ord("s"):
            # Convert back to original scale
            output_boxes = []
            for box in scaled_boxes:
                output_boxes.append({
                    "id": box["id"],
                    "x": int(box["x"] / scale),
                    "y": int(box["y"] / scale),
                    "width": int(box["width"] / scale),
                    "height": int(box["height"] / scale),
                    "ayah_number": box["ayah_number"]
                })
            
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump({"boxes": output_boxes}, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Saved to {OUTPUT_JSON}")
        
        elif key == 27:  # ESC
            break

cv2.destroyAllWindows()
print(f"\n👋 Exiting editor for page {page_num}")
