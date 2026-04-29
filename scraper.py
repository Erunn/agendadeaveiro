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
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
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
        events_dict = {}

        # Visita a Homepage e a página de Programação
        for path in ["", "/programacao"]:
            try:
                res = session.get(base_url + path, headers=HEADERS, timeout=15)
                soup = BeautifulSoup(res.text, 'html.parser')

                # Procura todos os links de eventos gerados
                for a in soup.find_all('a', href=re.compile(r'evento/')):
                    href = a['href']
                    clean_href = href if href.startswith('/') else '/' + href
                    url = base_url + clean_href
                    
                    if url in events_dict: continue

                    # MÁGICA: Procura o cartão "pai" que contém todos os dados pré-carregados!
                    card = a.find_parent('div', attrs={'data-bl-name': re.compile(r'Box|Grid Item|Slide|wrap|List\.card', re.I)})
                    if not card: continue

                    # Extrair Título Principal
                    title_el = card.find(lambda tag: tag.name == 'div' and 'titulo' in tag.get('data-bl-name', '').lower())
                    title = title_el.get_text(strip=True) if title_el else ""
                    if not title: continue # Ignora se for um card quebrado

                    # Extrair Subtítulo (se existir, ex: "Mochos no Telhado" para adicionar à "Fernanda...")
                    subtitle = ""
                    sub_elements = card.find_all(lambda tag: tag.name == 'div' and 'titulo' in tag.get('data-bl-name', '').lower())
                    if len(sub_elements) > 1:
                        subtitle = " - " + sub_elements[1].get_text(strip=True)
                    full_title = title + subtitle

                    # Extrair Imagem HD
                    img_url = ""
                    img_el = card.find('img')
                    if img_el and img_el.get('src') and 'empty-image' not in img_el.get('src'):
                        img_url = img_el['src']
                    else:
                        # Em muitos cartões do 23 Milhas, a imagem está em background-image num DIV
                        bg_img_el = card.find(lambda tag: tag.has_attr('style') and 'background-image' in tag['style'])
                        if bg_img_el:
                            bg_match = re.search(r'url\((.*?)\)', bg_img_el['style'])
                            if bg_match: img_url = bg_match.group(1).strip('"\'')

                    # Categoria
                    cat_el = card.find(lambda tag: tag.name == 'div' and 'cat' in tag.get('data-bl-name', '').lower())
                    cat = cat_el.get_text(strip=True) if cat_el else "Outros"

                    # Data (Dia + Mês)
                    dia_el = card.find(lambda tag: tag.name == 'div' and 'dia' in tag.get('data-bl-name', '').lower())
                    mes_el = card.find(lambda tag: tag.name == 'div' and 'mes' in tag.get('data-bl-name', '').lower())
                    dia = dia_el.get_text(strip=True) if dia_el else ""
                    mes = mes_el.get_text(strip=True) if mes_el else ""
                    
                    date_str = f"{dia} {mes} {datetime.now().year}" if dia and mes else ""
                    start_iso = parse_pt_date(date_str) if date_str else datetime.now().strftime('%Y-%m-%d')

                    # Hora
                    hora_el = card.find(lambda tag: tag.name == 'div' and 'hora' in tag.get('data-bl-name', '').lower())
                    time_str = hora_el.get_text(strip=True) if hora_el else ""
                    display_time = "Todo o dia"
                    if time_str:
                        t_clean = time_str.replace('h', ':').replace('H', ':')
                        start_iso += f"T{t_clean}:00"
                        display_time = time_str
                    else:
                        start_iso += "T00:00:00"

                    # Local / Umbrella
                    local_el = card.find(lambda tag: tag.name == 'div' and 'local' in tag.get('data-bl-name', '').lower())
                    umbrella = "23 Milhas"
                    if local_el:
                        loc_text = local_el.get_text(strip=True)
                        loc_lower = loc_text.lower()
                        if "casa" in loc_lower: umbrella = "Casa da Cultura de Ílhavo"
                        elif "fábrica" in loc_lower: umbrella = "Fábrica das Ideias da Gafanha"
                        elif "laboratório" in loc_lower: umbrella = "Laboratório das Artes"
                        elif "cais" in loc_lower: umbrella = "Cais Criativo da Costa Nova"
                        elif "planteia" in loc_lower: umbrella = "Planteia"
                        else: umbrella = loc_text

                    # Descrição do evento
                    desc_el = card.find(lambda tag: tag.name == 'div' and 'descri' in tag.get('data-bl-name', '').lower())
                    desc = desc_el.get_text(strip=True) if desc_el else ""

                    events_dict[url] = {
                        "title": full_title,
                        "start": start_iso,
                        "url": url,
                        "source": "23milhas",
                        "extendedProps": {
                            "umbrella": umbrella,
                            "image": img_url,
                            "source": "23milhas",
                            "description": desc,
                            "category": cat,
                            "category_normalized": normalize_category(cat),
                            "display_time": display_time
                        }
                    }
            except Exception as e:
                pass

        for ev in events_dict.values():
            final_23milhas.append(ev)

        print(f"-> Sucesso: {len(final_23milhas)} eventos do 23 Milhas extraídos e estruturados com perfeição!")

    except Exception as e:
        print(f"Erro global 23 Milhas: {e}")

    return final_23milhas

if __name__ == "__main__":
    results = get_teatro_data() + get_cinema_data() + get_23milhas_data()
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Sucesso Total! Aglomerados {len(results)} eventos guardados.")
