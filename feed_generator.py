import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import sys
import urllib3

# Suppress the "InsecureRequest" warnings from the Proxy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
URL = "https://www.matchi.se/facilities/g4pthepadelyard" 
TARGET_ANCHORS = [
    "ClassActivity-130961", 
    "ClassActivity-130975", 
    "ClassActivity-131169"
]
STATE_FILE = "seen_dates.json"
FEED_FILE = "feed.xml"

def get_proxies():
    host = os.environ.get("BRIGHTDATA_HOST")
    port = os.environ.get("BRIGHTDATA_PORT")
    user = os.environ.get("BRIGHTDATA_USERNAME")
    password = os.environ.get("BRIGHTDATA_PASSWORD")

    if not all([host, port, user, password]):
        print("⚠️ Missing Proxy Credentials! Attempting without proxy...")
        return None

    proxy_url = f"http://{user}:{password}@{host}:{port}"
    return {"http": proxy_url, "https": proxy_url}

def get_current_slots():
    print(f"🔎 Visiting {URL}...")
    proxies = get_proxies()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        if proxies:
            print("   🛡️ Using Bright Data Proxy...")
            response = requests.get(URL, headers=headers, proxies=proxies, timeout=30, verify=False)
        else:
            response = requests.get(URL, headers=headers, timeout=30)
        
        response.raise_for_status()
        print("✅ Page loaded successfully.")
    except Exception as e:
        print(f"❌ Error fetching page: {e}")
        return set()

    soup = BeautifulSoup(response.text, 'html.parser')
    found_slots = set()
    
    print("--- Parsing HTML Tables ---")
    
    for anchor_id in TARGET_ANCHORS:
        # 1. Find the Anchor Tag
        anchor = soup.find("a", attrs={"name": anchor_id})
        
        if anchor:
            print(f"🎯 Found Anchor: {anchor_id}")
            
            # 2. Find the container ROW immediately following the anchor
            container_row = anchor.find_next("div", class_="row")
            
            if container_row:
                # Get the Title (usually in an h4 tag inside this row)
                title_tag = container_row.find("h4")
                title_text = title_tag.get_text(strip=True) if title_tag else "Activity"
                print(f"   -> Activity Title: '{title_text}'")

                # 3. Find the Table inside this row
                table = container_row.find("table", class_="activity-occasions")
                
                if table:
                    # 4. Find all rows (tr) - including hidden ones
                    rows = table.find_all("tr", class_="activity-occasion")
                    print(f"   -> Found {len(rows)} rows in table.")
                    
                    for row in rows:
                        # Extract Date (in <small>) and Time (in <strong>)
                        date_tag = row.find("small")
                        time_tag = row.find("strong")
                        
                        if date_tag and time_tag:
                            date_str = date_tag.get_text(strip=True)
                            time_str = time_tag.get_text(strip=True)
                            
                            # Clean up strings
                            full_slot = f"{date_str} @ {time_str}"
                            
                            # Optional: Check if it's bookable (look for 'Book' text or waitlist)
                            # For now, we capture ALL dates that appear, as you want to know when dates are added.
                            unique_id = f"{full_slot} [{title_text}]"
                            
                            print(f"      -> Found Slot: {unique_id}")
                            found_slots.add(unique_id)
                else:
                    print("   ⚠️ No table found in this activity row.")
            else:
                print("   ⚠️ Anchor found, but no 'row' div followed it.")
        else:
            print(f"   ℹ️ Anchor {anchor_id} not found on page.")

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
 <description>Availability Updates</description>
 <link>{URL}</link>
 <lastBuildDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
 <pubDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
 <ttl>60</ttl>"""
    
    rss_footer = "\n</channel>\n</rss>"
    
    new_item = ""
    if new_slots:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
        guid = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        description_html = "<h3>New Slots Added:</h3><ul>" + "".join([f"<li>{s}</li>" for s in new_slots]) + "</ul>"
        
        new_item = f"""
 <item>
  <title>🎾 {len(new_slots)} New Slots Found!</title>
  <description><![CDATA[{description_html} <br/> <a href="{URL}">Book Now</a>]]></description>
  <link>{URL}</link>
  <guid isPermaLink="false">{guid}</guid>
  <pubDate>{timestamp}</pubDate>
 </item>"""

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
    
    print("💾 Files saved.")

def main():
    print("--- Starting Padel Monitor (Table Method) ---")
    current_slots = get_current_slots()
    
    # Load previously seen
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
        update_files(new_slots, current_slots)
    else:
        print("ℹ️ No new slots found.")
        # Ensure feed exists on first run
        if not os.path.exists(FEED_FILE):
             update_files(new_slots, current_slots)

if __name__ == "__main__":
    main()
