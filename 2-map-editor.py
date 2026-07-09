import cv2
import json
import os

boxes = []
input_mode = None  # None, "surah", or "ayah"
surah_input = ""
ayah_input = ""
pending_box = None
last_surah = None  # Remember last surah entered

image_path = "mushaf/p003.jpg"  # change this
filename = image_path.split("/")[-1]   # "p003.jpg"
number_str = filename[1:4]             # "003"
page_number = int(number_str)
# page_number = 563

img = cv2.imread(image_path)
# Resize image to fit 650px height while maintaining aspect ratio
height, width = img.shape[:2]
scale = 650 / height
new_width = int(width * scale)
img = cv2.resize(img, (new_width, 650))
clone = img.copy()

current_box = []
drawing = False

def draw_boxes():
    temp = clone.copy()
    for b in boxes:
        x, y, w, h, s, a = b
        cv2.rectangle(temp, (x, y), (x+w, y+h), (0,255,0), 2)
        cv2.putText(temp, f"{s}:{a}", (x, y-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    
    # Draw input UI if in input mode
    if input_mode == "surah":
        cv2.rectangle(temp, (20, 20), (400, 80), (200, 200, 200), -1)
        cv2.putText(temp, f"Enter Surah: {surah_input}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(temp, "(Press Enter to confirm, Backspace to delete)", (30, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    elif input_mode == "ayah":
        cv2.rectangle(temp, (20, 20), (400, 80), (200, 200, 200), -1)
        cv2.putText(temp, f"Enter Ayah: {ayah_input}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(temp, "(Press Enter to confirm, Backspace to delete)", (30, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    
    return temp

def mouse(event, x, y, flags, param):
    global drawing, current_box, input_mode, pending_box

    if input_mode:  # Don't accept mouse input while typing
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        current_box = [x, y]

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            temp = draw_boxes()
            cv2.rectangle(temp, (current_box[0], current_box[1]), (x, y), (0,0,255), 2)
            cv2.imshow("Editor", temp)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        x0, y0 = current_box
        w = x - x0
        h = y - y0

        global surah_input, last_surah
        pending_box = [x0, y0, w, h]
        input_mode = "surah"
        # Pre-fill with last surah if available
        if last_surah:
            surah_input = str(last_surah)
        else:
            surah_input = ""

cv2.namedWindow("Editor")
cv2.setMouseCallback("Editor", mouse)

while True:
    cv2.imshow("Editor", draw_boxes())
    key = cv2.waitKey(1) & 0xFF

    if input_mode == "surah":
        if key == 13:  # Enter
            if surah_input:
                input_mode = "ayah"
                surah_input = int(surah_input)
        elif key == 8:  # Backspace
            surah_input = surah_input[:-1]
        elif 48 <= key <= 57:  # Numbers 0-9
            if len(str(surah_input)) < 3:
                surah_input += chr(key)

    elif input_mode == "ayah":
        if key == 13:  # Enter
            if ayah_input:
                s = surah_input
                a = int(ayah_input)
                x0, y0, w, h = pending_box
                boxes.append([x0, y0, w, h, s, a])
                last_surah = s  # Remember this surah for next time
                input_mode = None
                surah_input = ""
                ayah_input = ""
                pending_box = None
                print(f"Added box: Surah {s}, Ayah {a}")
        elif key == 8:  # Backspace
            ayah_input = ayah_input[:-1]
        elif 48 <= key <= 57:  # Numbers 0-9
            if len(ayah_input) < 3:
                ayah_input += chr(key)

    else:  # Normal mode
        if key == ord("u"):
            if boxes:
                boxes.pop()
                print("Undo last box")

        elif key == ord("e"):
            output = {
                "page": page_number,
                "ayahs": []
            }

            for b in boxes:
                x, y, w, h, s, a = b
                output["ayahs"].append({
                    "surah": s,
                    "ayah": a,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h
                })

            with open(f"page_{page_number}.json", "w") as f:
                json.dump(output, f, indent=2)

            print("Saved JSON!")

        elif key == 27:  # ESC
            break

cv2.destroyAllWindows()