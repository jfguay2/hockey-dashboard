import requests
import json
import urllib.parse
import csv
import concurrent.futures

HEADERS = {
    'Authorization': 'API-Key f08ed9064e3cdc382e6abb305ff543d0150fb52f',
    'x-page-type': 'ZONE',
    'Referer': 'https://page.spordle.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_all_games():
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
    if r.status_code == 200:
        return r.json()
    return []

def get_box_score(game_id):
    url = f'https://pub-api.play.spordle.com/api/sp/games/{game_id}/boxScore'
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    return None

def get_lineups(game_id):
    url = f'https://pub-api.play.spordle.com/api/sp/games/{game_id}/lineups'
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        # Protection : Si la réponse contient une erreur, on retourne un dictionnaire vide
        if isinstance(data, dict) and 'error' not in data:
            return data
    return {}

def main():
    games = get_all_games()
    played_games = [g for g in games if g.get("teamStats")]

    all_data = []
    
    def fetch_game(game):
        game_id = game['id']
        box_score = get_box_score(game_id)
        if not box_score:
            return []
            
        lineups = get_lineups(game_id)
        
        home_team_id = game.get('homeTeam', {}).get('id')
        home_team_name = game.get('homeTeam', {}).get('name', '')
        away_team_name = game.get('awayTeam', {}).get('name', '')

        def get_team_name(t_id):
            return home_team_name if str(t_id) == str(home_team_id) else away_team_name

        game_info = {
            'Game_ID': game_id,
            'Date': game.get('date'),
            'Category': game.get('category', {}).get('name', ''),
            'Home_Team': home_team_name,
            'Away_Team': away_team_name
        }
        
        extracted = []
        
        # 1. TÉLÉCHARGER L'ALIGNEMENT (ROSTER) D'ABORD
        for t_id, players in lineups.items():
            if not isinstance(players, list): continue # Protection supplémentaire
            player_team = get_team_name(t_id)
            for p in players:
                # Ignorer les entraîneurs (qui n'ont généralement pas de numéro attribué)
                if p.get('number') is None:
                    continue
                    
                part = p.get('participant', {})
                roster_data = {**game_info, 'Player_Team': player_team, 'Type': 'Roster', 'Period': '', 'Time': '', 'Player': part.get('fullName'), 'Number': p.get('number'), 'Infraction': ''}
                extracted.append(roster_data)

        # 2. TÉLÉCHARGER LES BUTS ET PASSES
        for g in box_score.get('goals', []):
            p = g.get('participant', {})
            player_team = get_team_name(g.get('teamId'))
            goal_data = {**game_info, 'Player_Team': player_team, 'Type': 'Goal', 'Period': g.get('gameTime',{}).get('period'), 'Time': f"{g.get('gameTime',{}).get('minutes')}:{str(g.get('gameTime',{}).get('seconds')).zfill(2)}", 'Player': p.get('fullName'), 'Number': p.get('number'), 'Infraction': ''}
            extracted.append(goal_data)
            
            for a in g.get('assists', []):
                assist_data = {**game_info, 'Player_Team': player_team, 'Type': 'Assist', 'Period': g.get('gameTime',{}).get('period'), 'Time': f"{g.get('gameTime',{}).get('minutes')}:{str(g.get('gameTime',{}).get('seconds')).zfill(2)}", 'Player': a.get('fullName'), 'Number': a.get('number'), 'Infraction': ''}
                extracted.append(assist_data)
                
        # 3. TÉLÉCHARGER LES PÉNALITÉS
        for p in box_score.get('penalties', []):
            part = p.get('participant', {})
            player_team = get_team_name(p.get('teamId'))
            pen_data = {**game_info, 'Player_Team': player_team, 'Type': 'Penalty', 'Period': p.get('gameTime',{}).get('period'), 'Time': f"{p.get('gameTime',{}).get('minutes')}:{str(p.get('gameTime',{}).get('seconds')).zfill(2)}", 'Player': part.get('fullName'), 'Number': part.get('number'), 'Infraction': p.get('infraction')}
            extracted.append(pen_data)
            
        return extracted

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_game, played_games))
        
    for res in results:
        all_data.extend(res)
            
    if all_data:
        with open('league_stats.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Game_ID', 'Date', 'Category', 'Home_Team', 'Away_Team', 'Player_Team', 'Type', 'Period', 'Time', 'Player', 'Number', 'Infraction'])
            writer.writeheader()
            writer.writerows(all_data)

if __name__ == "__main__":
    main()
