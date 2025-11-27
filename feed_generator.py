import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import datetime
import html
import sys

# --- CONFIGURATION ---
URL = "https://www.matchi.se/facilities/g4pthepadelyard" # Removed parameters to look more natural
TARGET_KEYWORDS = ["Master Class", "Oscar Marhuenda", "Intermediate"]
STATE_FILE = "seen_dates.json"
FEED_FILE = "feed.xml"

def get_current_slots():
    print(f"🔎 Visiting {URL}...")
    
    # Cloudscraper automatically handles the "I am a human" handshake
    scraper = cloudscraper.create_scraper(browser='chrome')
    
    try:
        response = scraper.get(URL)
        # 403 errors will raise an exception here if not bypassed
        response.raise_for_status()
        print("✅ Page loaded successfully (Bot protection bypassed).")
    except Exception as e:
        print(f"❌ Error fetching page: {e}")
        return set()

    soup = BeautifulSoup(response.text, 'html.parser')
    found_slots = set()
    
    # DEBUG: Print titles to ensure we are seeing the right content
    print("--- Checking Page Content ---")
    headers = soup.find_all(['h3', 'h4', 'div'])
    
    target_node = None
    for tag in headers:
        text = tag.text.strip()
        # Check if ALL keywords exist in this text block
        if all(keyword in text for keyword in TARGET_KEYWORDS):
            print(f"🎯 FOUND TARGET SECTION: '{text}'")
            target_node = tag
            break
            
    if not target_node:
        print(f"⚠️ Could not find section matching keywords: {TARGET_KEYWORDS}")
        # print("Debug - first 500 chars of page text:", soup.text[:500])
        return set()

    # Locate the container (parent element)
    container = target_node.find_parent(class_="panel") or target_node.find_parent(class_="row")
    
    if not container:
        print("⚠️ Found header, but could not isolate the container box.")
        return set()

    # Extract dates
    print("   Scanning section for dates...")
    lines = container.get_text(separator="|").split("|")
    for line in lines:
        clean_line = line.strip()
        # We look for "2025-" or "2024-" which is Matchi's standard date format in code
        if "2025-" in clean_line or "2024-" in clean_line:
             print(f"      -> Found slot: {clean_line}")
             found_slots.add(clean_line)

    return found_slots

def update_files(new_slots, all_current_slots):
    # Update JSON State
    with open(STATE_FILE, 'w') as f:
        json.dump(list(all_current_slots), f)
    
    # Update RSS Feed
    rss_header = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
 <title>Padel Monitor: Oscar Marhuenda</title>
 <description>Updates for Master Class</description>
 <link>{URL}</link>
 <lastBuildDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
 <pubDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
 <ttl>60</ttl>"""
    
    rss_footer = "\n</channel>\n</rss>"
    
    new_item = ""
    if new_slots:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
        guid = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        # Create a nice HTML list for the email
        description_html = "<h3>New Dates Available:</h3><ul>" + "".join([f"<li>{s}</li>" for s in new_slots]) + "</ul>"
        
        new_item = f"""
 <item>
  <title>🎾 {len(new_slots)} New Slots Found!</title>
  <description><![CDATA[{description_html} <br/> <a href="{URL}">Book Now</a>]]></description>
  <link>{URL}</link>
  <guid isPermaLink="false">{guid}</guid>
  <pubDate>{timestamp}</pubDate>
 </item>"""

    # Preserve old items (keep history)
    old_items = ""
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if "<item>" in content:
                start = content.find("<item>")
                end = content.rfind("</item>") + 7
                old_items = content[start:end]

    final_items = (new_item + "\n" + old_items) if new_item else old_items

    with open(FEED_FILE, 'w', encoding='utf-8') as f:
        f.write(rss_header + final_items + rss_footer)
    
    print("💾 Feed updated and saved.")

def main():
    print("--- Starting Padel Monitor ---")
    current_slots = get_current_slots()
    
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

    # Always update files so the feed.xml is created on first run
    update_files(new_slots, current_slots)

if __name__ == "__main__":
    main()
