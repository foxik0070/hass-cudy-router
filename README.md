# Cudy Router Integration for Home Assistant

Custom integration pro Cudy routery s automatickou detekcí hardware. Testováno na **AC1200 (WR1200)** a **AX3000 (WR3000)**.

## Funkce

### Síťový výkon
| Entita | Popis | Jednotka |
|---|---|---|
| `sensor.download_speed` | Reálný download | Mbit/s |
| `sensor.upload_speed` | Reálný upload | Mbit/s |
| `sensor.download_total` | Celkem staženo | GB |
| `sensor.upload_total` | Celkem odesláno | GB |

### Zařízení
| Entita | Popis |
|---|---|
| `sensor.total_devices_connected` | Počet všech připojených zařízení |
| `sensor.wifi_devices_connected` | Počet Wi-Fi zařízení |
| `sensor.ethernet_devices_connected` | Počet drátových zařízení |
| `sensor.connected_devices_list` | Seznam zařízení s detaily (atributy) |

Atributy `connected_devices_list`:
- `hostname`, `ip`, `mac` — identifikace
- `connection` — typ připojení (`2.4G`, `5G`, `WIRED`)
- `signal` — síla signálu (dBm)
- `upload_speed`, `download_speed` — individuální rychlosti (Mbit/s)
- `online_time` — jak dlouho je zařízení připojeno
- `last_updated` — timestamp posledního refreshe

### Systémové informace (Diagnostic)
| Entita | Popis |
|---|---|
| `sensor.firmware_version` | Verze firmware |
| `sensor.hardware_version` | Verze hardware |
| `sensor.lan_ip_address` | LAN IP adresa routeru |
| `sensor.connected_time` | Uptime routeru |

### Device Tracker
Sleduje konkrétní zařízení podle MAC adresy. Stav `home`/`not_home` závisí na přítomnosti v tabulce připojených zařízení.

## Instalace

### Manuální
1. Zkopíruj obsah repozitáře do `config/custom_components/cudy_router/`.
2. Restartuj Home Assistant.

### HACS
Přidej repozitář jako vlastní a nainstaluj integraci přes HACS.

## Konfigurace

**Settings → Devices & Services → Add Integration → Cudy Router**

| Pole | Výchozí | Popis |
|---|---|---|
| Host | `192.168.10.1` | IP adresa routeru |
| Username | `admin` | Přihlašovací jméno |
| Password | — | Heslo |

### Volitelné nastavení (Options)
| Pole | Výchozí | Popis |
|---|---|---|
| Scan interval | `30` | Interval aktualizace v sekundách |
| Device list | — | Čárkou oddělené MAC adresy pro device tracker |

## Kompatibilita modelů

| Model | Řada | Poznámka |
|---|---|---|
| WR1200 | AC1200 | Data v Bytech, standardní HTML/JSON parsing |
| WR3000 | AX3000 | Hardware PPE offload — automatická korekce škálovacích faktorů |

Detekce probíhá automaticky podle hodnoty `hardware` ze systémové stránky routeru. Není potřeba žádná manuální konfigurace.

## Příklad dashboardu — seznam Wi-Fi klientů

```yaml
type: markdown
content: >-
  | Zařízení | Typ | Signál | Čas |

  | :--- | :--- | :--- | :--- |

  {% for device in state_attr('sensor.cudy_192_168_10_1_connected_devices_list', 'devices') -%}
    {%- if device.connection != 'WIRED' -%}
    {%- set sig = device.signal | replace(' dBm', '') | int(0) -%}
    {%- if sig <= -85 %}{% set icon = '🔴' -%}
    {%- elif sig <= -75 %}{% set icon = '🟠' -%}
    {%- elif sig <= -65 %}{% set icon = '🟡' -%}
    {%- else %}{% set icon = '🟢' %}{% endif -%}
    | **{{ device.hostname }}** ({{ device.ip }}) | {{ device.connection }} | {{ icon }} {{ device.signal }} | {{ device.online_time }} |
    {% endif -%}
  {%- endfor %}
title: Připojená zařízení
```

## Struktura souborů

```
custom_components/cudy_router/
├── __init__.py          # Setup a teardown integrace
├── config_flow.py       # UI průvodce konfigurací
├── const.py             # Konstanty (domain, názvy modulů)
├── coordinator.py       # DataUpdateCoordinator — řídí polling
├── device_tracker.py    # TrackerEntity pro sledování zařízení
├── manifest.json        # Metadata integrace
├── parser.py            # HTML/JSON parser pro data routeru
├── router.py            # HTTP klient (autentizace, fetch)
├── sensor.py            # SensorEntity definice
├── strings.json         # Texty pro UI
└── translations/
    └── en.json
```

## Architektura

```
coordinator.py
    └── router.py        (HTTP fetch, autentizace)
        └── parser.py    (parsování HTML/JSON odpovědí)
            ├── parse_system_info()    → MODULE_SYSTEM
            ├── parse_lan_info()       → MODULE_LAN
            ├── parse_bandwidth_json() → MODULE_BANDWIDTH
            └── parse_devices()        → MODULE_DEVICES

sensor.py        čte z coordinator.data[MODULE_*]
device_tracker.py čte z coordinator.data[MODULE_DEVICES]
```

Coordinator polluje router každých N sekund (výchozí 30). Všechna HTTP volání běží v executor poolu mimo async event loop.

## Kredity

Vychází z původní práce [armendkadrija](https://github.com/armendkadrija/hass-cudy-router-wr3600). Rozšířeno o univerzální AC/AX parser, pokročilé senzory a device tracker.
