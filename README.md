# Olympics NHL Points Aggregation

This script analyzes 2026 Winter Olympics Men's Ice Hockey stats and determines which NHL teams have scored the most points (goals + assists) through their players competing in the Olympics.

## Requirements

- Python 3.7+
- Virtual environment (recommended)

## Installation

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the script (generates both console output and HTML file)
python olympics_nhl_points.py
```

The script will:
1. Display rankings in the terminal
2. Generate `olympics_nhl_rankings.html` - an interactive website with:
   - **Sortable columns** - Click any column header to sort
   - **Accordion dropdowns** - Click "Show Players" to see individual player stats
   - **Beautiful responsive design** - Works on desktop, tablet, and mobile
   - **Real-time stats** - Timestamp shows when data was last updated

## How It Works

1. **Data Collection**: Fetches player statistics (goals and assists) from Quanthockey.com for all 12 countries participating in Men's Ice Hockey at the 2026 Olympics
   - Canada, USA, Sweden, Finland, Czech Republic, Slovakia, Switzerland, Germany, Latvia, Denmark, France, Italy

2. **NHL Roster Mapping**: Retrieves current rosters for all 32 NHL teams via the official NHL API and builds a mapping of player names to their NHL teams

3. **Aggregation**: Matches Olympic players to their NHL teams (non-NHL players are excluded) and calculates total points per team

4. **Results**: Displays a ranked list of NHL teams showing:
   - Total Olympic points (goals + assists)
   - Breakdown of goals and assists
   - Number of contributing players
   - Top 3 contributors per team with their individual stats

## Example Output

### Terminal Output
```
======================================================================
NHL TEAM RANKINGS BY OLYMPIC POINTS
======================================================================

Rank   Team   Points   Goals    Assists  Players 
----------------------------------------------------------------------
1      COL    4        2        2        4       
         └─ Nathan MacKinnon: 1G + 0A = 1P
         └─ Cale Makar: 0G + 1A = 1P
         └─ Gabriel Landeskog: 1G + 0A = 1P
2      NJD    4        2        2        3       
         └─ Timo Meier: 2G + 0A = 2P
...
```

### Generated Website
After running the script, open `olympics_nhl_rankings.html` in your browser to see:
- 🥇 Interactive table with gold/silver/bronze medals for top 3 teams
- 📊 Sortable columns (click headers to sort by any metric)
- 📋 Expandable player details for each team
- 📱 Responsive design that works on all devices
- 🎨 Beautiful gradient design with smooth animations

## Data Sources

- **Player Statistics**: [Quanthockey.com](https://www.quanthockey.com) - Olympic player stats
- **NHL Rosters**: [NHL API](https://api-web.nhle.com) - Current team rosters

## Notes

- Only NHL players are included in the rankings
- Stats are updated based on completed Olympic games
- Players not on current NHL rosters (e.g., those playing in European leagues) are excluded from team totals
