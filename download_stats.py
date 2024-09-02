import requests
import sqlite3
import os
import zlib

# URL der JSON-Daten
url_index = "https://players.tarkov.dev/profile/index.json"

# Name der SQLite-Datenbank
db_name = "tarkov_players.db"

# Funktion zum Erstellen der Datenbank und Tabellen
def create_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Tabelle für die Spielerliste erstellen, falls sie nicht existiert
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')
    
    # Tabelle für die Spielerprofile erstellen, falls sie nicht existiert
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_profiles (
            id INTEGER PRIMARY KEY,
            nickname TEXT,
            side TEXT,
            experience INTEGER,
            member_category INTEGER,
            selected_member_category INTEGER,
            achievements_count INTEGER,
            total_game_time INTEGER,
            sessions_pmc INTEGER,
            sessions_scav INTEGER,
            kills_pmc INTEGER,
            kills_scav INTEGER,
            deaths_pmc INTEGER,
            deaths_scav INTEGER,
            survived_pmc INTEGER,
            survived_scav INTEGER,
            longest_win_streak_pmc INTEGER,
            longest_win_streak_scav INTEGER,
            updated TIMESTAMP,
            is_banned BOOLEAN,
            FOREIGN KEY(id) REFERENCES players(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Funktion zum Herunterladen der JSON-Daten und Speichern in die Datenbank
def download_and_store_data(url, db_name):
    response = requests.get(url)
    data = response.json()
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Daten in die Tabelle einfügen
    for player_id, player_name in data.items():
        cursor.execute('''
            INSERT OR IGNORE INTO players (id, name)
            VALUES (?, ?)
        ''', (int(player_id), player_name))
    
    conn.commit()
    conn.close()

# Funktion zum Überprüfen, ob das Profil eines Spielers bereits gespeichert ist
def profile_exists(cursor, player_id):
    cursor.execute("SELECT 1 FROM player_profiles WHERE id = ?", (player_id,))
    return cursor.fetchone() is not None

# Funktion zum Herunterladen und Speichern der Spielerprofile
def fetch_and_store_profiles(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM players")
    player_ids = cursor.fetchall()
    
    for (player_id,) in player_ids:
        if profile_exists(cursor, player_id):
            print(f"Profil für Spieler {player_id} existiert bereits, überspringe...")
            continue
        
        profile_url = f"https://players.tarkov.dev/profile/{player_id}.json"
        
        try:
            response = requests.get(profile_url, headers={"Accept-Encoding": "identity"})
        except requests.exceptions.RequestException as e:
            print(f"Fehler beim Abrufen des Profils für Spieler {player_id}: {e}")
            continue
        
        if response.status_code == 200:
            try:
                # Manuelle Dekomprimierung falls notwendig
                if response.headers.get('Content-Encoding') == 'gzip':
                    profile_data = zlib.decompress(response.content, zlib.MAX_WBITS|16)
                    profile_data = profile_data.decode('utf-8')
                else:
                    profile_data = response.text

                profile_data = response.json()

            except (zlib.error, ValueError) as e:
                print(f"Fehler beim Dekomprimieren oder Dekodieren der Daten für Spieler {player_id}: {e}")
                continue

            info = profile_data.get('info', {})
            pmc_stats = profile_data.get('pmcStats', {}).get('eft', {}).get('overAllCounters', {}).get('Items', [])
            scav_stats = profile_data.get('scavStats', {}).get('eft', {}).get('overAllCounters', {}).get('Items', [])
            achievements = profile_data.get('achievements', {})
            is_banned = profile_data.get('isBanned', False)  # Abfragen des Bannstatus

            # Erstellen einer Hilfsfunktion zum Extrahieren von Statistiken
            def get_stat(stats, keys):
                try:
                    for item in stats:
                        if item['Key'] == keys:
                            return item['Value']
                    return None
                except TypeError: # Wenn stats None ist
                    return None

            # Einträge extrahieren oder auf None setzen, wenn sie nicht existieren
            nickname = info.get('nickname')
            side = info.get('side')
            experience = info.get('experience')
            member_category = info.get('memberCategory')
            selected_member_category = info.get('selectedMemberCategory')
            achievements_count = len(achievements) if achievements is not None else 0
            total_game_time = profile_data.get('pmcStats', {}).get('eft', {}).get('totalInGameTime')
            sessions_pmc = get_stat(pmc_stats, ['Sessions', 'Pmc'])
            sessions_scav = get_stat(scav_stats, ['Sessions', 'Scav'])
            kills_pmc = get_stat(pmc_stats, ['Kills'])
            kills_scav = get_stat(scav_stats, ['Kills'])
            deaths_pmc = get_stat(pmc_stats, ['Deaths'])
            deaths_scav = get_stat(scav_stats, ['Deaths'])
            survived_pmc = get_stat(pmc_stats, ['ExitStatus', 'Survived', 'Pmc'])
            survived_scav = get_stat(scav_stats, ['ExitStatus', 'Survived', 'Scav'])
            longest_win_streak_pmc = get_stat(pmc_stats, ['LongestWinStreak', 'Pmc'])
            longest_win_streak_scav = get_stat(scav_stats, ['LongestWinStreak', 'Scav'])
            updated = profile_data.get('updated')

            # Daten in die Tabelle einfügen
            cursor.execute('''
                INSERT OR REPLACE INTO player_profiles (
                    id, nickname, side, experience, member_category, selected_member_category, achievements_count,
                    total_game_time, sessions_pmc, sessions_scav, kills_pmc, kills_scav, deaths_pmc, deaths_scav,
                    survived_pmc, survived_scav, longest_win_streak_pmc, longest_win_streak_scav, updated, is_banned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                player_id, nickname, side, experience, member_category, selected_member_category, achievements_count,
                total_game_time, sessions_pmc, sessions_scav, kills_pmc, kills_scav, deaths_pmc, deaths_scav,
                survived_pmc, survived_scav, longest_win_streak_pmc, longest_win_streak_scav, updated, is_banned
            ))
            
            conn.commit()
            print(f"Profil für Spieler {player_id} erfolgreich gespeichert.")
        else:
            print(f"Fehler beim Abrufen des Profils für Spieler {player_id}. HTTP-Status: {response.status_code}")
    
    conn.close()

# Überprüfen, ob die Datenbank existiert, wenn nicht, wird sie erstellt
if not os.path.exists(db_name):
    create_database(db_name)

# JSON-Daten herunterladen und speichern
download_and_store_data(url_index, db_name)

# Spielerprofile abrufen und speichern
fetch_and_store_profiles(db_name)

print("Spielerprofile erfolgreich heruntergeladen und in der Datenbank gespeichert.")
