import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import html

# --- CONFIGURATION ---
URL = "https://www.matchi.se/facilities/g4pthepadelyard?date=&sport=#ClassActivity-130961"
TARGET_ACTIVITY = "Master Class With Oscar Marhuenda - Intermediate"
STATE_FILE = "seen_dates.json"
FEED_FILE = "feed.xml"
REPO_URL = "https://lukewd.github.io/padel-yard-activity-notifications" # We will set this up later

def get_current_slots():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page: {e}")
        return set()

    soup = BeautifulSoup(response.text, 'html.parser')
    found_slots = set()

    # Find the header for the specific activity
    activity_header = soup.find(lambda tag: tag.name in ["h1", "h2", "h3", "h4", "div"] and TARGET_ACTIVITY in tag.text)
    
    if not activity_header:
        print(f"Could not find activity header: {TARGET_ACTIVITY}")
        return set()

    # Find the container
    container = activity_header.find_parent(class_="panel") or activity_header.find_parent(class_="row")
    
    if not container:
        print("Could not isolate activity container.")
        return set()

    # Extract dates
    lines = container.get_text(separator="|").split("|")
    for line in lines:
        clean_line = line.strip()
        if "2025-" in clean_line or "2024-" in clean_line:
             found_slots.add(clean_line)

    return found_slots

def update_rss_feed(new_slots):
    # 1. Read existing RSS content or create header
    rss_header = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
 <title>Padel Availability Monitor</title>
 <description>Updates for {html.escape(TARGET_ACTIVITY)}</description>
 <link>{URL}</link>
 <lastBuildDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
 <pubDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
 <ttl>60</ttl>"""
    
    rss_footer = "\n</channel>\n</rss>"
    
    # 2. Generate the new item
    # We create a unique GUID using timestamp so IFTTT treats it as new
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    guid = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    description_html = "<ul>" + "".join([f"<li>{s}</li>" for s in new_slots]) + "</ul>"
    
    new_item = f"""
 <item>
  <title>New Dates Found! ({len(new_slots)} slots)</title>
  <description><![CDATA[New availability found:<br/> {description_html} <br/> <a href="{URL}">Book Now</a>]]></description>
  <link>{URL}</link>
  <guid isPermaLink="false">{guid}</guid>
  <pubDate>{timestamp}</pubDate>
 </item>"""

    # 3. Read old items from existing file to keep history (optional, but good for validity)
    old_items = ""
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # simple string manipulation to extract <item> blocks
            if "<item>" in content:
                start_index = content.find("<item>")
                end_index = content.rfind("</item>") + 7
                old_items = content[start_index:end_index]

    # 4. Limit history to last 10 items to keep file small
    # (Rough split by </item>)
    all_item_blocks = ([new_item] + old_items.split("</item>"))[:10]
    # Reconstruct valid XML blocks
    clean_items = []
    for item in all_item_blocks:
        if "<item>" in item:
            if not item.strip().endswith("</item>"):
                item += "</item>"
            clean_items.append(item)
            
    final_items_str = "\n".join(clean_items)

    # 5. Write file
    with open(FEED_FILE, 'w', encoding='utf-8') as f:
        f.write(rss_header + final_items_str + rss_footer)
    
    print("✅ RSS Feed updated.")

def main():
    print("Checking for new slots...")
    current_slots = get_current_slots()
    
    # Load previously seen slots
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try:
                seen_slots = set(json.load(f))
            except json.JSONDecodeError:
                seen_slots = set()
    else:
        seen_slots = set()

    # Compare
    new_slots = current_slots - seen_slots

    if new_slots:
        print(f"🎉 Found {len(new_slots)} new slots!")
        update_rss_feed(new_slots)
        
        # Update state file with CURRENT slots
        # We overwrite seen_slots with current_slots so if a slot disappears and reappears, we get alerted again.
        with open(STATE_FILE, 'w') as f:
            json.dump(list(current_slots), f)
    else:
        print("No new slots found.")

if __name__ == "__main__":
    main()
