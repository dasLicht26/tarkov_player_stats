import plotly.graph_objs as go
import numpy as np
import sqlite3
#from scipy.stats import norm

# Verbindung zur SQLite-Datenbank herstellen
conn = sqlite3.connect('large_data.db')
cursor = conn.cursor()

# Spielzeit-Bereiche festlegen
von = 0
bis = 200
schritte = 1
playtime_steps = np.arange(von, bis, schritte)
requests = {}
# Funktion zum Abrufen des Kill/Death-Verhältnisses für einen bestimmten Spielzeitbereich
def get_kd_distribution(playtime):
    query = """
    SELECT kills, deaths, runs 
    FROM pmc 
    WHERE totalInGameTime BETWEEN ? AND ?
    """
    playtime_s = int(playtime*60*60)
    #print(playtime)
    #print(playtime_s)
    cursor.execute(query, (playtime_s, playtime_s + 3600*schritte))
    rows = cursor.fetchall()
    requests[playtime] = len(rows)

    
    # Berechne das Kill/Death-Verhältnis (KD) pro Eintrag
    kd_ratios = [(row[0] / row[1]) if row[1] > 0 else 0 for row in rows if row[2] > 100]
    # Filtere alle KD-Werte unter 0.1 heraus
    kd_ratios = [kd for kd in kd_ratios if kd >= 0.1]   
    return kd_ratios

# Funktion zum Erstellen der Daten für einen bestimmten Zeitpunkt
def create_trace(playtime):
    kd_ratios = get_kd_distribution(playtime)
    
    if len(kd_ratios) == 0:
        return [go.Scatter(x=[], y=[], mode='lines', name=f'No data for {playtime}')]
    
    # Histogramm der KD-Verteilung
    hist_data = np.histogram(kd_ratios, bins=200, density=True)
    x_hist = hist_data[1][:-1]
    y_hist = hist_data[0]
    
    # Erstellen der Normalverteilung (Gaußkurve)
    #mu, std = norm.fit(kd_ratios)
    #x_norm = np.linspace(min(kd_ratios), max(kd_ratios), 100)
    #y_norm = norm.pdf(x_norm, mu, std)

    # Berechne den Durchschnitt des KD-Verhältnisses
    mean_kd = np.mean(kd_ratios)

    # besten 10% der Spieler
    best_10_percent_kd = np.percentile(kd_ratios, 90)  # 99. Perzentil (oberste 1%)

    # besten 1% der Spieler
    best_1_percent_kd = np.percentile(kd_ratios, 99)  # 99. Perzentil (oberste 1%)
    
    # besten 0.11% der Spieler
    best_01_percent_kd = np.percentile(kd_ratios, 99.9)  # 99. Perzentil (oberste 1%)

    return [
        go.Scatter(x=x_hist, y=y_hist, mode='lines', name='KD-Verteilung'),
        #go.Scatter(x=x_norm, y=y_norm, mode='lines', name='Gaußkurve', line=dict(dash='dash'))
        go.Scatter(x=[mean_kd, mean_kd], y=[0, max(y_hist)], mode='lines', name='Durchschnitt', line=dict(color='red', dash='dash')),
        # Vertikale Linie für die besten 1% der KD-Werte
        go.Scatter(x=[best_10_percent_kd, best_10_percent_kd], y=[0, max(y_hist)], mode='lines', name='Beste 10%', line=dict(color='blue', dash='dot')),
        go.Scatter(x=[best_1_percent_kd, best_1_percent_kd], y=[0, max(y_hist)], mode='lines', name='Beste 1%', line=dict(color='blue', dash='dot')),
        go.Scatter(x=[best_01_percent_kd, best_01_percent_kd], y=[0, max(y_hist)], mode='lines', name='Beste 0.1%', line=dict(color='blue', dash='dot'))
    ]

# Erstellen der ersten Datenreihe
data = create_trace(0)
# Erstellen des Layouts mit Slider
layout = go.Layout(
    title="Verteilung des Kill/Death-Verhältnisses über die Spielzeit",
    xaxis_title="Kill/Death-Verhältnis",
    xaxis=dict(range=[0, 20]),  # Begrenzung der X-Achse auf 0 bis 20
    yaxis_title="Häufigkeit",
    sliders=[{
        'active': 0,
        'currentvalue': {"prefix": "Spielzeit: "},
        'steps': [
            {'label': f'{i}', 'method': 'animate', 'args': [[f'{i}'], {'frame': {'duration': 0, 'redraw': True}}]} 
            for i in playtime_steps
        ]
    }],
    shapes=[
        # Vertikale Linie für den Durchschnittswert
        dict(
            type='line',
            x0=1, x1=1,
            y0=1, y1=1,  # Höhe der Linie (0 bis 1 = voller Bereich)
            xref='x', yref='paper',
            line=dict(color='red', width=2, dash='dash'),  # Rote gestrichelte Linie
            name='Durchschnitt'
        )
    ]
)
# Frames für die Animation
frames = [
    go.Frame(data=create_trace(playtime), name=f'{playtime}') 
    for playtime in playtime_steps
]

# Erstellen der Figur
fig = go.Figure(data=data, layout=layout, frames=frames)

# Anzeige des Graphen
fig.show()
print(requests)
# Schließe die Verbindung zur Datenbank
conn.close()
