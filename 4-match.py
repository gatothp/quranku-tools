import cv2
import numpy as np
import json

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

        results.append({
            "id": len(results) + 1,
            "x": x,
            "y": y,
            "width": w,
            "height": h
        })

        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

# Save results
with open(OUTPUT_JSON, "w") as f:
    json.dump({"boxes": results}, f, indent=2)

print(f"Detected: {len(results)} circles")

cv2.imshow("Matches", img)
cv2.waitKey(0)
cv2.destroyAllWindows()