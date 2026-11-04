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
TEAM_ID = 186848
OFFICE_ID = 6103

HEADERS = {
    'Authorization': 'API-Key f08ed9064e3cdc382e6abb305ff543d0150fb52f',
    'x-page-type': 'ZONE',
    'Referer': 'https://page.spordle.com/'
}

def fetch_schedule():
    # 1. Games (League, Tournaments, Exhibition)
    filter_games = {
        'where': {
            'or': [{'homeTeamId': TEAM_ID}, {'awayTeamId': TEAM_ID}]
        },
        'include': ['surface', 'category', 'awayTeam', 'homeTeam', 'arena']
    }
    url_games = 'https://pub-api.play.spordle.com/api/sp/games?filter=' + urllib.parse.quote(json.dumps(filter_games))
    r_g = requests.get(url_games, headers=HEADERS)
    raw_games = r_g.json() if r_g.status_code == 200 else []

    # 2. Practices & Gym
    filter_practices = {
        'where': {
            'date': {'between': ['2026-08-01', '2027-05-01']},
            'or': [{'officeId': {'inq': [OFFICE_ID]}}, {'secondaryOfficeId': OFFICE_ID}],
            'teams': {'id': TEAM_ID}
        },
        'fields': {'recurrence': False},
        'include': ['practiceType', 'surface', 'teams']
    }
    url_practices = 'https://pub-api.play.spordle.com/api/sp/practices?filter=' + urllib.parse.quote(json.dumps(filter_practices))
    r_p = requests.get(url_practices, headers=HEADERS)
    raw_practices = r_p.json() if r_p.status_code == 200 else []

    all_events = {}

    # Process games
    for g in raw_games:
        g_id = f"game_{g.get('id')}"
        home = g.get('homeTeam', {}).get('name', 'N/A')
        away = g.get('awayTeam', {}).get('name', 'N/A')
        surf = g.get('surface', {})
        venue = surf.get('venue', {}) if isinstance(surf, dict) else {}
        arena_name = g.get('arena', {}).get('name') if isinstance(g.get('arena'), dict) else (venue.get('name') or 'N/A')
        rink = surf.get('name', '') if isinstance(surf, dict) else ''
        loc = f"{arena_name} ({rink})" if rink else arena_name

        status = g.get('status', 'Active')
        is_conflict = (status == 'Conflict')
        conflict_note = None
        if is_conflict:
            if g.get('date') == '2026-12-12':
                conflict_note = "Conflit officiel Spordle : deux matchs de ligue programmés le même jour (#3131 à 13h30 vs Cyclones et #3136 à 18h30 vs Élites Lanaudière)"
            elif g.get('date') == '2027-02-07':
                conflict_note = "Conflit officiel Spordle : match #3180 programmé à 11h00 au lendemain d'un match de soirée le 6 février"
            else:
                conflict_note = "Conflit d'horaire officiel signalé dans Spordle"

        all_events[g_id] = {
            'id': g_id,
            'spordle_id': g.get('id'),
            'type': 'game',
            'summary': f"Match: {home} vs {away}",
            'date': g.get('startTime', g.get('date')),
            'end_date': g.get('endTime'),
            'home': home,
            'away': away,
            'location': loc,
            'status': status,
            'is_conflict': is_conflict,
            'conflict_note': conflict_note
        }

    # Process practices
    for p in raw_practices:
        p_id = f"practice_{p.get('id')}"
        ptype = p.get('practiceType', {}).get('name') if p.get('practiceType') else 'Pratique'
        surf = p.get('surface', {})
        venue = surf.get('venue', {}) if isinstance(surf, dict) else {}
        arena_name = venue.get('name') or 'Centre Slush Puppie / Pierre Lafontaine'
        rink = surf.get('name') or surf.get('alias') or 'Glace'
        loc = f"{arena_name} ({rink})"

        p_type_label = 'gym' if 'gym' in str(rink).lower() or 'gym' in str(ptype).lower() else 'practice'
        prefix = 'Gym' if p_type_label == 'gym' else ('Pratique' if 'prat' in ptype.lower() else ptype)

        status = p.get('status', 'Active')
        is_conflict = (status == 'Conflict')
        conflict_note = f"Conflit d'installation ou de disponibilité signalé dans Spordle ({p.get('date')})" if is_conflict else None

        all_events[p_id] = {
            'id': p_id,
            'spordle_id': p.get('id'),
            'type': p_type_label,
            'summary': f"{prefix}: Royal Outaouais M17 AA",
            'date': p.get('startTime', p.get('date')),
            'end_date': p.get('endTime'),
            'home': 'ROYAL OUTAOUAIS',
            'away': None,
            'location': loc,
            'status': status,
            'is_conflict': is_conflict,
            'conflict_note': conflict_note
        }

    return all_events

def send_telegram(msg):
    if BOT_TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception as err:
            print(f"Telegram error: {err}")

def format_time(dt_str):
    if not dt_str: return "À déterminer"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        est = pytz.timezone('America/Toronto')
        return dt.astimezone(est).strftime('%d %b %Y à %H:%M')
    except Exception:
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
        for ev_id, curr_e in current_schedule.items():
            legacy_id = str(curr_e.get('spordle_id', ''))
            prev_e = previous_schedule.get(ev_id) or (previous_schedule.get(legacy_id) if legacy_id else None)

            if not prev_e:
                icon = "🏒" if curr_e['type'] == 'game' else ("🏋️" if curr_e['type'] == 'gym' else "🥅")
                label = "NOUVEAU MATCH AJOUTÉ" if curr_e['type'] == 'game' else ("NOUVELLE SÉANCE GYM" if curr_e['type'] == 'gym' else "NOUVELLE PRATIQUE")
                alert_text = f"{icon} *{label}*\n{curr_e['summary']}\nHeure: {format_time(curr_e['date'])}\nLieu: {curr_e['location']}"
                if curr_e.get('is_conflict'):
                    alert_text += f"\n⚠️ *CONFLIT D'HORAIRE SIGNALÉ (!)* : {curr_e.get('conflict_note', '')}"
                changes.append(alert_text)
            else:
                mods = []
                if curr_e['date'] != prev_e.get('date'):
                    mods.append(f"Heure changée pour {format_time(curr_e['date'])}")
                if curr_e['location'] != prev_e.get('location'):
                    mods.append(f"Lieu changé pour {curr_e['location']}")
                if curr_e['status'] != prev_e.get('status'):
                    mods.append(f"Statut changé pour {curr_e['status']}")
                if curr_e.get('is_conflict') and not prev_e.get('is_conflict'):
                    mods.append(f"⚠️ Conflit d'horaire officiel signalé (!) : {curr_e.get('conflict_note', '')}")
                if mods:
                    icon = "🏒" if curr_e['type'] == 'game' else ("🏋️" if curr_e['type'] == 'gym' else "🥅")
                    changes.append(f"{icon} *ÉVÉNEMENT MODIFIÉ*\n{curr_e['summary']}\n" + "\n".join(f"- {m}" for m in mods))

        for prev_id, prev_e in previous_schedule.items():
            canonical_id = prev_id if prev_id.startswith(('game_', 'practice_')) else f"game_{prev_id}"
            if canonical_id not in current_schedule:
                changes.append(f"❌ *ÉVÉNEMENT RETIRÉ/ANNULÉ*\n{prev_e.get('summary', 'Événement')}\nOriginalement prévu le: {format_time(prev_e.get('date'))}")

        if changes:
            header = "🚨 *Mise à jour de l'horaire (M17 AA)* 🚨\n\n"
            send_telegram(header + "\n\n".join(changes))
    else:
        send_telegram("✅ *Surveillance de l'horaire activée*\nJe surveille l'horaire complet (matchs, pratiques et gym) du Royal Outaouais M17 AA. Vous serez alerté ici de tout changement !")

    # Save updated previous_schedule.json
    with open('previous_schedule.json', 'w', encoding='utf-8') as f:
        json.dump(current_schedule, f, indent=2, ensure_ascii=False)

    # Generate Calendar File with stable UIDs and conflict warnings
    cal = Calendar()
    cal.creator = "-//Royal Outaouais M17 AA//Watchdog Calendar//FR"
    for ev_id, ev in current_schedule.items():
        if ev.get('status') == 'Cancelled':
            continue
        e = Event()
        e.uid = f"{ev_id}@royal-outaouais.lheq"
        flag = "[!] " if ev.get('is_conflict') else ""
        e.name = f"{flag}{ev['summary']}"
        e.begin = ev['date']
        if ev.get('end_date'):
            e.end = ev['end_date']
        else:
            try:
                dt = datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))
                e.end = dt + timedelta(hours=1, minutes=30)
            except Exception:
                pass
        e.location = ev.get('location', '')
        desc = f"Événement: {ev.get('summary')}\nStatut: {ev.get('status', 'Active')}"
        if ev.get('is_conflict'):
            desc += f"\nATTENTION CONFLIT (!): {ev.get('conflict_note', '')}"
            e.status = 'TENTATIVE'
        else:
            e.status = 'CONFIRMED'
        e.description = desc
        cal.events.add(e)

    with open('royal_outaouais_u17.ics', 'w', encoding='utf-8') as f:
        f.writelines(cal.serialize_iter())

if __name__ == "__main__":
    main()
