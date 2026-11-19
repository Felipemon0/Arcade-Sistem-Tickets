import os
import math
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import get_connection, initialize_db

initialize_db()

app = FastAPI(title="Central Pier Arcade — Ticket Inventory")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IOT_API_KEY = os.getenv("IOT_API_KEY", "arcade-iot-dev-key")
REQUIRE_IOT_AUTH = os.getenv("REQUIRE_IOT_AUTH", "false").lower() == "true"


@app.get("/")
def serve_frontend():
    return FileResponse("index.html")


@app.get("/manifest.json")
def serve_manifest():
    return FileResponse("manifest.json", media_type="application/manifest+json")


@app.get("/icon.svg")
def serve_icon_svg():
    return FileResponse("icon.svg", media_type="image/svg+xml")


@app.get("/icon-192.png")
def serve_icon_192():
    return FileResponse("icon-192.png", media_type="image/png")


@app.get("/icon-512.png")
def serve_icon_512():
    return FileResponse("icon-512.png", media_type="image/png")


@app.get("/apple-touch-icon.png")
def serve_apple_touch_icon():
    return FileResponse("apple-touch-icon.png", media_type="image/png")


class MovementInput(BaseModel):
    amount: float


class CountInput(BaseModel):
    new_in_use: float


class StorageInput(BaseModel):
    boxes: int
    blocks_per_box: float = 50.0


class SensorAlertInput(BaseModel):
    machine_id: int
    low_stock: bool
    sensor_node: str


@app.get("/api/dashboard")
def get_dashboard():
    conn = get_connection()
    machine_rows = conn.execute("SELECT * FROM machines ORDER BY id ASC").fetchall()
    storage = conn.execute("SELECT * FROM storage WHERE id = 1").fetchone()
    logs = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 15").fetchall()
    conn.close()

    machines = []
    total_in_use = 0.0
    total_reserve = 0.0
    active_alerts = 0

    for m in machine_rows:
        percentage = round((m["in_use"] / m["max_capacity"]) * 100, 1)
        needs_refill = percentage <= 35.0
        if needs_refill:
            active_alerts += 1

        total_in_use += m["in_use"]
        total_reserve += m["reserve"]

        machines.append({
            "id": m["id"],
            "name": m["name"],
            "in_use": round(m["in_use"], 2),
            "reserve": round(m["reserve"], 2),
            "max_capacity": m["max_capacity"],
            "percentage": percentage,
            "alert": needs_refill
        })

    storage_blocks = round(storage["storage_blocks"], 2)
    total_blocks = round(total_in_use + total_reserve + storage_blocks, 2)
    total_tickets = int(round(total_blocks * 2000))

    return {
        "kpis": {
            "total_blocks": total_blocks,
            "total_tickets": total_tickets,
            "in_use": round(total_in_use, 2),
            "reserve": round(total_reserve, 2),
            "storage_blocks": storage_blocks,
            "storage_boxes": storage["storage_boxes"],
            "active_alerts": active_alerts,
            "total_units": len(machines)
        },
        "machines": machines,
        "logs": [dict(log) for log in logs]
    }


@app.post("/api/machines/{machine_id}/refill")
def refill_machine(machine_id: int, data: MovementInput):
    conn = get_connection()
    machine = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()

    if not machine:
        conn.close()
        raise HTTPException(status_code=404, detail="Machine not found")

    if data.amount <= 0 or data.amount > machine["reserve"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient blocks in floor reserve")

    new_in_use = round(machine["in_use"] + data.amount, 2)
    new_reserve = round(machine["reserve"] - data.amount, 2)
    now = datetime.now().strftime("%b %d, %H:%M")

    conn.execute(
        "UPDATE machines SET in_use = ?, reserve = ? WHERE id = ?",
        (new_in_use, new_reserve, machine_id)
    )
    conn.execute(
        "INSERT INTO audit_log (machine_name, action, amount, timestamp) VALUES (?, ?, ?, ?)",
        (machine["name"], "Refilled from reserve", round(data.amount, 2), now)
    )
    conn.commit()
    conn.close()

    return {"message": f"Refilled +{data.amount} blq into {machine['name']}"}


@app.post("/api/machines/{machine_id}/count")
def update_physical_count(machine_id: int, data: CountInput):
    conn = get_connection()
    machine = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()

    if not machine:
        conn.close()
        raise HTTPException(status_code=404, detail="Machine not found")

    if data.new_in_use < 0 or data.new_in_use > machine["max_capacity"]:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Value must be between 0 and {machine['max_capacity']}")

    delta = round(data.new_in_use - machine["in_use"], 2)
    now = datetime.now().strftime("%b %d, %H:%M")

    conn.execute("UPDATE machines SET in_use = ? WHERE id = ?", (round(data.new_in_use, 2), machine_id))
    conn.execute(
        "INSERT INTO audit_log (machine_name, action, amount, timestamp) VALUES (?, ?, ?, ?)",
        (machine["name"], f"Count updated ({delta:+} blq)", round(data.new_in_use, 2), now)
    )
    conn.commit()
    conn.close()

    return {"message": f"Updated {machine['name']} to {data.new_in_use} blq"}


@app.post("/api/machines/{machine_id}/restock-reserve")
def restock_reserve(machine_id: int, data: MovementInput):
    conn = get_connection()
    machine = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    storage = conn.execute("SELECT * FROM storage WHERE id = 1").fetchone()

    if not machine:
        conn.close()
        raise HTTPException(status_code=404, detail="Machine not found")

    if data.amount <= 0 or data.amount > storage["storage_blocks"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient blocks in storage")

    new_reserve = round(machine["reserve"] + data.amount, 2)
    new_storage_blocks = round(storage["storage_blocks"] - data.amount, 2)
    new_storage_boxes = math.ceil(new_storage_blocks / 50.0) if new_storage_blocks > 0 else 0
    now = datetime.now().strftime("%b %d, %H:%M")

    conn.execute("UPDATE machines SET reserve = ? WHERE id = ?", (new_reserve, machine_id))
    conn.execute(
        "UPDATE storage SET storage_blocks = ?, storage_boxes = ? WHERE id = 1",
        (new_storage_blocks, new_storage_boxes)
    )
    conn.execute(
        "INSERT INTO audit_log (machine_name, action, amount, timestamp) VALUES (?, ?, ?, ?)",
        (machine["name"], "Storage → Floor reserve", round(data.amount, 2), now)
    )
    conn.commit()
    conn.close()

    return {"message": f"Moved +{data.amount} blq from storage to {machine['name']} reserve"}


@app.post("/api/storage/add-boxes")
def add_storage_boxes(data: StorageInput):
    if data.boxes <= 0:
        raise HTTPException(status_code=400, detail="Enter at least 1 box")

    added_blocks = round(data.boxes * data.blocks_per_box, 2)
    now = datetime.now().strftime("%b %d, %H:%M")

    conn = get_connection()
    storage = conn.execute("SELECT * FROM storage WHERE id = 1").fetchone()
    new_blocks = round(storage["storage_blocks"] + added_blocks, 2)
    new_boxes = storage["storage_boxes"] + data.boxes

    conn.execute(
        "UPDATE storage SET storage_blocks = ?, storage_boxes = ? WHERE id = 1",
        (new_blocks, new_boxes)
    )
    conn.execute(
        "INSERT INTO audit_log (machine_name, action, amount, timestamp) VALUES (?, ?, ?, ?)",
        ("Central Storage", f"Added {data.boxes} box(es)", added_blocks, now)
    )
    conn.commit()
    conn.close()

    return {"message": f"Added {data.boxes} box(es) (+{added_blocks} blq) to storage"}


@app.post("/api/iot/sensor-alert")
def receive_sensor_alert(
    data: SensorAlertInput,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    # Optional X-API-Key header verification
    if REQUIRE_IOT_AUTH and not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    if x_api_key is not None and x_api_key != IOT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    conn = get_connection()
    machine = conn.execute("SELECT * FROM machines WHERE id = ?", (data.machine_id,)).fetchone()

    if not machine:
        conn.close()
        raise HTTPException(status_code=404, detail="Machine not found")

    current_in_use = machine["in_use"]
    max_capacity = machine["max_capacity"]
    threshold = round(max_capacity * 0.35, 2)
    low_stock_triggered = False

    if data.low_stock:
        # If in_use is above the 35% threshold, update in_use to round(max_capacity * 0.30, 2)
        if current_in_use > threshold:
            new_in_use = round(max_capacity * 0.30, 2)
            now = datetime.now().strftime("%b %d, %H:%M")

            conn.execute(
                "UPDATE machines SET in_use = ? WHERE id = ?",
                (new_in_use, data.machine_id)
            )
            conn.execute(
                "INSERT INTO audit_log (machine_name, action, amount, timestamp) VALUES (?, ?, ?, ?)",
                (machine["name"], "IoT Sensor: Low ticket threshold reached", new_in_use, now)
            )
            conn.commit()
            low_stock_triggered = True
            current_in_use = new_in_use

    conn.close()

    message = (
        f"Low stock triggered for {machine['name']} (set to {current_in_use} blq)"
        if low_stock_triggered
        else f"Sensor alert acknowledged for {machine['name']} (node: {data.sensor_node})"
    )

    return {
        "status": "success",
        "machine_id": data.machine_id,
        "machine_name": machine["name"],
        "sensor_node": data.sensor_node,
        "low_stock": data.low_stock,
        "low_stock_triggered": low_stock_triggered,
        "in_use": current_in_use,
        "message": message
    }
