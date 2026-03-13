
import re

def _parse_unified_content(text: str):
    parsed = {"title": "", "subtitle": "", "sections": {}, "images": []}

    # 1. Extract [IMAGE] blocks
    image_blocks = re.findall(r'\[IMAGE\](.*?)\[/IMAGE\]', text, re.S)
    for block in image_blocks:
        img_data = {}
        for line in block.strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                img_data[k.strip().lower()] = v.strip()
        if img_data:
            parsed["images"].append(img_data)

    # Remove image blocks from text
    clean_text = re.sub(r'\[IMAGE\].*?\[/IMAGE\]', '', text, flags=re.S)

    # 2. Extract Main Title (# Header)
    title_match = re.search(r'^#\s*(.+)$', clean_text, re.MULTILINE)
    if title_match:
        full_title = title_match.group(1).strip()
        parsed["title"] = full_title

    # 3. Split by ## headers
    sections_raw = re.split(r'^##\s*(?:\d+\.?\s*)?(.+)$', clean_text, flags=re.MULTILINE)
    for i in range(1, len(sections_raw) - 1, 2):
        header = sections_raw[i].strip()
        content = sections_raw[i+1].strip()
        parsed["sections"][header] = content

    return parsed

test_input = """
# Sustainable Architecture: The Future of Living

## Introduction

[IMAGE]
Type: architecture
Description: modern eco-friendly building with solar panels and greenery
Placement: after section header
[/IMAGE]

Sustainable architecture focuses on reducing environmental impact while improving building performance. 
It represents a holistic approach to design that considers the entire lifecycle of a building.

## Core Principles

[IMAGE]
Type: diagram
Description: building orientation optimizing sunlight and ventilation
Placement: after section header
[/IMAGE]

The core principles of sustainable design include energy efficiency, water conservation, and the use of sustainable materials.
These principles are essential for creating buildings that are both environmentally friendly and economically viable.
"""

parsed = _parse_unified_content(test_input)
print(f"Title: {parsed['title']}")
print(f"Images count: {len(parsed['images'])}")
for idx, img in enumerate(parsed['images']):
    print(f"Image {idx+1}: {img.get('description')}")
print(f"Sections found: {list(parsed['sections'].keys())}")
if "[IMAGE]" in parsed['sections'].get("Introduction", ""):
    print("Error: [IMAGE] block still in content")
else:
    print("Success: [IMAGE] block removed from content")
