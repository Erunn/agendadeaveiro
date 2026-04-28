import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
session = requests.Session()

def parse_pt_date(date_str):
    months = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12',
        # Suporte para abreviaturas comuns
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }
    try:
        # Limpa strings como "28 de abril" ou "28 abril 2026"
        clean_str = date_str.lower().replace(' de ', ' ').strip()
        parts = clean_str.split()
        
        day = parts[0].zfill(2)
        month_name = parts[1].replace('.', '') # remove pontos de abr. set. etc
        month = months.get(month_name, '01')
        
        year = datetime.now().year
        # Se estamos em Dezembro e o evento é em Janeiro, assume o próximo ano
        if datetime.now().month == 12 and month == '01':
            year += 1
            
        return f"{year}-{month}-{day}"
    except Exception as e:
        print(f"Data error on '{date_str}': {e}")
        return datetime.now().strftime('%Y-%m-%d')

def get_data():
    all_events = []
    base_url = "https://www.teatroaveirense.pt"
    
    print("Starting scraper for Teatro Aveirense...")
    
    try:
        res = session.get(f"{base_url}/pt/programacao/", headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.programa_item')
        
        print(f"Found {len(items)} items in listing.")
        
        for item in items:
            h2 = item.select_one('h2')
            date_el = item.select_one('.data')
            link_el = item.select_one('a')
            
            if h2 and date_el and link_el:
                # 1. Umbrella vs Event Name Logic
                span = h2.find('span')
                umbrella_name = span.get_text().strip() if span else ""
                
                # Clone para não afetar o soup original
                h2_clone = BeautifulSoup(str(h2), 'html.parser').find('h2')
                if h2_clone.span:
                    h2_clone.span.decompose()
                
                # Limpeza profunda do nome do evento
                event_name = h2_clone.get_text().replace('::', '').strip()
                event_name = " ".join(event_name.split()) # Remove espaços/tabs extras
                
                if umbrella_name:
                    final_title = f"{umbrella_name.upper()}\n{event_name}"
                else:
                    final_title = event_name

                # 2. Precision Hour Fetching
                url = link_el['href']
                if not url.startswith('http'):
                    url = base_url + url
                
                time_iso = ""
                try:
                    # Pequeno delay para evitar bloqueios
                    time.sleep(0.5) 
                    event_page = session.get(url, headers=HEADERS, timeout=5)
                    inner_soup = BeautifulSoup(event_page.text, 'html.parser')
                    horario_p = inner_soup.select_one('p.horarios_txt')
                    
                    if horario_p:
                        text_content = horario_p.get_text(separator="\n")
                        lines = text_content.split('\n')
                        
                        for line in lines:
                            if 'h' in line.lower() and any(char.isdigit() for char in line):
                                # Regex para pegar o formato 21h30 ou 21:30
                                time_part = re.split(r'[–\u2014-]', line)[0].strip()
                                match = re.search(r'(\d{1,2})[h:](\d{2})', time_part.lower())
                                if match:
                                    h = match.group(1).zfill(2)
                                    m = match.group(2)
                                    time_iso = f"T{h}:{m}:00"
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
                print(f"Processed: {event_name}")

    except Exception as e: 
        print(f"General Scraper Error: {e}")

    # Save to JSON
    if all_events:
        with open('events.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)
        print(f"Scraper finished successfully. Total events: {len(all_events)}")
    else:
        print("No events scraped. Check if the website structure has changed.")

if __name__ == "__main__":
    get_data()
