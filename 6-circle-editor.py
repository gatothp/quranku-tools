import cv2
import json
import os
import openpyxl

# Prompt for page number
page_input = input("Enter page number or range (e.g., 7 or 3-4): ").strip()

# Parse page input
if "-" in page_input:
    try:
        start_page, end_page = map(int, page_input.split("-"))
        page_range = list(range(start_page, end_page + 1))
        print(f"\n📖 Processing pages: {start_page}-{end_page}")
    except:
        print("❌ Invalid range format. Use 'N' or 'N-M'")
        exit(1)
else:
    try:
        page_num = int(page_input)
        page_range = [page_num]
        print(f"\n📖 Processing page: {page_num}")
    except:
        print("❌ Invalid page number")
        exit(1)

# Process each page
for page_num in page_range:
    IMAGE_PATH = f"D:\\apps\\android\\quran\\app\\src\\main\\assets\\files\\mushaf\\madinah_v2\\p{page_num:03d}.jpg"
    BOXES_JSON = f"bbox/p{page_num:03d}.json"
    OUTPUT_JSON = f"bbox/p{page_num:03d}.json"
    EXCEL_PATH = "files/quran.xlsx"
    
    print(f"\n✏️  Editing page {page_num}...")
    
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
    if not os.path.exists(BOXES_JSON):
        print(f"❌ File not found: {BOXES_JSON}")
        continue
    
    with open(BOXES_JSON, "r") as f:
        data = json.load(f)
        boxes = data["boxes"]
    
    # Validate circle count
    detected_circles = len(boxes)
    if expected_ayat:
        if detected_circles == expected_ayat:
            print(f"✅ {detected_circles} circles (matches {expected_ayat} ayat)")
        else:
            print(f"⚠️  {detected_circles} circles but {expected_ayat} ayat expected")
    else:
        print(f"ℹ️  {detected_circles} circles detected")
    
    # Load image
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print(f"❌ Image not found: {IMAGE_PATH}")
        continue
    
    height, width = img.shape[:2]
    scale = 650 / height
    new_width = int(width * scale)
    img = cv2.resize(img, (new_width, 650))
    
    # Add space on the right for UI panel (150 pixels)
    panel_width = 150
    display_img = cv2.copyMakeBorder(img, 0, 0, 0, panel_width, cv2.BORDER_CONSTANT, value=(50, 50, 50))
    clone = display_img.copy()
    
    # Scale boxes to match resized image
    scaled_boxes = []
    for box in boxes:
        scaled_boxes.append({
            "id": box["id"],
            "x": int(box["x"] * scale),
            "y": int(box["y"] * scale),
            "width": int(box["width"] * scale),
            "height": int(box["height"] * scale),
            "surat": box.get("surat", 0),
            "ayat": box.get("ayat", 0)
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
            
            # Draw surat:ayat number
            if b["surat"] and b["ayat"]:
                text = f"{b['surat']}:{b['ayat']}"
                cv2.putText(temp, text, (x, y-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            elif b["ayat"]:
                text = f":{b['ayat']}"
                cv2.putText(temp, text, (x, y-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Draw UI on the right panel
        panel_x = new_width + 10
        
        if editing:
            cv2.putText(temp, f"Editing:", (panel_x, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            cv2.putText(temp, f"Circle #{current_box_idx + 1}", (panel_x, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, f"Ayat: {number_input}_", (panel_x, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(temp, f"Surat: {scaled_boxes[current_box_idx]['surat']}", (panel_x, 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, "(ENTER) Confirm", (panel_x, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(ESC) Cancel", (panel_x, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 200), 1)
        else:
            # Draw instructions
            cv2.putText(temp, f"Page {page_num}", (panel_x, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            cv2.putText(temp, f"Circle {current_box_idx + 1}/{len(scaled_boxes)}", (panel_x, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, f"Surat: {scaled_boxes[current_box_idx]['surat']}", (panel_x, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, f"Ayat: {scaled_boxes[current_box_idx]['ayat']}", (panel_x, 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            cv2.putText(temp, "---", (panel_x, 145),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
            cv2.putText(temp, "(E) Edit", (panel_x, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(W/P) Previous", (panel_x, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(N) Next", (panel_x, 210),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(S) Save", (panel_x, 230),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(ESC) Exit", (panel_x, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 200), 1)
        
        return temp
    
    cv2.namedWindow(f"Circle Editor - Page {page_num}")
    
    print(f"✅ Loaded {len(scaled_boxes)} circles")
    print()
    
    while True:
        cv2.imshow(f"Circle Editor - Page {page_num}", draw_boxes())
        key = cv2.waitKey(1) & 0xFF
        
        if editing:
            if key == 13:  # Enter
                scaled_boxes[current_box_idx]["ayat"] = int(number_input) if number_input else 0
                editing = False
                number_input = ""
                print(f"✅ Circle {current_box_idx + 1}: ayat = {scaled_boxes[current_box_idx]['ayat']}")
            elif key == 8:  # Backspace
                number_input = number_input[:-1]
            elif key == 27:  # ESC
                editing = False
                number_input = ""
            else:
                # Accept digit input
                if 48 <= key <= 57:  # 0-9
                    number_input += chr(key)
        else:
            if key == ord("e"):  # Edit
                number_input = str(scaled_boxes[current_box_idx]["ayat"])
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
                        "surat": box["surat"],
                        "ayat": box["ayat"]
                    })
                
                with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                    json.dump({"page": page_num, "boxes": output_boxes}, f, ensure_ascii=False, indent=2)
                
                print(f"✅ Saved to {OUTPUT_JSON}")
                break
            
            elif key == 27:  # ESC
                break
    
    cv2.destroyAllWindows()

print(f"\n✅ Done!")
