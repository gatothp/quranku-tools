"""
SCRIPT: 7-viewer.py (Interactive Viewer/Editor)
PURPOSE: View and edit bounding boxes (circles or ayah boxes) with interactive UI

INPUT:
  - User: Data type selection (1=circles from bbox/, 2=boxes from bbox_ayat/)
  - User: Page number or range (e.g., "3" or "3-5")
  - JSON: bbox/p###.json or bbox_ayat/p###.json
  - Image: Quran mushaf pages (jpg) from madinah_v2 folder
  - Excel: quran.xlsx - For validation against expected ayat count

FEATURES:
  - View circles or boxes overlaid on Quran page image
  - Navigate: (W/P) Previous, (N) Next
  - Edit ayat: (E) Edit Ayat number
  - Edit surat: (R) Edit Surat number
  - Delete: (D) Delete circle/box (with confirmation)
  - Save: (S) Save changes back to JSON
  - Exit: (ESC) Exit without saving

UI:
  - Main area: Scaled image with boxes (green=selected, gray=others)
  - Right panel: Current box info, instructions, and keyboard shortcuts
  - Resizes image to 650px height for visibility
  - Shows ayat:surat labels on each box

OUTPUT:
  - JSON: Updated bbox/p###.json or bbox_ayat/p###.json with edits
  - Console: Validation results and operation confirmations
"""

import cv2
import json
import os
import openpyxl

# Prompt for data source
data_choice = input("Pilih data (1-circle, 2-box) [default: 1]: ").strip()
if not data_choice:
    data_choice = "1"

if data_choice == "1":
    data_folder = "bbox"
elif data_choice == "2":
    data_folder = "bbox_ayat"
else:
    print("❌ Invalid choice. Using default (1-circle)")
    data_folder = "bbox"

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
    BOXES_JSON = f"{data_folder}/p{page_num:03d}.json"
    OUTPUT_JSON = f"{data_folder}/p{page_num:03d}.json"
    EXCEL_PATH = "files/quran.xlsx"
    
    print(f"\n✏️  Editing page {page_num}...")
    
    # Load and validate against Excel (only for circles)
    expected_ayat = None
    if data_choice == "1":
        try:
            wb = openpyxl.load_workbook(EXCEL_PATH)
            sheet = wb['hal-ayat']
            
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if row[0] == page_num:
                    expected_ayat = row[1]
                    break
        except Exception as e:
            print(f"⚠️  Could not load Excel file: {e}")
    
    # Load boxes
    if not os.path.exists(BOXES_JSON):
        print(f"❌ File not found: {BOXES_JSON}")
        continue
    
    with open(BOXES_JSON, "r") as f:
        data = json.load(f)
        boxes = data["boxes"]
    
    # Show count message (different for circles vs boxes)
    detected_count = len(boxes)
    if data_choice == "1":
        # For circles, show validation against Excel
        if expected_ayat:
            if detected_count == expected_ayat:
                print(f"✅ {detected_count} circles (matches {expected_ayat} ayat)")
            else:
                print(f"⚠️  {detected_count} circles but {expected_ayat} ayat expected")
        else:
            print(f"ℹ️  {detected_count} circles detected")
    else:
        # For boxes, just show count without validation
        print(f"ℹ️  {detected_count} rectangles detected")
    
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
    confirming_delete = False
    editing_surat = False
    editing_width = False
    
    # For boxes: create RTL-ordered index mapping
    rtl_order = list(range(len(scaled_boxes)))  # Default order
    if data_choice == "2":
        # Group by line and sort RTL
        line_height_px = 650 / 15
        boxes_by_line = {}
        for i, b in enumerate(scaled_boxes):
            line_idx = int(b["y"] / line_height_px)
            if line_idx not in boxes_by_line:
                boxes_by_line[line_idx] = []
            boxes_by_line[line_idx].append(i)
        
        rtl_order = []
        for line_idx in sorted(boxes_by_line.keys()):
            # Sort by X descending (right to left)
            line_boxes = sorted(boxes_by_line[line_idx], 
                              key=lambda i: -scaled_boxes[i]["x"])
            rtl_order.extend(line_boxes)
    
    def draw_boxes():
        temp = clone.copy()
        
        if data_choice == "2":
            # For boxes: group by Y line and sort by X position (RTL order)
            line_height_px = 650 / 15  # Approximate line height
            boxes_by_line = {}
            
            # Group boxes by line (Y coordinate)
            for i, b in enumerate(scaled_boxes):
                line_idx = int(b["y"] / line_height_px)
                if line_idx not in boxes_by_line:
                    boxes_by_line[line_idx] = []
                boxes_by_line[line_idx].append((i, b))
            
            # Draw boxes sorted by line, then by X position (right to left = descending X)
            for line_idx in sorted(boxes_by_line.keys()):
                # Sort by X position descending (right to left)
                boxes_by_line[line_idx].sort(key=lambda item: -item[1]["x"])
                for i, b in boxes_by_line[line_idx]:
                    x, y, w, h = b["x"], b["y"], b["width"], b["height"]
                    # Red for normal, green for selected
                    color = (0, 255, 0) if i == current_box_idx else (0, 0, 255)
                    thickness = 3 if i == current_box_idx else 2
                    cv2.rectangle(temp, (x, y), (x+w, y+h), color, thickness)
                    
                    # Draw ayat number only in smaller font
                    if b["ayat"]:
                        text = f"{b['ayat']}"
                        cv2.putText(temp, text, (x + 5, y + 15),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        else:
            # For circles: original behavior (green for selected, gray for others)
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
        
        if confirming_delete:
            cv2.putText(temp, "DELETE?", (panel_x, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
            cv2.putText(temp, f"Circle #{current_box_idx + 1}", (panel_x, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, f"Surat: {scaled_boxes[current_box_idx]['surat']}", (panel_x, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, f"Ayat: {scaled_boxes[current_box_idx]['ayat']}", (panel_x, 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, "(Y) Yes Delete", (panel_x, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            cv2.putText(temp, "(N) Cancel", (panel_x, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
        elif editing_surat:
            cv2.putText(temp, f"Editing Surat:", (panel_x, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            cv2.putText(temp, f"Circle #{current_box_idx + 1}", (panel_x, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, f"Surat: {number_input}_", (panel_x, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(temp, f"Ayat: {scaled_boxes[current_box_idx]['ayat']}", (panel_x, 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, "(ENTER) Confirm", (panel_x, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(DEL) Clear", (panel_x, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 200), 1)
            cv2.putText(temp, "(ESC) Cancel", (panel_x, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 200), 1)
        elif editing_width:
            cv2.putText(temp, f"Editing Width:", (panel_x, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            cv2.putText(temp, f"Rectangle #{current_box_idx + 1}", (panel_x, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, f"Width: {number_input}_", (panel_x, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(temp, f"Current: {scaled_boxes[current_box_idx]['width']}", (panel_x, 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, "(ENTER) Confirm", (panel_x, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(DEL) Clear", (panel_x, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 200), 1)
            cv2.putText(temp, "(ESC) Cancel", (panel_x, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 200), 1)
        elif editing:
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
            
            # Show position differently for circles vs boxes
            if data_choice == "2":
                current_pos = rtl_order.index(current_box_idx) + 1
                cv2.putText(temp, f"Rectangle {current_pos}/{len(scaled_boxes)}", (panel_x, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            else:
                cv2.putText(temp, f"Circle {current_box_idx + 1}/{len(scaled_boxes)}", (panel_x, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            cv2.putText(temp, f"Surat: {scaled_boxes[current_box_idx]['surat']}", (panel_x, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(temp, f"Ayat: {scaled_boxes[current_box_idx]['ayat']}", (panel_x, 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            cv2.putText(temp, "---", (panel_x, 145),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
            cv2.putText(temp, "(E) Edit Ayat", (panel_x, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(R) Edit Surat", (panel_x, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(W) Edit Width", (panel_x, 210),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(P) Previous", (panel_x, 230),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(N) Next", (panel_x, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(D) Delete", (panel_x, 270),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 200), 1)
            cv2.putText(temp, "(S) Save", (panel_x, 290),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 100), 1)
            cv2.putText(temp, "(ESC) Exit", (panel_x, 310),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 200), 1)
        
        return temp
    
    cv2.namedWindow(f"Circle Editor - Page {page_num}")
    
    item_type = "circles" if data_choice == "1" else "rectangles"
    print(f"✅ Loaded {len(scaled_boxes)} {item_type}")
    print()
    
    while True:
        cv2.imshow(f"Circle Editor - Page {page_num}", draw_boxes())
        key = cv2.waitKey(1) & 0xFF
        
        if confirming_delete:
            if key == ord("y"):  # Yes, delete
                deleted_box = scaled_boxes.pop(current_box_idx)
                print(f"❌ Deleted circle #{current_box_idx + 1} (was surat {deleted_box['surat']}, ayat {deleted_box['ayat']})")
                confirming_delete = False
                
                # Adjust index if we deleted the last circle
                if current_box_idx >= len(scaled_boxes) and len(scaled_boxes) > 0:
                    current_box_idx = len(scaled_boxes) - 1
            
            elif key == ord("n"):  # Cancel delete
                confirming_delete = False
        
        elif editing_surat:
            if key == 13:  # Enter
                scaled_boxes[current_box_idx]["surat"] = int(number_input) if number_input else 0
                editing_surat = False
                number_input = ""
                print(f"✅ Circle {current_box_idx + 1}: surat = {scaled_boxes[current_box_idx]['surat']}")
            elif key == 8:  # Backspace
                number_input = number_input[:-1]
            elif key == 46:  # Delete key
                number_input = ""
            elif key == 27:  # ESC
                editing_surat = False
                number_input = ""
            elif 48 <= key <= 57:  # 0-9
                number_input += chr(key)
        
        elif editing_width:
            if key == 13:  # Enter
                scaled_boxes[current_box_idx]["width"] = int(number_input) if number_input else scaled_boxes[current_box_idx]["width"]
                editing_width = False
                number_input = ""
                print(f"✅ Rectangle {current_box_idx + 1}: width = {scaled_boxes[current_box_idx]['width']}")
            elif key == 8:  # Backspace
                number_input = number_input[:-1]
            elif key == 46:  # Delete key
                number_input = ""
            elif key == 27:  # ESC
                editing_width = False
                number_input = ""
            elif 48 <= key <= 57:  # 0-9
                number_input += chr(key)
        
        elif editing:
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
            elif 48 <= key <= 57:  # 0-9
                number_input += chr(key)
        else:
            if key == ord("e"):  # Edit
                number_input = str(scaled_boxes[current_box_idx]["ayat"])
                editing = True
            
            elif key == ord("r"):  # R for edit surat
                number_input = str(scaled_boxes[current_box_idx]["surat"])
                editing_surat = True
            
            elif key == ord("w"):  # W for edit width
                number_input = str(scaled_boxes[current_box_idx]["width"])
                editing_width = True
            
            elif key == ord("p"):  # P for previous
                if data_choice == "2":
                    # For boxes: use RTL order
                    current_pos = rtl_order.index(current_box_idx)
                    if current_pos > 0:
                        current_box_idx = rtl_order[current_pos - 1]
                else:
                    # For circles: original order
                    if current_box_idx > 0:
                        current_box_idx -= 1
            
            elif key == ord("n"):  # N for next
                if data_choice == "2":
                    # For boxes: use RTL order
                    current_pos = rtl_order.index(current_box_idx)
                    if current_pos < len(rtl_order) - 1:
                        current_box_idx = rtl_order[current_pos + 1]
                else:
                    # For circles: original order
                    if current_box_idx < len(scaled_boxes) - 1:
                        current_box_idx += 1
            
            elif key == ord("d"):  # D for delete
                if len(scaled_boxes) > 0:
                    confirming_delete = True
            
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
