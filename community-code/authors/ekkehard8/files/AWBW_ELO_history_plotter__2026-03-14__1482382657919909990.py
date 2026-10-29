# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 10:28:18 2026
@author: Ekkehard8
"""
# Change to True only whenever you load a username for the first time. Roughly 15 matches/second:
RUN_SCRAPER = False         
# Used for scraping, file names, graph title. As appears on links. eg. "渡" Case-sensitive:
username = "Renz_Ai"                  
# Specify a date to not take all history ("MM/DD/YYYY", "YYYY-MM-DD", etc.) write None otherwise:
start_date_str = None
# All games from start_date_str or first match if None up to {years} later. eg. 0.15 or 2 or 10.5 or None for infinite: 
years = 3.015
# Graph date range may be smaller as it takes the range of the games that exist within the given date range. 
force_date_range = False # Make true to force specified date range above                   
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
        dates_temp = re.findall(r'Ended on (\d{1,2}/\d{1,2}/\d{4})', html)
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
        #If pesky refunded elo match appears, rerun to delete malicious date.
        removed_dates = 0
        expected_dates = (len(matches) - before) // 2
        
        if len(dates_temp) != expected_dates:
            date_matches = list(re.finditer(r'Ended on (\d{1,2}/\d{1,2}/\d{4})', html))
            dates_temp = []
            prev_end = 0
            for match in date_matches:
                section = html[prev_end:match.start()]
                if re.search(r'\((\d+(?:\.\d{0,2})?)\)', section):
                    dates_temp.append(match.group(1))
                else:
                    removed_dates += 1 
                prev_end = match.end()
        
        dates.extend(dates_temp)
        games_on_page = (len(matches) - before) // 2          # ← current page
        print(f" → {games_on_page} complete games on this page")

        if games_on_page < 50 - removed_dates:          # stops when page is not full of games
            break

        start += step
        time.sleep(1.2)


    # ============== PROCESS INTO GAMES ==============
    print(f"\nProcessing {len(matches)//2} games ({len(matches)} player/elo entries + {len(dates)} dates)...")

    if len(matches) + removed_dates != len(dates) * 2:
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
            print(f"Incomplete pair between game {i-48} and {i+1} — skipping the rest")
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
            'opp_elo':  opp_entry['elo'],
            'recency': i
        })

    # ============== SAVE CSV ==============
    output_file = f"{username}_awbw_games.csv"

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:   # utf-8-sig = somewhat friendly with Chinese/special chars
        writer = csv.DictWriter(f, fieldnames=['date', 'opp', 'user_elo', 'opp_elo', 'recency'])
        writer.writeheader()
        writer.writerows(games)

    print(f"Saved {len(games)} complete games to: {output_file}")
    print("   Columns: date, opp, user_elo, opp_elo")
else:
    print(f"Scraper skipped. (Using existing {username}_awbw_elo_history.csv)")
#%% Plotter
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FuncFormatter
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

# ============== CONFIGURATION ==============
csv_filename = f"{username}_awbw_games.csv"
output_filename = f"{username}_elo_history.png"
use_dot_scaler = True # Toggle false for uniform dot size as if 500 games plotted.

text_scale = 1.4  # Increase this number to make ALL text bigger at once
fig_width = 14
fig_height = 8

# Colors 
bright_blue = "#00A4FF"  
faint_gold_bg = "#F5E8B7" 
dark_green = "#006400"
red_color = "#E6392E"
blue_color = "#0066FF"
gray = "#808080"

# =============================================================

# Load the CSV
df = pd.read_csv(csv_filename)
# Parse dates (MM/DD/YYYY format in the CSV)
df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
# Sort chronologically (oldest first)
df = df.iloc[::-1].reset_index(drop=True)
first_match_date = df['date'].iat[0]
last_match_date = df['date'].iat[-1]
# 30th chronological match vertical line (extremely faint red, barely visible)
boost_line_date = pd.to_datetime('01/01/2000',format='%m/%d/%Y')
total_games = len(df)
if len(df) >= 30:
    boost_line_date = df['date'].iloc[29]
# Trim data for desired date range
last_trimmed_elo = None
if start_date_str is None: 
    start_date = df['date'].iat[0] 
else:
    start_date = pd.to_datetime(start_date_str)
if years is None:
    end_date = last_match_date
else:
    # Add fractional years (365.25-day average handles leap years reasonably well)
    end_date = start_date + pd.Timedelta(days=float(years) * 365.25)
trimmed = False
if years is not None or start_date_str is not None:
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)].reset_index(drop=True)
    if len(df) < total_games: trimmed = True
def human_date(dt: datetime) -> str:
    """
    Format a single date according to the rules:
      - Jan 1st        → "2025"
      - Any 1st of month → "December 2025"
      - Other days     → "December 10, 2025"
    """
    if dt.day == 1:
        if dt.month == 1:
            return str(dt.year)
        else:
            return dt.strftime("%B %Y")
    else:
        return dt.strftime("%B %d, %Y")    
if force_date_range:
    if start_date_str is None: start_date_str = start_date
    print(f"{human_date(pd.to_datetime(start_date_str))} to {human_date(pd.to_datetime(start_date_str) + pd.Timedelta(days=float(years) * 365.25))}")
else:
    print(f"{human_date(start_date)} to {human_date(end_date)}")
    
# Calculate elo change for every row
# The very first row (oldest match) uses 800 as the starting ELO
df['change'] = df['user_elo'].diff()
if last_trimmed_elo:
    period_start_elo = last_trimmed_elo
else:
    period_start_elo = 800
df.loc[0, 'change'] = df.loc[0, 'user_elo'] - period_start_elo

post_result_elo = False # Toggle on to use post-result elo for opp dot height
if not post_result_elo: 
    df['opp_elo'] = df['opp_elo'] + np.where(df['recency'] > 29, df['change'], df['change'] * 0.6)

num_green = (df['change'] > 0).sum()
num_zero = (df['change'] == 0).sum()
num_red = (df['change'] < 0).sum()

# Prepare marker sizes and colors for opp_elo dots
#max_abs_change = df['change'].abs().max() if df['change'].abs().max() > 0 else 1
dot_scaler = 1
sizes = 50 + 5 * np.abs(df['change'].values) #~125 "normal" dot size. 50 minimum
# Half as big per factor of 20 away from 500. More games; smaller dots.
if use_dot_scaler and len(df) > 0:
    dot_scaler = 2 ** (np.log(500 / len(df)) / np.log(20))
    sizes = sizes * dot_scaler
    
def get_dot_color(c, user_elo):
    if c > 0:
        return dark_green
    elif c < 0:
        return red_color
    else:  # c == 0
        return gray if user_elo == 700 else blue_color   

colors = [get_dot_color(c, elo) 
          for c, elo in zip(df['change'], df['user_elo'])]

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
if trimmed:
    title_str = f"{username}'s global league elo partial history ({num_green}/{num_red}/{num_zero} games)"
else:
    title_str = f"{username}'s global league elo history ({num_green}/{num_red}/{num_zero} games)"
ax.set_title(title_str,
             fontsize=18 * text_scale, pad=20, color=dark_green)
# ax.set_xlabel("Date", fontsize=14 * text_scale)
# ax.set_ylabel("ELO Rating", fontsize=14 * text_scale)

ax.tick_params(axis='both', labelsize=12 * text_scale)

# Date formatting on x-axis
if force_date_range:
    date_min = start_date
    date_max = end_date
else:   
    date_min = df['date'].min()
    date_max = df['date'].max()    
ax.set_xlim(date_min, date_max)
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
if span_years > 8.5:
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))   # "2020", "2021", etc.
    rotation = 0
elif span_years > 2.75:    
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1, bymonth=(1,4,7,10)))

    def quarter_fmt(x, pos):
        dt = mdates.num2date(x)
        q = ((dt.month - 1) // 3) + 1
        return f"Q{q}"
    ax.xaxis.set_major_formatter(FuncFormatter(quarter_fmt))
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
else:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    if span_years > 2.2:
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
plt.xticks(rotation=rotation, ha='left')
# Grid 
ax.yaxis.set_major_locator(MultipleLocator(100))
ax.grid(True, linestyle='--', alpha=0.4, color='gray')

# Legend
# ax.legend(fontsize=11 * text_scale, loc='upper left', frameon=True, facecolor='white', edgecolor='none')
# Empty space before/after line horizontally
ax.margins(x=0.0055)

plt.tight_layout()
plt.savefig(output_filename, dpi=300, bbox_inches='tight')
print(f"Graph saved as: {output_filename}")
plt.show()



