import requests
import json
import urllib.parse
import csv
import concurrent.futures
from datetime import datetime

# API Configuration
HEADERS = {
    'Authorization': 'API-Key f08ed9064e3cdc382e6abb305ff543d0150fb52f',
    'x-page-type': 'ZONE',
    'Referer': 'https://page.spordle.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_all_games():
    print("Fetching league schedule...")
    filter_obj = {
        "order": ["startTime ASC", "number ASC"],
        "where": {
            "and": [
                {"date": {"between": ["2026-08-01", "2027-05-01"]}},
                {"effectiveOffices": [6103]}
            ]
        },
        "include": ["teamStats", "surface", "office", "category", "awayTeam", "homeTeam"]
    }
    url = 'https://pub-api.play.spordle.com/api/sp/games?filter=' + urllib.parse.quote(json.dumps(filter_obj))
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def get_box_score(game_id):
    url = f'https://pub-api.play.spordle.com/api/sp/games/{game_id}/boxScore'
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    return None

def main():
    games = get_all_games()
    print(f"Found {len(games)} games in the schedule.")
    
    # Filter only games that have been played/have stats available
    # teamStats usually isn't empty if the game is over and recorded.
    played_games = [g for g in games if g.get("teamStats")]
    print(f"Found {len(played_games)} completed games with stats.")

    all_goals = []
    all_penalties = []
    
    print("Fetching box scores for played games... This might take a minute.")
    
    def fetch_game(game):
        game_id = game['id']
        box_score = get_box_score(game_id)
        if not box_score:
            return None
        
        game_info = {
            'Game_ID': game_id,
            'Date': game.get('date'),
            'Category': game.get('category', {}).get('name', ''),
            'Home_Team': game.get('homeTeam', {}).get('name', ''),
            'Away_Team': game.get('awayTeam', {}).get('name', '')
        }
        
        goals = []
        for g in box_score.get('goals', []):
            p = g.get('participant', {})
            goal_data = {**game_info, 'Type': 'Goal', 'Period': g.get('gameTime',{}).get('period'), 'Time': f"{g.get('gameTime',{}).get('minutes')}:{str(g.get('gameTime',{}).get('seconds')).zfill(2)}", 'Player': p.get('fullName'), 'Number': p.get('number')}
            goals.append(goal_data)
            
            for a in g.get('assists', []):
                assist_data = {**game_info, 'Type': 'Assist', 'Period': g.get('gameTime',{}).get('period'), 'Time': f"{g.get('gameTime',{}).get('minutes')}:{str(g.get('gameTime',{}).get('seconds')).zfill(2)}", 'Player': a.get('fullName'), 'Number': a.get('number')}
                goals.append(assist_data)
                
        penalties = []
        for p in box_score.get('penalties', []):
            part = p.get('participant', {})
            pen_data = {**game_info, 'Type': 'Penalty', 'Period': p.get('gameTime',{}).get('period'), 'Time': f"{p.get('gameTime',{}).get('minutes')}:{str(p.get('gameTime',{}).get('seconds')).zfill(2)}", 'Player': part.get('fullName'), 'Number': part.get('number'), 'Infraction': p.get('infraction')}
            penalties.append(pen_data)
            
        return goals, penalties

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_game, played_games))
        
    for res in results:
        if res:
            all_goals.extend(res[0])
            all_penalties.extend(res[1])
            
    print(f"Extracted {len(all_goals)} goals/assists and {len(all_penalties)} penalties.")
    
    # Save to CSV
    if all_goals or all_penalties:
        with open('league_stats.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write Header
            writer.writerow(['Game_ID', 'Date', 'Category', 'Home_Team', 'Away_Team', 'Type', 'Period', 'Time', 'Player', 'Number', 'Infraction'])
            
            for row in all_goals:
                writer.writerow([row['Game_ID'], row['Date'], row['Category'], row['Home_Team'], row['Away_Team'], row['Type'], row['Period'], row['Time'], row['Player'], row['Number'], ''])
            for row in all_penalties:
                writer.writerow([row['Game_ID'], row['Date'], row['Category'], row['Home_Team'], row['Away_Team'], row['Type'], row['Period'], row['Time'], row['Player'], row['Number'], row['Infraction']])
        print("Successfully saved to league_stats.csv")

if __name__ == "__main__":
    main()
