import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime, timedelta

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
            return default_date or datetime.now().strftime('%Y-%m-%d')

        year = datetime.now().year
        for d in days:
            if len(d) == 4:
                year = int(d)
                break
        else:
            if datetime.now().month >= 10 and month in ['01', '02', '03']:
                year += 1

        return f"{year}-{month}-{day}"
    except Exception:
        return default_date or datetime.now().strftime('%Y-%m-%d')

def get_teatro_data():
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
            img_url = img_el.get('src', '') if img_el else ""
            if img_url and not img_url.startswith('http'):
                img_url = base_url + img_url

            resumo_text = item.select_one('.resumo').get_text(strip=True) if item.select_one('.resumo') else ""
            categoria_el = item.select_one('.categoria')
            categoria_text = "Vários"
            if categoria_el:
                if categoria_el.select_one('.sr-only'): categoria_el.select_one('.sr-only').decompose()
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

                listing_date = parse_pt_date(date_el.text.strip())
                daily_schedules = {}
                
                try:
                    time.sleep(0.2) 
                    event_page = session.get(url, headers=HEADERS, timeout=5)
                    inner_soup = BeautifulSoup(event_page.text, 'html.parser')
                    horarios_elements = inner_soup.select('.horarios_txt')
                    
                    if horarios_elements:
                        for hp in horarios_elements:
                            text_content = hp.get_text(separator="\n").lower()
                            lines = text_content.split('\n')
                            day_date = parse_pt_date(lines[0], default_date=listing_date)
                            times_in_block = re.findall(r'(\d{1,2})[h:](\d{2})', text_content)
                            if day_date not in daily_schedules: daily_schedules[day_date] = set()
                            for h, m in times_in_block: daily_schedules[day_date].add(f"{h.zfill(2)}:{m}")
                except Exception: pass

                if not daily_schedules: daily_schedules[listing_date] = set()
                    
                for d_date, times_set in daily_schedules.items():
                    sorted_times = sorted(list(times_set))
                    display_time = " / ".join(sorted_times) if sorted_times else "Todo o dia"
                    time_iso = f"T{sorted_times[0]}:00" if sorted_times else ""

                    all_events.append({
                        "title": final_title,
                        "start": d_date + time_iso,
                        "url": url,
                        "source": "teatro",
                        "extendedProps": {
                            "image": img_url,
                            "source": "teatro",
                            "description": resumo_text,
                            "category": categoria_text,
                            "display_time": display_time,
                            "is_glicinias": False
                        },
                        "raw_event_name": event_name,
                        "raw_umbrella_name": umbrella_name
                    })
        
        umbrella_names = {ev["raw_umbrella_name"].lower() for ev in all_events if ev.get("raw_umbrella_name")}
        final_teatro = []
        for ev in all_events:
            if ev.get("raw_event_name", "").lower() in umbrella_names: continue
            ev.pop("raw_event_name", None); ev.pop("raw_umbrella_name", None)
            final_teatro.append(ev)
        return final_teatro
    except Exception as e:
        print(f"Erro Teatro: {e}"); return []

def get_cinema_data():
    cinema_events_by_date = {}
    url = "https://cinecartaz.publico.pt/cinema/zon-lusomundo-glicinias-17718"
    print("A iniciar scraper para Cinema Glicínias...")
    try:
        res = session.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        day_map = {'2ª': 0, '3ª': 1, '4ª': 2, '5ª': 3, '6ª': 4, 'sáb.': 5, 'dom.': 6, 'sab': 5, 'dom': 6}
        today = datetime.now().date()
        days_to_next_wed = (2 - today.weekday()) % 7
        if days_to_next_wed == 0: days_to_next_wed = 7 
        target_dates = [today + timedelta(days=i) for i in range(days_to_next_wed + 1)]

        for block in soup.select('.movie-card'):
            title = block.select_one('.movie-card__title').get_text(strip=True)
            img_el = block.select_one('.flex-media img')
            img_url = img_el['src'] if img_el else ""
            
            for p in block.select('.movie-card__info p'):
                if 'Sessões:' in p.get_text():
                    text = p.get_text(strip=True).replace('Sessões:', '')
                    if ':' not in text: continue
                    dias_raw, horarios = text.split(':', 1)
                    dias_list = dias_raw.lower().split()
                    for dt in target_dates:
                        is_showing = any(d in day_map and day_map[d] == dt.weekday() for d in dias_list)
                        if is_showing:
                            date_str = dt.strftime('%Y-%m-%d')
                            if date_str not in cinema_events_by_date: cinema_events_by_date[date_str] = []
                            cinema_events_by_date[date_str].append({"titulo": title, "img": img_url, "horas": horarios.strip()})

        final_cinema = []
        for d_date, movies in cinema_events_by_date.items():
            final_cinema.append({
                "title": "CINEMA: GLICÍNIAS PLAZA",
                "start": d_date,
                "url": url,
                "source": "cinema",
                "extendedProps": { "is_glicinias": True, "movies": movies, "source": "cinema" }
            })
        return final_cinema
    except Exception as e:
        print(f"Erro Cinema: {e}"); return []

if __name__ == "__main__":
    results = get_teatro_data() + get_cinema_data()
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Sucesso! Total: {len(results)}")
