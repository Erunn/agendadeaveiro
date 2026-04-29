import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
session = requests.Session()

def parse_pt_date(date_str):
    months = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12',
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }
    try:
        clean_str = date_str.lower().replace(' de ', ' ').strip()
        days = re.findall(r'\d+', clean_str)
        day = days[0].zfill(2) if days else '01'
        
        month = '01'
        for word in clean_str.split():
            word_clean = re.sub(r'[^a-zç]', '', word)
            if word_clean in months:
                month = months[word_clean]
                break
        
        year = datetime.now().year
        if datetime.now().month == 12 and month == '01':
            year += 1
            
        return f"{year}-{month}-{day}"
    except Exception as e:
        print(f"Data error: {e}")
        return datetime.now().strftime('%Y-%m-%d')

def get_data():
    all_events = []
    base_url = "https://www.teatroaveirense.pt"
    
    print("A iniciar scraper para Teatro Aveirense...")
    
    try:
        res = session.get(f"{base_url}/pt/programacao/", headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.programa_item')
        
        for item in items:
            h2 = item.select_one('h2')
            date_el = item.select_one('.data')
            link_el = item.select_one('a')
            
            # --- IMAGEM ---
            img_el = item.select_one('img')
            img_url = ""
            if img_el:
                img_url = img_el.get('src', '')
                if img_url and not img_url.startswith('http'):
                    img_url = base_url + img_url

            # --- RESUMO ---
            resumo_el = item.select_one('.resumo')
            resumo_text = resumo_el.get_text(strip=True) if resumo_el else ""

            # --- CATEGORIA ---
            categoria_el = item.select_one('.categoria')
            categoria_text = "Vários"
            if categoria_el:
                sr = categoria_el.select_one('.sr-only')
                if sr: sr.decompose() # Remove "Categoria:" oculto
                categoria_text = categoria_el.get_text(strip=True)
            
            if h2 and date_el and link_el:
                span = h2.find('span')
                umbrella_name = span.get_text().strip() if span else ""
                
                h2_clone = BeautifulSoup(str(h2), 'html.parser').find('h2')
                if h2_clone.span: h2_clone.span.decompose()
                
                event_name = " ".join(h2_clone.get_text().replace('::', '').strip().split())
                final_title = f"<b>{umbrella_name.upper()}</b><br>{event_name}" if umbrella_name else event_name

                url = link_el['href']
                if not url.startswith('http'): url = base_url + url
                
                time_iso = ""
                try:
                    time.sleep(0.3) 
                    event_page = session.get(url, headers=HEADERS, timeout=5)
                    horario_p = BeautifulSoup(event_page.text, 'html.parser').select_one('p.horarios_txt')
                    
                    if horario_p:
                        for line in horario_p.get_text(separator="\n").split('\n'):
                            if 'h' in line.lower() and any(char.isdigit() for char in line):
                                match = re.search(r'(\d{1,2})[h:](\d{2})', re.split(r'[–\u2014-]', line)[0].strip().lower())
                                if match:
                                    time_iso = f"T{match.group(1).zfill(2)}:{match.group(2)}:00"
                                    break
                except: pass

                all_events.append({
                    "title": final_title,
                    "start": parse_pt_date(date_el.text.strip()) + time_iso,
                    "url": url,
                    "source": "teatro",
                    "color": "#e67e22",
                    "extendedProps": {
                        "image": img_url,
                        "source": "teatro",
                        "description": resumo_text,
                        "category": categoria_text # Enviando categoria!
                    }
                })
                print(f"Processado: {event_name}")

    except Exception as e: print(f"Erro: {e}")

    if all_events:
        with open('events.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)

if __name__ == "__main__": get_data()
