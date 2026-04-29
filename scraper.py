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

        if not month: return default_date or datetime.now().strftime('%Y-%m-%d')

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

def clean_times_and_tags(text):
    """Converte '16h' ou '16h30' em '16:00' e '16:30', mantendo o resto do texto intacto (como [VP])."""
    def replacer(m):
        h = int(m.group(1) or m.group(3))
        m_min = int(m.group(2) or m.group(4) or 0)
        return f"{h:02d}:{m_min:02d}"
    return re.sub(r'(?<!\d)(\d{1,2})[hH](\d{2})?|(?<!\d)(\d{1,2}):(\d{2})', replacer, text)

def parse_days_from_str(text):
    day_map = {'2ª': 0, '3ª': 1, '4ª': 2, '5ª': 3, '6ª': 4, 'sáb': 5, 'sab': 5, 'dom': 6}
    found = set()
    if 'todos os dias' in text: return set(range(7))
    for k, v in day_map.items():
        if k in text: found.add(v)
    return found

def normalize_category(cat_str):
    cat = cat_str.lower()
    if 'teatro' in cat: return 'teatro'
    if 'cinema' in cat or 'filme' in cat: return 'cinema'
    if 'música' in cat or 'musica' in cat: return 'música'
    if 'dança' in cat or 'danca' in cat: return 'dança'
    if 'workshop' in cat or 'oficina' in cat: return 'workshop'
    if 'ópera' in cat or 'opera' in cat: return 'ópera'
    if 'festival' in cat: return 'festival'
    return 'outros'

def get_teatro_data():
    all_events = []
    base_url = "https://www.teatroaveirense.pt"
    print("A iniciar scraper para Teatro Aveirense...")
    
    try:
        res = session.get(f"{base_url}/pt/programacao/", headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for item in soup.select('.programa_item'):
            h2 = item.select_one('h2')
            date_el = item.select_one('.data')
            link_el = item.select_one('a')
            
            img_el = item.select_one('img')
            img_url = img_el.get('src', '') if img_el else ""
            if img_url and not img_url.startswith('http'): img_url = base_url + img_url

            resumo_text = item.select_one('.resumo').get_text(strip=True) if item.select_one('.resumo') else ""
            categoria_el = item.select_one('.categoria')
            categoria_text = "Outros"
            if categoria_el:
                if categoria_el.select_one('.sr-only'): categoria_el.select_one('.sr-only').decompose()
                categoria_text = categoria_el.get_text(strip=True)
            
            if h2 and date_el and link_el:
                span = h2.find('span')
                umbrella_name = span.get_text().strip() if span else ""
                
                h2_clone = BeautifulSoup(str(h2), 'html.parser').find('h2')
                if h2_clone.span: h2_clone.span.decompose()
                event_name = " ".join(h2_clone.get_text().replace('::', '').strip().split())
                url = link_el['href']
                if not url.startswith('http'): url = base_url + url

                listing_date = parse_pt_date(date_el.text.strip())
                daily_schedules = {}
                
                try:
                    time.sleep(0.2) 
                    event_page = session.get(url, headers=HEADERS, timeout=5)
                    inner_soup = BeautifulSoup(event_page.text, 'html.parser')
                    for hp in inner_soup.select('.horarios_txt'):
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
                        "title": event_name,
                        "start": d_date + time_iso,
                        "url": url,
                        "source": "teatro",
                        "extendedProps": {
                            "umbrella": umbrella_name, "image": img_url, "source": "teatro",
                            "description": resumo_text, "category": categoria_text,
                            "category_normalized": normalize_category(categoria_text), "display_time": display_time
                        },
                        "raw_event_name": event_name, "raw_umbrella_name": umbrella_name
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
    final_cinema = []
    base_cine_url = "https://cinecartaz.publico.pt"
    url = f"{base_cine_url}/cinema/zon-lusomundo-glicinias-17718"
    print("A iniciar scraper para Cinema Glicínias...")
    try:
        res = session.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        today = datetime.now().date()
        days_to_next_wed = (2 - today.weekday()) % 7
        if days_to_next_wed == 0: days_to_next_wed = 7 
        target_dates = [today + timedelta(days=i) for i in range(days_to_next_wed + 1)]

        for block in soup.select('.movie-card'):
            title = block.select_one('.movie-card__title').get_text(strip=True)
            img_el = block.select_one('.flex-media img')
            img_url = img_el['src'] if img_el else ""
            link_el = block.select_one('a.block-link')
            movie_url = base_cine_url + link_el['href'] if link_el and 'href' in link_el.attrs else url
            
            movie_times_by_date = {} 
            
            for p in block.select('.movie-card__info p'):
                text_content = p.get_text(separator="\n").strip()
                if 'Sessões:' not in text_content: continue
                
                current_days = set(range(7)) 
                for line in text_content.split('\n'):
                    s_raw = line.strip()
                    s_lower = s_raw.lower()
                    if not s_raw or s_lower == 'sessões:': continue
                    
                    if re.search(r'\d{1,2}[hH:]\d{0,2}', s_lower):
                        inline_days = parse_days_from_str(s_lower)
                        if inline_days: current_days = inline_days
                        
                        # Extrai as horas + tags ignorando os dias da semana escritos antes de ":"
                        if ':' in s_raw and any(d in s_lower.split(':')[0] for d in ['2ª', '3ª', '4ª', '5ª', '6ª', 'sáb', 'sab', 'dom', 'dia']):
                            times_str = s_raw.split(':', 1)[1].strip()
                        else:
                            times_str = s_raw
                            
                        formatted_times = clean_times_and_tags(times_str)
                        if not formatted_times: continue
                        
                        for dt in target_dates:
                            if dt.weekday() in current_days:
                                date_str = dt.strftime('%Y-%m-%d')
                                if date_str not in movie_times_by_date:
                                    movie_times_by_date[date_str] = []
                                if formatted_times not in movie_times_by_date[date_str]:
                                    movie_times_by_date[date_str].append(formatted_times)
                    else:
                        new_days = parse_days_from_str(s_lower)
                        if new_days: current_days = new_days

            for date_str, times_list in movie_times_by_date.items():
                if times_list:
                    final_cinema.append({
                        "title": title,
                        "start": date_str,
                        "url": movie_url,
                        "source": "cinema",
                        "extendedProps": {
                            "image": img_url,
                            "display_time": " | ".join(times_list), # Junta várias linhas de sessões com " | "
                            "source": "cinema",
                            "category": "Cinema",
                            "category_normalized": "cinema"
                        }
                    })
        return final_cinema
    except Exception as e:
        print(f"Erro Cinema: {e}"); return []

if __name__ == "__main__":
    results = get_teatro_data() + get_cinema_data()
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Sucesso! Total de eventos guardados: {len(results)}")
