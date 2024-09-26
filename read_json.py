import sqlite3
import ijson

# Verbindung zur SQLite-Datenbank herstellen
conn = sqlite3.connect('large_data.db')
cursor = conn.cursor()

# JSON-Datei verarbeiten
path = r"C:\Users\PaulGustavLehmann\Downloads\tarkovstats_18032024\tarkovstats_18032024.json"
counter = 0
counter_h = 0
with open(path, 'r') as f:
    objects = ijson.items(f, 'item')

    for o in objects:
        counter += 1
        counter_h += 1
        if counter_h == 1000:
            print(counter)
            conn.commit()
            counter_h = 0
            
        # player
        accountId = o['accountId']
        name = o['name']
        banned = int(o['banned'])
        try:
            cursor.execute('''
                INSERT INTO player (accountId, name, banned)
                VALUES (?, ?, ?)
            ''', (accountId, name, banned))
        except sqlite3.IntegrityError:
            pass

        
        # query
        date = o['queryTime']
        queryId = o['_id']['Machine']
        
        try:
            cursor.execute('''
                INSERT INTO query (id, date)
                VALUES (?, ?)
            ''', (queryId, date))
        except sqlite3.IntegrityError:
            pass

        
        # pmc
        totalInGameTime = o['data']['pmcStats']['eft']['totalInGameTime']
        pmc_items = o['data']['pmcStats']['eft']['overAllCounters']['Items']
        experience = o['data']['info']['experience']
        registrationDate = o['data']['info']['registrationDate']
        pmcId = f'{accountId}_{registrationDate}_{totalInGameTime}'
        pmc_runThroughs = 0
        pmc_missingInAction = 0
        pmc_longestWinStreak = 0
        pmc_survivedRuns = 0
        pmc_deaths = 0
        pmc_kills = 0
        pmc_runs = 0
        if pmc_items:
            for pmc_item in pmc_items:
                keys = pmc_item['Key']
                value = pmc_item['Value']
                if "Sessions" in keys:
                    pmc_runs = value
                elif "Survived" in keys:
                    pmc_survivedRuns = value
                elif "Deaths" in keys:
                    pmc_deaths = value
                elif "Kills" in keys:
                    pmc_kills = value
                elif "LongestWinStreak" in keys:
                    pmc_longestWinStreak = value
                elif "MissingInAction" in keys:
                    pmc_missingInAction = value
                elif "Runner" in keys:
                    pmc_runThroughs = value

        try:
            cursor.execute('''
                INSERT INTO pmc (id, accountId, experience, registrationDate, runThrough, missingInAction, longestWinStreak, survivedRuns, deaths, kills, runs, queryId, totalInGameTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pmcId, accountId, experience, registrationDate, pmc_runThroughs, pmc_missingInAction, pmc_longestWinStreak, pmc_survivedRuns, pmc_deaths, pmc_kills, pmc_runs, queryId, totalInGameTime))
        except sqlite3.IntegrityError:
            pass
        # scav
        scavId = f'{accountId}_{registrationDate}_{totalInGameTime}'
        scav_items = o['data']['scavStats']['eft']['overAllCounters']['Items']
        scav_missingInAction = 0
        scav_longestWinStreak = 0
        scav_survivedRuns = 0
        scav_deaths = 0
        scav_kills = 0
        scav_runs = 0
        if scav_items:
            for scav_item in scav_items:
                keys = scav_item['Key']
                value = scav_item['Value']
                if "Sessions" in keys:
                    scav_runs = value
                elif "Survived" in keys:
                    scav_survivedRuns = value
                elif "Deaths" in keys:
                    scav_deaths = value
                elif "Kills" in keys:
                    scav_kills = value
                elif "LongestWinStreak" in keys:
                    scav_longestWinStreak = value
                elif "MissingInAction" in keys:
                    scav_missingInAction = value
        try:
            cursor.execute('''
                INSERT INTO scav (id, missingInAction, longestWinStreak, survivedRuns, deaths, kills, runs, queryId, accountId)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (scavId, scav_missingInAction, scav_longestWinStreak, scav_survivedRuns, scav_deaths, scav_kills, scav_runs, queryId, accountId))

            # Änderungen speichern und Verbindung schließen
        except sqlite3.IntegrityError:
            pass
conn.commit()        
conn.close()
