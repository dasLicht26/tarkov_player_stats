import requests
import sqlite3
import zlib
import datetime
import ctypes
# URL der JSON-Daten
url_index = "https://players.tarkov.dev/profile/index.json"
conn = sqlite3.connect(r'C:\Users\PaulGustavLehmann\AppData\Local\projects\other\large_data_test\large_data.db')
cursor = conn.cursor()

# Name der SQLite-Datenbank
db_name = "tarkov_players.db"

def get_timestamp_ms_to_s(time_ms):

    # Schritt 1: Konvertiere Millisekunden in Sekunden
    if len(str(time_ms)) == 10:
        # Zeitstempel ist bereits in Sekunden
        timestamp_in_seconds = time_ms
    else:
        timestamp_in_seconds = time_ms / 1000

    # Schritt 2: Erstelle ein datetime-Objekt
    dt = datetime.datetime.fromtimestamp(timestamp_in_seconds)

    # Schritt 3: Überprüfe, ob die Uhrzeit bereits auf Mitternacht steht
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        # Zeit ist bereits Mitternacht, gib den ursprünglichen Timestamp zurück
        unix_timestamp_midnight = int(timestamp_in_seconds)
    else:
        # Zeit ist nicht Mitternacht, setze auf 00:00:00
        dt_midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        unix_timestamp_midnight = int(dt_midnight.timestamp())


    return unix_timestamp_midnight


# Funktion zum Herunterladen der JSON-Daten und Speichern in die Datenbank
def get_player_ids():
    response = requests.get(url_index)
    data = response.json()

    # Daten in die Tabelle einfügen
    for player_id, player_name in data.items():

        accountId = player_id
        name = player_name

        try:
            cursor.execute('''
                INSERT INTO player (accountId, name)
                VALUES (?, ?)
            ''', (accountId, name))
            print(f"Player {player_id} successfully added.")
        except sqlite3.IntegrityError:
            pass
    conn.commit()

# Funktion zum Herunterladen und Speichern der Spielerprofile
def update_profiles():
    
    cursor.execute("SELECT accountId FROM player")
    accountIds = cursor.fetchall()

    # Erstellen einer Hilfsfunktion zum Extrahieren von Statistiken
    def get_stat(stats, keys):
        try:
            for item in stats:
                if item['Key'] == keys:
                    return item['Value']
            return 0
        except TypeError: # Wenn stats None ist
            return 0
        

    counter_h = 0
    for index, (accountId,) in enumerate(accountIds):

        counter_h += 1
        if counter_h == 100:
            print(index)
            conn.commit()
            counter_h = 0
        if index < 446900:
            continue


        profile_url = f"https://players.tarkov.dev/profile/{accountId}.json"
        
        try:
            response = requests.get(profile_url, headers={"Accept-Encoding": "identity"})
        except requests.exceptions.RequestException as e:
            print(f"Fehler beim Abrufen des Profils für Spieler {accountId}: {e}")
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
                print(f"Fehler beim Dekomprimieren oder Dekodieren der Daten für Spieler {accountId}: {e}")
                continue
            
            # add Query
            updated = profile_data.get('updated')
            date = get_timestamp_ms_to_s(updated)
            queryId = get_timestamp_ms_to_s(updated)
            try:
                cursor.execute('''
                    INSERT INTO query (id, date)
                    VALUES (?, ?)
                ''', (queryId, date))
            except sqlite3.IntegrityError:
                pass

            # suche ob Plyer bereits ein PMC mit dieser QueryId hat
            cursor.execute('''
                SELECT * FROM pmc
                WHERE accountId = ? AND queryId = ?
            ''', (accountId, queryId))
            pmc = cursor.fetchone()

            if pmc is not None:
                print(f"Profil mit Query {queryId} für Spieler {accountId} bereits vorhanden.")
                continue

            #update Player
            is_banned = profile_data.get('isBanned')  # Abfragen des Bannstatus
            try:
                try:
                    cursor.execute('''
                        UPDATE player
                        SET banned = ?
                        WHERE accountId = ?
                    ''',  (int(is_banned), accountId))
                except TypeError:
                    pass
            except sqlite3.IntegrityError:
                pass


            # add PMC
            info = profile_data.get('info', {})
            pmc_stats = profile_data.get('pmcStats', {}).get('eft', {}).get('overAllCounters', {}).get('Items', [])
            totalInGameTime = profile_data.get('pmcStats', {}).get('eft', {}).get('totalInGameTime')
            pmcId = f'{accountId}_{queryId}_{totalInGameTime}'
            #nickname = info.get('nickname')
            #side = info.get('side')
            experience = info.get('experience')
            #member_category = info.get('memberCategory')
            #selected_member_category = info.get('selectedMemberCategory')
            #achievements_count = len(achievements) if achievements is not None else 0
            
            pmc_runs = get_stat(pmc_stats, ['Sessions', 'Pmc'])
            pmc_kills = get_stat(pmc_stats, ['Kills'])
            pmc_deaths = get_stat(pmc_stats, ['Deaths'])
            pmc_survivedRuns = get_stat(pmc_stats, ['ExitStatus', 'Survived', 'Pmc'])
            pmc_longestWinStreak = get_stat(pmc_stats, ['LongestWinStreak', 'Pmc'])
            pmc_missingInAction= get_stat(pmc_stats, ['MissingInAction', 'Pmc'])
            pmc_runThroughs = get_stat(pmc_stats, ['Runner', 'Pmc'])
            registrationDate = 0

            try:
                cursor.execute('''
                    INSERT INTO pmc (id, accountId, experience, registrationDate, runThrough, missingInAction, longestWinStreak, survivedRuns, deaths, kills, runs, queryId, totalInGameTime)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (pmcId, accountId, experience, registrationDate, pmc_runThroughs, pmc_missingInAction, pmc_longestWinStreak, pmc_survivedRuns, pmc_deaths, pmc_kills, pmc_runs, queryId, totalInGameTime))
            except sqlite3.IntegrityError:
                pass
            
            # add SCAV
            scav_stats = profile_data.get('scavStats', {}).get('eft', {}).get('overAllCounters', {}).get('Items', [])
            scavId = f'{accountId}_{queryId}_{totalInGameTime}'
            scav_runs = get_stat(scav_stats, ['Sessions', 'Scav'])
            scav_kills = get_stat(scav_stats, ['Kills'])
            scav_deaths = get_stat(scav_stats, ['Deaths'])
            scav_survivedRuns = get_stat(scav_stats, ['ExitStatus', 'Survived', 'Scav'])
            scav_longestWinStreak = get_stat(scav_stats, ['LongestWinStreak', 'Scav'])
            scav_missingInAction = get_stat(scav_stats, ['MissingInAction', 'Scav'])
#
            try:
                cursor.execute('''
                    INSERT INTO scav (id, missingInAction, longestWinStreak, survivedRuns, deaths, kills, runs, queryId, accountId)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (scavId, scav_missingInAction, scav_longestWinStreak, scav_survivedRuns, scav_deaths, scav_kills, scav_runs, queryId, accountId))

            # Änderungen speichern und Verbindung schließen
            except sqlite3.IntegrityError:
                pass

        else:
            print(f"Fehler beim Abrufen des Profils für Spieler {accountId}. HTTP-Status: {response.status_code}")

    conn.commit()    
    conn.close()




if __name__ == "__main__":
    # JSON-Daten herunterladen und speichern
    get_player_ids()
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
    # Spielerprofile abrufen und speichern
    update_profiles()

    print("Spielerprofile erfolgreich heruntergeladen und in der Datenbank gespeichert.")