# DSAB Dartliga (3K Darts) für Home Assistant

[![HACS Custom][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![Validate][validate-badge]][validate-url]
[![License][license-badge]](LICENSE)
![Home Assistant][ha-badge]

Holt **Tabelle, Spielplan, Ergebnisse und Spielerstatistik** einer DSAB-Liga aus
dem [3K-Darts-Portal](https://portal.3k-darts.com) nach Home Assistant – als
Sensoren und als Kalender, damit du nie wieder einen Spieltag verpasst.

> *English summary:* Home Assistant custom integration that pulls standings,
> fixtures, results and player statistics of German DSAB darts leagues from the
> 3K Darts portal. Set up entirely via the UI; provides sensors and a calendar.

## Funktionen

- 🏆 Komplette Ligatabelle inkl. Punkte, Sets, Legs und Bilanz
- 📅 Kalender mit allen Spielen der Liga oder nur des eigenen Teams – inkl. Spiellokal und Adresse
- 🎯 Nächstes Spiel und letztes Ergebnis des eigenen Teams
- 👤 Spielerrangliste der Liga und Spielerstatistik des eigenen Teams
- ⚡ Automatisch schnellere Aktualisierung (alle 5 Minuten), solange ein Spiel läuft
- 🖱️ Einrichtung komplett über die Oberfläche, mehrere Ligen/Teams parallel möglich

## Installation

### Über HACS (empfohlen)

[![In HACS öffnen][my-hacs-badge]][my-hacs-url]

Oder manuell in HACS:

1. HACS öffnen → ⋮ (oben rechts) → **Benutzerdefinierte Repositories**.
2. `https://github.com/DHansel91/ha-dsab-darts` eintragen, Typ **Integration**, hinzufügen.
3. Nach **DSAB Dartliga (3K Darts)** suchen und **Herunterladen**.
4. Home Assistant neu starten.

### Manuell

1. `dsab_darts.zip` aus dem neuesten [Release][release-url] herunterladen.
2. Den Inhalt nach `config/custom_components/dsab_darts/` deiner
   Home-Assistant-Installation entpacken.
3. Home Assistant neu starten.

## Einrichtung

[![Integration hinzufügen][my-config-badge]][my-config-url]

Oder: *Einstellungen → Geräte & Dienste → Integration hinzufügen →
„DSAB Dartliga (3K Darts)“*.

Der Assistent fragt nacheinander ab:

1. **Region** (z. B. „Dartliga Nordoberpfalz“)
2. **Saison** (die aktuelle ist vorausgewählt)
3. **Liga** (z. B. „BZ 01“, „A 02“) – hat eine Liga mehrere Phasen, folgt eine Phasen-Auswahl
4. **Team** (optional) – für die Team-Sensoren

Mehrere Ligen oder Teams lassen sich als eigene Einträge anlegen.

### Optionen

Über **Konfigurieren** am Integrationseintrag:

| Option | Standard | Beschreibung |
|---|---|---|
| Aktualisierungsintervall | 30 min (min. 5) | Abfrageintervall außerhalb laufender Spiele |

Während ein Spiel läuft (Anwurf bis 6 h danach), wird unabhängig davon alle
5 Minuten aktualisiert.

## Entitäten

Pro Eintrag wird ein Gerät (Dienst) mit folgenden Entitäten angelegt.

### Liga

| Entität | Zustand | Wichtige Attribute |
|---|---|---|
| Tabellenführer | Teamname | `liga`, `saison`, `region`, `tabelle` (komplette Tabelle) |
| Nächster Spieltag | Zeitpunkt | `spieltag`, `spiele` |
| Letzter Spieltag | Name des Spieltags | `spiele` mit Ergebnissen |
| Bester Spieler | Spielername | `spieler` (Top 10) |
| Kalender „Spiele“ | an während eines Spiels | alle Spiele inkl. Spiellokal |

### Team (nur mit gewähltem Team)

| Entität | Zustand | Wichtige Attribute |
|---|---|---|
| Tabellenplatz | Platz | Punkte, Sets, Legs, Bilanz |
| Punkte | Punkte | – |
| Nächstes Spiel | Zeitpunkt | `gegner`, `heimspiel`, `spiellokal`, `adresse`, `gegner_platz` |
| Letztes Ergebnis | z. B. `11:9` (eigene Sets zuerst) | `gegner`, `ausgang`, `legs` |
| Spielerstatistik | Anzahl Spieler | `spieler` des eigenen Teams |

Der Kalender zeigt mit Team nur dessen Spiele, sonst alle Spiele der Liga.

> Die großen Listen-Attribute (`tabelle`, `spiele`, `spieler`) werden nicht in
> der Recorder-Datenbank gespeichert, um sie klein zu halten.

## Beispiele

### Erinnerung am Spieltag

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

### Tabelle als Markdown-Karte

```yaml
type: markdown
title: Tabelle
content: |
  | # | Team | Sp | Pkt | Sets |
  |---|---|---|---|---|
  {% for t in state_attr('sensor.dc_mexikaner_bz_01_tabellenfuhrer', 'tabelle') -%}
  | {{ t.platz }} | {{ t.team }} | {{ t.spiele }} | {{ t.punkte }} | {{ t.sets }} |
  {% endfor %}
```

> Entitäts-IDs und Attributnamen bitte an die eigene Installation anpassen
> (unter *Entwicklerwerkzeuge → Zustände* nachsehen).

## Fehlersuche

Debug-Logging aktivieren, entweder über *Einstellungen → Geräte & Dienste →
DSAB Dartliga → Debug-Protokollierung aktivieren* oder in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.dsab_darts: debug
```

Fehler und Wünsche bitte als [Issue][issues-url] melden – idealerweise mit
Log-Auszug, Region und Liga.

## Hinweise

- Die Integration nutzt die öffentliche, undokumentierte Frontend-API des Portals.
  Ändert 3K Darts die API, kann ein Update nötig sein.
- Mandant ist fest auf DSAB (`mandantKey=1758`) eingestellt.
- Dies ist kein offizielles Projekt des DSAB oder von 3K Darts.

## Entwicklung

```bash
pip install pytest-homeassistant-custom-component
pytest
```

Die Tests laufen gegen echte, aufgezeichnete API-Antworten in `tests/fixtures`.
Bei jedem Push prüft GitHub Actions die Integration mit der HACS-Action,
`hassfest` und den Tests.

## Lizenz

[MIT](LICENSE)

<!-- Links -->
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[hacs-url]: https://hacs.xyz
[release-badge]: https://img.shields.io/github/v/release/DHansel91/ha-dsab-darts?style=for-the-badge
[release-url]: https://github.com/DHansel91/ha-dsab-darts/releases
[validate-badge]: https://img.shields.io/github/actions/workflow/status/DHansel91/ha-dsab-darts/validate.yml?branch=main&label=Validate&style=for-the-badge
[validate-url]: https://github.com/DHansel91/ha-dsab-darts/actions/workflows/validate.yml
[license-badge]: https://img.shields.io/github/license/DHansel91/ha-dsab-darts?style=for-the-badge
[ha-badge]: https://img.shields.io/badge/Home%20Assistant-2024.11%2B-blue?style=for-the-badge&logo=homeassistant
[issues-url]: https://github.com/DHansel91/ha-dsab-darts/issues
[my-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[my-hacs-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=DHansel91&repository=ha-dsab-darts&category=integration
[my-config-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
[my-config-url]: https://my.home-assistant.io/redirect/config_flow_start/?domain=dsab_darts
