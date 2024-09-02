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
SELECT kills_pmc, deaths_pmc, total_game_time
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

# Aufteilen in zwei Gruppen: Neuer als 100 Tage und älter als 100 Tage
new_accounts = df[df['account_age_days'] <= 100]
old_accounts = df[df['account_age_days'] > 100]

# Funktion zum Erstellen einer Grafik für eine bestimmte Gruppe
def create_kd_plot(df, title_suffix):
    if df.empty:
        print(f"Keine Daten für {title_suffix}")
        return
    
    account_count = len(df)
    df['kd_ratio'] = df['kills_pmc'] / df['deaths_pmc']
    
    kd_mean = df['kd_ratio'].mean()
    kd_std = df['kd_ratio'].std()
    
    # Wahrscheinlichkeit für bestimmte K/D-Werte berechnen
    prob_kd_10 = 1 - norm.cdf(10, kd_mean, kd_std)
    prob_kd_15 = 1 - norm.cdf(15, kd_mean, kd_std)
    prob_kd_25 = 1 - norm.cdf(25, kd_mean, kd_std)
    prob_kd_30 = 1 - norm.cdf(30, kd_mean, kd_std)
    prob_kd_less_1 = norm.cdf(1, kd_mean, kd_std)
    
    # Anzahl der Spieler, die in diese K/D-Bereiche fallen
    num_kd_10 = df[df['kd_ratio'] > 10].shape[0]
    num_kd_15 = df[df['kd_ratio'] > 15].shape[0]
    num_kd_25 = df[df['kd_ratio'] > 25].shape[0]
    num_kd_30 = df[df['kd_ratio'] > 30].shape[0]
    num_kd_less_1 = df[df['kd_ratio'] < 1].shape[0]
    
    x_values = np.linspace(df['kd_ratio'].min(), df['kd_ratio'].max(), 1000)
    gauss_curve = norm.pdf(x_values, kd_mean, kd_std)
    
    plt.figure(figsize=(12, 8))
    
    density = df['kd_ratio'].plot(kind='density', linewidth=2, label='K/D Ratio Dichte')
    plt.plot(x_values, gauss_curve, 'r-', linewidth=2, label='Normalverteilung')
    
    # Titel und Informationen über der Grafik anzeigen
    plt.title(f'Verteilung der K/D Ratio mit Gaußscher Glocke ({title_suffix})\n'
              f'Anzahl der Profile: {account_count}\n'
              f'Wahrscheinlichkeit K/D > 10: {prob_kd_10:.4%} ({num_kd_10} Spieler)\n'
              f'Wahrscheinlichkeit K/D > 15: {prob_kd_15:.4%} ({num_kd_15} Spieler)\n'
              #f'Wahrscheinlichkeit K/D > 25: {prob_kd_25:.4%} ({num_kd_25} Spieler)\n'
              #f'Wahrscheinlichkeit K/D > 30: {prob_kd_30:.4%} ({num_kd_30} Spieler)\n'
              f'Wahrscheinlichkeit K/D < 1: {prob_kd_less_1:.4%} ({num_kd_less_1} Spieler)\n')
    
    plt.xlabel('K/D Ratio')
    plt.ylabel('Dichte')
    
    kd_ranges = [(0, 1), (1, 2), (2, 3), (3, 5), (5, 10), (10, 20), (20, df['kd_ratio'].max())]
    counts = [(df['kd_ratio'].between(r[0], r[1])).sum() for r in kd_ranges]
    
    for i, (r, count) in enumerate(zip(kd_ranges, counts)):
        plt.text(df['kd_ratio'].max() * 0.8, 0.9 - i * 0.05, f'{r[0]} <= K/D < {r[1]}: {count} Spieler', fontsize=10)
    
    plt.legend()
    plt.xlim(left=0, right=df['kd_ratio'].max() * 1.1)
    
    plt.show()

# Erstellen der drei Grafiken
create_kd_plot(new_accounts, "Accounts neuer als 100 Tage")
create_kd_plot(old_accounts, "Accounts älter als 100 Tage")
create_kd_plot(df, "Alle Accounts (kombiniert)")
