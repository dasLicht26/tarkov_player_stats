import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm
import datetime

# Name der SQLite-Datenbank
db_name = "tarkov_players.db"

# Verbindung zur Datenbank herstellen
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# Datumsschwellwert für die Auswahl (16.08.2024)
date_threshold = datetime.datetime(2024, 8, 16)

# SQL-Abfrage für Profile, die nach dem 16.08.2024 aktualisiert wurden und Kills/Deaths beinhalten
query = '''
SELECT kills_pmc, deaths_pmc
FROM player_profiles
WHERE updated > ?
AND kills_pmc IS NOT NULL
AND deaths_pmc IS NOT NULL
AND deaths_pmc > 0
'''

# Daten als DataFrame laden
df = pd.read_sql_query(query, conn, params=(date_threshold.timestamp() * 1000,))

conn.close()

# K/D Ratio berechnen
df['kd_ratio'] = df['kills_pmc'] / df['deaths_pmc']

account_count = len(df)
print(f"Anzahl der Accounts, die die Bedingungen erfüllen: {account_count}")

# Statistiken berechnen
kd_mean = df['kd_ratio'].mean()
kd_std = df['kd_ratio'].std()

# Daten für die Gaußsche Glockenkurve vorbereiten
x_values = np.linspace(df['kd_ratio'].min(), df['kd_ratio'].max(), 1000)
gauss_curve = norm.pdf(x_values, kd_mean, kd_std)

# Grafik erstellen
plt.figure(figsize=(10, 6))

# Histogramm der K/D Ratio
plt.hist(df['kd_ratio'], bins=30, density=True, alpha=0.6, color='b')

# Gaußsche Glockenkurve hinzufügen
plt.plot(x_values, gauss_curve, 'r-', linewidth=2, label='Normalverteilung')

# Titel und Achsenbeschriftungen
plt.title('Verteilung der K/D Ratio mit Gaußscher Glocke')
plt.xlabel('K/D Ratio')
plt.ylabel('Dichte')

# Legende hinzufügen
plt.legend()

# Grafik anzeigen
plt.show()
