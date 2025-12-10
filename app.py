import sqlite3
import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'aktienportfolio.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
DATA_PATH = os.path.join(os.path.dirname(__file__), 'database', 'sample_data.sql')


def get_db_connection():
    """Create a database connection with foreign keys enabled"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Initialize the database with schema and sample data"""
    # Ensure database directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = get_db_connection()
    
    # Read and execute schema
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    # Check if data already exists
    cursor = conn.execute("SELECT COUNT(*) FROM Unternehmen")
    if cursor.fetchone()[0] == 0:
        # Read and execute sample data
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
    
    conn.commit()
    conn.close()

PREDEFINED_QUERIES = {
    "portfolio_overview": {
        "name": "Portfolio-Übersicht: Aktuelle Positionen und Gewinne/Verluste",
        "description": "Zeigt für jeden Investor den aktuellen Wert seiner Positionen und den unrealisierten Gewinn/Verlust - wichtig für die Vermögensübersicht.",
        "query": """
            SELECT 
                i.Vorname || ' ' || i.Nachname AS Investor,
                d.Bezeichnung AS Depot,
                u.Name AS Unternehmen,
                a.Ticker,
                SUM(CASE WHEN t.Typ = 'Kauf' THEN t.Menge ELSE -t.Menge END) AS AktuelleAnzahl,
                ROUND(AVG(CASE WHEN t.Typ = 'Kauf' THEN t.Stueckpreis END), 2) AS DurchschnittlicherKaufpreis,
                a.AktuellerKurs,
                ROUND(SUM(CASE WHEN t.Typ = 'Kauf' THEN t.Menge ELSE -t.Menge END) * a.AktuellerKurs, 2) AS AktuellerWert,
                ROUND(SUM(CASE WHEN t.Typ = 'Kauf' THEN t.Menge ELSE -t.Menge END) * 
                    (a.AktuellerKurs - AVG(CASE WHEN t.Typ = 'Kauf' THEN t.Stueckpreis END)), 2) AS UnrealisierterGewinn
            FROM Transaktionen t
            JOIN Depot d ON t.DepotID = d.DepotID
            JOIN Investor i ON d.InvestorID = i.InvestorID
            JOIN Aktie a ON t.ISIN = a.ISIN
            JOIN Unternehmen u ON a.UnternehmenID = u.UnternehmenID
            WHERE d.Status = 'Aktiv'
            GROUP BY i.InvestorID, d.DepotID, a.ISIN
            HAVING AktuelleAnzahl > 0
            ORDER BY i.Nachname, d.Bezeichnung, AktuellerWert DESC
        """
    },
    
    "risk_concentration": {
        "name": "Risikoanalyse: Investoren mit hoher Branchenkonzentration",
        "description": "Identifiziert Investoren, die mehr als 50% ihres Portfolios in einer Branche haben - wichtig für Risikomanagement und Diversifikationsberatung.",
        "query": """
            WITH PortfolioPerBranche AS (
                SELECT 
                    i.InvestorID,
                    i.Vorname || ' ' || i.Nachname AS Investor,
                    u.Branche,
                    SUM(CASE WHEN t.Typ = 'Kauf' THEN t.Menge ELSE -t.Menge END) * a.AktuellerKurs AS BranchenWert
                FROM Transaktionen t
                JOIN Depot d ON t.DepotID = d.DepotID
                JOIN Investor i ON d.InvestorID = i.InvestorID
                JOIN Aktie a ON t.ISIN = a.ISIN
                JOIN Unternehmen u ON a.UnternehmenID = u.UnternehmenID
                WHERE d.Status = 'Aktiv'
                GROUP BY i.InvestorID, u.Branche
                HAVING BranchenWert > 0
            ),
            GesamtPortfolio AS (
                SELECT InvestorID, SUM(BranchenWert) AS GesamtWert
                FROM PortfolioPerBranche
                GROUP BY InvestorID
            )
            SELECT 
                p.Investor,
                p.Branche,
                ROUND(p.BranchenWert, 2) AS WertInBranche,
                ROUND(g.GesamtWert, 2) AS GesamtPortfolioWert,
                ROUND(p.BranchenWert / g.GesamtWert * 100, 1) AS ProzentAnteil
            FROM PortfolioPerBranche p
            JOIN GesamtPortfolio g ON p.InvestorID = g.InvestorID
            WHERE p.BranchenWert / g.GesamtWert > 0.5
            ORDER BY ProzentAnteil DESC
        """
    },
    
    "top_performers": {
        "name": "Top-Performer: Aktien mit höchstem Kursgewinn im Beobachtungszeitraum",
        "description": "Analysiert welche Aktien die beste Performance gezeigt haben - nützlich für die Identifikation erfolgreicher Investments.",
        "query": """
            SELECT 
                u.Name AS Unternehmen,
                a.Ticker,
                u.Branche,
                u.Land,
                MIN(k.Endkurs) AS TiefsterKurs,
                MAX(k.Endkurs) AS HoechsterKurs,
                a.AktuellerKurs,
                ROUND((a.AktuellerKurs - MIN(k.Endkurs)) / MIN(k.Endkurs) * 100, 2) AS PerformanceInProzent,
                COUNT(DISTINCT k.Datum) AS AnzahlHandelstage
            FROM Aktie a
            JOIN Unternehmen u ON a.UnternehmenID = u.UnternehmenID
            JOIN Kursverlauf k ON a.ISIN = k.ISIN
            GROUP BY a.ISIN
            ORDER BY PerformanceInProzent DESC
            LIMIT 10
        """
    },
    
    "inactive_depots": {
        "name": "Inaktive Depots: Keine Aktivität in den letzten 60 Tagen",
        "description": "Findet Depots ohne kürzliche Transaktionen - wichtig für Kundenreaktivierung und Beziehungsmanagement.",
        "query": """
            SELECT 
                i.Vorname || ' ' || i.Nachname AS Investor,
                i.EMail,
                d.Bezeichnung AS Depot,
                d.Status,
                MAX(t.Datum) AS LetzteTransaktion,
                julianday('now') - julianday(MAX(t.Datum)) AS TageOhneAktivitaet,
                COUNT(t.TransaktionsID) AS GesamtTransaktionen,
                GROUP_CONCAT(DISTINCT tel.Nummer) AS Telefonnummern
            FROM Depot d
            JOIN Investor i ON d.InvestorID = i.InvestorID
            LEFT JOIN Transaktionen t ON d.DepotID = t.DepotID
            LEFT JOIN Telefonnummer tel ON i.InvestorID = tel.InvestorID
            WHERE d.Status = 'Aktiv'
            GROUP BY d.DepotID
            HAVING TageOhneAktivitaet > 60 OR LetzteTransaktion IS NULL
            ORDER BY TageOhneAktivitaet DESC
        """
    },
    
    "volatility_alert": {
        "name": "Volatilitäts-Warnung: Aktien mit hohen Tagesschwankungen",
        "description": "Identifiziert Aktien mit überdurchschnittlicher Volatilität - wichtig für Risikowarnungen an Investoren.",
        "query": """
            SELECT 
                u.Name AS Unternehmen,
                a.Ticker,
                k.Datum,
                k.Oeffnungskurs,
                k.Tiefstkurs,
                k.Hoechstkurs,
                k.Endkurs,
                ROUND((k.Hoechstkurs - k.Tiefstkurs) / k.Oeffnungskurs * 100, 2) AS Tagesvolatilitaet,
                k.Volumen
            FROM Kursverlauf k
            JOIN Aktie a ON k.ISIN = a.ISIN
            JOIN Unternehmen u ON a.UnternehmenID = u.UnternehmenID
            WHERE (k.Hoechstkurs - k.Tiefstkurs) / k.Oeffnungskurs > 0.05
            ORDER BY Tagesvolatilitaet DESC
            LIMIT 15
        """
    },
    
    "trading_activity": {
        "name": "Handelsaktivität: Transaktionsvolumen pro Monat und Investor",
        "description": "Zeigt das monatliche Handelsvolumen",
        "query": """
            SELECT 
                i.Vorname || ' ' || i.Nachname AS Investor,
                strftime('%Y-%m', t.Datum) AS Monat,
                COUNT(*) AS AnzahlTransaktionen,
                SUM(CASE WHEN t.Typ = 'Kauf' THEN 1 ELSE 0 END) AS Kaeufe,
                SUM(CASE WHEN t.Typ = 'Verkauf' THEN 1 ELSE 0 END) AS Verkaeufe,
                ROUND(SUM(t.Gesamtwert), 2) AS Gesamtvolumen,
                ROUND(AVG(t.Gesamtwert), 2) AS DurchschnittlicheTransaktion
            FROM Transaktionen t
            JOIN Depot d ON t.DepotID = d.DepotID
            JOIN Investor i ON d.InvestorID = i.InvestorID
            GROUP BY i.InvestorID, strftime('%Y-%m', t.Datum)
            ORDER BY Monat DESC, Gesamtvolumen DESC
        """
    },
    
    "dividend_portfolio": {
        "name": "Dividenden-Aktien: Beliebte Aktien bei langfristigen Investoren",
        "description": "Zeigt welche Aktien häufig von Investoren mit Dividenden-/Altersvorsorge-Depots gehalten werden.",
        "query": """
            SELECT 
                u.Name AS Unternehmen,
                a.Ticker,
                u.Branche,
                COUNT(DISTINCT d.DepotID) AS AnzahlDepots,
                SUM(CASE WHEN t.Typ = 'Kauf' THEN t.Menge ELSE -t.Menge END) AS GesamteAktien,
                ROUND(SUM(CASE WHEN t.Typ = 'Kauf' THEN t.Menge ELSE -t.Menge END) * a.AktuellerKurs, 2) AS GesamtInvestiert,
                GROUP_CONCAT(DISTINCT d.Bezeichnung) AS DepotTypen
            FROM Transaktionen t
            JOIN Depot d ON t.DepotID = d.DepotID
            JOIN Aktie a ON t.ISIN = a.ISIN
            JOIN Unternehmen u ON a.UnternehmenID = u.UnternehmenID
            WHERE d.Bezeichnung LIKE '%Dividenden%' 
               OR d.Bezeichnung LIKE '%Altersvorsorge%'
               OR d.Bezeichnung LIKE '%Konservativ%'
               OR d.Bezeichnung LIKE '%Familienvorsorge%'
            GROUP BY a.ISIN
            HAVING GesamteAktien > 0
            ORDER BY AnzahlDepots DESC, GesamtInvestiert DESC
        """
    },
    
    "pnl_analysis": {
        "name": "Gewinn/Verlust-Analyse: Realisierte Gewinne durch Verkäufe",
        "description": "Berechnet die realisierten Gewinne/Verluste aus abgeschlossenen Transaktionen",
        "query": """
            SELECT 
                i.Vorname || ' ' || i.Nachname AS Investor,
                d.Bezeichnung AS Depot,
                u.Name AS Unternehmen,
                t_sell.Datum AS Verkaufsdatum,
                t_sell.Menge AS VerkaufteMenge,
                t_sell.Stueckpreis AS Verkaufspreis,
                t_sell.Gesamtwert AS Verkaufswert,
                ROUND(AVG(t_buy.Stueckpreis), 2) AS DurchschnittlicherEinkaufspreis,
                ROUND(t_sell.Gesamtwert - (t_sell.Menge * AVG(t_buy.Stueckpreis)), 2) AS RealisierterGewinn
            FROM Transaktionen t_sell
            JOIN Depot d ON t_sell.DepotID = d.DepotID
            JOIN Investor i ON d.InvestorID = i.InvestorID
            JOIN Aktie a ON t_sell.ISIN = a.ISIN
            JOIN Unternehmen u ON a.UnternehmenID = u.UnternehmenID
            JOIN Transaktionen t_buy ON t_buy.DepotID = t_sell.DepotID 
                AND t_buy.ISIN = t_sell.ISIN 
                AND t_buy.Typ = 'Kauf'
                AND t_buy.Datum < t_sell.Datum
            WHERE t_sell.Typ = 'Verkauf'
            GROUP BY t_sell.TransaktionsID
            ORDER BY RealisierterGewinn DESC
        """
    },
    
    "regional_distribution": {
        "name": "Regionale Verteilung: Investitionen nach Ländern",
        "description": "Analysiert wie die Investments geografisch verteilt sind",
        "query": """
            SELECT 
                u.Land,
                COUNT(DISTINCT u.UnternehmenID) AS AnzahlUnternehmen,
                COUNT(DISTINCT t.DepotID) AS AnzahlDepotsMitInvestments,
                SUM(CASE WHEN t.Typ = 'Kauf' THEN t.Menge ELSE -t.Menge END) AS GesamteAktien,
                ROUND(SUM((CASE WHEN t.Typ = 'Kauf' THEN t.Menge ELSE -t.Menge END) * a.AktuellerKurs), 2) AS GesamtwertAktuell,
                GROUP_CONCAT(DISTINCT u.Branche) AS Branchen
            FROM Transaktionen t
            JOIN Aktie a ON t.ISIN = a.ISIN
            JOIN Unternehmen u ON a.UnternehmenID = u.UnternehmenID
            GROUP BY u.Land
            HAVING GesamteAktien > 0
            ORDER BY GesamtwertAktuell DESC
        """
    },
    
    "depot_performance": {
        "name": "Depot-Performance: Wertentwicklung über Zeit",
        "description": "Zeigt die historische Wertentwicklung der Depots",
        "query": """
            SELECT 
                i.Vorname || ' ' || i.Nachname AS Investor,
                d.Bezeichnung AS Depot,
                d.Status,
                MIN(h.Datum) AS ErsterEintrag,
                MAX(h.Datum) AS LetzterEintrag,
                (SELECT Gesamtwert FROM HistorischerDepotwert WHERE DepotID = d.DepotID ORDER BY Datum ASC LIMIT 1) AS StartWert,
                (SELECT Gesamtwert FROM HistorischerDepotwert WHERE DepotID = d.DepotID ORDER BY Datum DESC LIMIT 1) AS EndWert,
                ROUND(((SELECT Gesamtwert FROM HistorischerDepotwert WHERE DepotID = d.DepotID ORDER BY Datum DESC LIMIT 1) - 
                       (SELECT Gesamtwert FROM HistorischerDepotwert WHERE DepotID = d.DepotID ORDER BY Datum ASC LIMIT 1)), 2) AS AbsolutePerformance,
                ROUND(SUM(h.DailyPnL), 2) AS GesamtPnL,
                COUNT(h.Datum) AS AnzahlBewertungen
            FROM HistorischerDepotwert h
            JOIN Depot d ON h.DepotID = d.DepotID
            JOIN Investor i ON d.InvestorID = i.InvestorID
            GROUP BY d.DepotID
            ORDER BY AbsolutePerformance DESC
        """
    },
    
    "investor_contacts": {
        "name": "Investoren-Kontaktdaten: Vollständige Übersicht",
        "description": "Zeigt alle Kontaktinformationen der Investoren mit ihren Depots",
        "query": """
            SELECT 
                i.Vorname || ' ' || i.Nachname AS Name,
                i.EMail,
                i.Strasse || ', ' || i.PLZ || ' ' || i.Ort AS Adresse,
                GROUP_CONCAT(tel.Typ || ': ' || tel.Nummer, ' | ') AS Telefonnummern,
                COUNT(DISTINCT d.DepotID) AS AnzahlDepots,
                GROUP_CONCAT(d.Bezeichnung || ' (' || d.Status || ')', ' | ') AS Depots
            FROM Investor i
            LEFT JOIN Telefonnummer tel ON i.InvestorID = tel.InvestorID
            LEFT JOIN Depot d ON i.InvestorID = d.InvestorID
            GROUP BY i.InvestorID
            ORDER BY i.Nachname, i.Vorname
        """
    },
    
    "stock_popularity": {
        "name": "Aktien-Beliebtheit: Meistgehandelte Titel",
        "description": "Zeigt welche Aktien am häufigsten gehandelt werden",
        "query": """
            SELECT 
                u.Name AS Unternehmen,
                a.Ticker,
                a.Waehrung,
                u.Branche,
                COUNT(t.TransaktionsID) AS AnzahlTransaktionen,
                SUM(t.Menge) AS GesamtGehandelteMenge,
                ROUND(SUM(t.Gesamtwert), 2) AS GesamtHandelsvolumen,
                COUNT(DISTINCT t.DepotID) AS AnzahlVerschiedeneDepots,
                a.AktuellerKurs AS AktuellerKurs
            FROM Aktie a
            JOIN Unternehmen u ON a.UnternehmenID = u.UnternehmenID
            LEFT JOIN Transaktionen t ON a.ISIN = t.ISIN
            GROUP BY a.ISIN
            ORDER BY AnzahlTransaktionen DESC, GesamtHandelsvolumen DESC
        """
    }
}


@app.route('/')
def index():
    """Main page with query selection."""
    return render_template('index.html', queries=PREDEFINED_QUERIES)


@app.route('/execute_query/<query_id>')
def execute_query(query_id):
    """Execute a predefined query and return results."""
    if query_id not in PREDEFINED_QUERIES:
        return jsonify({'error': 'Query not found'}), 404
    
    query_info = PREDEFINED_QUERIES[query_id]
    
    try:
        conn = get_db_connection()
        cursor = conn.execute(query_info['query'])
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        results = [dict(zip(columns, row)) for row in rows]
        
        return jsonify({
            'name': query_info['name'],
            'description': query_info['description'],
            'query': query_info['query'].strip(),
            'columns': columns,
            'results': results,
            'row_count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/custom_query', methods=['POST'])
def custom_query():
    """Execute a custom SQL query (SELECT only for safety)."""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    # Safety check - only allow SELECT queries
    if not query.upper().startswith('SELECT'):
        return jsonify({'error': 'Nur SELECT-Abfragen sind erlaubt'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.execute(query)
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        results = [dict(zip(columns, row)) for row in rows]
        
        return jsonify({
            'columns': columns,
            'results': results,
            'row_count': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/schema')
def get_schema():
    """Return the database schema information."""
    conn = get_db_connection()
    
    # Get all tables
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    schema_info = {}
    for table in tables:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                'name': row[1],
                'type': row[2],
                'not_null': bool(row[3]),
                'primary_key': bool(row[5])
            })
        
        # Get foreign keys
        cursor = conn.execute(f"PRAGMA foreign_key_list({table})")
        foreign_keys = []
        for row in cursor.fetchall():
            foreign_keys.append({
                'column': row[3],
                'references_table': row[2],
                'references_column': row[4]
            })
        
        # Get row count
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
        
        schema_info[table] = {
            'columns': columns,
            'foreign_keys': foreign_keys,
            'row_count': row_count
        }
    
    conn.close()
    return jsonify(schema_info)


@app.route('/statistics')
def get_statistics():
    """Return database statistics."""
    conn = get_db_connection()
    
    stats = {}
    
    # Total investors
    cursor = conn.execute("SELECT COUNT(*) FROM Investor")
    stats['total_investors'] = cursor.fetchone()[0]
    
    # Total depots
    cursor = conn.execute("SELECT COUNT(*) FROM Depot")
    stats['total_depots'] = cursor.fetchone()[0]
    
    # Active depots
    cursor = conn.execute("SELECT COUNT(*) FROM Depot WHERE Status = 'Aktiv'")
    stats['active_depots'] = cursor.fetchone()[0]
    
    # Total stocks
    cursor = conn.execute("SELECT COUNT(*) FROM Aktie")
    stats['total_stocks'] = cursor.fetchone()[0]
    
    # Total companies
    cursor = conn.execute("SELECT COUNT(*) FROM Unternehmen")
    stats['total_companies'] = cursor.fetchone()[0]
    
    # Total transactions
    cursor = conn.execute("SELECT COUNT(*) FROM Transaktionen")
    stats['total_transactions'] = cursor.fetchone()[0]
    
    # Total transaction volume
    cursor = conn.execute("SELECT ROUND(SUM(Gesamtwert), 2) FROM Transaktionen")
    stats['total_volume'] = cursor.fetchone()[0] or 0
    
    # Countries
    cursor = conn.execute("SELECT COUNT(DISTINCT Land) FROM Unternehmen")
    stats['countries'] = cursor.fetchone()[0]
    
    # Industries
    cursor = conn.execute("SELECT COUNT(DISTINCT Branche) FROM Unternehmen")
    stats['industries'] = cursor.fetchone()[0]
    
    conn.close()
    return jsonify(stats)


if __name__ == '__main__':
    print("Initialisiere Datenbank...")
    init_database()
    print("Datenbank initialisiert!")
    print("\nStarte Webserver auf http://127.0.0.1:5000")
    print("Drücke Ctrl+C zum Beenden\n")
    app.run(debug=True, port=5000)

