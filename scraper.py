import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
session = requests.Session() # Keeps the connection open for speed

def get_data():
    all_events = []
    res = session.get("https://www.teatroaveirense.pt/pt/programacao/", headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    items = soup.select('.programa_item')

    for item in items:
        h2 = item.select_one('h2')
        date_el = item.select_one('.data')
        link_el = item.select_one('a')

        if h2 and date_el:
            # Hierarchy Logic
            umbrella = h2.find('span').get_text().strip() if h2.find('span') else ""
            h2_clone = BeautifulSoup(str(h2), 'html.parser').find('h2')
            if h2_clone.span: h2_clone.span.decompose()
            performance_name = h2_clone.get_text().replace('::', '').strip()
            
            # 1. Try to find Time in the main listing first
            time_match = re.search(r'(\d{2}[h:]\d{2})', item.get_text())
            
            # 2. If not found, only THEN make the second request
            url = "https://www.teatroaveirense.pt" + link_el['href']
            if not time_match:
                try:
                    event_page = session.get(url, headers=HEADERS, timeout=5)
                    # This looks exactly for the tag in your screenshot
                    inner_soup = BeautifulSoup(event_page.text, 'html.parser')
                    horario_el = inner_soup.select_one('.horarios_txt')
                    if horario_el:
                        time_match = re.search(r'(\d{2}[h:]\d{2})', horario_el.get_text())
                except: pass

            time_iso = "T" + time_match.group(1).replace('h', ':') if time_match else ""
            
            all_events.append({
                "title": f"{umbrella}\n{performance_name}",
                "start": parse_pt_date(date_el.text.strip()) + time_iso,
                "url": url,
                "source": "teatro",
                "color": "#e67e22"
            })

    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)
