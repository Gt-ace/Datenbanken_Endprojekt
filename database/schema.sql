-- Aktienportfolio Datenbank Schema
-- Gruppe 9 - Datenbanken Endprojekt

-- Unternehmen (Company) - Master data for companies
CREATE TABLE IF NOT EXISTS Unternehmen (
    UnternehmenID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name VARCHAR(100) NOT NULL,
    Branche VARCHAR(50) NOT NULL,
    Land VARCHAR(50) NOT NULL
);

-- Aktie (Stock) - Stock instruments
CREATE TABLE IF NOT EXISTS Aktie (
    ISIN VARCHAR(12) PRIMARY KEY,
    UnternehmenID INTEGER NOT NULL,
    Ticker VARCHAR(10) NOT NULL,
    Waehrung VARCHAR(3) NOT NULL DEFAULT 'EUR',
    AktuellerKurs DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (UnternehmenID) REFERENCES Unternehmen(UnternehmenID)
);

-- Kursverlauf (Price History) - Historical stock prices
CREATE TABLE IF NOT EXISTS Kursverlauf (
    Datum DATE NOT NULL,
    ISIN VARCHAR(12) NOT NULL,
    Oeffnungskurs DECIMAL(10, 2) NOT NULL,
    Tiefstkurs DECIMAL(10, 2) NOT NULL,
    Hoechstkurs DECIMAL(10, 2) NOT NULL,
    Endkurs DECIMAL(10, 2) NOT NULL,
    Volumen INTEGER NOT NULL,
    PRIMARY KEY (Datum, ISIN),
    FOREIGN KEY (ISIN) REFERENCES Aktie(ISIN)
);

-- Investor - Personal data of investors
CREATE TABLE IF NOT EXISTS Investor (
    InvestorID INTEGER PRIMARY KEY AUTOINCREMENT,
    Nachname VARCHAR(50) NOT NULL,
    Vorname VARCHAR(50) NOT NULL,
    EMail VARCHAR(100) UNIQUE NOT NULL,
    Strasse VARCHAR(100),
    PLZ VARCHAR(10),
    Ort VARCHAR(50)
);

-- Telefonnummer (Phone Number) - Multiple phones per investor
CREATE TABLE IF NOT EXISTS Telefonnummer (
    TelefonID INTEGER PRIMARY KEY AUTOINCREMENT,
    InvestorID INTEGER NOT NULL,
    Typ VARCHAR(20) NOT NULL, -- 'Mobil', 'Privat', 'Geschäftlich'
    Nummer VARCHAR(20) NOT NULL,
    FOREIGN KEY (InvestorID) REFERENCES Investor(InvestorID)
);

-- Depot (Portfolio) - Investment accounts
CREATE TABLE IF NOT EXISTS Depot (
    DepotID INTEGER PRIMARY KEY AUTOINCREMENT,
    InvestorID INTEGER NOT NULL,
    Bezeichnung VARCHAR(100) NOT NULL,
    Status VARCHAR(20) NOT NULL DEFAULT 'Aktiv', -- 'Aktiv', 'Gesperrt', 'Geschlossen'
    FOREIGN KEY (InvestorID) REFERENCES Investor(InvestorID)
);

-- Transaktionen - Buy/Sell records
CREATE TABLE IF NOT EXISTS Transaktionen (
    TransaktionsID INTEGER PRIMARY KEY AUTOINCREMENT,
    DepotID INTEGER NOT NULL,
    ISIN VARCHAR(12) NOT NULL,
    Datum DATETIME NOT NULL,
    Typ VARCHAR(10) NOT NULL, -- 'Kauf', 'Verkauf'
    Menge INTEGER NOT NULL,
    Stueckpreis DECIMAL(10, 2) NOT NULL,
    Gesamtwert DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (DepotID) REFERENCES Depot(DepotID),
    FOREIGN KEY (ISIN) REFERENCES Aktie(ISIN)
);

-- HistorischerDepotwert (Historical Portfolio Value)
CREATE TABLE IF NOT EXISTS HistorischerDepotwert (
    Datum DATE NOT NULL,
    DepotID INTEGER NOT NULL,
    Gesamtwert DECIMAL(12, 2) NOT NULL,
    DailyPnL DECIMAL(12, 2) NOT NULL DEFAULT 0,
    PRIMARY KEY (Datum, DepotID),
    FOREIGN KEY (DepotID) REFERENCES Depot(DepotID)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_aktie_unternehmen ON Aktie(UnternehmenID);
CREATE INDEX IF NOT EXISTS idx_kursverlauf_datum ON Kursverlauf(Datum);
CREATE INDEX IF NOT EXISTS idx_transaktionen_depot ON Transaktionen(DepotID);
CREATE INDEX IF NOT EXISTS idx_transaktionen_datum ON Transaktionen(Datum);
CREATE INDEX IF NOT EXISTS idx_depot_investor ON Depot(InvestorID);
CREATE INDEX IF NOT EXISTS idx_historischer_depotwert_datum ON HistorischerDepotwert(Datum);

