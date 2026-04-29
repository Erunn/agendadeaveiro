import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
session = requests.Session()

def parse_pt_date(date_str, default_date=None):
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
        if not days:
            return default_date or datetime.now().strftime('%Y-%m-%d')
        
        day = days[0].zfill(2)

        month = None
        for word in clean_str.split():
            word_clean = re.sub(r'[^a-zç]', '', word)
            if word_clean in months:
                month = months[word_clean]
                break

        if not month:
            if default_date: return default_date
            return datetime.now().strftime('%Y-%m-%d')

        year = datetime.now().year
        # Procura se o ano com 4 dígitos foi explicitamente escrito no HTML
        for d in days:
            if len(d) == 4:
                year = int(d)
                break
        else:
            if datetime.now().month >= 10 and month in ['01', '02', '03']:
                year += 1

        return f"{year}-{month}-{day}"
    except Exception as e:
        return default_date or datetime.now().strftime('%Y-%m-%d')

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
            
            img_el = item.select_one('img')
            img_url = ""
            if img_el:
                img_url = img_el.get('src', '')
                if img_url and not img_url.startswith('http'):
                    img_url = base_url + img_url

            resumo_el = item.select_one('.resumo')
            resumo_text = resumo_el.get_text(strip=True) if resumo_el else ""

            categoria_el = item.select_one('.categoria')
            categoria_text = "Vários"
            if categoria_el:
                sr = categoria_el.select_one('.sr-only')
                if sr: sr.decompose()
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

                # Data base encontrada na listagem principal
                listing_date = parse_pt_date(date_el.text.strip())
                daily_schedules = {}
                
                try:
                    time.sleep(0.3) 
                    event_page = session.get(url, headers=HEADERS, timeout=5)
                    inner_soup = BeautifulSoup(event_page.text, 'html.parser')
                    
                    horarios_elements = inner_soup.select('.horarios_txt')
                    if horarios_elements:
                        for hp in horarios_elements:
                            text_content = hp.get_text(separator="\n").lower()
                            lines = text_content.split('\n')
                            
                            # A data costuma estar na 1ª linha. Se falhar, usa a data da listagem
                            day_date = parse_pt_date(lines[0], default_date=listing_date)
                            
                            # Apanha TODAS as horas mencionadas no bloco
                            times_in_block = re.findall(r'(\d{1,2})[h:](\d{2})', text_content)
                            
                            if day_date not in daily_schedules:
                                daily_schedules[day_date] = set()
                            
                            # Adiciona as horas ao "saco" desse dia (o set() impede duplicados)
                            for h, m in times_in_block:
                                daily_schedules[day_date].add(f"{h.zfill(2)}:{m}")
                except Exception as e:
                    print(f"Erro ao buscar detalhes do evento: {e}")

                # Se não encontrou horários detalhados, marca como "Todo o dia"
                if not daily_schedules:
                    daily_schedules[listing_date] = set()
                    
                # Cria um evento final por cada dia distinto agrupando as horas
                for d_date, times_set in daily_schedules.items():
                    sorted_times = sorted(list(times_set))
                    if sorted_times:
                        display_time = " / ".join(sorted_times) # ex: 15:30 / 21:30
                        time_iso = f"T{sorted_times[0]}:00"
                    else:
                        display_time = "Todo o dia"
                        time_iso = ""

                    all_events.append({
                        "title": final_title,
                        "start": d_date + time_iso,
                        "url": url,
                        "source": "teatro",
                        "color": "#e67e22",
                        "extendedProps": {
                            "image": img_url,
                            "source": "teatro",
                            "description": resumo_text,
                            "category": categoria_text,
                            "display_time": display_time
                        }
                    })
                print(f"Processado: {event_name} ({len(daily_schedules)} dia(s) processados)")

    except Exception as e: print(f"Erro Geral: {e}")

    if all_events:
        with open('events.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)

if __name__ == "__main__": get_data()
