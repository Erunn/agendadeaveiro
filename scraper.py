import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# Headers to prevent being blocked
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def parse_pt_date(date_str):
    months = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04', 'maio': '05', 
        'junho': '06', 'julho': '07', 'agosto': '08', 'setembro': '09', 'outubro': '10', 
        'novembro': '11', 'dezembro': '12'
    }
    try:
        d = date_str.lower().replace(' de ', ' ').split()
        day = d[0].zfill(2)
        month = months.get(d[1], '01')
        return f"{datetime.now().year}-{month}-{day}"
    except:
        return datetime.now().strftime('%Y-%m-%d')

def get_data():
    all_events = []

    # 1. TEATRO AVEIRENSE
    try:
        res = requests.get("https://www.teatroaveirense.pt/pt/programacao/", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.item'):
            title = item.select_one('.title a')
            if title:
                all_events.append({
                    "title": title.text.strip(),
                    "start": parse_pt_date(item.select_one('.date').text),
                    "url": "https://www.teatroaveirense.pt" + title['href'],
                    "source": "teatro",
                    "color": "#e67e22"
                })
    except: print("Error scraping Teatro")

    # 2. CINEMA GLICINIAS
    try:
        res = requests.get("https://cinecartaz.publico.pt/cinema/zon-lusomundo-glicinias-17718", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        for movie in soup.select('.highlight-item'):
            title = movie.select_one('h3 a')
            if title:
                all_events.append({
                    "title": title.text.strip(),
                    "start": datetime.now().strftime('%Y-%m-%d'),
                    "url": "https://cinecartaz.publico.pt" + title['href'],
                    "source": "cinema",
                    "color": "#3498db"
                })
    except: print("Error scraping Cinema")

    # 3. CMA AGENDA
    try:
        res = requests.get("https://www.cm-aveiro.pt/visitantes/agenda-aveiro", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.list-item'):
            title = item.select_one('.title')
            if title:
                all_events.append({
                    "title": title.text.strip(),
                    "start": parse_pt_date(item.select_one('.date-wrapper').text),
                    "source": "cma",
                    "color": "#27ae60"
                })
    except: print("Error scraping CMA")

    # 4. VIRAL AGENDA
    try:
        res = requests.get("https://www.viralagenda.com/pt/aveiro/aveiro", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        for event in soup.select('.event-item'):
            title = event.select_one('.title a')
            if title:
                all_events.append({
                    "title": title.text.strip(),
                    "start": datetime.now().strftime('%Y-%m-%d'),
                    "url": "https://www.viralagenda.com" + title['href'],
                    "source": "viral",
                    "color": "#8e44ad"
                })
    except: print("Error scraping Viral")

    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    get_data()
