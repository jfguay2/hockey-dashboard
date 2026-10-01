import requests
import json
import os
from datetime import datetime, timedelta
import urllib.parse
import pytz
from ics import Calendar, Event

# Load from secure GitHub vault
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TEAM_NAME = "ROYAL OUTAOUAIS"
CATEGORY = "U17 AA"

HEADERS = {
    'Authorization': 'API-Key f08ed9064e3cdc382e6abb305ff543d0150fb52f',
    'x-page-type': 'ZONE',
    'Referer': 'https://page.spordle.com/'
}

def fetch_schedule():
    filter_obj = {
        "order": ["startTime ASC", "number ASC"],
        "where": {
            "and": [
                {"date": {"between": ["2026-08-01", "2027-05-01"]}},
                {"effectiveOffices": [6103]}
            ]
        },
        "include": ["surface", "category", "awayTeam", "homeTeam"]
    }
    url = 'https://pub-api.play.spordle.com/api/sp/games?filter=' + urllib.parse.quote(json.dumps(filter_obj))
    r = requests.get(url, headers=HEADERS)
    games = r.json() if r.status_code == 200 else []
    
    target_games = {}
    for g in games:
        home = g.get('homeTeam', {}).get('name', '') or ''
        away = g.get('awayTeam', {}).get('name', '') or ''
        cat = g.get('category', {}).get('name', '') or ''
        
        # Isolate U17 AA Royal Outaouais
        if (TEAM_NAME in home or TEAM_NAME in away) and cat == CATEGORY:
            g_id = str(g.get('id'))
            target_games[g_id] = {
                'id': g_id,
                # CORRECTION ICI: Utiliser 'startTime' au lieu de 'date'
                'date': g.get('startTime', g.get('date')),
                'home': home,
                'away': away,
                'location': g.get('surface', {}).get('name', 'À déterminer'),
                'status': g.get('status', 'Scheduled')
            }
    return target_games

def send_telegram(msg):
    if BOT_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def format_time(dt_str):
    if not dt_str: return "TBD"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        est = pytz.timezone('America/Toronto')
        return dt.astimezone(est).strftime('%d %b %Y à %H:%M')
    except:
        return dt_str

def main():
    current_schedule = fetch_schedule()
    
    try:
        with open('previous_schedule.json', 'r', encoding='utf-8') as f:
            previous_schedule = json.load(f)
    except FileNotFoundError:
        previous_schedule = None
        
    if previous_schedule is not None:
        changes = []
        for g_id, curr_g in current_schedule.items():
            if g_id not in previous_schedule:
                changes.append(f"🏒 *NOUVEAU MATCH AJOUTÉ*\n{curr_g['home']} vs {curr_g['away']}\nHeure: {format_time(curr_g['date'])}\nAréna: {curr_g['location']}")
            else:
                prev_g = previous_schedule[g_id]
                mods = []
                if curr_g['date'] != prev_g['date']:
                    mods.append(f"Heure changée pour {format_time(curr_g['date'])}")
                if curr_g['location'] != prev_g['location']:
                    mods.append(f"Aréna changé pour {curr_g['location']}")
                if curr_g['status'] != prev_g['status']:
                    mods.append(f"Statut changé pour {curr_g['status']}")
                if mods:
                    changes.append(f"⚠️ *MATCH MODIFIÉ*\n{curr_g['home']} vs {curr_g['away']}\n" + "\n".join(f"- {m}" for m in mods))
                    
        for g_id, prev_g in previous_schedule.items():
            if g_id not in current_schedule:
                changes.append(f"❌ *MATCH ANNULÉ*\n{prev_g['home']} vs {prev_g['away']}\nOriginalement prévu le: {format_time(prev_g['date'])}")

        if changes:
            send_telegram("🚨 *Mise à jour de l'horaire (M17 AA)* 🚨\n\n" + "\n\n".join(changes))
    else:
        send_telegram("✅ *Surveillance de l'horaire activée*\nJe surveille l'horaire du Royal Outaouais M17 AA. Vous serez alerté ici si quoi que ce soit change !")

    # Save memory
    with open('previous_schedule.json', 'w', encoding='utf-8') as f:
        json.dump(current_schedule, f, indent=2)

    # Generate Calendar File
    cal = Calendar()
    for g_id, curr_g in current_schedule.items():
        if curr_g['status'] == 'Cancelled': continue
        e = Event()
        e.name = f"{curr_g['home']} vs {curr_g['away']}"
        e.begin = curr_g['date']
        try:
            dt = datetime.fromisoformat(curr_g['date'].replace('Z', '+00:00'))
            e.end = dt + timedelta(hours=1, minutes=30)
        except:
            pass
        e.location = curr_g['location']
        cal.events.add(e)
        
    with open('royal_outaouais_u17.ics', 'w', encoding='utf-8') as f:
        f.writelines(cal.serialize_iter())

if __name__ == "__main__":
    main()
