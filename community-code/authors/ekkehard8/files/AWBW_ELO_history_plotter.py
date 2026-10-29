# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 10:28:18 2026
@author: Ekkehard8
"""
# Change to True only whenever you load a username for the first time. Roughly 40 matches/second:
RUN_SCRAPER = False           
# Used for scraping, file names, graph title. As appears on links. eg. "渡" Case-sensitive:
username = "TheFineMelody"                  
# Specify a date to not take all history ("MM/DD/YYYY", "YYYY-MM-DD", etc.) write None otherwise:
start_date_str = "2020-02-20"
# All games from start_date_str (required) up to {years} later. eg. 0.15 or 2 or 10.5 or None for infinite: 
years = 8.05
# Graph date range may be smaller as it takes the range of the games that exist within the given date range.                    
#%% Scraper
if RUN_SCRAPER:
    import requests
    import re
    import csv
    import time
    from bs4 import BeautifulSoup
    from typing import List, Dict
    import urllib.parse

    # ============== CONFIG ==============
    output_file = f"{username}_awbw_elo_history.csv"
    max_retries = 5
    # ====================================

    def fetch_page(url: str) -> str:
        """Fetch with fake headers + exponential backoff (handles DNS, timeouts, temporary glitches)"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://awbw.amarriner.com/',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(max_retries):
            try:
                r = requests.get(url, headers=headers, timeout=20)
                r.raise_for_status()
                return r.text
            except Exception as e:
                print(f"  Attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # 1s → 2s → 4s → 8s...
        return ""

    print(f"Starting scrape for user: {username}")
    matches: List[Dict[str, str]] = []
    dates = []
    start = 1
    step = 50

    while True:
        url = f"https://awbw.amarriner.com/gamescompleted.php?start={start}&username={username}&league=Y"
        print(f"Fetching page start={start}...")
        html = fetch_page(url)
        if not html:
            print(" Failed after retries. Stopping.")
            break

        soup = BeautifulSoup(html, 'html.parser')
        dates.extend(re.findall(r'Ended on (\d{1,2}/\d{1,2}/\d{4})', html))

        before = len(matches)                                 
        for a in soup.find_all('a', href=re.compile(r'profile\.php\?username=')):
            username_match = re.search(r'username=([^&"]+)', a['href'])
            if not username_match:
                continue
            player_name = username_match.group(1)

            container = a.find_parent(['div', 'li', 'tr', 'td']) or a.parent
            if container:
                text = container.get_text()
                elo_match = re.search(r'\((\d+(?:\.\d{0,2})?)\)', text)
                if elo_match:
                    matches.append({'player': player_name, 'elo': elo_match.group(1)})

        games_on_page = (len(matches) - before) // 2          # ← current page
        print(f" → {games_on_page} complete games on this page")

        if games_on_page < 50:          # stops when page is not full of games
            break

        start += step
        time.sleep(1.2)


    # ============== PROCESS INTO GAMES ==============
    print(f"\nProcessing {len(matches)//2} games ({len(matches)} player/elo entries + {len(dates)} dates)...")

    if len(matches) != len(dates) * 2:
        print(f"WARNING: Expected exactly {len(dates)*2} entries, got {len(matches)}. Results may be off.")

    games = []

    
    def encode_name(name: str) -> str:
        """Turn a name into the encoded form AWBW uses."""
        # Step 1: spaces → +
        name = name.replace(" ", "+")
        # Step 2: percent-encode everything except + (and normal safe chars)
        return urllib.parse.quote(name, safe="+")
    username_encoded = encode_name(username)

    for i in range(len(dates)):
        pair = matches[i*2 : i*2 + 2]
        if len(pair) < 2:
            print(f"Incomplete pair at game {i+1} — skipping the rest")
            break

        # Detect which player is {username} and flip if needed
        if pair[0]['player'] == username_encoded:
            user_entry = pair[0]
            opp_entry = pair[1]
        elif pair[1]['player'] == username_encoded:
            user_entry = pair[1]
            opp_entry = pair[0]
        else:
            print(f"Username '{username}' not found in game {i+1} — using first entry as user")
            user_entry = pair[0]
            opp_entry = pair[1]

        games.append({
            'date':     dates[i],
            'opp':      opp_entry['player'],
            'user_elo': user_entry['elo'],
            'opp_elo':  opp_entry['elo']
        })

    # ============== SAVE CSV ==============
    output_file = f"{username}_awbw_games.csv"

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:   # utf-8-sig = somewhat friendly with Chinese/special chars
        writer = csv.DictWriter(f, fieldnames=['date', 'opp', 'user_elo', 'opp_elo'])
        writer.writeheader()
        writer.writerows(games)

    print(f"Saved {len(games)} complete games to: {output_file}")
    print("   Columns: date, opp, user_elo, opp_elo")
else:
    print(f"Scraper skipped. (Using existing {username}_awbw_elo_history.csv)")
#%%
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ============== CONFIGURATION ==============
csv_filename = f"{username}_awbw_games.csv"
output_filename = f"{username}_elo_history.png"

text_scale = 1.4  # Increase this number to make ALL text bigger at once
fig_width = 14
fig_height = 8

# Colors 
bright_blue = "#00A4FF"  
faint_gold_bg = "#F5E8B7" 
dark_green = "#006400"
red_color = "#E6392E"
blue_color = "#0066FF"

# =============================================================

# Load the CSV
df = pd.read_csv(csv_filename)
# Parse dates (MM/DD/YYYY format in the CSV)
df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
# Sort chronologically (oldest first)
df = df.iloc[::-1].reset_index(drop=True)
# 25th chronological match vertical line (extremely faint red, barely visible)
if len(df) >= 25:
    boost_line_date = df['date'].iloc[24]
# Trim data for desired date range
if start_date_str is not None:
    start_date = pd.to_datetime(start_date_str)  # pandas auto-detects common formats (MM/DD/YYYY, YYYY-MM-DD, etc.)
    
    if years is not None:
        # Add fractional years (365.25-day average handles leap years reasonably well)
        end_date = start_date + pd.Timedelta(days=float(years) * 365.25)
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)].reset_index(drop=True)
        print(f"Trimmed to: {start_date.date()} → {end_date.date()}  ({len(df)} games)")
    else:
        # Only start date was given → trim from start onward
        df = df[df['date'] >= start_date].reset_index(drop=True)
        print(f"Trimmed from: {start_date.date()} onward  ({len(df)} games)")
else:
    print("No 'start_date' in CONFIG → using full date range")
# Calculate elo change for every row
# The very first row (oldest match) uses 800 as the starting ELO
df['change'] = df['user_elo'].diff()
df.loc[0, 'change'] = df.loc[0, 'user_elo'] - 800.0

num_blue = (df['change'] == 0).sum()

# Prepare marker sizes and colors for opp_elo dots
max_abs_change = df['change'].abs().max() if df['change'].abs().max() > 0 else 1
sizes = [50 + 150 * (abs(c) / max_abs_change) for c in df['change']]  # size range 50-200

def get_dot_color(c):
    if c > 0:
        return dark_green
    elif c < 0:
        return red_color
    else:
        return blue_color

colors = [get_dot_color(c) for c in df['change']]

# ============== PLOT ==============
fig = plt.figure(figsize=(fig_width, fig_height))
fig.patch.set_facecolor(faint_gold_bg)

ax = plt.gca()
ax.set_facecolor(faint_gold_bg)
plt.rcParams['font.sans-serif'] = [
    'Noto Sans CJK JP', 'Noto Sans CJK SC', 'Yu Gothic', 'Hiragino Sans',
    'Arial Unicode MS', 'Microsoft YaHei', 'SimHei'
] + plt.rcParams.get('font.sans-serif', [])
plt.rcParams['axes.unicode_minus'] = False
# Main user ELO line (bright blue, thick)
ax.plot(df['date'], df['user_elo'],
        color=bright_blue,
        linewidth=3,
        label="Your ELO"
        )

# Opponent ELO dots (size = elo exchange, color = gain/loss)

ax.scatter(df['date'], df['opp_elo'],
           s=sizes,
           c=colors,
           alpha=0.65,
           edgecolors='white',
           linewidth=0.3,
            label="Opponent ELO\n(size ∝ elo change)"
            )
# Formatting
ax.set_title(f"{username}'s global league elo history ({len(df)}-{num_blue} games)",
             fontsize=18 * text_scale, pad=20, color=dark_green)
# ax.set_xlabel("Date", fontsize=14 * text_scale)
# ax.set_ylabel("ELO Rating", fontsize=14 * text_scale)

ax.tick_params(axis='both', labelsize=12 * text_scale)

# Date formatting on x-axis    
date_min = df['date'].min()
date_max = df['date'].max()
span_years = (date_max - date_min).days / 365.25
SHOW_YEAR_BOUNDARIES = True      # False to hide the year vertical lines
year_line_alpha = 0.50           
year_line_width = 1.85
SHOW_BOOST_LINE = True
if pd.notna(boost_line_date) and SHOW_BOOST_LINE and date_min <= boost_line_date <= date_max:
    ax.axvline(boost_line_date,                     
               color='red',
               alpha=0.18,
               linewidth=0.95,
               zorder=0)
if span_years > 18:
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))   # "2020", "2021", etc.
    rotation = 0
elif span_years > 12:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    rotation = 45
elif span_years > 7.5:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    rotation = 45
elif span_years > 6:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    rotation = 45
elif span_years > 4.5:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    rotation = 45
elif span_years > 3:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    rotation = 45
else:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    if span_years > 1.5:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        rotation = 45
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        rotation = 0
    if SHOW_YEAR_BOUNDARIES:
        years = sorted(df['date'].dt.year.unique())
        for y in years[1:]:
            year_start = pd.to_datetime(f"{y}-01-01")
            if date_min < year_start < date_max:
                ax.axvline(year_start,
                           color='gray',
                           linewidth=year_line_width,
                           alpha=year_line_alpha,
                           linestyle='--',
                           zorder=1)  # behind the data

    # === x-axis label listing the years spanned (e.g."2022, 2023, 2024") ===
    years_list = sorted(df['date'].dt.year.unique())
    year_text = ", ".join(map(str, years_list))
    ax.set_xlabel(f"{year_text}",
                  fontsize=13 * text_scale,
                  labelpad=12,
                  alpha=1,
                  color=dark_green)

plt.xticks(rotation=rotation, ha='right')
# Grid 
ax.grid(True, linestyle='--', alpha=0.35, color='gray')

# Legend
# ax.legend(fontsize=11 * text_scale, loc='upper left', frameon=True, facecolor='white', edgecolor='none')
# Empty space before/after line horizontally
ax.margins(x=0.0057)

plt.tight_layout()
plt.savefig(output_filename, dpi=300, bbox_inches='tight')
print(f"Graph saved as: {output_filename}")
plt.show()



