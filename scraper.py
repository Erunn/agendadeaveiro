import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
session = requests.Session()

def parse_pt_date(date_str):
    months = {'janeiro':'01','fevereiro':'02','março':'03','abril':'04','maio':'05','junho':'06','julho':'07','agosto':'08','setembro':'09','outubro':'10','novembro':'11','dezembro':'12'}
    try:
        parts = date_str.lower().strip().split()
        day = parts[0].zfill(2)
        month = months.get(parts[1], '01')
        return f"{datetime.now().year}-{month}-{day}"
    except:
        return datetime.now().strftime('%Y-%m-%d')

def get_data():
    all_events = []
    try:
        res = session.get("https://www.teatroaveirense.pt/pt/programacao/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.programa_item')
        
        for item in items:
            h2 = item.select_one('h2')
            date_el = item.select_one('.data')
            link_el = item.select_one('a')
            
            if h2 and date_el and link_el:
                # 1. Umbrella vs Event Name Logic
                span = h2.find('span')
                umbrella_name = span.get_text().strip() if span else ""
                
                # Clone H2 to isolate the event name (the text not inside the span)
                h2_clone = BeautifulSoup(str(h2), 'html.parser').find('h2')
                if h2_clone.span: h2_clone.span.decompose()
                event_name = h2_clone.get_text().replace('::', '').strip()
                
                # Format: Umbrella on first line, Event Name on second
                # Using .upper() for the Umbrella helps the CSS hierarchy
                if umbrella_name:
                    final_title = f"{umbrella_name.upper()}\n{event_name}"
                else:
                    final_title = event_name

                # 2. Precision Hour Fetching from Sub-page
                url = "https://www.teatroaveirense.pt" + link_el['href']
                time_iso = ""
                try:
                    event_page = session.get(url, headers=HEADERS, timeout=5)
                    inner_soup = BeautifulSoup(event_page.text, 'html.parser')
                    horario_p = inner_soup.select_one('p.horarios_txt')
                    
                    if horario_p:
                        # Use separator to preserve the line break between Date and Time
                        text_content = horario_p.get_text(separator="\n")
                        lines = text_content.split('\n')
                        
                        for line in lines:
                            # Look for the line containing the time (e.g., "21h30")
                            if 'h' in line and any(char.isdigit() for char in line):
                                # Isolate the part before the hyphen/en-dash
                                # Uses a regex to split by various hyphen types
                                time_part = re.split(r'[–\u2014-]', line)[0].strip()
                                
                                # Convert 21h30 to 21:30
                                match = re.search(r'(\d{1,2})h(\d{2})', time_part)
                                if match:
                                    h = match.group(1).zfill(2)
                                    m = match.group(2)
                                    time_iso = f"T{h}:{m}:00"
                                    print(f"Time found: {h}:{m} for {event_name}")
                                    break
                except Exception as e:
                    print(f"Error fetching detail for {event_name}: {e}")

                all_events.append({
                    "title": final_title,
                    "start": parse_pt_date(date_el.text.strip()) + time_iso,
                    "url": url,
                    "source": "teatro",
                    "color": "#e67e22"
                })

    except Exception as e: 
        print(f"General Scraper Error: {e}")

    # Save to JSON
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)
    print(f"Scraper finished. Total events: {len(all_events)}")

if __name__ == "__main__":
    get_data()
