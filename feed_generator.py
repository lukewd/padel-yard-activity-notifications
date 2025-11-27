import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import sys

# --- CONFIGURATION ---
URL = "https://www.matchi.se/facilities/g4pthepadelyard" 
TARGET_KEYWORDS = ["Master Class", "Oscar Marhuenda", "Intermediate"]
STATE_FILE = "seen_dates.json"
FEED_FILE = "feed.xml"

def get_proxies():
    # Read credentials from GitHub Secrets (Environment Variables)
    host = os.environ.get("BRIGHTDATA_HOST")
    port = os.environ.get("BRIGHTDATA_PORT")
    user = os.environ.get("BRIGHTDATA_USERNAME")
    password = os.environ.get("BRIGHTDATA_PASSWORD")

    if not all([host, port, user, password]):
        print("⚠️ Missing Proxy Credentials! Attempting without proxy (might fail)...")
        return None

    # Construct the connection string
    # Format: http://user:password@host:port
    proxy_url = f"http://{user}:{password}@{host}:{port}"
    
    return {
        "http": proxy_url,
        "https": proxy_url
    }

def get_current_slots():
    print(f"🔎 Visiting {URL}...")
    
    proxies = get_proxies()
    
    # Fake being a real Chrome browser on Windows
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        if proxies:
            print("   🛡️ Using Bright Data Proxy...")
            response = requests.get(URL, headers=headers, proxies=proxies, timeout=30, verify=True)
        else:
            response = requests.get(URL, headers=headers, timeout=30)
            
        response.raise_for_status()
        print("✅ Page loaded successfully.")
    except Exception as e:
        print(f"❌ Error fetching page: {e}")
        return set()

    soup = BeautifulSoup(response.text, 'html.parser')
    found_slots = set()
    
    # DEBUG: Print headers to confirm we see the content
    print("--- Content Check ---")
    headers = soup.find_all(['h3', 'h4', 'div'])
    
    target_node = None
    for tag in headers:
        text = tag.text.strip()
        if all(keyword in text for keyword in TARGET_KEYWORDS):
            print(f"🎯 FOUND TARGET: '{text}'")
            target_node = tag
            break
            
    if not target_node:
        print(f"⚠️ Could not find section matching: {TARGET_KEYWORDS}")
        return set()

    # Find Container
    container = target_node.find_parent(class_="panel") or target_node.find_parent(class_="row")
    
    if not container:
        print("⚠️ Found header, but could not isolate container.")
        return set()

    # Extract Dates
    print("   Scanning for dates...")
    lines = container.get_text(separator="|").split("|")
    for line in lines:
        clean_line = line.strip()
        if "2025-" in clean_line or "2024-" in clean_line:
             print(f"      -> Found: {clean_line}")
             found_slots.add(clean_line)

    return found_slots

def update_files(new_slots, all_current_slots):
    # Update JSON
    with open(STATE_FILE, 'w') as f:
        json.dump(list(all_current_slots), f)
    
    # Update RSS
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
        description_html = "<h3>Available Slots:</h3><ul>" + "".join([f"<li>{s}</li>" for s in new_slots]) + "</ul>"
        
        new_item = f"""
 <item>
  <title>🎾 {len(new_slots)} Slots Available!</title>
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
    print("--- Starting Padel Monitor (Proxy Enabled) ---")
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
        update_files(new_slots, current_slots) # Update both files
    else:
        print("ℹ️ No new slots found.")
        # We STILL update files if it's the first run (file missing)
        if not os.path.exists(FEED_FILE):
             update_files(new_slots, current_slots)

if __name__ == "__main__":
    main()
