import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def parse_pt_date(date_str):
    months = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04', 'maio': '05', 
        'junho': '06', 'julho': '07', 'agosto': '08', 'setembro': '09', 'outubro': '10', 
        'novembro': '11', 'dezembro': '12'
    }
    try:
        # Clean string: "28 Abril" -> ["28", "abril"]
        clean = date_str.lower().replace(' de ', ' ').strip()
        parts = clean.split()
        day = parts[0].zfill(2)
        month = months.get(parts[1], '01')
        return f"{datetime.now().year}-{month}-{day}"
    except:
        return datetime.now().strftime('%Y-%m-%d')

def get_data():
    all_events = []

    # 1. TEATRO AVEIRENSE (Updated Selector)
    try:
        res = requests.get("https://www.teatroaveirense.pt/pt/programacao/", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # The site structure usually uses an article or div with a specific class for the list
        items = soup.find_all(class_='item') # Or check if it is 'event-item'
        for item in items:
            title_el = item.select_one('h2 a') or item.select_one('.title a')
            date_el = item.select_one('.date')
            if title_el and date_el:
                all_events.append({
                    "title": f"🎭 {title_el.text.strip()}",
                    "start": parse_pt_date(date_el.text.strip()),
                    "url": "https://www.teatroaveirense.pt" + title_el['href'],
                    "source": "teatro", "color": "#e67e22"
                })
        print(f"Teatro: Found {len(items)} items")
    except Exception as e: print(f"Teatro Error: {e}")

    # 2. CINEMA GLICINIAS (Updated for Filmspot/Cinecartaz style)
    try:
        res = requests.get("https://filmspot.pt/cinema/cinemas-nos-glicinias-aveiro-24/", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for movie in soup.select('.movie-item, .film-info'): # Common selectors for cinema lists
            title = movie.select_one('h3, .title')
            if title:
                all_events.append({
                    "title": f"🎬 {title.text.strip()}",
                    "start": datetime.now().strftime('%Y-%m-%d'),
                    "source": "cinema", "color": "#3498db"
                })
    except Exception as e: print(f"Cinema Error: {e}")

    # 3. VIRAL AGENDA (Updated Selector)
    try:
        res = requests.get("https://www.viralagenda.com/pt/aveiro/aveiro", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for event in soup.select('.event-item, .item'):
            title = event.select_one('.title a, h3 a')
            if title:
                all_events.append({
                    "title": f"🌟 {title.text.strip()}",
                    "start": datetime.now().strftime('%Y-%m-%d'),
                    "url": "https://www.viralagenda.com" + title['href'] if title['href'].startswith('/') else title['href'],
                    "source": "viral", "color": "#8e44ad"
                })
    except Exception as e: print(f"Viral Error: {e}")

    # Final Save
    if all_events:
        with open('events.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)
        print(f"SUCCESS: Saved {len(all_events)} events to events.json")
    else:
        print("WARNING: No events found. Check website selectors.")

if __name__ == "__main__":
    get_data()
