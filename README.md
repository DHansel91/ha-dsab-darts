# DSAB Dartliga (3K Darts) für Home Assistant

Holt Tabelle, Spielplan, Ergebnisse und Spielerstatistik einer DSAB-Liga aus dem
[3K-Darts-Portal](https://portal.3k-darts.com) nach Home Assistant.

## Installation (HACS)

1. HACS → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/DHansel91/ha-dsab-darts`, Typ **Integration**.
2. „DSAB Dartliga (3K Darts)“ installieren und Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → DSAB Dartliga*.

## Einrichtung

Der Assistent fragt nacheinander ab:

1. **Region** (z. B. „Dartliga Nordoberpfalz“)
2. **Saison** (die aktuelle ist vorausgewählt)
3. **Liga** (z. B. „BZ 01“, „A 02“) – hat eine Liga mehrere Phasen, folgt eine Phasen-Auswahl
4. **Team** (optional) – für Team-Sensoren

Mehrere Ligen oder Teams lassen sich als eigene Einträge anlegen.

## Entities

| Entity | Zustand | Wichtige Attribute |
|---|---|---|
| Tabellenführer | Teamname | `tabelle` (komplette Tabelle) |
| Nächster Spieltag | Zeitpunkt | `spieltag`, `spiele` |
| Letzter Spieltag | Name des Spieltags | `spiele` mit Ergebnissen |
| Bester Spieler | Spielername | `spieler` (Top 10) |
| Kalender „Spiele“ | an während eines Spiels | alle Spiele inkl. Spiellokal |

Zusätzlich mit gewähltem Team:

| Entity | Zustand | Wichtige Attribute |
|---|---|---|
| Tabellenplatz | Platz | Punkte, Sets, Legs, Bilanz |
| Punkte | Punkte | – |
| Nächstes Spiel | Zeitpunkt | `gegner`, `heimspiel`, `spiellokal`, `adresse` |
| Letztes Ergebnis | z. B. `11:9` (eigene Sets zuerst) | `gegner`, `ausgang`, `legs` |
| Spielerstatistik | Anzahl Spieler | `spieler` des eigenen Teams |

Der Kalender zeigt mit Team nur dessen Spiele, sonst alle Spiele der Liga.

## Aktualisierung

Standardmäßig alle 30 Minuten (einstellbar über *Konfigurieren*). Während ein
Spiel läuft (Anwurf bis 6 h danach), wird alle 5 Minuten aktualisiert.

## Beispiel: Erinnerung am Spieltag

```yaml
triggers:
  - trigger: calendar
    event: start
    offset: "-2:00:00"
    entity_id: calendar.dc_mexikaner_bz_01_spiele
actions:
  - action: notify.mobile_app_handy
    data:
      title: "Darts heute"
      message: "{{ trigger.calendar_event.summary }} – {{ trigger.calendar_event.location }}"
```

## Hinweise

- Die Integration nutzt die öffentliche, undokumentierte Frontend-API des Portals.
  Ändert 3K Darts die API, kann ein Update nötig sein.
- Mandant ist fest auf DSAB (`mandantKey=1758`) eingestellt.

## Entwicklung

```bash
pip install pytest-homeassistant-custom-component
pytest
```

Die Tests laufen gegen echte, aufgezeichnete API-Antworten in `tests/fixtures`.
