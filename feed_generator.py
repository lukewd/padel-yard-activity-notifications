import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import sys
import urllib3
import hashlib

# Suppress the "InsecureRequest" warnings from the Proxy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
# Each facility page and the ClassActivity anchors to watch on it
TARGETS = [
    {
        "location": "Wandsworth",
        "url": "https://www.matchi.se/facilities/g4pthepadelyard",
        "anchors": [
            "ClassActivity-130961",  # Oscar Marhuenda
            "ClassActivity-130975",  # Oscar Marhuenda
            "ClassActivity-131169",  # Oscar Marhuenda
            "ClassActivity-141279",  # Lower Intermediate Group Lesson Levels 3-4
        ],
    },
    {
        "location": "Vauxhall",
        "url": "https://www.matchi.se/facilities/g4pvauxhallpadelyard",
        "anchors": [
            "ClassActivity-134171",  # Lower Intermediate Group Lesson Level 3-4
        ],
    },
]
URL = TARGETS[0]["url"]  # Channel link for the feed
OCCASIONS_URL = "https://www.matchi.se/facilities/activityOccasions"  # Backs the 'Show more occasions' link
LEGACY_LOCATION = "Wandsworth"  # Slots saved before multi-location support
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")  # Push notifications via ntfy.sh (optional)
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def fetch_html(url, proxies, params=None):
    if proxies:
        response = requests.get(url, headers=HEADERS, params=params, proxies=proxies, timeout=30, verify=False)
    else:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')

def fetch_more_rows(container_row, proxies):
    """The page only includes the first few occasions; the rest load via the 'Show more occasions' link."""
    link = container_row.find("a", class_="load-activity-occasions")
    if not link:
        return []

    loaded = int(link.get("data-loaded-count", 0))
    total = int(link.get("data-total-count", 0))
    rows = []
    while loaded < total:
        soup = fetch_html(OCCASIONS_URL, proxies, params={
            "activityId": link.get("data-activity-id"),
            "offset": loaded,
            "max": total - loaded,
        })
        batch = soup.find_all("tr", class_="activity-occasion")
        if not batch:
            break
        rows.extend(batch)
        loaded += len(batch)
    return rows

def get_current_slots(target, proxies):
    """Returns the set of slots for one facility, or None if the page couldn't be fetched."""
    url = target["url"]
    location = target["location"]
    print(f"🔎 Visiting {url}...")
    
    try:
        if proxies:
            print("   🛡️ Using Bright Data Proxy...")
        soup = fetch_html(url, proxies)
        print("✅ Page loaded successfully.")
    except Exception as e:
        print(f"❌ Error fetching page: {e}")
        return None
    found_slots = set()
    
    print("--- Parsing HTML Tables ---")
    
    for anchor_id in target["anchors"]:
        # Find the Anchor Tag
        anchor = soup.find("a", attrs={"name": anchor_id})
        
        if not anchor:
            print(f"   ⚠️ {anchor_id} not found on {location} page")
        else:
            # Find the container ROW immediately following the anchor
            container_row = anchor.find_next("div", class_="row")
            
            if container_row:
                # Get the Title
                title_tag = container_row.find("h4")
                title_text = title_tag.get_text(strip=True) if title_tag else "Activity"

                # Find the Table inside this row
                table = container_row.find("table", class_="activity-occasions")
                
                if table:
                    # Find all rows (tr), including those behind 'Show more occasions'
                    rows = table.find_all("tr", class_="activity-occasion")
                    try:
                        rows += fetch_more_rows(container_row, proxies)
                    except Exception as e:
                        # Treat as a failed fetch so a partial list doesn't overwrite the state
                        print(f"❌ Error loading more occasions for {anchor_id}: {e}")
                        return None
                    
                    for row in rows:
                        date_tag = row.find("small")
                        time_tag = row.find("strong")
                        
                        if date_tag and time_tag:
                            date_str = date_tag.get_text(strip=True)
                            time_str = time_tag.get_text(strip=True)
                            
                            # Clean string for the slot
                            full_slot = f"{date_str} @ {time_str}"
                            # Unique ID includes the class title and location so we know which class it is
                            unique_id = f"{full_slot} [{title_text}] | {location}"
                            
                            found_slots.add(unique_id)
    
    print(f"   -> Total slots found on {location} page: {len(found_slots)}")
    return found_slots

def update_files(new_slots, all_current_slots):
    # 1. Update JSON State (Memory)
    with open(STATE_FILE, 'w') as f:
        json.dump(list(all_current_slots), f)
    
    # 2. Prepare RSS Header
    rss_header = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
 <title>Padel Yard Monitor</title>
 <description>Availability Updates</description>
 <link>{URL}</link>
 <lastBuildDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
 <pubDate>{datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
 <ttl>15</ttl>"""
    
    rss_footer = "\n</channel>\n</rss>"
    
    # 3. Create ONE Summary Item if there are new slots
    new_item_block = ""
    if new_slots:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
        # Create a unique ID for this BATCH of updates
        guid = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Build the HTML list for the email body
        # We sort them so the email looks tidy
        sorted_slots = sorted(list(new_slots))
        description_html = "<h3>New Dates Added!</h3><ul>" + "".join([f"<li>{s}</li>" for s in sorted_slots]) + "</ul>"
        book_links = " ".join([f'<a href="{t["url"]}">Book {t["location"]}</a>' for t in TARGETS])
        
        new_item_block = f"""
 <item>
  <title>🎾 {len(new_slots)} New Slots Available!</title>
  <description><![CDATA[{description_html} <br/> {book_links}]]></description>
  <link>{URL}</link>
  <guid isPermaLink="false">{guid}</guid>
  <pubDate>{timestamp}</pubDate>
 </item>"""

    # 4. Read old items to keep history
    old_items = ""
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if "<item>" in content:
                start = content.find("<item>")
                end = content.rfind("</item>") + 7
                old_items = content[start:end]

    # Combine
    final_content = rss_header + new_item_block + "\n" + old_items + rss_footer

    with open(FEED_FILE, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print("💾 Files saved (Summary Mode).")

def send_push(new_slots):
    """Sends a push notification via ntfy. Returns False if it failed."""
    if not NTFY_TOPIC:
        print("ℹ️ NTFY_TOPIC not set, skipping push notification.")
        return True

    sorted_slots = sorted(new_slots)
    body = "\n".join(sorted_slots)
    # Tapping opens the page for the location with new slots (first one if both)
    locations = [t for t in TARGETS if any(s.endswith(f" | {t['location']}") for s in new_slots)]
    headers = {
        "Title": f"{len(new_slots)} new padel slot{'s' if len(new_slots) != 1 else ''}",
        "Tags": "tennis",
        "Click": locations[0]["url"] if locations else URL,
        "Actions": "; ".join([f"view, Book {t['location']}, {t['url']}" for t in locations]),
    }

    try:
        response = requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode("utf-8"), headers=headers, timeout=30)
        response.raise_for_status()
        print("📲 Push notification sent.")
        return True
    except Exception as e:
        print(f"❌ Error sending push notification: {e}")
        return False

def main():
    print("--- Starting Padel Monitor ---")

    # Load previously seen
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try:
                seen_slots = set(json.load(f))
            except:
                seen_slots = set()
    else:
        seen_slots = set()

    # Older entries have no location suffix; they all came from Wandsworth
    seen_slots = {s if " | " in s else f"{s} | {LEGACY_LOCATION}" for s in seen_slots}

    proxies = get_proxies()
    current_slots = set()
    for target in TARGETS:
        slots = get_current_slots(target, proxies)
        if slots is None:
            # Fetch failed: keep what we'd seen here so it isn't re-announced next time
            slots = {s for s in seen_slots if s.endswith(f" | {target['location']}")}
        current_slots |= slots

    new_slots = current_slots - seen_slots

    if new_slots:
        print(f"🎉 FOUND {len(new_slots)} NEW SLOTS!")
        update_files(new_slots, current_slots)
        if not send_push(new_slots):
            # Fail the job so the new state isn't committed and the next run retries
            sys.exit(1)
    else:
        print("ℹ️ No new slots found.")
        # Create the file purely for initialization if it's missing
        if not os.path.exists(FEED_FILE):
             update_files(set(), current_slots)

if __name__ == "__main__":
    main()
