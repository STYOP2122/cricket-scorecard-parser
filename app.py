from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re

app = Flask(__name__)

def validate_url(url):
    pattern = r'^https://www\.espncricinfo\.com/series/.*/full-scorecard$'
    return re.match(pattern, url) is not None

def fetch_page(url):
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    
    # Настройки для Chrome в Render.com
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    options.binary_location = "/usr/bin/chromium-browser"
    
    # Используем webdriver-manager для управления драйвером
    service = ChromeService(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    
    try:
        print(f"Загружаю страницу: {url}")
        driver.get(url)
        time.sleep(5)  # Ожидание загрузки JS
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        print("✅ Страница успешно загружена")
        return soup
    except Exception as e:
        print(f"❌ Ошибка при загрузке страницы: {str(e)}")
        raise
    finally:
        driver.quit()
        
def parse_scorecard(soup):
    innings = soup.find_all("div", class_="ds-rounded-lg")
    data = {}

    for inn in innings:
        title_tag = inn.find("span", class_="ds-text-title-xs")
        if not title_tag:
            continue
        title = title_tag.text.strip()
        team = title.split(" Innings")[0]
        
        bat_table = inn.find("table", class_="ds-w-full")
        if not bat_table:
            continue
            
        batters = []
        bat_rows = bat_table.find_all("tr")[1:]
        for row in bat_rows:
            cols = row.find_all("td")
            if len(cols) < 8:
                continue
                
            try:
                name_span = cols[0].find("span", class_="ds-inline-flex")
                name = name_span.text.strip() if name_span else cols[0].text.strip()
                
                batters.append({
                    'name': name,
                    'runs': int(cols[2].text.strip()),
                    '4s': int(cols[5].text.strip()),
                    '6s': int(cols[6].text.strip())
                })
            except (ValueError, AttributeError):
                continue

        if batters:
            data[team] = {'batters': batters, 'bowlers': []}

    for i, (team, info) in enumerate(data.items()):
        next_inn_index = (i + 1) % len(data)
        next_inn = innings[next_inn_index]
        
        bowl_table = next_inn.find("table", class_="ds-w-full")
        if bowl_table:
            bowl_table = bowl_table.find_next("table", class_="ds-w-full")
            
        if bowl_table:
            bowlers = []
            bowl_rows = bowl_table.find_all("tr")[1:]
            for row in bowl_rows:
                cols = row.find_all("td")
                if len(cols) < 8:
                    continue
                    
                try:
                    name_span = cols[0].find("span", class_="ds-inline-flex")
                    name = name_span.text.strip() if name_span else cols[0].text.strip()
                    
                    bowlers.append({
                        'name': name,
                        'wickets': int(cols[4].text.strip()),
                        'runs': int(cols[3].text.strip())
                    })
                except (ValueError, AttributeError):
                    continue
            
            info['bowlers'] = bowlers

    return data
    
def find_top_batters(batters):
    if not batters:
        return []
    max_runs = max(b['runs'] for b in batters)
    return [b for b in batters if b['runs'] == max_runs]

def find_top_bowlers(bowlers):
    if not bowlers:
        return []
    max_wickets = max(b['wickets'] for b in bowlers)
    candidates = [b for b in bowlers if b['wickets'] == max_wickets]
    min_runs = min(b['runs'] for b in candidates)
    return [b for b in candidates if b['runs'] == min_runs]

def find_most_fours(batters):
    if not batters:
        return []
    max_fours = max(b['4s'] for b in batters)
    return [b for b in batters if b['4s'] == max_fours]

def find_most_sixes(batters):
    if not batters:
        return []
    max_sixes = max(b['6s'] for b in batters)
    return [b for b in batters if b['6s'] == max_sixes]

def analyze(data):
    all_batters = []
    all_bowlers = []
    
    for team, info in data.items():
        all_batters.extend(info['batters'])
        all_bowlers.extend(info['bowlers'])

    if not all_batters or not all_bowlers:
        return {}

    top_batters = find_top_batters(all_batters)
    top_bowlers = find_top_bowlers(all_bowlers)
    most_fours = find_most_fours(all_batters)
    most_sixes = find_most_sixes(all_batters)

    by_team = {}
    for team, info in data.items():
        team_batters = info['batters']
        team_bowlers = info['bowlers']
        
        tb = find_top_batters(team_batters)
        tw = find_top_bowlers(team_bowlers)
        mf = find_most_fours(team_batters)
        ms = find_most_sixes(team_batters)
        
        by_team[team] = {
            'top_batter': tb,
            'top_bowler': tw,
            'most_fours': mf,
            'most_sixes': ms
        }

    return {
        'top_batter': top_batters,
        'top_bowler': top_bowlers,
        'most_fours': most_fours,
        'most_sixes': most_sixes,
        'by_team': by_team
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_url():
    url = request.form.get('url')
    
    if not validate_url(url):
        return jsonify({'error': 'Invalid URL format'}), 400
    
    try:
        soup = fetch_page(url)
        data = parse_scorecard(soup)
        stats = analyze(data)
        
        if not stats:
            return jsonify({'error': 'No data found on the page'}), 400
            
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)