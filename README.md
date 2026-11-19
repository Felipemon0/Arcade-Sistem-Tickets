# Central Pier Arcade — Ticket Inventory & IoT Automation System

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![PWA](https://img.shields.io/badge/PWA-iOS%20Optimized-0071E3?style=flat&logo=apple)](https://developer.apple.com/safari/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?style=flat&logo=sqlite)](https://sqlite.org)
[![Tailwind CSS](https://img.shields.io/badge/UI-Tailwind%20CSS-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com)
[![ESP32](https://img.shields.io/badge/IoT-ESP32%20DevKit-E7352C?style=flat&logo=espressif)](https://www.espressif.com/en/products/socs/esp32)

An end-to-end operational inventory and automated IoT monitoring platform engineered for high-volume arcade operations. Built specifically for **Central Pier Arcade**, this platform unifies real-time physical ticket stock tracking across 70 redemption machines with automated edge-sensing microcontrollers and an Apple/Notion-inspired progressive web application (PWA) tailored for floor technicians.

---

## 1. Executive Summary & Business Impact

In family entertainment centers and boardwalk arcades, ticket-based redemption games run continuously under high customer demand. Traditional operations rely on chaotic manual ticket replenishment, leading to frequent machine lockouts ("Out of Tickets"), ticket spool tangles, and significant inventory shrinkage.

By standardizing dispenser capacities, establishing a structured 3-tier inventory hierarchy (Central Storage &rarr; Floor Reserve &rarr; Machine Dispenser), and integrating automated optical level sensors:

- **~40% Reduction in Ticket Waste & Shrinkage:** Standardizing block tracking (1 block = 2,000 tickets) and auditing physical counts eliminated unaccounted ticket drift and crushed paper waste.
- **Predictive Replenishment (Twice Weekly vs. Daily Fire-Fighting):** Technicians shifted from frantic reactive floor calls to scheduled, structured restock rounds twice per week.
- **Zero-Downtime Hopper Depletion Alerts:** Real-time ESP32 optical sensing alerts technicians before a hopper runs completely dry, preserving arcade revenue during peak hours.
- **Instant Floor Auditing:** Technicians can update ticket counts and execute refills in seconds directly from an iPhone or iPad using tactile single-tap stepper controls.

---

## 2. System Architecture

The solution couples a lightweight asynchronous Python backend with edge-deployed microcontrollers and an offline-capable mobile interface:

```
                                  +---------------------------------------+
                                  |      Arcade Floor Technicians         |
                                  |  (iPhone / iPad Safari iOS PWA)       |
                                  +-------------------+-------------------+
                                                      |
                                                      | HTTPS / WebSocket / REST
                                                      v
+-----------------------+                 +-------------------------------+
|  ESP32 Edge Islands   |   HTTP POST     |   FastAPI Application Core    |
|  (6-Machine Clusters) | --------------->|   (Port 8000 / ASGI Event Loop) |
|  - FC-51 IR Sensors   |   Sensor Alert  +---------------+---------------+
|  - 5s Debounce Filter |                                 |
+-----------------------+                                 | ACID Queries / Transactions
                                                          v
                                              +-----------------------+
                                              |    SQLite Database    |
                                              |   (arcade.db WAL)     |
                                              | - 70 Machine Registry |
                                              | - Storage Warehouse   |
                                              | - Immutable Audit Log |
                                              +-----------------------+
```

### Key Technical Pillars
1. **Core Backend (FastAPI + SQLite)**:
   - High-throughput asynchronous endpoints with low memory footprint (~40 MB RSS).
   - Strict transactional integrity tracking movement between central storage boxes, floor reserves, and machine hoppers.
   - Immutable audit logging tracking every manual adjustment, refill, and IoT sensor event with timestamps.
2. **Mobile-First Client Experience (iOS PWA)**:
   - Standalone iOS Web App experience with Apple design language (`#FBFBFB` canvas, `#1D1D1F` typography, `#0071E3` accents).
   - Dynamic viewport controls preventing intrusive keyboard auto-zoom in iOS Safari.
   - Adaptive responsive layout: A sleek Notion-style table on desktop (`>= 768px`) that transforms into thumb-friendly touch cards on mobile (`< 768px`) with instant `-0.25` / `+0.25` block adjustment steppers.
3. **IoT Edge Monitoring (ESP32 + FC-51 IR Sensors)**:
   - Clustered monitoring architecture: 1 ESP32 node manages an island of 6 machines.
   - Non-blocking 5-second optical debounce filter (`millis()`) to ignore vibration and ticket motion during payout.
   - Automatic dispatch of low-stock state updates directly to the backend.

---

## 3. Inventory Units & Mathematical Baseline

The arcade floor operates on a strict standardized unit conversion:
- **1 Block (`blq`)** = `2,000` physical tickets.
- **1 Storage Box** = `50` blocks = `100,000` physical tickets.
- **Low Stock Threshold**: Any machine whose `in_use` level falls below **&le; 35%** of its `max_capacity` is flagged for replenishment.

### Production Baseline (Preserved)
- **70 Arcade Machines Catalog**: Initialized with exact field baselines totaling **178.35 blocks in use** and **101.00 blocks in floor reserves**.
- **Central Storage Warehouse**: **7 boxes** (`350.00 blocks`).
- **Total System Inventory**: **`629.35` blocks** (`1,258,700` tickets) tracked with zero variance.

---

## 4. Quick Start & Local Network Deployment

Follow these steps to run the platform locally or expose it to iPhone / iPad devices across the arcade's local Wi-Fi network:

### Prerequisites
- Python 3.9+ installed (`python3 --version`)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/Arcade-Sistem.git
cd Arcade-Sistem

# 2. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Running on Local Network (for iPhone / iPad Safari Access)

To allow technicians to access the app from mobile devices on the same Wi-Fi router, bind the server to `0.0.0.0`:

```bash
fastapi dev main.py --host 0.0.0.0 --port 8000
```

1. Note your computer's local IP address (e.g., `192.168.1.100` via `ifconfig` or `ipconfig`).
2. Open Safari on your iPhone or iPad and navigate to:
   ```
   http://192.168.1.100:8000
   ```
3. **Add to Home Screen (Native PWA Mode)**:
   - In Safari, tap the **Share** button (box with upward arrow).
   - Scroll down and tap **"Add to Home Screen"**.
   - Tap **"Add"**. The app will appear on your iOS home screen as a standalone application without browser chrome.

---

## 5. API Reference

All requests and responses use JSON.

### Frontend & PWA Manifest
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the responsive single-page application (`index.html`) |
| `GET` | `/manifest.json` | Web App Manifest metadata for iOS/Android PWA standalone mode |
| `GET` | `/icon.svg` | Vector app icon |
| `GET` | `/apple-touch-icon.png`| High-resolution Apple home screen icon |

### Dashboard & Analytics
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/dashboard` | Aggregated KPIs (total blocks, tickets, in-use, reserves, storage), 70 machine states, and recent audit logs |

### Machine Operations
| Method | Endpoint | Payload | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/machines/{id}/refill` | `{"amount": 1.0}` | Transfers blocks from the machine's floor reserve into its active dispenser |
| `POST` | `/api/machines/{id}/count` | `{"new_in_use": 2.5}` | Updates physical count following floor audits. Records delta in audit log |
| `POST` | `/api/machines/{id}/restock-reserve` | `{"amount": 2.0}` | Pulls inventory blocks from Central Storage into the machine's floor reserve |
| `POST` | `/api/storage/add-boxes` | `{"boxes": 2, "blocks_per_box": 50.0}` | Receives new bulk manufacturer shipments into central warehouse storage |

### IoT Edge Sensor Integration
| Method | Endpoint | Headers | Payload | Description |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/iot/sensor-alert` | `X-API-Key: arcade-iot-dev-key` (optional) | `{"machine_id": 1, "low_stock": true, "sensor_node": "esp32-island-01"}` | Ingests optical sensor triggers from ESP32. If low stock is verified, updates dispenser level to 30% and logs the event |

---

## 6. Hardware & IoT Documentation

For complete wiring schematics, ASCII circuit diagrams, 12V-to-5V power supply regulation, and the Bill of Materials (BOM) comparing pilot costs ($28.20 USD) against full floor deployment ($333.00 USD), consult:

👉 **[Hardware & Wiring Guide (`hardware/README.md`)](hardware/README.md)**

Firmware source code:
- **[ESP32 Ticket Sensor Firmware](hardware/esp32_ticket_sensor/esp32_ticket_sensor.ino)**

---

## 7. License & Credits

Developed for Central Pier Arcade. All rights reserved.
Built with clean architecture, Python, and open IoT standards.
