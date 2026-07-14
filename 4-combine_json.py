import json
import os
from pathlib import Path

def combine_bbox_ayat():
    """Combine bbox_ayat JSON files into a single file with user-specified page range."""
    
    bbox_ayat_dir = Path("bbox_ayat")
    
    # Get all JSON files
    json_files = sorted([f for f in bbox_ayat_dir.glob("p*.json")], 
                       key=lambda x: int(x.stem[1:]))
    
    if not json_files:
        print("No JSON files found in bbox_ayat folder.")
        return
    
    # Extract page numbers from filenames
    available_pages = [int(f.stem[1:]) for f in json_files]
    print(f"Available pages: {min(available_pages)} - {max(available_pages)}")
    
    # Get user input for page range
    while True:
        try:
            range_input = input(f"Enter page range ({min(available_pages)}-{max(available_pages)}) e.g., 603-604: ")
            
            if '-' not in range_input:
                print("Please enter range in format: start-end (e.g., 603-604)")
                continue
            
            start_page, end_page = map(int, range_input.split('-'))
            
            if start_page < min(available_pages) or end_page > max(available_pages):
                print(f"Pages must be between {min(available_pages)} and {max(available_pages)}")
                continue
            
            if start_page > end_page:
                print("Start page must be less than or equal to end page.")
                continue
            
            break
        except ValueError:
            print("Please enter valid integers in format: start-end")
    
    # Combine JSON files in ascending order
    combined_data = {}
    
    for page_num in range(start_page, end_page + 1):
        file_path = bbox_ayat_dir / f"p{page_num:03d}.json"
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Format page key as "page002", "page603", etc.
                    page_num_value = data.get('page', page_num)
                    page_key = f"page{page_num_value:03d}"
                    # Remove redundant "page" field, keep only "boxes"
                    boxes = data.get("boxes", [])
                    combined_data[page_key] = boxes
                    print(f"Added p{page_num:03d}.json ({page_key})")
            except json.JSONDecodeError:
                print(f"Error: Could not decode p{page_num:03d}.json")
        else:
            print(f"File p{page_num:03d}.json not found, skipping.")
    
    # Write combined data to output file
    output_path = bbox_ayat_dir / "bbox.json"
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        print(f"\nSuccessfully created {output_path}")
        print(f"Combined {len(combined_data)} files (pages {start_page}-{end_page})")
    except IOError as e:
        print(f"Error writing to {output_path}: {e}")

if __name__ == "__main__":
    combine_bbox_ayat()
