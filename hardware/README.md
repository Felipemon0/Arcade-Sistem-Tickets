# Hardware Architecture & Wiring Guide — IoT Ticket Sensor Node

This directory contains the firmware, wiring schematics, and Bill of Materials (BOM) for the **Central Pier Arcade IoT Ticket Monitoring Node**. 

Each hardware node is driven by a single **ESP32 microcontroller** that monitors an island of **6 arcade machines** in real time using **FC-51 Infrared Proximity Sensors**. When a machine's ticket stack drops below ~30% capacity, the node debounces the signal and automatically notifies the central FastAPI inventory server over Wi-Fi.

---

## 1. System Architecture & Principle of Operation

```
+---------------------------------------------------------------------------------------+
|                                ARCADE 6-MACHINE ISLAND                                |
|                                                                                       |
|  [Machine 1]  [Machine 2]  [Machine 3]  [Machine 4]  [Machine 5]  [Machine 6]         |
|  [FC-51 IR]   [FC-51 IR]   [FC-51 IR]   [FC-51 IR]   [FC-51 IR]   [FC-51 IR]          |
|      |            |            |            |            |            |               |
|   GPIO 13      GPIO 12      GPIO 14      GPIO 27      GPIO 26      GPIO 25            |
|      \            \            \            /            /            /               |
|       +--------------------------------------------------------------+                |
|                                       |                                               |
|                       +-------------------------------+                               |
|                       |        ESP32 Controller       |                               |
|                       |   (5s Non-Blocking Debounce)  |                               |
|                       +---------------+---------------+                               |
|                                       | 2.4 GHz Wi-Fi (WPA2)                          |
+---------------------------------------|-----------------------------------------------+
                                        v
                    +---------------------------------------+
                    |        FastAPI Inventory Backend      |
                    |   POST /api/iot/sensor-alert          |
                    +---------------------------------------+
```

### Optical Sensing Mechanics
1. **Hopper Geometry**: Standard arcade ticket hoppers (e.g., Deltronic Labs DL-1275 / Happ Controls) hold fan-folded ticket blocks vertically or accordion-stacked.
2. **Mounting Location**: The FC-51 sensor is fixed to the inner hopper side bracket at approximately **1.5 to 2.0 inches above the lower feed roller**, which corresponds precisely to **~30% remaining block capacity**.
3. **Detection Logic (Active-Low)**:
   - **Normal Level (Tickets Present)**: The IR emitter beam reflects off the side of the ticket paper into the phototransistor receiver. The comparator output (`OUT`) pulls **LOW (0V)**, and the onboard sensor LED illuminates.
   - **Low Stock (Tickets Depleted Below Line)**: When tickets drop below the sensor line, the beam shoots across into open space or a non-reflective matte backplate. The comparator output (`OUT`) swings **HIGH (3.3V)**, and the onboard LED turns OFF.
4. **5-Second Debounce Filter**:
   - As tickets are dispensed during payout, ticket paper shifts, vibrates, and flutters.
   - The ESP32 firmware requires the `HIGH` state to persist continuously for **5,000 ms (`DEBOUNCE_DELAY_MS`)** without interruption before confirming a `LOW STOCK` state transition.
   - This eliminates 100% of false alarms caused by mechanical motion, paper vibration, or brief manual adjustments.

---

## 2. Power Architecture (12V to 5V Step-Down)

Arcade cabinets universally supply a regulated `+12V DC` rail (typically from a standard arcade switching power supply or JAMMA harness). To avoid requiring an external AC wall adapter for each island, the IoT node taps the internal `+12V DC` rail of the host machine and steps it down via an adjustable DC-DC buck converter.

```
 Cabinet 12V DC Rail (+) ----+
                             |
                   +---------v---------+
                   |  DC-DC Step-Down  |
                   |   Buck Converter  |-----> +5.0V Regulated -----> ESP32 5V (VIN) Pin
                   |  (LM2596 / MP1584)|                       +----> 6x FC-51 VCC Pins
                   +---------+---------+
                             |
 Cabinet Common GND  (-) ----+-------------------------------> Common GND
                                                               +----> ESP32 GND Pin
                                                               +----> 6x FC-51 GND Pins
```

> **Safety & Voltage Level Notice**:
> - The FC-51 sensor modules operate safely at **3.3V to 5.0V DC**. Powering them directly from the ESP32 `3.3V` regulated pin or using 3.3V-compatible pull-ups ensures the digital output signals (`OUT`) never exceed the ESP32's maximum GPIO tolerance (3.3V).
> - Set the LM2596 buck converter trimpot to output exactly **`5.05V DC`** before connecting the ESP32 `VIN` pin.

---

## 3. Comprehensive ASCII Wiring Diagram

```
                              +--------------------+
                              |  LM2596 BUCK CONV. |
      Cabinet +12V DC ------->| IN+           OUT+ |---> +5.0V Rail
      Cabinet 0V (GND) ------>| IN-           OUT- |---> System GND Rail
                              +--------------------+
                                      |         |
                                      |         |
             +------------------------+         +--------------------------+
             |                                                             |
             v                                                             v
       +------------+                                               +-------------+
       | ESP32 VIN  |                                               | FC-51 #1..#6|
       | ESP32 GND  |                                               | VCC & GND   |
       +------------+                                               +-------------+

===================================================================================
                       ESP32 PIN CONNECTIONS (NodeMCU-32S)
===================================================================================

    [POWER]
    +5.0V Buck Rail  ---------------> ESP32 VIN (Pin 19 / 5V)
    Common GND       ---------------> ESP32 GND (Pin 14)

    [SENSORS: GPIO INPUTS WITH INTERNAL PULL-UPS]
    FC-51 #1 (Machine 1: Spindependence 1) OUT ---> GPIO 13
    FC-51 #2 (Machine 2: Spindependence 2) OUT ---> GPIO 12
    FC-51 #3 (Machine 3: Spindependence 3) OUT ---> GPIO 14
    FC-51 #4 (Machine 4: Spindependence 5) OUT ---> GPIO 27
    FC-51 #5 (Machine 5: Spindependence 4) OUT ---> GPIO 26
    FC-51 #6 (Machine 6: Plinko 1)         OUT ---> GPIO 25

    [COMMON SENSOR POWER BUS]
    ESP32 3V3 (or 5V) Pin ---------> Sensor Bus VCC (Red wire to all 6 FC-51s)
    ESP32 GND             ---------> Sensor Bus GND (Black wire to all 6 FC-51s)
```

### Pin Assignment Table

| Channel | Arcade Machine Target | ESP32 GPIO | Pin Mode | Logic Function |
| :---: | :--- | :---: | :---: | :--- |
| **CH 0** | Spindependence 1 (ID: 1) | `GPIO 13` | `INPUT_PULLUP` | Active-Low (`0` = OK, `1` = Low Stock) |
| **CH 1** | Spindependence 2 (ID: 2) | `GPIO 12` | `INPUT_PULLUP` | Active-Low (`0` = OK, `1` = Low Stock) |
| **CH 2** | Spindependence 3 (ID: 3) | `GPIO 14` | `INPUT_PULLUP` | Active-Low (`0` = OK, `1` = Low Stock) |
| **CH 3** | Spindependence 5 (ID: 4) | `GPIO 27` | `INPUT_PULLUP` | Active-Low (`0` = OK, `1` = Low Stock) |
| **CH 4** | Spindependence 4 (ID: 5) | `GPIO 26` | `INPUT_PULLUP` | Active-Low (`0` = OK, `1` = Low Stock) |
| **CH 5** | Plinko 1 (ID: 6)         | `GPIO 25` | `INPUT_PULLUP` | Active-Low (`0` = OK, `1` = Low Stock) |

---

## 4. Bill of Materials (BOM) & Cost Breakdown

The hardware architecture uses readily available, industrial-grade commercial-off-the-shelf (COTS) components to keep deployment costs under **$5 USD per arcade machine**.

### A. 6-Machine Pilot Node (1 Island)

| Item | Component Description | Qty | Unit Cost (USD) | Total Cost (USD) |
| :--- | :--- | :---: | :---: | :---: |
| 1 | **ESP32 DevKit v1 / NodeMCU-32S** (Dual Core, 2.4 GHz Wi-Fi/BLE) | 1 | $4.50 | $4.50 |
| 2 | **FC-51 Infrared Obstacle Proximity Modules** (LM393 Comparator) | 6 | $0.85 | $5.10 |
| 3 | **LM2596 / MP1584 DC-DC Step-Down Buck Converter** (12V to 5V) | 1 | $1.60 | $1.60 |
| 4 | **22 AWG 3-Conductor Shielded Cable** (Harness runs, ~18m total) | 1 | $10.00 | $10.00 |
| 5 | **Custom 3D Printed Hopper Brackets** (Black PETG, 6 units) | 6 | $0.50 | $3.00 |
| 6 | **ABS Enclosure Box & Screw Terminal Blocks** | 1 | $4.00 | $4.00 |
| **TOTAL** | **Single 6-Machine Pilot Node** | — | — | **$28.20 USD** |
| *Per Machine* | *Pilot cost per monitored arcade unit* | — | — | **$4.70 USD** |

---

### B. Full Floor Rollout — 70 Machines (12 ESP32 Nodes)

To cover all 70 machines across the arcade floor, the floor is partitioned into **11 islands of 6 machines** plus **1 island of 4 machines** (12 ESP32 nodes total):

| Item | Component Description | Bulk Qty | Unit Cost (USD) | Total Cost (USD) |
| :--- | :--- | :---: | :---: | :---: |
| 1 | **ESP32 DevKit v1 Boards** (Bulk pack of 12) | 12 | $4.00 | $48.00 |
| 2 | **FC-51 IR Sensor Modules** (Bulk pack of 72 including spares) | 72 | $0.75 | $54.00 |
| 3 | **DC-DC Buck Step-Down Converters** (Bulk pack of 12) | 12 | $1.50 | $18.00 |
| 4 | **22 AWG 3-Conductor Shielded Wire** (250-meter bulk spool) | 1 | $85.00 | $85.00 |
| 5 | **3D Printed PETG Hopper Mounting Brackets** (70 units) | 70 | $0.40 | $28.00 |
| 6 | **Junction Enclosures & 6-Way Terminal Barrier Strips** | 12 | $3.75 | $45.00 |
| 7 | **Harness Accessories** (Heat shrink, zip ties, ferrules, spade lugs) | 1 | $25.00 | $25.00 |
| 8 | **Spare Buffer Modules** (2x ESP32, 5x FC-51 sensors) | 1 | $30.00 | $30.00 |
| **TOTAL** | **Full 70-Machine Floor Rollout (12 Nodes)** | — | — | **$333.00 USD** |
| *Per Machine* | *Comprehensive cost per monitored machine* | — | — | **$4.75 USD** |

---

## 5. Sensor Calibration & Optical Interference Mitigation

### Potentiometer Calibration Procedure
1. Mount the FC-51 module in the ticket hopper bracket with the hopper empty.
2. Power the module with 3.3V or 5V.
3. Turn the onboard 10k multi-turn trimpot **counter-clockwise** until the output LED `D0` turns completely OFF.
4. Insert a stack of 1 block of redemption tickets into the hopper in front of the sensor (at a distance of approximately **15 mm to 25 mm**).
5. Turn the trimpot slowly **clockwise** until the `D0` indicator LED turns solid ON (reflecting off the ticket surface).
6. Remove the tickets and verify that the `D0` LED immediately turns OFF. Repeat 3 times to ensure repeatability.

### Ambient Light Immunity in Arcade Environments
Arcade floors feature high-intensity LED light strips, strobes, and neon marquees:
- **Optical Shroud**: The 3D-printed PETG bracket includes a **10 mm tubular shroud** around the receiver phototransistor to block stray oblique ambient light.
- **Hopper Enclosure**: Since ticket hoppers are located inside the lower locked metal/wooden cabinet door, ambient light levels are naturally attenuated.
- **Hysteresis & Debounce**: The firmware's 5-second hysteresis window ensures that momentary reflections or human hands during customer play never cause erroneous low-stock triggers.

---

## 6. Testing the IoT Endpoint Directly

You can simulate sensor trigger events from a laptop or terminal using `curl`:

```bash
# 1. Trigger Low Stock on Machine 1 (Spindependence 1)
curl -X POST http://localhost:8000/api/iot/sensor-alert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: arcade-iot-dev-key" \
  -d '{"machine_id": 1, "low_stock": true, "sensor_node": "esp32-island-01"}'

# 2. Normal Stock Restored Acknowledgement
curl -X POST http://localhost:8000/api/iot/sensor-alert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: arcade-iot-dev-key" \
  -d '{"machine_id": 1, "low_stock": false, "sensor_node": "esp32-island-01"}'
```
