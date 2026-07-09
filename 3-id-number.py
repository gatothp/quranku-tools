import cv2
import numpy as np
import json

IMAGE_PATH = "mushaf/p003.jpg"
OUTPUT_JSON = "filtered_boxes.json"

MIN_RADIUS = 18
MAX_RADIUS = 35

img = cv2.imread(IMAGE_PATH)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

blur = cv2.GaussianBlur(gray, (9, 9), 2)

# Binary image (important for filtering)
_, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

circles = cv2.HoughCircles(
    blur,
    cv2.HOUGH_GRADIENT,
    dp=1.2,
    minDist=60,
    param1=100,
    param2=28,
    minRadius=MIN_RADIUS,
    maxRadius=MAX_RADIUS
)

results = []

if circles is not None:
    circles = np.round(circles[0, :]).astype("int")

    for i, (x, y, r) in enumerate(circles):

        # === Extract ROI ===
        x0 = max(0, x - r)
        y0 = max(0, y - r)
        x1 = min(img.shape[1], x + r)
        y1 = min(img.shape[0], y + r)

        roi = thresh[y0:y1, x0:x1]

        # === FILTER 1: pixel density ===
        black_pixels = np.sum(roi > 0)
        area = roi.shape[0] * roi.shape[1]
        density = black_pixels / area

        # Ayah circles have LOW density (mostly white)
        if density > 0.35:
            continue

        # === FILTER 2: circular mask check ===
        mask = np.zeros_like(roi)
        cv2.circle(mask, (r, r), r, 255, -1)

        inside_pixels = np.sum((roi > 0) & (mask > 0))
        ratio = inside_pixels / (np.pi * r * r)

        # Too messy inside → likely text
        if ratio > 0.5:
            continue

        # === PASS ===
        w = 2 * r
        h = 2 * r

        results.append({
            "id": int(len(results) + 1),
            "x": int(x0),
            "y": int(y0),
            "width": int(w),
            "height": int(h)
        })

        # Draw accepted
        cv2.circle(img, (x, y), r, (0, 255, 0), 2)
        cv2.rectangle(img, (x0, y0), (x0 + w, y0 + h), (255, 0, 0), 2)

# Save
with open(OUTPUT_JSON, "w") as f:
    json.dump({"boxes": results}, f, indent=2)

print(f"Final filtered circles: {len(results)}")

cv2.imshow("Filtered", img)
cv2.waitKey(0)
cv2.destroyAllWindows()