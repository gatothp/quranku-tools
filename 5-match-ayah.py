import cv2
import numpy as np
import json
from PIL import Image
import os

try:
    import pytesseract
    
    # Try multiple possible Tesseract paths
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\User\AppData\Local\Tesseract-OCR\tesseract.exe',
    ]
    
    tesseract_path = None
    for path in possible_paths:
        if os.path.exists(path):
            tesseract_path = path
            break
    
    if tesseract_path:
        pytesseract.pytesseract.pytesseract_cmd = tesseract_path
        TESSERACT_AVAILABLE = True
    else:
        TESSERACT_AVAILABLE = False
        print(f"⚠️  Tesseract executable not found at expected locations")
except ImportError:
    TESSERACT_AVAILABLE = False

IMAGE_PATH = "mushaf/p005.jpg"
TEMPLATE_PATH = "mushaf/circle.png"
OUTPUT_JSON = "matched_boxes.json"

img = cv2.imread(IMAGE_PATH)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

template = cv2.imread(TEMPLATE_PATH, 0)
tw, th = template.shape[::-1]

# Try multiple scales (IMPORTANT)
scales = np.linspace(0.8, 1.2, 10)

results = []
seen = []

def extract_number_from_circle(gray_img, x, y, w, h):
    """Extract the number inside the circle using basic image analysis"""
    try:
        # Extract center region of circle (where number should be)
        roi = gray_img[max(0, y+h//4):min(gray_img.shape[0], y+3*h//4), 
                       max(0, x+w//4):min(gray_img.shape[1], x+3*w//4)]
        
        if roi.size < 10:
            return ""
        
        # Invert and threshold
        _, binary = cv2.threshold(255 - roi, 100, 255, cv2.THRESH_BINARY)
        
        # Save for debugging
        # cv2.imwrite(f"roi_{x}_{y}.png", binary)
        
        # Try pytesseract with config
        if TESSERACT_AVAILABLE:
            import subprocess
            import tempfile
            import os
            
            # Save ROI temporarily
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                cv2.imwrite(tmp.name, binary)
                try:
                    result = subprocess.run(
                        [r'C:\Program Files\Tesseract-OCR\tesseract.exe', 
                         tmp.name, 'stdout', '-l', 'ara', '--psm', '8'],
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

        # Convert back to original scale
        x = int(pt[0] / scale)
        y = int(pt[1] / scale)
        w = int(tw / scale)
        h = int(th / scale)

        # Expand bounding box by 20% in all directions
        expand = 1.4
        x = int(x - w * (expand - 1) / 2)
        y = int(y - h * (expand - 1) / 2)
        w = int(w * expand)
        h = int(h * expand)

        # === Avoid duplicates ===
        too_close = False
        for (sx, sy) in seen:
            if abs(x - sx) < 20 and abs(y - sy) < 20:
                too_close = True
                break

        if too_close:
            continue

        seen.append((x, y))
        
        # Extract Arabic number from circle
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

# Save results
if not TESSERACT_AVAILABLE:
    print("⚠️  Tesseract not found - ayah_number fields will be empty.")
    print("To enable OCR, install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")

with open(OUTPUT_JSON, "w") as f:
    json.dump({"boxes": results}, f, ensure_ascii=False, indent=2)

print(f"Detected: {len(results)} circles")

cv2.imshow("Matches", img)
cv2.waitKey(0)
cv2.destroyAllWindows()