#!/usr/bin/env python3
"""
Olympics NHL Points Aggregation Script

Fetches 2026 Olympics Men's Ice Hockey stats (goals + assists),
maps players to their NHL teams, and ranks NHL teams by total Olympic points.
"""

import requests
from bs4 import BeautifulSoup
import unicodedata
from collections import defaultdict
import sys
import time
import json
from datetime import datetime


# NHL team abbreviations (all 32 teams)
NHL_TEAMS = [
    'ANA', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI', 'COL', 'DAL', 'DET',
    'EDM', 'FLA', 'LAK', 'MIN', 'MTL', 'NJD', 'NSH', 'NYI', 'NYR', 'OTT',
    'PHI', 'PIT', 'SEA', 'SJS', 'STL', 'TBL', 'TOR', 'UTA', 'VAN', 'VGK',
    'WPG', 'WSH'
]

# Browser headers to mimic a real browser request
# Note: Accept-Encoding is omitted - requests handles compression automatically
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}


def normalize_name(name):
    """
    Normalize a player name for matching.
    - Converts to lowercase
    - Removes accents/diacritics
    - Standardizes whitespace
    
    Args:
        name: Player name string (e.g., "MCDAVID Connor" or "Connor McDavid")
    
    Returns:
        Normalized name (e.g., "connor mcdavid")
    """
    # Normalize unicode to decomposed form, then filter out combining characters
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    # Convert to lowercase and standardize whitespace
    return ' '.join(name.lower().split())


def fetch_with_retry(url, params=None, max_retries=3, timeout=45, extra_headers=None):
    """
    Fetch a URL with retry logic and browser-like headers.
    
    Args:
        url: URL to fetch
        params: Query parameters
        max_retries: Maximum number of retries
        timeout: Request timeout in seconds
        extra_headers: Additional headers to merge with browser headers
    
    Returns:
        Response object
    """
    headers = BROWSER_HEADERS.copy()
    if extra_headers:
        headers.update(extra_headers)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.RequestException, Exception) as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s (error: {str(e)[:100]})")
                time.sleep(wait_time)
            else:
                raise


def fetch_quanthockey_stats(country_code):
    """
    Fetch player stats from Quanthockey for a specific Olympic team.
    
    Args:
        country_code: Country code (e.g., 'canada', 'usa', 'sweden')
    
    Returns:
        List of dicts with player stats (name, goals, assists, points)
    """
    url = f"https://www.quanthockey.com/olympics/en/teams/team-{country_code}-players-2026-olympics-stats.html"
    
    try:
        response = fetch_with_retry(url, timeout=30, max_retries=2)
    except Exception as e:
        print(f"    Error: {str(e)[:100]}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    players = []
    
    # Find the stats table
    tables = soup.find_all('table')
    print(f"    Found {len(tables)} table(s)")
    for table in tables:
        rows = table.find_all('tr')
        
        for row in rows[2:]:  # Skip first two header rows
            cols = row.find_all(['td', 'th'])  # Some cells are th, some are td
            if len(cols) >= 9:  # Need at least rank, name, team, age, pos, GP, G, A, P
                try:
                    # Column indices: 0=Rank, 1=(blank), 2=Name (with link), 3=Team, 4=Age, 5=Pos, 6=GP, 7=G, 8=A, 9=P
                    name_cell = cols[2]
                    name_link = name_cell.find('a')
                    if name_link:
                        player_name = name_link.get_text(strip=True)
                    else:
                        player_name = name_cell.get_text(strip=True)
                    
                    # Skip if no name
                    if not player_name:
                        continue
                    
                    goals_text = cols[7].get_text(strip=True)
                    assists_text = cols[8].get_text(strip=True)
                    
                    goals = int(goals_text) if goals_text and goals_text.isdigit() else 0
                    assists = int(assists_text) if assists_text and assists_text.isdigit() else 0
                    points = goals + assists
                    
                    if points > 0:  # Only include players with points
                        players.append({
                            'name': player_name,
                            'goals': goals,
                            'assists': assists,
                            'points': points
                        })
                except (ValueError, IndexError) as e:
                    continue
    
    print(f"    Parsed {len(players)} players with points")
    return players


def fetch_olympic_games():
    """
    Fetch all Olympic Men's Ice Hockey games from the scores API.
    
    Returns:
        List of dicts with 'phaseCode' and 'eventUnitCode' for each game
    """
    url = "https://www.olympics.com/wmr-api/api/v2/results/scores"
    params = {
        'competitionCode': 'OWG2026',
        'disciplineCode': 'IHO',
        'genderCode': 'M',
        'eventCode': 'TEAM6-------------',
        'phaseCode': '*',
        'eventUnitCode': '*',
        'languageCode': 'ENG'
    }
    
    # Add API-specific headers
    api_headers = {
        'Referer': 'https://www.olympics.com/en/milano-cortina-2026/results/iho/m/team6-------------/team-sports-statistics-event',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://www.olympics.com',
    }
    
    print("Fetching Olympic games list...")
    
    try:
        response = fetch_with_retry(url, params=params, extra_headers=api_headers)
        data = response.json()
    except Exception as e:
        print(f"Warning: Could not fetch games from API: {e}")
        print("Using hardcoded game list from latest known data...")
        # Fallback to known games from preliminary rounds
        return [
            {'phaseCode': 'gpa-', 'eventUnitCode': '000100--', 'description': "Men's Prelim. Round - Group A"},
            {'phaseCode': 'gpa-', 'eventUnitCode': '000200--', 'description': "Men's Prelim. Round - Group A"},
            {'phaseCode': 'gpb-', 'eventUnitCode': '000100--', 'description': "Men's Prelim. Round - Group B"},
            {'phaseCode': 'gpb-', 'eventUnitCode': '000200--', 'description': "Men's Prelim. Round - Group B"},
            {'phaseCode': 'gpc-', 'eventUnitCode': '000100--', 'description': "Men's Prelim. Round - Group C"},
            {'phaseCode': 'gpc-', 'eventUnitCode': '000200--', 'description': "Men's Prelim. Round - Group C"},
        ]
    
    games = []
    for game in data.get('Data', []):
        phase_code = game.get('PhaseCode', '').lower()
        event_unit_code = game.get('EventUnitCode', '').lower()
        if phase_code and event_unit_code:
            games.append({
                'phaseCode': phase_code,
                'eventUnitCode': event_unit_code,
                'description': game.get('UnitDescription', 'Unknown')
            })
    
    print(f"Found {len(games)} games")
    return games


def parse_play_by_play(phase_code, event_unit_code):
    """
    Scrape a play-by-play page to extract goals and assists.
    
    Args:
        phase_code: Phase code (e.g., 'gpa-')
        event_unit_code: Event unit code (e.g., '000200--')
    
    Returns:
        Dict mapping player names to {'goals': int, 'assists': int}
    """
    url = f"https://www.olympics.com/en/milano-cortina-2026/results/iho/m/team6-------------/{phase_code}/{event_unit_code}/team-playbyplay"
    
    # Add page-specific headers
    page_headers = {
        'Referer': 'https://www.olympics.com/en/milano-cortina-2026/results/iho/m/team6-------------/team-sports-statistics-event',
    }
    
    try:
        response = fetch_with_retry(url, timeout=45, max_retries=2, extra_headers=page_headers)
    except Exception as e:
        print(f"  Warning: Could not fetch {phase_code}/{event_unit_code}: {str(e)[:100]}")
        return {}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    player_stats = defaultdict(lambda: {'goals': 0, 'assists': 0})
    seen_events = set()  # To deduplicate events (shown twice on page)
    
    # Find all goal events
    # Goals are in divs or sections with text containing "Goal"
    # The structure has athlete links with href="/en/milano-cortina-2026/results/athlete-details/{athleteCode}"
    
    # Look for all text nodes containing "Goal"
    for element in soup.find_all(string=lambda text: text and 'Goal' in text):
        parent = element.parent
        
        # Navigate up to find the container with player links
        for _ in range(10):  # Search up the tree
            if not parent:
                break
            
            # Find athlete links in this container
            athlete_links = parent.find_all('a', href=lambda x: x and '/athlete-details/' in x)
            
            if athlete_links and len(athlete_links) >= 1:
                # First link is the goal scorer
                scorer_link = athlete_links[0]
                scorer_name = scorer_link.get_text(strip=True)
                scorer_code = scorer_link.get('href', '').split('/')[-1]
                
                # Create unique event ID
                event_id = f"{scorer_code}_{scorer_name}"
                
                if event_id not in seen_events:
                    seen_events.add(event_id)
                    player_stats[scorer_name]['goals'] += 1
                    
                    # Additional links are assisters
                    for assist_link in athlete_links[1:]:
                        assister_name = assist_link.get_text(strip=True)
                        # Check if this is actually an assist (look for "Assist" text nearby)
                        assist_context = str(parent)
                        if 'Assist' in assist_context or 'assist' in assist_context:
                            player_stats[assister_name]['assists'] += 1
                
                break  # Found the container, no need to go higher
            
            parent = parent.parent
    
    return dict(player_stats)


def fetch_nhl_rosters():
    """
    Fetch all NHL team rosters and build a name->team mapping.
    
    Returns:
        Dict mapping normalized player name to NHL team abbreviation
    """
    player_to_team = {}
    
    print("\nFetching NHL rosters...")
    for team_abbrev in NHL_TEAMS:
        url = f"https://api-web.nhle.com/v1/roster/{team_abbrev}/current"
        
        try:
            response = fetch_with_retry(url, timeout=15, max_retries=2)
            roster = response.json()
            
            # Process forwards, defensemen, and goalies
            for position_group in ['forwards', 'defensemen', 'goalies']:
                for player in roster.get(position_group, []):
                    first_name = player.get('firstName', {}).get('default', '')
                    last_name = player.get('lastName', {}).get('default', '')
                    
                    if first_name and last_name:
                        full_name = f"{first_name} {last_name}"
                        normalized = normalize_name(full_name)
                        player_to_team[normalized] = team_abbrev
            
            print(f"  {team_abbrev}: {len(roster.get('forwards', [])) + len(roster.get('defensemen', [])) + len(roster.get('goalies', []))} players")
        
        except requests.RequestException as e:
            print(f"  Warning: Could not fetch roster for {team_abbrev}: {e}")
    
    print(f"Total NHL players mapped: {len(player_to_team)}")
    return player_to_team


def main():
    """Main execution function."""
    print("=" * 70)
    print("Olympics 2026 - NHL Team Points Aggregation")
    print("=" * 70)
    
    # Olympic countries participating in Men's Ice Hockey
    # Using lowercase for Quanthockey URLs
    olympic_countries = [
        'canada', 'usa', 'sweden', 'finland', 'czech-republic',
        'slovakia', 'switzerland', 'germany', 'latvia', 'denmark',
        'france', 'italy'
    ]
    
    # Step 1: Fetch stats from Quanthockey
    print("\nFetching Olympic player stats from Quanthockey...")
    all_player_stats = {}
    
    for country in olympic_countries:
        print(f"  {country.title()}...")
        players = fetch_quanthockey_stats(country)
        
        for player in players:
            # Use normalized name as key to avoid duplicates
            name_key = normalize_name(player['name'])
            if name_key not in all_player_stats:
                all_player_stats[name_key] = {
                    'name': player['name'],
                    'goals': player['goals'],
                    'assists': player['assists']
                }
            else:
                # Shouldn't happen, but just in case
                all_player_stats[name_key]['goals'] += player['goals']
                all_player_stats[name_key]['assists'] += player['assists']
    
    print(f"\nTotal unique players with points: {len(all_player_stats)}")
    
    # Step 2: Fetch NHL rosters
    player_to_team = fetch_nhl_rosters()
    
    # Step 3: Aggregate by NHL team
    print("\nAggregating points by NHL team...")
    nhl_team_stats = defaultdict(lambda: {
        'points': 0,
        'goals': 0,
        'assists': 0,
        'players': []
    })
    
    unmatched_players = []
    
    for normalized_name, stats in all_player_stats.items():
        nhl_team = player_to_team.get(normalized_name)
        
        if nhl_team:
            points = stats['goals'] + stats['assists']
            nhl_team_stats[nhl_team]['points'] += points
            nhl_team_stats[nhl_team]['goals'] += stats['goals']
            nhl_team_stats[nhl_team]['assists'] += stats['assists']
            nhl_team_stats[nhl_team]['players'].append({
                'name': stats['name'],
                'goals': stats['goals'],
                'assists': stats['assists'],
                'points': points
            })
        else:
            unmatched_players.append({
                'name': stats['name'],
                'goals': stats['goals'],
                'assists': stats['assists']
            })
    
    # Step 4: Display results
    print("\n" + "=" * 70)
    print("NHL TEAM RANKINGS BY OLYMPIC POINTS")
    print("=" * 70)
    
    # Sort teams by points (descending), then by goals (descending) as tiebreaker
    sorted_teams = sorted(
        nhl_team_stats.items(),
        key=lambda x: (x[1]['points'], x[1]['goals']),
        reverse=True
    )
    
    if not sorted_teams:
        print("\nNo NHL players found with Olympic points.")
    else:
        print(f"\n{'Rank':<6} {'Team':<6} {'Points':<8} {'Goals':<8} {'Assists':<8} {'Players':<8}")
        print("-" * 70)
        
        for rank, (team, stats) in enumerate(sorted_teams, 1):
            print(f"{rank:<6} {team:<6} {stats['points']:<8} {stats['goals']:<8} {stats['assists']:<8} {len(stats['players']):<8}")
            
            # Show top contributors for this team
            top_players = sorted(stats['players'], key=lambda x: x['points'], reverse=True)[:3]
            for player in top_players:
                print(f"         └─ {player['name']}: {player['goals']}G + {player['assists']}A = {player['points']}P")
        
        print("\n" + "=" * 70)
        print(f"Total NHL teams with points: {len(sorted_teams)}")
        print(f"Total NHL players with points: {sum(len(stats['players']) for stats in nhl_team_stats.values())}")
    
    if unmatched_players:
        print(f"\nNote: {len(unmatched_players)} players with points were not matched to NHL rosters")
        print("(likely playing in European leagues or other non-NHL leagues)")
    
    # Generate HTML output
    generate_html(sorted_teams, len(all_player_stats), len(unmatched_players))


def generate_html(sorted_teams, total_players, unmatched_count):
    """Generate a static HTML website with sortable table and accordions."""
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2026 Olympics - NHL Team Rankings</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .stats-summary {{
            display: flex;
            justify-content: space-around;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .stat-box {{
            text-align: center;
        }}
        
        .stat-box .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2a5298;
        }}
        
        .stat-box .label {{
            color: #6c757d;
            margin-top: 5px;
            font-size: 0.9em;
        }}
        
        .table-container {{
            padding: 20px 40px 40px;
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        thead {{
            background: #2a5298;
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            position: relative;
        }}
        
        th:hover {{
            background: #1e3c72;
        }}
        
        th.sortable::after {{
            content: ' ⇅';
            opacity: 0.5;
            font-size: 0.8em;
        }}
        
        th.sorted-asc::after {{
            content: ' ▲';
            opacity: 1;
        }}
        
        th.sorted-desc::after {{
            content: ' ▼';
            opacity: 1;
        }}
        
        tbody tr {{
            border-bottom: 1px solid #dee2e6;
            transition: background-color 0.2s;
        }}
        
        tbody tr:hover {{
            background-color: #f8f9fa;
        }}
        
        td {{
            padding: 15px;
        }}
        
        .rank {{
            font-weight: bold;
            color: #2a5298;
            font-size: 1.1em;
        }}
        
        .team-name {{
            font-weight: 600;
            font-size: 1.05em;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .team-logo {{
            width: 32px;
            height: 32px;
            object-fit: contain;
        }}
        
        .expand-btn {{
            background: #2a5298;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background-color 0.2s;
        }}
        
        .expand-btn:hover {{
            background: #1e3c72;
        }}
        
        .accordion-content {{
            display: none;
            padding: 20px;
            background: #f8f9fa;
            border-left: 3px solid #2a5298;
            margin: 10px 0;
        }}
        
        .accordion-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
        }}
        
        .accordion-header .team-logo {{
            width: 40px;
            height: 40px;
        }}
        
        .accordion-header h3 {{
            margin: 0;
        }}
        
        .accordion-content.active {{
            display: block;
            animation: slideDown 0.3s ease-out;
        }}
        
        @keyframes slideDown {{
            from {{
                opacity: 0;
                max-height: 0;
            }}
            to {{
                opacity: 1;
                max-height: 500px;
            }}
        }}
        
        .player-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }}
        
        .player-card {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .player-name {{
            font-weight: 600;
            color: #1e3c72;
            margin-bottom: 8px;
        }}
        
        .player-stats {{
            display: flex;
            justify-content: space-between;
            font-size: 0.9em;
            color: #6c757d;
        }}
        
        .stat {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        .stat-value {{
            font-weight: bold;
            color: #2a5298;
            font-size: 1.2em;
        }}
        
        .stat-label {{
            font-size: 0.8em;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9em;
        }}
        
        .medal {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 5px;
        }}
        
        .medal-1 {{ background: linear-gradient(135deg, #FFD700, #FFA500); }}
        .medal-2 {{ background: linear-gradient(135deg, #C0C0C0, #808080); }}
        .medal-3 {{ background: linear-gradient(135deg, #CD7F32, #8B4513); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏒 2026 Winter Olympics - NHL Team Rankings 🥇</h1>
            <p>Men's Ice Hockey - Points by NHL Team</p>
            <p style="font-size: 0.9em; margin-top: 10px; opacity: 0.8;">Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <div class="stats-summary">
            <div class="stat-box">
                <div class="number">{len(sorted_teams)}</div>
                <div class="label">NHL Teams</div>
            </div>
            <div class="stat-box">
                <div class="number">{sum(len(stats['players']) for _, stats in sorted_teams)}</div>
                <div class="label">NHL Players</div>
            </div>
            <div class="stat-box">
                <div class="number">{sum(stats['points'] for _, stats in sorted_teams)}</div>
                <div class="label">Total Points</div>
            </div>
            <div class="stat-box">
                <div class="number">{total_players}</div>
                <div class="label">All Olympic Players</div>
            </div>
        </div>
        
        <div class="table-container">
            <table id="rankingsTable">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th class="sortable" data-sort="team">Team</th>
                        <th class="sortable" data-sort="points">Points</th>
                        <th class="sortable" data-sort="goals">Goals</th>
                        <th class="sortable" data-sort="assists">Assists</th>
                        <th class="sortable" data-sort="players">Players</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for rank, (team, stats) in enumerate(sorted_teams, 1):
        medal_html = ''
        if rank == 1:
            medal_html = '<span class="medal medal-1"></span>'
        elif rank == 2:
            medal_html = '<span class="medal medal-2"></span>'
        elif rank == 3:
            medal_html = '<span class="medal medal-3"></span>'
        
        logo_url = f"https://assets.nhle.com/logos/nhl/svg/{team}_light.svg"
        
        html_content += f"""
                    <tr data-team="{team}" data-points="{stats['points']}" data-goals="{stats['goals']}" data-assists="{stats['assists']}" data-players="{len(stats['players'])}">
                        <td class="rank">{medal_html}{rank}</td>
                        <td class="team-name">
                            <img src="{logo_url}" alt="{team}" class="team-logo" onerror="this.style.display='none'">
                            <span>{team}</span>
                        </td>
                        <td>{stats['points']}</td>
                        <td>{stats['goals']}</td>
                        <td>{stats['assists']}</td>
                        <td>{len(stats['players'])}</td>
                        <td><button class="expand-btn" onclick="toggleAccordion('{team}')">Show Players</button></td>
                    </tr>
                    <tr id="accordion-{team}" class="accordion-row">
                        <td colspan="7">
                            <div class="accordion-content">
                                <div class="accordion-header">
                                    <img src="{logo_url}" alt="{team}" class="team-logo" onerror="this.style.display='none'">
                                    <h3>{team} Player Statistics</h3>
                                </div>
                                <div class="player-list">
"""
        
        # Sort players by points (descending), then goals
        sorted_players = sorted(stats['players'], key=lambda p: (p['points'], p['goals']), reverse=True)
        
        for player in sorted_players:
            html_content += f"""
                                    <div class="player-card">
                                        <div class="player-name">{player['name']}</div>
                                        <div class="player-stats">
                                            <div class="stat">
                                                <span class="stat-value">{player['goals']}</span>
                                                <span class="stat-label">Goals</span>
                                            </div>
                                            <div class="stat">
                                                <span class="stat-value">{player['assists']}</span>
                                                <span class="stat-label">Assists</span>
                                            </div>
                                            <div class="stat">
                                                <span class="stat-value">{player['points']}</span>
                                                <span class="stat-label">Points</span>
                                            </div>
                                        </div>
                                    </div>
"""
        
        html_content += """
                                </div>
                            </div>
                        </td>
                    </tr>
"""
    
    html_content += f"""
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Data Sources: Quanthockey.com (Olympic Stats) • NHL API (Team Rosters)</p>
            <p style="margin-top: 5px;">Note: {unmatched_count} players with points not on current NHL rosters</p>
        </div>
    </div>
    
    <script>
        function toggleAccordion(team) {{
            const accordion = document.getElementById('accordion-' + team);
            const content = accordion.querySelector('.accordion-content');
            const allAccordions = document.querySelectorAll('.accordion-content');
            
            // Close other accordions
            allAccordions.forEach(acc => {{
                if (acc !== content) {{
                    acc.classList.remove('active');
                }}
            }});
            
            // Toggle current accordion
            content.classList.toggle('active');
        }}
        
        let currentSort = {{ column: null, direction: 'desc' }};
        
        function sortTable(column) {{
            const table = document.getElementById('rankingsTable');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr:not(.accordion-row)'));
            
            // Determine sort direction
            if (currentSort.column === column) {{
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentSort.column = column;
                currentSort.direction = 'desc';
            }}
            
            // Sort rows
            rows.sort((a, b) => {{
                let aVal, bVal;
                
                if (column === 'team') {{
                    aVal = a.dataset.team;
                    bVal = b.dataset.team;
                    return currentSort.direction === 'asc' 
                        ? aVal.localeCompare(bVal)
                        : bVal.localeCompare(aVal);
                }} else {{
                    aVal = parseInt(a.dataset[column]);
                    bVal = parseInt(b.dataset[column]);
                    
                    if (currentSort.direction === 'asc') {{
                        return aVal - bVal;
                    }} else {{
                        // For descending, use goals as tiebreaker for points
                        if (column === 'points' && aVal === bVal) {{
                            return parseInt(b.dataset.goals) - parseInt(a.dataset.goals);
                        }}
                        return bVal - aVal;
                    }}
                }}
            }});
            
            // Clear existing rows
            const allRows = tbody.querySelectorAll('tr');
            allRows.forEach(row => row.remove());
            
            // Re-insert sorted rows with their accordions
            rows.forEach((row, index) => {{
                const team = row.dataset.team;
                const accordionRow = document.getElementById('accordion-' + team);
                
                // Update rank
                const rankCell = row.querySelector('.rank');
                const currentRank = index + 1;
                let medalHtml = '';
                if (currentRank === 1) medalHtml = '<span class="medal medal-1"></span>';
                else if (currentRank === 2) medalHtml = '<span class="medal medal-2"></span>';
                else if (currentRank === 3) medalHtml = '<span class="medal medal-3"></span>';
                rankCell.innerHTML = medalHtml + currentRank;
                
                tbody.appendChild(row);
                tbody.appendChild(accordionRow);
            }});
            
            // Update header indicators
            document.querySelectorAll('th').forEach(th => {{
                th.classList.remove('sorted-asc', 'sorted-desc');
                if (th.dataset.sort === column) {{
                    th.classList.add('sorted-' + currentSort.direction);
                }}
            }});
        }}
        
        // Add click handlers to sortable headers
        document.querySelectorAll('th.sortable').forEach(th => {{
            th.addEventListener('click', () => {{
                sortTable(th.dataset.sort);
            }});
        }});
        
        // Set initial sort state
        document.querySelector('th[data-sort="points"]').classList.add('sorted-desc');
    </script>
</body>
</html>
"""
    
    # Write to file
    output_file = 'olympics_nhl_rankings.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n{'=' * 70}")
    print(f"✅ Static website generated: {output_file}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
