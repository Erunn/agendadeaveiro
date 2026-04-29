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
        if not days: return default_date or datetime.now().strftime('%Y-%m-%d')
        day = days[0].zfill(2)
        month = next((m for k, m in months.items() if k in clean_str), "01")
        year = next((d for d in days if len(d) == 4), datetime.now().year)
        return f"{year}-{month}-{day}"
    except: return default_date or datetime.now().strftime('%Y-%m-%d')

def clean_times_and_tags(text):
    def replacer(m):
        h = int(m.group(1) or m.group(3))
        m_min = int(m.group(2) or m.group(4) or 0)
        return f"{h:02d}:{m_min:02d}"
    return re.sub(r'(?<!\d)(\d{1,2})[hH](\d{2})?|(?<!\d)(\d{1,2}):(\d{2})', replacer, text)

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
            img_el = item.select_one('img')
            img_url = img_el.get('src', '') if img_el else ""
            if img_url and not img_url.startswith('http'): img_url = base_url + img_url
            
            if h2 and date_el and link_el:
                title = h2.get_text(strip=True).replace('::', '')
                url = base_url + link_el['href'] if not link_el['href'].startswith('http') else link_el['href']
                date_iso = parse_pt_date(date_el.text.strip())
                all_events.append({
                    "title": title, "start": date_iso, "url": url, "source": "teatro",
                    "extendedProps": {"image": img_url, "display_time": "Ver Horário", "category_normalized": "teatro"}
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
            img_url = block.select_one('img')['src'] if block.select_one('img') else ""
            for p in block.select('.movie-card__info p'):
                text = p.get_text(separator="\n").strip()
                if 'sess' in text.lower():
                    times = clean_times_and_tags(text)
                    times_clean = re.sub(r'(?i)^sess[õo]e?s\s*:?\s*', '', times).lstrip(' :,-')
                    for dt in target_dates:
                        final_cinema.append({
                            "title": title, "start": dt.strftime('%Y-%m-%d'), "url": url, "source": "cinema",
                            "extendedProps": {"image": img_url, "display_time": times_clean, "category_normalized": "cinema"}
                        })
        return final_cinema
    except: return []

def get_23milhas_data():
    events = []
    base_url = "https://www.23milhas.pt"
    try:
        res = session.get(base_url + "/programacao", headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        # Captura links escapados do JS
        raw_urls = re.findall(r'(/evento/[^"\'\s\\><]+|evento/[^"\'\s\\><]+)', res.text.replace('\\/', '/'))
        unique_urls = set([base_url + (u if u.startswith('/') else '/' + u) for u in raw_urls])
        
        for url in list(unique_urls)[:15]:
            try:
                time.sleep(0.2)
                ev_res = session.get(url, headers=HEADERS, timeout=10)
                ev_res.encoding = 'utf-8'
                ev_soup = BeautifulSoup(ev_res.text, 'html.parser')
                
                og_title = ev_soup.find('meta', property='og:title')
                title_full = og_title['content'].replace(' - 23 Milhas', '').strip() if og_title else ""
                
                # Separação Título vs Umbrella
                title, umbrella = title_full, "23 Milhas"
                for sep in [" - ", " | "]:
                    if sep in title_full:
                        parts = title_full.split(sep, 1)
                        title, umbrella = parts[0].strip(), parts[1].strip()
                        break
                
                img = ev_soup.find('meta', property='og:image')['content'] if ev_soup.find('meta', property='og:image') else ""
                
                # Data e Hora do texto da página
                page_text = ev_soup.get_text()
                date_match = re.search(r'\d{1,2}\s+de\s+[a-zç]+', page_text.lower())
                date_iso = parse_pt_date(date_match.group(0)) if date_match else datetime.now().strftime('%Y-%m-%d')
                
                time_match = re.search(r'\d{2}:\d{2}', page_text)
                display_time = time_match.group(0) if time_match else "Todo o dia"
                
                events.append({
                    "title": title, "start": date_iso, "url": url, "source": "23milhas",
                    "extendedProps": {"image": img, "umbrella": umbrella, "display_time": display_time, "category_normalized": "outros"}
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
