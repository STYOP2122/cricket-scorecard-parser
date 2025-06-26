from flask import Flask, request, render_template_string
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re
import tempfile

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Cricket Scorecard Parser</title>
</head>
<body>
    <h2>Cricket Scorecard Parser</h2>
    <form method="post">
        <input name="url" size="80" placeholder="https://www.espncricinfo.com/.../full-scorecard" required>
        <button type="submit">Analyze</button>
    </form>
    <pre>{{ result }}</pre>
</body>
</html>
'''

def validate_url(url):
    pattern = r'^https://www\.espncricinfo\.com/series/.*/full-scorecard$'
    return re.match(pattern, url) is not None

def fetch_page(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0")

    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    return soup

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
        by_team[team] = {
            'top_batter': find_top_batters(info['batters']),
            'top_bowler': find_top_bowlers(info['bowlers']),
            'most_fours': find_most_fours(info['batters']),
            'most_sixes': find_most_sixes(info['batters']),
        }

    return {
        'top_batter': top_batters,
        'top_bowler': top_bowlers,
        'most_fours': most_fours,
        'most_sixes': most_sixes,
        'by_team': by_team
    }

def format_players(players):
    if not players:
        return "N/A"
    names = [p['name'] for p in players]
    return " and ".join(names) + f" ({players[0]['runs']} runs)"

def format_bowlers(bowlers):
    if not bowlers:
        return "N/A"
    names = [b['name'] for b in bowlers]
    return " and ".join(names) + f" ({bowlers[0]['wickets']}/{bowlers[0]['runs']})"

def format_fours(players):
    if not players:
        return "N/A"
    names = [p['name'] for p in players]
    return " and ".join(names) + f" ({players[0]['4s']} fours)"

def format_sixes(players):
    if not players:
        return "N/A"
    names = [p['name'] for p in players]
    return " and ".join(names) + f" ({players[0]['6s']} sixes)"

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    if request.method == "POST":
        url = request.form.get("url")
        if not validate_url(url):
            result = "❌ Invalid URL. Must end with /full-scorecard"
        else:
            try:
                soup = fetch_page(url)
                data = parse_scorecard(soup)
                stats = analyze(data)

                if not stats:
                    result = "❌ Could not extract data. Try another link."
                else:
                    result += f"🏆 Top batters: {format_players(stats['top_batter'])}\n"
                    result += f"🎯 Top bowlers: {format_bowlers(stats['top_bowler'])}\n"
                    result += f"💥 Most 4s: {format_fours(stats['most_fours'])}\n"
                    result += f"💣 Most 6s: {format_sixes(stats['most_sixes'])}\n"

                    for team, vals in stats['by_team'].items():
                        result += f"\n--- {team} ---\n"
                        result += f"Top batters: {format_players(vals['top_batter'])}\n"
                        result += f"Top bowlers: {format_bowlers(vals['top_bowler'])}\n"
                        result += f"Most 4s: {format_fours(vals['most_fours'])}\n"
                        result += f"Most 6s: {format_sixes(vals['most_sixes'])}\n"
            except Exception as e:
                result = f"❌ Error: {str(e)}"
    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    app.run(debug=True)