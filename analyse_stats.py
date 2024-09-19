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

# SQL-Abfrage für Profile, die nach dem 16.08.2024 aktualisiert wurden und Kills/Deaths beinhalten
query = '''
SELECT kills_pmc, deaths_pmc, total_game_time, is_banned
FROM player_profiles
WHERE updated > ?
AND kills_pmc IS NOT NULL
AND deaths_pmc IS NOT NULL
AND deaths_pmc > 0
'''

# Datumsschwellwert für die Auswahl (16.08.2024)
date_threshold = datetime.datetime(2024, 8, 16)

# Daten als DataFrame laden
df = pd.read_sql_query(query, conn, params=(date_threshold.timestamp() * 1000,))

conn.close()

# Umwandlung von total_game_time in Tage
df['account_age_days'] = df['total_game_time'] / (60 * 60 * 24)

# Aufteilen in zwei Gruppen: Neuer als 50 Tage und älter als 50 Tage
new_accounts = df[(df['account_age_days'] <= 50) & (df['is_banned'] == 0)]
old_accounts = df[(df['account_age_days'] > 50) & (df['is_banned'] == 0)]
banned_accounts = df[df['is_banned'] == 1] if 'is_banned' in df.columns and df['is_banned'].notna().any() else pd.DataFrame()

# Funktion zum Erstellen der Kurven für eine bestimmte Gruppe
def create_kd_curve(df, label, color):
    if df.empty:
        return 0, 0, 0, 0
    
    df['kd_ratio'] = df['kills_pmc'] / df['deaths_pmc']
    
    # Ausrichtung der Gaußschen Normalverteilung am Peak der K/D-Ratio
    kd_mode = df['kd_ratio'].mode().iloc[0]  # Peak bestimmen
    kd_std = df['kd_ratio'].std()
    
    # Wahrscheinlichkeit für K/D > 15 berechnen
    prob_kd_15 = 1 - norm.cdf(15, kd_mode, kd_std)
    
    # Anzahl der Spieler, die in diesen K/D-Bereich fallen
    num_kd_15 = df[df['kd_ratio'] > 15].shape[0]
    
    # Erwartete Anzahl von Spielern über K/D 15 nach der Gaußschen Verteilung
    expected_kd_15 = prob_kd_15 * len(df)
    
    x_values = np.linspace(df['kd_ratio'].min(), df['kd_ratio'].max(), 1000)
    gauss_curve = norm.pdf(x_values, kd_mode, kd_std)
    
    # Dichtekurve der K/D-Ratio
    df['kd_ratio'].plot(kind='density', linewidth=2, label=f'{label} (Tatsächlich)', color=color)
    
    # Gaußsche Normalverteilung am Peak
    plt.plot(x_values, gauss_curve, linestyle='--', linewidth=2, label=f'{label} (Gauß)', color=color)
    
    return num_kd_15, expected_kd_15, len(df), df['kd_ratio'].max()

# Erstellen der Grafik
plt.figure(figsize=(12, 8))

# Kurven für neue, alte und gebannte Accounts erstellen
new_kd_15, new_expected_kd_15, new_count, new_max_kd = create_kd_curve(new_accounts, "Neue Accounts (< 50 Tage)", "blue")
old_kd_15, old_expected_kd_15, old_count, old_max_kd = create_kd_curve(old_accounts, "Alte Accounts (> 50 Tage)", "green")
banned_kd_15, banned_expected_kd_15, banned_count, banned_max_kd = create_kd_curve(banned_accounts, "Gesperrte Accounts", "red")

# Zusammenfassen der Informationen im Titel
total_count = new_count + old_count + banned_count
total_kd_15 = new_kd_15 + old_kd_15 + banned_kd_15
total_expected_kd_15 = new_expected_kd_15 + old_expected_kd_15 + banned_expected_kd_15

plt.title(f'Verteilung der K/D Ratio mit Gaußscher Glocke (Gesamt)\n'
          f'Anzahl der Profile: {total_count}\n'
          f'Tatsächliche Anzahl Spieler mit K/D > 15: {total_kd_15}\n'
          f'Erwartete Anzahl Spieler mit K/D > 15 (laut Gauß): {total_expected_kd_15:.2f}')

plt.xlabel('K/D Ratio')
plt.ylabel('Dichte')

plt.legend()

# Bestimme das Maximum für die x-Achse nur, wenn Daten vorhanden sind
max_kd_ratio = max(new_max_kd, old_max_kd, banned_max_kd)
if max_kd_ratio > 0:
    plt.xlim(left=0, right=max_kd_ratio * 1.1)

plt.show()
