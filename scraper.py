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
    def replacer(m):
        try:
            h_str = m.group(1) or m.group(3)
            m_str = m.group(2) or m.group(4)
            h = int(h_str)
            m_min = int(m_str) if m_str else 0
            return f"{h:02d}:{m_min:02d}"
        except Exception:
            return m.group(0)
    return re.sub(r'(?<!\d)(\d{1,2})[hH](\d{2})?|(?<!\d)(\d{1,2}):(\d{2})', replacer, text)

def parse_days_from_str(text):
    day_map = {'2ª': 0, '2a': 0, '3ª': 1, '3a': 1, '4ª': 2, '4a': 2, '5ª': 3, '5a': 3, '6ª': 4, '6a': 4, 'sáb': 5, 'sab': 5, 'dom': 6}
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
        html_text = res.content.decode('utf-8', errors='replace') # Forçar UTF-8 contra caracteres estranhos
        soup = BeautifulSoup(html_text, 'html.parser')
        
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
                    event_html = event_page.content.decode('utf-8', errors='replace')
                    inner_soup = BeautifulSoup(event_html, 'html.parser')
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
                        "title": event_name, "start": d_date + time_iso, "url": url, "source": "teatro",
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
        html_text = res.content.decode('utf-8', errors='replace') # Forçar UTF-8
        soup = BeautifulSoup(html_text, 'html.parser')
        
        today = datetime.now().date()
        days_to_next_wed = (2 - today.weekday()) % 7
        if days_to_next_wed == 0: days_to_next_wed = 7 
        target_dates = [today + timedelta(days=i) for i in range(days_to_next_wed + 1)]

        for block in soup.select('.movie-card'):
            title_el = block.select_one('.movie-card__title')
            if not title_el: continue
            title = title_el.get_text(strip=True)
            img_el = block.select_one('img')
            img_url = img_el['src'] if img_el and 'src' in img_el.attrs else ""
            link_el = block.select_one('a.block-link')
            movie_url = base_cine_url + link_el['href'] if link_el and 'href' in link_el.attrs else url
            movie_times_by_date = {} 
            
            for p in block.select('.movie-card__info p'):
                text_content = p.get_text(separator="\n").strip()
                if not re.search(r'(?i)sess[õo]e?s', text_content): continue
                current_days = set(range(7)) 
                for line in text_content.split('\n'):
                    s_raw = line.strip()
                    s_lower = s_raw.lower()
                    if not s_raw or re.match(r'(?i)^sess[õo]e?s:$', s_lower): continue
                    if re.search(r'\d{1,2}[hH:]\d{0,2}', s_lower):
                        inline_days = parse_days_from_str(s_lower)
                        if inline_days: current_days = inline_days
                        times_str = s_raw
                        if ':' in s_raw:
                            prefix, suffix = s_raw.split(':', 1)
                            if any(d in prefix.lower() for d in ['2ª', '2a', '3ª', '3a', '4ª', '4a', '5ª', '5a', '6ª', '6a', 'sáb', 'sab', 'dom', 'dia', 'sess']):
                                times_str = suffix.strip()
                        formatted_times = clean_times_and_tags(times_str)
                        formatted_times = re.sub(r'(?i)^sess[õo]e?s\s*:?\s*', '', formatted_times).lstrip(' :,-')
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
                        "title": title, "start": date_str, "url": movie_url, "source": "cinema",
                        "extendedProps": {
                            "image": img_url, "display_time": " | ".join(times_list), 
                            "source": "cinema", "category": "Cinema", "category_normalized": "cinema"
                        }
                    })
        return final_cinema
    except Exception as e:
        print(f"Erro Cinema: {e}")
        return []

def get_23milhas_data():
    final_23milhas = []
    base_url = "https://www.23milhas.pt"
    print("A iniciar scraper para 23 Milhas (Ílhavo)...")
    try:
        event_links = set()

        for path in ["", "/programacao"]:
            try:
                res = session.get(base_url + path, headers=HEADERS, timeout=15)
                html_text = res.content.decode('utf-8', errors='replace')
                
                raw_urls = re.findall(r'(/evento/[^"\'\s\\><]+|evento/[^"\'\s\\><]+)', html_text.replace('\\/', '/'))
                for r_url in raw_urls:
                    clean_url = r_url if r_url.startswith('/') else '/' + r_url
                    clean_url = clean_url.rstrip('.,;:') 
                    event_links.add(base_url + clean_url)
            except Exception:
                pass

        print(f"-> Encontrados {len(event_links)} links potenciais. A recolher detalhes sem truncaturas...")

        for url in event_links:
            try:
                time.sleep(0.1)
                ev_res = session.get(url, headers=HEADERS, timeout=5)
                ev_html = ev_res.content.decode('utf-8', errors='replace') # Forçar UTF-8 na página de detalhe
                ev_soup = BeautifulSoup(ev_html, 'html.parser')

                # TÍTULO E UMBRELLA LIMPOS (Separação a partir do Hífen ou Barra Vertical)
                title = ""
                og_title = ev_soup.find('meta', property='og:title')
                if og_title: 
                    title = og_title['content'].replace(' - 23 Milhas', '').strip()
                
                if not title: continue 

                # Separação Inteligente: O Nome fica antes do "-", o Umbrella fica com o que estiver depois
                umbrella = ""
                if " - " in title:
                    parts = title.split(" - ", 1)
                    title = parts[0].strip()
                    umbrella = parts[1].strip().rstrip('. ')
                elif " | " in title:
                    parts = title.split(" | ", 1)
                    title = parts[0].strip()
                    umbrella = parts[1].strip().rstrip('. ')

                # IMAGEM
                img_url = ""
                og_img = ev_soup.find('meta', property='og:image')
                if og_img: img_url = og_img['content']

                # TEXTOS PARA DATAS E HORAS
                page_text = ev_soup.get_text(separator=' ').lower()
                all_texts = [el.get_text(strip=True) for el in ev_soup.find_all(string=True) if el.get_text(strip=True)]
                
                months_regex = r'(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)'
                date_match = re.search(r'\b(\d{1,2})\s+(?:de\s+)?' + months_regex + r'(?:\s+(?:de\s+)?(\d{4}))?\b', page_text)
                
                date_str = ""
                if date_match:
                    y = date_match.group(3) or str(datetime.now().year)
                    date_str = f"{date_match.group(1)} {date_match.group(2)} {y}"
                
                start_iso = parse_pt_date(date_str) if date_str else datetime.now().strftime('%Y-%m-%d')

                time_str = ""
                cat_str = ""
                for i, txt in enumerate(all_texts):
                    t_low = txt.lower()
                    if t_low == 'horário' and i + 1 < len(all_texts):
                        time_str = all_texts[i+1]
                    if t_low == 'categoria' and i + 1 < len(all_texts):
                        cat_str = all_texts[i+1]
                
                display_time = "Todo o dia"
                if time_str:
                    time_match = re.search(r'\b(\d{1,2}[:hH]\d{2})\b', time_str)
                    if time_match:
                        t_clean = time_match.group(1).replace('h', ':').replace('H', ':')
                        start_iso += f"T{t_clean}:00"
                        display_time = time_str
                    else:
                        start_iso += "T00:00:00"
                else:
                    time_match = re.search(r'\b(\d{1,2}[:hH]\d{2})\b', page_text)
                    if time_match:
                        t_clean = time_match.group(1).replace('h', ':').replace('H', ':')
                        start_iso += f"T{t_clean}:00"
                        display_time = time_match.group(1)
                    else:
                        start_iso += "T00:00:00"

                # LOCAL / UMBRELLA (Se não apanhou Umbrella no título, deduz do local)
                if not umbrella:
                    umbrella = "23 Milhas"
                    if "casa cultura" in page_text or "casa da cultura" in page_text: umbrella = "Casa da Cultura de Ílhavo"
                    elif "fábrica das ideias" in page_text or "fábrica" in page_text: umbrella = "Fábrica das Ideias da Gafanha"
                    elif "laboratório das artes" in page_text: umbrella = "Laboratório das Artes"
                    elif "cais criativo" in page_text: umbrella = "Cais Criativo da Costa Nova"
                    elif "planteia" in page_text: umbrella = "Planteia"

                # CATEGORIA
                cat = "Outros"
                if cat_str:
                    cat_low = cat_str.lower()
                    if "música" in cat_low or "concerto" in cat_low: cat = "Música"
                    elif "teatro" in cat_low: cat = "Teatro"
                    elif "oficina" in cat_low or "workshop" in cat_low: cat = "Workshop"
                    elif "dança" in cat_low or "danca" in cat_low: cat = "Dança"
                    elif "experiência" in cat_low or "experiencia" in cat_low: cat = "Multidisciplinar"
                    else: cat = cat_str.capitalize()
                else:
                    if "música" in page_text or "concerto" in page_text: cat = "Música"
                    elif "teatro" in page_text: cat = "Teatro"
                    elif "oficina" in page_text or "workshop" in page_text: cat = "Workshop"
                    elif "dança" in page_text or "danca" in page_text: cat = "Dança"
                    elif "experiência" in page_text or "experiencia" in page_text: cat = "Multidisciplinar"

                final_23milhas.append({
                    "title": title,
                    "start": start_iso,
                    "url": url,
                    "source": "23milhas",
                    "extendedProps": {
                        "umbrella": umbrella,
                        "image": img_url,
                        "source": "23milhas",
                        "description": "",
                        "category": cat,
                        "category_normalized": normalize_category(cat),
                        "display_time": display_time
                    }
                })
            except Exception as e:
                pass

        print(f"-> Sucesso: {len(final_23milhas)} eventos do 23 Milhas extraídos perfeitamente!")

    except Exception as e:
        print(f"Erro global 23 Milhas: {e}")

    return final_23milhas

if __name__ == "__main__":
    results = get_teatro_data() + get_cinema_data() + get_23milhas_data()
    # A garantia absoluta de que o JSON grava com formato internacional para acentos
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Sucesso Total! Aglomerados {len(results)} eventos guardados.")
