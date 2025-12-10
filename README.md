# Aktienportfolio Datenbank - Gruppe 9

## Projektübersicht

Dieses Projekt implementiert ein Aktienportfolio-Managementsystem als Teil des Datenbanken-Endprojekts. Es ermöglicht die Verwaltung von Investoren, Depots, Aktien und Transaktionen mit einer modernen Web-Benutzeroberfläche.

## DBMS-Auswahl: SQLite

### Begründung

Wir haben **SQLite** als Datenbankmanagementsystem aus folgenden Gründen gewählt:

1. **Einfachheit und Portabilität**: SQLite speichert die gesamte Datenbank in einer einzigen Datei. Dies vereinfacht die Installation, Konfiguration und den Transport des Projekts erheblich.

2. **Keine Server-Installation erforderlich**: Anders als MySQL oder PostgreSQL benötigt SQLite keinen separaten Datenbankserver. Die Datenbank läuft direkt in der Anwendung (embedded database).

3. **ACID-Konformität**: SQLite unterstützt vollständige ACID-Transaktionen (Atomicity, Consistency, Isolation, Durability) und garantiert damit Datenintegrität.

4. **SQL-Standardkonformität**: SQLite unterstützt die meisten SQL-Funktionen, die für komplexe Abfragen mit JOINs, Subqueries, Common Table Expressions (CTEs) und Aggregatfunktionen benötigt werden.

5. **Ressourcenschonend**: Keine separate Speichernutzung durch einen Datenbankserver – ideal für Entwicklung und Demonstration.

6. **Ideal für Lernprojekte**: Für Universitätsprojekte bietet SQLite die perfekte Balance zwischen Funktionalität und Einfachheit.

### Einschränkungen

Für ein Produktionssystem mit vielen gleichzeitigen Benutzern würde man **PostgreSQL** oder **MySQL** verwenden, da SQLite bei konkurrierenden Schreibzugriffen limitiert ist.

## Datenbankschema

Das relationale Modell umfasst **8 Tabellen**:

| Tabelle | Beschreibung |
|---------|--------------|
| `Unternehmen` | Stammdaten der Unternehmen (Name, Branche, Land) |
| `Aktie` | Wertpapiere mit ISIN, Ticker und aktuellem Kurs |
| `Kursverlauf` | Historische Kursdaten (OHLC + Volumen) |
| `Investor` | Personendaten der Investoren |
| `Telefonnummer` | Mehrere Telefonnummern pro Investor (1:N) |
| `Depot` | Anlagekonten der Investoren |
| `Transaktionen` | Kauf- und Verkaufsaufträge |
| `HistorischerDepotwert` | Tägliche Portfolio-Bewertungen |

## Installation

### Voraussetzungen

- Python 3.8+
- pip (Python Package Manager)

### Setup

```bash
# In das Projektverzeichnis wechseln
cd Datebanken_Endprojekt

# Virtuelle Umgebung erstellen (optional, empfohlen)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# oder: venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python app.py
```

Die Anwendung ist dann unter **http://127.0.0.1:5000** erreichbar.

## Funktionen der Web-Oberfläche

### 1. Vordefinierte Abfragen

Die Anwendung bietet 12 vordefinierte SQL-Abfragen, die praxisrelevante Geschäftsszenarien abdecken:

| Abfrage | Geschäftswert |
|---------|---------------|
| **Portfolio-Übersicht** | Aktuelle Positionen und unrealisierte Gewinne/Verluste |
| **Risikoanalyse** | Identifikation von Investoren mit hoher Branchenkonzentration |
| **Top-Performer** | Aktien mit bester Kursentwicklung |
| **Inaktive Depots** | Depots ohne Aktivität (für Kundenreaktivierung) |
| **Volatilitäts-Warnung** | Aktien mit überdurchschnittlichen Schwankungen |
| **Handelsaktivität** | Monatliches Transaktionsvolumen pro Investor |
| **Dividenden-Aktien** | Beliebte Aktien bei langfristigen Anlegern |
| **Gewinn/Verlust-Analyse** | Realisierte Gewinne (Steuerberechnung) |
| **Regionale Verteilung** | Geografische Diversifikation |
| **Depot-Performance** | Historische Wertentwicklung |
| **Investoren-Kontakte** | Vollständige Kontaktdaten |
| **Aktien-Beliebtheit** | Meistgehandelte Titel |

### 2. Eigene SQL-Abfragen

Benutzer können eigene SELECT-Abfragen eingeben und ausführen.

### 3. Schema-Ansicht

Übersicht über alle Tabellen mit Spalten, Datentypen und Beziehungen.

### 4. Statistik-Dashboard

Live-Statistiken: Anzahl Investoren, Depots, Aktien, Transaktionen, Handelsvolumen.

## Beispieldaten

Die Datenbank wird mit realistischen Beispieldaten initialisiert:

- **15 Unternehmen** (DAX + US-Tech)
- **15 Aktien** mit echten ISINs
- **10 Investoren** mit deutschen Adressen
- **16 Telefonnummern**
- **12 Depots** (verschiedene Strategien)
- **46 Transaktionen** (Jan-Apr 2024)
- **Kursverlauf** für ausgewählte Aktien
- **Historische Depotwerte**

## SQL-Abfragen "mit Geschichte"

Unsere Abfragen wurden so gestaltet, dass sie reale Geschäftsanforderungen erfüllen:

### Beispiel 1: Risikoanalyse für Diversifikationsberatung

```sql
-- Findet Investoren mit mehr als 50% des Portfolios in einer Branche
WITH PortfolioPerBranche AS (...)
SELECT Investor, Branche, ProzentAnteil
FROM ...
WHERE BranchenWert / GesamtWert > 0.5
```

**Geschäftswert**: Berater können Kunden mit Klumpenrisiko identifizieren und proaktiv eine bessere Diversifikation empfehlen.

### Beispiel 2: Inaktive Depots für Kundenreaktivierung

```sql
-- Depots ohne Aktivität in den letzten 60 Tagen
SELECT Investor, EMail, Telefonnummern, TageOhneAktivitaet
FROM ...
WHERE TageOhneAktivitaet > 60
```

**Geschäftswert**: Das CRM-Team kann inaktive Kunden kontaktieren, um Abwanderung zu verhindern.

## Projektstruktur

```
Datebanken_Endprojekt/
├── app.py                 # Flask-Anwendung
├── requirements.txt       # Python-Abhängigkeiten
├── README.md              # Diese Dokumentation
├── database/
│   ├── schema.sql         # DDL-Statements
│   ├── sample_data.sql    # Beispieldaten
│   └── aktienportfolio.db # SQLite-Datenbank (generiert)
├── templates/
│   └── index.html         # Web-Interface
└── *.pdf                  # Projektdokumentation
```

## Autoren

**Gruppe 9** - Datenbanken Endprojekt

---

*Erstellt im Dezember 2024*

