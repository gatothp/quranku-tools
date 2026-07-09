import requests
import json
from collections import defaultdict

PAGE_WIDTH = 1200
PAGE_HEIGHT = 1971
LINES_PER_PAGE = 15
MARGIN_X = 12
MARGIN_Y = 5

# Fetch Quran data
url = "https://api.quran.com/api/v4/verses/by_page/1?words=false&per_page=50"
all_pages = {}

print("Fetching Quran data...")

for page in range(1, 605):
    if page % 50 == 0:
        print(f"  Fetching page {page}...")
    url = f"https://api.quran.com/api/v4/verses/by_page/{page}?words=false&per_page=50"
    res = requests.get(url).json()
    
    verses = res["verses"]
    
    ayahs = []
    for v in verses:
        # Try different text field names; fall back to empty string if none exist
        text = v.get("text_uthmani") or v.get("text_imlaei") or v.get("text") or ""
        
        ayahs.append({
            "surah": int(v["verse_key"].split(":")[0]),
            "ayah": int(v["verse_key"].split(":")[1]),
            "text": text
        })
    
    all_pages[page] = ayahs

print("Generating coordinates...")

dataset = []

for page, ayahs in all_pages.items():
    line_height = (PAGE_HEIGHT - 2*MARGIN_Y) / LINES_PER_PAGE
    
    page_data = {
        "page": page,
        "ayahs": []
    }
    
    line = 0
    x_cursor = MARGIN_X
    
    for ayah in ayahs:
        # simple width estimation based on text length
        text_len = len(ayah["text"])
        width = max(40, min(200, text_len * 4))
        
        if x_cursor + width > PAGE_WIDTH - MARGIN_X:
            # move to next line
            line += 1
            x_cursor = MARGIN_X
        
        y = MARGIN_Y + line * line_height
        
        page_data["ayahs"].append({
            "surah": ayah["surah"],
            "ayah": ayah["ayah"],
            "x": int(x_cursor),
            "y": int(y),
            "width": int(width),
            "height": int(line_height)
        })
        
        x_cursor += width + 3
    
    dataset.append(page_data)

print("Saving file...")

with open("quran_604_pages.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print("✅ Done! File saved as quran_604_pages.json")