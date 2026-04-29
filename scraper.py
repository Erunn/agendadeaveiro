import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime, timedelta

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
session = requests.Session()

def parse_pt_date(date_str, default_date=None):
    months = {'janeiro':'01','fevereiro':'02','março':'03','abril':'04','maio':'05','junho':'06','julho':'07','agosto':'08','setembro':'09','outubro':'10','novembro':'11','dezembro':'12','jan':'01','fev':'02','mar':'03','abr':'04','mai':'05','jun':'06','jul':'07','ago':'08','set':'09','out':'10','nov':'11','dez':'12'}
    try:
        clean = date_str.lower().replace(' de ', ' ').strip()
        days = re.findall(r'\d+', clean)
        if not days: return default_date or datetime.now().strftime('%Y-%m-%d')
        day = days[0].zfill(2)
        month = next((m for k, m in months.items() if k in clean), "01")
        year = next((d for d in days if len(d) == 4), datetime.now().year)
        return f"{year}-{month}-{day}"
    except: return default_date or datetime.now().strftime('%Y-%m-%d')

def sort_cinema_times(time_str):
    """Separa, ordena cronologicamente e junta as horas de novo mantendo tags."""
    if not time_str or "Todo o dia" in time_str: return time_str
    parts = re.split(r'[|,]', time_str)
    entries = []
    for p in parts:
        p = p.strip()
        if not p: continue
        # Extrai a hora HH:MM para ordenar
        match = re.search(r'(\d{1,2}:\d{2})', p)
        if match:
            t_norm = match.group(1).zfill(5) # Garante formato 09:00 para sorting
            entries.append((t_norm, p))
    entries.sort(key=lambda x: x[0])
    return ", ".join([e[1] for e in entries])

def get_teatro_data():
    all_events = []
    base_url = "https://www.teatroaveirense.pt"
    try:
        res = session.get(f"{base_url}/pt/programacao/", headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.programa_item'):
            h2 = item.select_one('h2')
            date_el = item.select_one('.data')
            link_el = item.select_one('a')
            img_url = item.select_one('img')['src'] if item.select_one('img') else ""
            if img_url and not img_url.startswith('http'): img_url = base_url + img_url
            if h2 and date_el:
                title = h2.get_text(strip=True).replace('::', '')
                all_events.append({
                    "title": title, "start": parse_pt_date(date_el.text), "url": base_url + link_el['href'],
                    "source": "teatro", "extendedProps": {"image": img_url, "display_time": "Ver detalhes", "category_normalized": "teatro"}
                })
        return all_events
    except: return []

def get_cinema_data():
    final_cinema = []
    url = "https://cinecartaz.publico.pt/cinema/zon-lusomundo-glicinias-17718"
    try:
        res = session.get(url, headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        target_dates = [datetime.now().date() + timedelta(days=i) for i in range(8)]
        for block in soup.select('.movie-card'):
            title = block.select_one('.movie-card__title').get_text(strip=True)
            img = block.select_one('img')['src'] if block.select_one('img') else ""
            for p in block.select('.movie-card__info p'):
                text = p.get_text(separator=" ").strip()
                if 'sess' in text.lower():
                    # Limpa e Ordena as horas!
                    raw_times = re.sub(r'(?i)^sess[õo]e?s\s*:?\s*', '', text).lstrip(' :,-')
                    raw_times = re.sub(r'(\d{1,2})[hH](\d{2})?', r'\1:\2', raw_times).replace(':None', ':00')
                    sorted_times = sort_cinema_times(raw_times)
                    for dt in target_dates:
                        final_cinema.append({
                            "title": title, "start": dt.strftime('%Y-%m-%d'), "url": url, "source": "cinema",
                            "extendedProps": {"image": img, "display_time": sorted_times, "category_normalized": "cinema"}
                        })
        return final_cinema
    except: return []

def get_23milhas_data():
    events = []
    base = "https://www.23milhas.pt"
    try:
        res = session.get(base + "/programacao", headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        links = set(re.findall(r'/evento/[^"\'\s>]+', res.text.replace('\\/', '/')))
        for l in list(links)[:12]:
            try:
                time.sleep(0.3)
                ev_res = session.get(base + l, headers=HEADERS, timeout=10)
                ev_res.encoding = 'utf-8'
                ev_soup = BeautifulSoup(ev_res.text, 'html.parser')
                title_full = ev_soup.find('meta', property='og:title')['content'].replace(' - 23 Milhas', '').strip()
                title, umbrella = title_full, "23 Milhas"
                for sep in [" - ", " | "]:
                    if sep in title_full:
                        parts = title_full.split(sep, 1)
                        title, umbrella = parts[0].strip(), parts[1].strip()
                        break
                img = ev_soup.find('meta', property='og:image')['content'] if ev_soup.find('meta', property='og:image') else ""
                txt = ev_soup.get_text().lower()
                date_match = re.search(r'\d{1,2}\s+de\s+[a-zç]+', txt)
                date_iso = parse_pt_date(date_match.group(0)) if date_match else datetime.now().strftime('%Y-%m-%d')
                time_match = re.search(r'\d{2}:\d{2}', txt)
                events.append({
                    "title": title, "start": date_iso, "url": base + l, "source": "23milhas",
                    "extendedProps": {"image": img, "umbrella": umbrella, "display_time": time_match.group(0) if time_match else "Consultar", "category_normalized": "outros"}
                })
            except: continue
        return events
    except: return []

if __name__ == "__main__":
    all_ev = get_teatro_data() + get_cinema_data() + get_23milhas_data()
    today = datetime.now().strftime('%Y-%m-%d')
    valid = [e for e in all_ev if e['start'] >= today]
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(valid, f, ensure_ascii=False, indent=2)
