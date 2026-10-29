# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 10:28:18 2026
@author: Ekkehard8
"""
## ALL names are case-sensitive and should be written as you see them on links, surrounded in "". eg. "渡" 
# Change to True only whenever you load a username for the first time. Roughly 15 matches/second:
RUN_SCRAPER = False
# Used for scraping, file names, graph title.
username = "Humita"     
# Alt account. Use None otherwise 
alt = None
# Specify a start date ("MM/DD/YYYY", "YYYY-MM-DD", etc.) or None:
start_date_str = None
# Specify a range in years eg. 0.15 or 2 or 10.5 or None for max: 
years = None
# Graph date range may be smaller as it takes the range of the games that exist within the given date range. 
# Optional second player can be added if loaded before. Write None if no rival:
rival = None
# Make true to force specified date range above:    
force_date_range = False 
# Toggle on to be told ~5 players you've rematched the most on the GL ladder.
find_rivals = True    
#%% Imports and functions  
# Imports and functions   
import requests
import re
import csv
import time
from bs4 import BeautifulSoup
from typing import List, Dict
import urllib.parse   
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FuncFormatter
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np 
import hashlib
import colorsys
from matplotlib.patheffects import withStroke
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
def encode_name(name: str) -> str:
    """Turn a name into the encoded form AWBW uses (space → +, literal + → %2B)."""
    return urllib.parse.quote_plus(name)
def decode_name(encoded: str) -> str:
    """Reverse AWBW encoding (+ back to space, %2B back to +)."""
    return urllib.parse.unquote_plus(encoded)
def fetch_page(url: str) -> str:    
    max_retries = 5
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
def name_to_color(name: str) -> str:
    h = int(hashlib.sha256(name.encode('utf-8')).hexdigest(), 16)
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.52, 0.88)
    return f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
def needs_outline(hex_color: str, bg="#F5E8B7", lum_threshold: float = 0.72) -> bool:
    """True if the color is too light against the background."""
    r = int(hex_color[1:3], 16) / 255.0
    g = int(hex_color[3:5], 16) / 255.0
    b = int(hex_color[5:7], 16) / 255.0
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return lum > lum_threshold
def plot_line_with_outline(ax, x, y, color: str, label: str | None = None,
                           lw: float = 3.0, alpha: float = 1.0, zorder: float = 2.5):
    plot_kwargs = dict(lw=lw, alpha=alpha, zorder=zorder)
    if needs_outline(color):
        ax.plot(x, y, color=color, label=label,
                path_effects=[withStroke(linewidth=lw + 4.0, foreground="#222222")],
                **plot_kwargs)
    else:
        ax.plot(x, y, color=color, label=label, **plot_kwargs)
def rgb_to_hls(hex_color: str):
    r = int(hex_color[1:3], 16) / 255.0
    g = int(hex_color[3:5], 16) / 255.0
    b = int(hex_color[5:7], 16) / 255.0
    return colorsys.rgb_to_hls(r, g, b)

def get_distinct_rival_color(main_color: str, rival_name: str, min_hue_diff: float = 20.0) -> str:
    #Returns a rival color. If too close to main (hue distance < 20°), shifts hue +55° and slightly boosts saturation.
    rival_base = name_to_color(rival_name)
    if main_color.upper() == rival_base:
        return "#E6392E"  # bright red fallback   
    h1, _, _ = rgb_to_hls(main_color)
    h2, l2, s2 = rgb_to_hls(rival_base)    
    hue1 = h1 * 360
    hue2 = h2 * 360
    diff = min(abs(hue1 - hue2), 360 - abs(hue1 - hue2))    
    if diff >= min_hue_diff:
        return rival_base  # already distinct    
    new_hue = (hue2 + 55) % 360 / 360.0
    new_sat = min(0.96, s2 + 0.09)
    r, g, b = colorsys.hls_to_rgb(new_hue, l2, new_sat)
    new_color = f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
    return new_color

#%% Scraper
# Scraper
def scrape(name: str):
    # ============== CONFIG ==============
    output_file = f"{name}_awbw_elo_history.csv"
    # ====================================
    print(f"Starting scrape for user: {name}")
    matches: List[Dict[str, str]] = []
    dates = []
    start = 1
    step = 50

    while True:
        url = f"https://awbw.amarriner.com/gamescompleted.php?start={start}&username={name}&league=Y"
        print(f"Fetching page start={start}...")
        html = fetch_page(url)
        if not html:
            print(" Failed after retries. Stopping.")
            break
        soup = BeautifulSoup(html, 'html.parser')
        dates_temp = re.findall(r'Ended on (\d{1,2}/\d{1,2}/\d{4})', html)
        before = len(matches)                                 
        for a in soup.find_all('a', href=re.compile(r'profile\.php\?username=')):
            name_match = re.search(r'username=([^&"]+)', a['href'])
            if not name_match:
                continue
            player_name = name_match.group(1)
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
            dates_temp = [] # clean the slate
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
    name_encoded = encode_name(name)

    for i in range(len(dates)):
        pair = matches[i*2 : i*2 + 2]
        if len(pair) < 2:
            print(f"Incomplete pair between game {i-48} and {i+1} — skipping the rest")
            break

        # Detect which player is {username} and flip if needed
        if pair[0]['player'] == name_encoded:
            user_entry = pair[0]
            opp_entry = pair[1]
        elif pair[1]['player'] == name_encoded:
            user_entry = pair[1]
            opp_entry = pair[0]
        else:
            print(f"Username '{name}' not found in game {i+1} — using first entry as user")
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
    output_file = f"{name}_awbw_games.csv"
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:   # utf-8-sig = somewhat friendly with Chinese/special chars
        writer = csv.DictWriter(f, fieldnames=['date', 'opp', 'user_elo', 'opp_elo', 'recency'])
        writer.writeheader()
        writer.writerows(games)
    print(f"Saved {len(games)} complete games to: {output_file}")

if RUN_SCRAPER:
    scrape(username)
    if alt is not None: scrape(alt)
else:
    print(f"Scraper skipped. (Using existing {username}_awbw_games.csv)")
    
#%% find rivals
# find rivals
if find_rivals:
    csv_filename = f"{username}_awbw_games.csv"
    df = pd.read_csv(csv_filename)
    c = df['opp'].value_counts()    
    if alt is not None:                    
        csv_filename_alt = f"{alt}_awbw_games.csv"
        try:
            df_alt = pd.read_csv(csv_filename_alt)
            c = c.add(df_alt['opp'].value_counts(), fill_value=0).astype(int)
        except FileNotFoundError:
            pass  # alt optional
    
    rivals = list(c[c>8].index) + list(c[(c>1)&(c<=8)].index)[:5]
    [print(f" {decode_name(o)} (×{c[o]})") for o in rivals] or print("No opponent was rematched.")
    
    
    
#%% Plotter
# Plotter

# ============== CONFIGURATION ==============
csv_filename = f"{username}_awbw_games.csv"
rival_csv_filename = f"{rival}_awbw_games.csv"
alt_csv_filename = f"{alt}_awbw_games.csv"
output_filename = f"{username}_elo_history.png"
if rival is not None: output_filename = f"{username}_vs_{rival}_elo_history.png"
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
orange = "#ff7f0e"
black = "#000000"

# =============================================================

# Load the CSVs
df = pd.read_csv(csv_filename)
df_alt = pd.DataFrame(columns=['date', 'opp', 'user_elo', 'opp_elo', 'recency'])
# Alt logic
if alt is not None:
    alt_encoded = encode_name(alt)
    try:
        df_alt = pd.read_csv(alt_csv_filename)
        print(f"Using {alt}_awbw_games.csv")
    except FileNotFoundError:
        df_alt = pd.DataFrame(columns=['date', 'opp', 'user_elo', 'opp_elo', 'recency'])
        print("Alt file not found")
    if len(df_alt) > 0:
        df_alt['date'] = pd.to_datetime(df_alt['date'], format='%m/%d/%Y')
        df_alt = df_alt.iloc[::-1].reset_index(drop=True)
        total_games_alt = len(df_alt)
has_alt = alt is not None and len(df_alt) > 0
# Parse dates (MM/DD/YYYY format in the CSV)
df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
# Sort chronologically (oldest first)
df = df.iloc[::-1].reset_index(drop=True)
if not has_alt:
    first_match_date = df['date'].iat[0]
    last_match_date = df['date'].iat[-1]
else:
    first_match_date = min(df['date'].iat[0], df_alt['date'].iat[0])
    last_match_date = max(df['date'].iat[-1], df_alt['date'].iat[-1])
# 30th chronological match vertical line (extremely faint red, barely visible)
boost_line_date = pd.to_datetime('01/01/2000',format='%m/%d/%Y')
boost_line_date_alt = pd.to_datetime('01/01/2000',format='%m/%d/%Y')
total_games = len(df)
if len(df) >= 30:
    boost_line_date = df['date'].iloc[29]
if len(df_alt) >= 30:
    boost_line_date_alt = df_alt['date'].iloc[29]
# Trim data for desired date range
last_trimmed_elo = None
last_trimmed_elo_alt = None
if start_date_str is None: 
    start_date = first_match_date
else:
    start_date = pd.to_datetime(start_date_str)
if years is None:
    end_date = last_match_date
else:
    # Add fractional years (365.25-day average handles leap years reasonably well)
    end_date = start_date + pd.Timedelta(days=float(years) * 365.25)
trimmed = False
if years is not None or start_date_str is not None:
    last_trimmed_elo = df[df['date'] < start_date]['user_elo'].iloc[-1] if (df['date'] < start_date).any() else None
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)].reset_index(drop=True)
    if has_alt:
        last_trimmed_elo_alt = df_alt[df_alt['date'] < start_date]['user_elo'].iloc[-1] if (df_alt['date'] < start_date).any() else None
        df_alt = df_alt[(df_alt['date'] >= start_date) & (df_alt['date'] <= end_date)].reset_index(drop=True)
    
    if len(df) < total_games: 
        trimmed = True   
    if has_alt:
        if len(df_alt) < total_games_alt: 
            trimmed = True   
if force_date_range:
    if start_date_str is None: start_date_str = start_date
    print(f"{human_date(pd.to_datetime(start_date_str))} to {human_date(end_date)}")
else:
    print(f"{human_date(start_date)} to {human_date(end_date)}")
    
# Calculate elo change for every row
# The very first row (oldest match) uses 800 as the starting ELO
df['change'] = df['user_elo'].diff()
if has_alt:
    df_alt['change'] = df_alt['user_elo'].diff()
if last_trimmed_elo:
    period_start_elo = last_trimmed_elo
else:
    period_start_elo = 800
df.loc[0, 'change'] = df.loc[0, 'user_elo'] - period_start_elo
if last_trimmed_elo_alt:
    period_start_elo_alt = last_trimmed_elo_alt
else:
    period_start_elo_alt = 800
if has_alt:
    df_alt.loc[0, 'change'] = df_alt.loc[0, 'user_elo'] - period_start_elo_alt

post_result_elo = False # Toggle on to use post-result elo for opp dot height
if not post_result_elo: 
    df['opp_elo'] = df['opp_elo'] + np.where(df['recency'] > 29, df['change'], df['change'] * 0.6)
    if has_alt:
        df_alt['opp_elo'] = df_alt['opp_elo'] + np.where(df_alt['recency'] > 29, df_alt['change'], df_alt['change'] * 0.6)

num_green = (df['change'] > 0).sum()
num_zero = (df['change'] == 0).sum()
num_red = (df['change'] < 0).sum()
if has_alt:
    num_green2 = (df_alt['change'] > 0).sum()
    num_zero2 = (df_alt['change'] == 0).sum()
    num_red2 = (df_alt['change'] < 0).sum()

# Prepare marker sizes and colors for opp_elo dots
#max_abs_change = df['change'].abs().max() if df['change'].abs().max() > 0 else 1
dot_scaler = 1
sizes = 50 + 5 * np.abs(df['change'].values) #~125 "normal" dot size. 50 floor
if has_alt:
    sizes_alt = 50 + 5 * np.abs(df_alt['change'].values)
else:
    sizes_alt = np.array([])

# Half as big per factor of 20 away from 500. More games; smaller dots.
if use_dot_scaler and len(df) > 0:
    dot_scaler = 2 ** (np.log(500 / len(df)) / np.log(20))
    sizes = sizes * dot_scaler
    if has_alt:
        sizes_alt = sizes_alt * dot_scaler
    
def get_dot_color(c, user_elo):
    if c > 0:
        return dark_green
    elif c < 0:
        return red_color
    else:  # c == 0
        return gray if user_elo == 700 else blue_color   

colors = [get_dot_color(c, elo) 
          for c, elo in zip(df['change'], df['user_elo'])]
if has_alt: 
    colors_alt = [get_dot_color(c, elo) 
          for c, elo in zip(df_alt['change'], df_alt['user_elo'])]
else:
    colors_alt = np.array([])

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
# Determine whether it makes sense for earlier activity to be attributed to the alt first or main
def determine_alt_first(df, df_alt):
    """
    Returns True if alt should appear first in the legend (e.g. "alt / username").
      - After 5+ matches (chronological), whichever reaches 60% + 1 first is "first".
      - If never reached, same check from the end determines who was "last".
      - If still tied, earliest first-match date wins.
      - If both started on the exact same day, add dates cumulatively until one pulls ahead.
      - Ultimate fallback: random.
    """
    if len(df) == 0 or len(df_alt) == 0:
        return False

    # Build combined timeline (main first in ties on same date)
    combined = [(row['date'], 'main') for _, row in df.iterrows()]
    combined += [(row['date'], 'alt') for _, row in df_alt.iterrows()]
    combined.sort(key=lambda x: x[0])

    # 1. Forward pass
    c_main = c_alt = 0
    for _, who in combined:
        if who == 'main':
            c_main += 1
        else:
            c_alt += 1
        total = c_main + c_alt
        if total >= 5:
            if c_alt >= 0.6 * total + 1:      # 60% + 1 threshold
                return True
            if c_main >= 0.6 * total + 1:
                return False

    # 2. Backward pass (determines who was "last")
    c_main = c_alt = 0
    for _, who in reversed(combined):
        if who == 'main':
            c_main += 1
        else:
            c_alt += 1
        total = c_main + c_alt
        if total >= 5:
            if c_alt >= 0.6 * total + 1:      # alt was last → main was first
                return False
            if c_main >= 0.6 * total + 1:     
                return True

    # 3. Fallback: first-match date
    if df_alt['date'].iloc[0] < df['date'].iloc[0]:
        return True
    if df['date'].iloc[0] < df_alt['date'].iloc[0]:
        return False

    # 4. Same first date → accumulate until tie breaks
    c_main = c_alt = 0
    for _, who in combined:
        if who == 'main':
            c_main += 1
        else:
            c_alt += 1
        if c_alt != c_main:
            return c_alt > c_main

    # 5. Last resort
    import random
    return random.choice([True, False])

# Determine order and create legend label
if has_alt:
    alt_first = determine_alt_first(df, df_alt)
    leg = f"{alt} / {username}" if alt_first else f"{username} / {alt}"
else:
    leg = username
# Draw lines
main_color = name_to_color(username)
plot_line_with_outline(ax, df['date'], df['user_elo'], main_color, label=leg)
if has_alt:
    plot_line_with_outline(ax, df_alt['date'], df_alt['user_elo'], main_color)
    
# Opponent ELO dots (size = elo exchange, color = gain/loss)
ax.scatter(df['date'], df['opp_elo'],
           s=sizes,
           c=colors,
           alpha=0.65,
           edgecolors='white',
           linewidth=0.3,
            )

ax.scatter(df_alt['date'], df_alt['opp_elo'],
           s=sizes_alt,
           c=colors_alt,
           alpha=0.65,
           edgecolors='black',
           linewidth=0.3,
            )
# Formatting
if has_alt:
    title_str = f"{username} ({num_green}/{num_red}/{num_zero}), {alt} ({num_green2}/{num_red2}/{num_zero2})"
    if trimmed:
        title_str += " partial history"
    else:
        title_str += " elo history"
else:
    title_str = f"{username}'s global league elo " + ("partial " if trimmed else "") + f"history ({num_green}/{num_red}/{num_zero} games)"
# ax.set_xlabel("Date", fontsize=14 * text_scale)
# ax.set_ylabel("ELO Rating", fontsize=14 * text_scale)

ax.tick_params(axis='both', labelsize=12 * text_scale)

# Date formatting on x-axis
if force_date_range:
    date_min = start_date
    date_max = end_date
else:   
    if has_alt:
        date_min = min(df['date'].min(), df_alt['date'].min())
        date_max = max(df['date'].max(), df_alt['date'].max())
        years_list = sorted(set(df['date'].dt.year) | set(df_alt['date'].dt.year))
    else:
        date_min = df['date'].min()
        date_max = df['date'].max()
        years_list = sorted(df['date'].dt.year.unique())
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
if pd.notna(boost_line_date_alt) and SHOW_BOOST_LINE and date_min <= boost_line_date_alt <= date_max:
    ax.axvline(boost_line_date_alt,                     
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
    years_list = sorted(set(df['date'].dt.year) | set(df_alt['date'].dt.year)) if has_alt else sorted(df['date'].dt.year.unique())
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
    years_list = years_list = sorted(set(df['date'].dt.year) | set(df_alt['date'].dt.year)) if has_alt else sorted(df['date'].dt.year.unique())
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

# ============== RIVAL LOGIC ==============
df_rival = None
if rival is not None:
    rival_encoded = encode_name(rival)
    try:
        df_rival = pd.read_csv(rival_csv_filename)
        print(f"Using existing {rival}_awbw_elo_history.csv")
    except FileNotFoundError:
        df_rival = pd.DataFrame(columns=['date', 'opp', 'user_elo', 'opp_elo', 'recency'])
        print("Rival file not found")
    
    df_rival['date'] = pd.to_datetime(df_rival['date'], format='%m/%d/%Y')
    df_rival = df_rival[(df_rival['date'] >= start_date) & (df_rival['date'] <= end_date)].reset_index(drop=True)
    # Draw rival line
    rival_color = get_distinct_rival_color(main_color, rival)
    plot_line_with_outline(ax, df_rival["date"], df_rival["user_elo"], 
                           rival_color, label=f"{rival}", lw=2.1, alpha=0.7, zorder = 0.1)
    def highlight_vs_rival(df_part, sizes_part):
        duels = df_part["opp"].astype(str).str.strip() == rival_encoded
        if not duels.any():
            return
        # Big colored ring (win/loss color)
        sizes2 = 250 + 15 * np.abs(df_part['change'].values)
        ax.scatter(
            df_part['date'][duels], df_part['opp_elo'][duels],
            s = sizes2[duels] * 2 * dot_scaler,
            facecolors = 'none',
            edgecolors = [get_dot_color(cv, ev) for cv, ev in zip(df_part['change'][duels], df_part['user_elo'][duels])],
            linewidth = 4.1 * dot_scaler,
            zorder = 4.8
        )
        ax.scatter(
            df_part['date'][duels], df_part['opp_elo'][duels],
            s = sizes_part[duels],
            facecolors = 'none',
            edgecolors = black,
            linewidth = 3.5 * dot_scaler,
            zorder = 4.9
        )
    # Apply
    highlight_vs_rival(df, sizes)
    if has_alt:
        highlight_vs_rival(df_alt, sizes_alt)
# Upper left legend
ax.legend(fontsize=13 * text_scale, loc='upper left', frameon=True, facecolor='none', edgecolor='none')
# Empty space before/after line horizontally
ax.margins(x=0.0055)

# Extend xlim if rival goes beyond main + alt range
if df_rival is not None and not df_rival.empty:
    output_filename = f"{username}"
    if has_alt:
        output_filename += f",{alt}"
    output_filename += f"_vs_{rival}"
    output_filename += "_elo_history.png"
    left, right = ax.get_xlim()
    data_min = min(df['date'].min(), df_alt['date'].min() if has_alt else df['date'].min())
    data_max = max(df['date'].max(), df_alt['date'].max() if has_alt else df['date'].max())
    if df_rival['date'].min() < data_min:
        left = df_rival['date'].min()
    if df_rival['date'].max() > data_max:
        right = df_rival['date'].max()
    ax.set_xlim(left, right)

if df_rival is not None and not df_rival.empty:
    title_str += f" vs {rival}"
ax.set_title(title_str,
             fontsize=18 * text_scale, pad=20, color=dark_green)
plt.tight_layout()
plt.savefig(output_filename, dpi=300, bbox_inches='tight')
print(f"Graph saved as: {output_filename}")
plt.show()


