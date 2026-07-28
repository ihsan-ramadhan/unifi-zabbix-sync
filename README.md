# unifi-zabbix-sync

Sinkronisasi device UniFi Network Controller ke host Zabbix secara otomatis. Ambil daftar device dari UniFi API, buat/update/hapus host di Zabbix supaya selaras. Host dikelompokkan ke host group berdasarkan tipe device (AP, Switch, Gateway), pakai SNMP interface.

## Fitur

- Ambil device dari UniFi Controller via Integration API (paginasi otomatis).
- Buat host Zabbix jika device baru terdeteksi.
- Update host Zabbix jika ada perubahan: nama, IP, group, template, SNMP community/version, inventory.
- Hapus host Zabbix otomatis jika device hilang dari UniFi (`delete_missing: true`).
- Host group dinamis berdasarkan tipe device: `UniFi AP`, `UniFi Switch`, `UniFi Gateway`, `UniFi` (fallback).
- Template Zabbix dipetakan per tipe device.
- SNMP interface otomatis (default SNMPv2c, community `"zabbix"`), bisa diatur via env.
- Inventory Zabbix terisi: MAC, model, firmware, tipe device.

## Struktur

```
config/config.yaml      # pengaturan non-rahasia (host group, template map, delete_missing)
.env                    # kredensial
.env.example            # template .env
src/
  main.py               # entry point: jalankan sync
  config.py             # loader config.yaml + .env
  unifi.py              # UniFi API client (fetch devices + paginasi)
  zabbix.py             # Zabbix API client (pyzabbix)
  sync.py               # logika sinkronisasi inti
  logger.py             # setup logging
```

## Setup

```bash
git clone https://github.com/ihsan-ramadhan/unifi-zabbix-sync.git
cd unifi-zabbix-sync
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# isi .env dengan kredensial UniFi + Zabbix
```

## Konfigurasi

| Variabel | Wajib | Keterangan |
|---|---|---|
| `UNIFI_URL` | ya | URL UniFi Network Controller |
| `UNIFI_API_KEY` | ya | API key UniFi (Integration API) |
| `UNIFI_SITE_ID` | ya | Site ID UniFi |
| `UNIFI_VERIFY_SSL` | tidak | `false` matikan verifikasi TLS (default `true`) |
| `ZABBIX_URL` | ya | URL endpoint Zabbix JSON-RPC (`/api_jsonrpc.php`) |
| `ZABBIX_TOKEN` | ya | API token Zabbix |
| `ZABBIX_SNMP_COMMUNITY` | tidak | SNMP community string (default `zabbix`) |

### `config/config.yaml`

```yaml
sync:
  host_group: "UniFi"              # fallback host group
  host_groups:                    # mapping group per tipe device
    uap: "UniFi AP"
    usw: "UniFi Switch"
    gateway: "UniFi Gateway"
    default: "UniFi"
  delete_missing: true             # true = hapus host Zabbix yg tidak ada di UniFi
  templates:                      # mapping template Zabbix per tipe device
    uap: "Generic by SNMP"
    usw: "Generic by SNMP"
    gateway: "Template Net ICMP Ping"
    default: "Template Net ICMP Ping"
```

## Pemetaan Device UniFi → Zabbix

| UniFi | Zabbix |
|---|---|
| `macAddress` (tanpa `:`) | `host` (unique key) |
| `name` (fallback: `model`) | `name` (visible name) |
| `ipAddress` | interface `ip` (SNMP, port 161) |
| `features` (`accessPoint`/`switching`/`gateway`/`routing`) | tipe device → host group + template |
| `macAddress` | inventory `macaddress_a` |
| `model` | inventory `model` |
| `firmwareVersion` | inventory `software` |
| tipe device | inventory `hardware` |

## Menjalankan

```bash
source venv/bin/activate
python src/main.py
```

## Catatan

- Kredensial di `.env`, bukan di `config.yaml`.
- `UNIFI_VERIFY_SSL=false` hanya untuk controller self-signed internal. Aktifkan `true` di produksi.
- SNMP community default `"zabbix"` — ganti via `ZABBIX_SNMP_COMMUNITY` sesuai kebutuhan.

## Status

Berfungsi end-to-end. Sudah diuji sinkronisasi 54 device UniFi ke Zabbix 7.0.x.
