import sqlite3
import ijson

# Verbindung zur SQLite-Datenbank herstellen
conn = sqlite3.connect(r"C:\Users\PaulGustavLehmann\AppData\Local\projects\other\large_data_test\large_data.db")
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
        if counter < 2243000:
            continue
        
        if counter_h >= 1000:
            print(counter)
            conn.commit()
            counter_h = 0          
            
        # update pmc
        accountId = o['accountId']
        accountType = o['data']['info']['memberCategory']
        cursor.execute(''' UPDATE pmc SET accountType = ? WHERE accountId = ? ''', (accountType, accountId))

conn.commit()        
conn.close()
