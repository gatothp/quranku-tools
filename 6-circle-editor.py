import cv2
import json
import os
import openpyxl

IMAGE_PATH = "mushaf/p005.jpg"
BOXES_JSON = "matched_boxes.json"
OUTPUT_JSON = "circle_numbers.json"
EXCEL_PATH = "files/quran.xlsx"

# Extract page number from image path
page_num = int(IMAGE_PATH.split("/")[-1][1:4])

# Load and validate against Excel
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

# Load boxes
with open(BOXES_JSON, "r") as f:
    data = json.load(f)
    boxes = data["boxes"]

# Validate circle count
detected_circles = len(boxes)
if expected_ayat:
    if detected_circles == expected_ayat:
        print(f"✅ Page {page_num}: {detected_circles} circles detected (matches {expected_ayat} ayat in Excel)")
    else:
        print(f"⚠️  Page {page_num}: {detected_circles} circles detected but {expected_ayat} ayat expected")
else:
    print(f"ℹ️  Page {page_num}: {detected_circles} circles detected")

# Load boxes
with open(BOXES_JSON, "r") as f:
    data = json.load(f)
    boxes = data["boxes"]

# Load image
img = cv2.imread(IMAGE_PATH)
height, width = img.shape[:2]
scale = 650 / height
new_width = int(width * scale)
img = cv2.resize(img, (new_width, 650))
clone = img.copy()

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
        
        # Draw ID and number
        text = f"#{i+1}"
        if b["ayah_number"]:
            text += f" {b['ayah_number']}"
        cv2.putText(temp, text, (x, y-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # Draw input UI if editing
    if editing:
        cv2.rectangle(temp, (20, 20), (400, 80), (200, 200, 200), -1)
        cv2.putText(temp, f"Circle #{current_box_idx + 1} - Enter Number: {number_input}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(temp, "(Press Enter to confirm, Backspace to delete, ESC to cancel)", (30, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    else:
        # Draw instructions
        cv2.rectangle(temp, (20, 20), (600, 100), (50, 50, 50), -1)
        cv2.putText(temp, f"Circle {current_box_idx + 1}/{len(scaled_boxes)}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(temp, "E: Edit | W/P: Previous | N: Next | S: Save | ESC: Exit", (30, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return temp

cv2.namedWindow("Circle Editor")

print(f"✅ Loaded {len(scaled_boxes)} circles from {BOXES_JSON}")
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
            # Accept any character input
            if key >= 32 and key < 127:  # Printable ASCII
                number_input += chr(key)
    else:
        if key == ord("e"):  # Edit
            number_input = scaled_boxes[current_box_idx]["ayah_number"]
            editing = True
        
        elif key == ord("w") or key == ord("p"):  # W or P for previous
            if current_box_idx > 0:
                current_box_idx -= 1
        
        elif key == ord("n"):  # N for next
            if current_box_idx < len(scaled_boxes) - 1:
                current_box_idx += 1
        
        elif key == ord("s"):  # Save
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
