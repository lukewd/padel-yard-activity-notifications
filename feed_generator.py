import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import html
import sys

# --- CONFIGURATION ---
URL = "https://www.matchi.se/facilities/g4pthepadelyard?date=&sport="
# We split the target into keywords to be more flexible
TARGET_KEYWORDS = ["Master Class", "Oscar Marhuenda", "Intermediate"]
STATE_FILE = "seen_dates.json"
FEED_FILE = "feed.xml"

# Headers to make us look like a real browser (Chrome on Windows)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def get_current_slots():
    print(f"🔎 Visiting {URL}...")
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        print("✅ Page loaded successfully.")
    except Exception as e:
        print(f"❌ Error fetching page: {e}")
        return set()

    soup = BeautifulSoup(response.text, 'html.parser')
    found_slots = set()
    
    # Debug: Print all H3/H4 headers found to verify we are seeing content
    print("--- Headers Found on Page ---")
    headers = soup.find_all(['h3', 'h4', 'h5', 'strong', 'div'])
    # We only print the first few to avoid log spam, just to check visibility
    for h in headers[:10]:
         if "Oscar" in h.text:
             print(f"   Found potential match: '{h.text.strip()}'")

    # 1. Find the section
    # We look for ANY tag that contains ALL our keywords
    target_node = None
    for tag in soup.find_all(['h3', 'h4', 'div']):
        text = tag.text.strip()
        if all(keyword in text for keyword in TARGET_KEYWORDS):
            target_node = tag
            print(f"🎯 LOCKED ON TARGET: '{text}'")
            break
    
    if not target_node:
        print(f"⚠️ Could not find specific activity section matching: {TARGET_KEYWORDS}")
        return set()

    # 2. Find the container (The box that holds the dates)
    # We traverse up 3 levels to find the container (panel/row)
    container = target_node.find_parent(class_="panel") or target_node.find_parent(class_="row") or target_node.find_parent(class_="media-body")
    
    if not container:
        print("⚠️ Found header, but could not isolate the container box.")
        return set()

    # 3. Extract dates
    print("   Scanning container for dates...")
    lines = container.get_text(separator="|").split("|")
    for line in lines:
        clean_line = line.strip()
        # Look for YYYY-MM-DD pattern
        if "2025-" in clean_line or "2024-" in clean_line:
             print(f"      -> Found slot: {clean_line}")
             found_slots.add(clean_line)

    return found_slots

def update_files(new_slots, all_current_slots):
    # Update JSON State
    with open(STATE_FILE, 'w') as f:
        json.dump(list(all_current_slots), f)
    
    # Update RSS Feed (Always create it if missing)
    rss_header = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
 <title>Padel Availability Monitor</title>
 <description>Updates for Oscar Marhuenda Classes</description>
 <link>{URL}</link>
 <lastBuildDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
 <pubDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
 <ttl>60</ttl>"""
    
    rss_footer = "\n</channel>\n</rss>"
    
    # If we have NEW slots, add an item
    new_item = ""
    if new_slots:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
        guid = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        description_html = "<ul>" + "".join([f"<li>{s}</li>" for s in new_slots]) + "</ul>"
        
        new_item = f"""
 <item>
  <title>New Availability! ({len(new_slots)} slots)</title>
  <description><![CDATA[Found new slots:<br/> {description_html} <br/> <a href="{URL}">Book Now</a>]]></description>
  <link>{URL}</link>
  <guid isPermaLink="false">{guid}</guid>
  <pubDate>{timestamp}</pubDate>
 </item>"""

    # Read old items
    old_items = ""
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if "<item>" in content:
                start = content.find("<item>")
                end = content.rfind("</item>") + 7
                old_items = content[start:end]

    # Combine
    if new_item:
        final_items = new_item + "\n" + old_items
    else:
        final_items = old_items

    with open(FEED_FILE, 'w', encoding='utf-8') as f:
        f.write(rss_header + final_items + rss_footer)
    
    print("💾 Files saved successfully.")

def main():
    print("--- Starting Padel Monitor ---")
    current_slots = get_current_slots()
    
    # Load seen slots
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try:
                seen_slots = set(json.load(f))
            except:
                seen_slots = set()
    else:
        seen_slots = set()

    new_slots = current_slots - seen_slots

    if new_slots:
        print(f"🎉 FOUND {len(new_slots)} NEW SLOTS!")
    else:
        print("ℹ️ No new slots found this run.")

    # We update the files EVERY time now, to ensure they exist
    update_files(new_slots, current_slots)

if __name__ == "__main__":
    main()
