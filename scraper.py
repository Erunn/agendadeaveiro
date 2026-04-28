import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def parse_pt_date(date_str):
    months = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
    }
    try:
        # Example: "28 abril"
        parts = date_str.lower().strip().split()
        day = parts[0].zfill(2)
        month = months.get(parts[1], '01')
        return f"{datetime.now().year}-{month}-{day}"
    except:
        return datetime.now().strftime('%Y-%m-%d')

def get_data():
    all_events = []

    # 1. TEATRO AVEIRENSE (Based on your screenshots)
    try:
        res = requests.get("https://www.teatroaveirense.pt/pt/programacao/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        items = soup.select('.programa_item')
        print(f"Teatro: Found {len(items)} items with class .programa_item")
        
        for item in items:
            title_el = item.select_one('h2')
            date_el = item.select_one('.data')
            link_el = item.select_one('a')
            
            if title_el and date_el:
                title_text = title_el.get_text(separator=" ").strip()
                date_text = date_el.text.strip()
                
                url = link_el['href'] if link_el else ""
                if url and not url.startswith('http'):
                    url = "https://www.teatroaveirense.pt" + url

                all_events.append({
                    "title": f"🎭 {title_text}",
                    "start": parse_pt_date(date_text),
                    "url": url,
                    "source": "teatro",
                    "color": "#e67e22"
                })
    except Exception as e: print(f"Teatro Error: {e}")

    # 2. VIRAL AGENDA (Generic fallback)
    try:
        res = requests.get("https://www.viralagenda.com/pt/aveiro/aveiro", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Viral Agenda usually uses event-item or similar
        for event in soup.select('.event-item, .item'):
            title = event.select_one('.title a, h3 a')
            if title:
                all_events.append({
                    "title": f"🌟 {title.text.strip()}",
                    "start": datetime.now().strftime('%Y-%m-%d'),
                    "url": "https://www.viralagenda.com" + title['href'] if title['href'].startswith('/') else title['href'],
                    "source": "viral",
                    "color": "#8e44ad"
                })
    except Exception as e: print(f"Viral Error: {e}")

    # SAVE TO FILE
    if all_events:
        with open('events.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)
        print(f"SUCCESS: Saved {len(all_events)} events.")
    else:
        print("CRITICAL: No events found.")

if __name__ == "__main__":
    get_data()
