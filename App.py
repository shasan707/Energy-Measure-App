import os
import csv
import sqlite3
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler
from tuya_device import get_device_status, turn_on, turn_off
import pandas as pd

app = Flask(__name__)
DB = 'energy.db'
CSV = 'energy.csv'
COST_RATE = 8.5  # BDT per kWh

def init_storage():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        ts TEXT PRIMARY KEY,
        power REAL,
        current REAL,
        voltage REAL,
        kwh REAL
    )
    """)
    conn.commit()
    conn.close()
    print("Database initialized and table 'readings' created if not exists.")

    if not os.path.exists(CSV):
        with open(CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ts', 'power', 'current', 'voltage', 'kwh'])
    init_storage()

def record_reading():
    status = get_device_status()
    

    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    kwh = status["power"] * (1/60) / 1000.0
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO readings (ts,power,current,voltage,kwh) VALUES (?,?,?,?,?)",
        (ts, status["power"], status["current"], status["voltage"], kwh)
    )
    conn.commit()
    conn.close()

    with open(CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([ts, status["power"], status["current"], status["voltage"], kwh])

scheduler = BackgroundScheduler()
scheduler.add_job(record_reading, 'interval', minutes=1, next_run_time=datetime.utcnow())
scheduler.start()

@app.route("/")
def dashboard():
    return render_template("dashboard.html", today=datetime.utcnow().date().isoformat())

@app.route("/manual")
def manual():
    return render_template("manual.html")

@app.route("/status")
def api_status():
    return jsonify(get_device_status())

@app.route("/summary")
def summary():
    # Determine start/end ISO strings
    start = request.args.get("start")
    end = request.args.get("end")
    if not (start and end):
        # day mode
        d = request.args.get("date") or datetime.utcnow().date().isoformat()
        start = f"{d}T00:00:00"
        end = f"{d}T23:59:59"

    # Query SQLite directly
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # 1) total rows & kWh sum
    c.execute(
        "SELECT COUNT(*), COALESCE(SUM(kwh),0) FROM readings WHERE ts BETWEEN ? AND ?",
        (start, end)
    )
    row_count, total_kwh = c.fetchone()

    # 2) hourly kWh sums
    c.execute("""
    SELECT SUBSTR(ts,12,2) AS hour, COALESCE(SUM(kwh),0)
    FROM readings
    WHERE ts BETWEEN ? AND ?
    GROUP BY hour
    """, (start, end))
    rows = c.fetchall()
    conn.close()

    # Build full 24-hour trend
    hourly_map = {int(hr): kw for hr, kw in rows}
    trend = [{"hour": h, "kwh": round(hourly_map.get(h, 0), 3)} for h in range(24)]
    cost = total_kwh * COST_RATE

    # (Optional) print for debugging
    print(f"[SUMMARY] {start} → {end}: {row_count} rows, {total_kwh:.3f} kWh")

    return jsonify(kwh=round(total_kwh, 3), cost=round(cost, 2), trend=trend)

@app.route("/history")
def api_history():
    start = request.args.get("start")
    end = request.args.get("end")
    if not (start and end):
        d = request.args.get("date") or datetime.utcnow().date().isoformat()
        start = f"{d}T00:00:00"
        end = f"{d}T23:59:59"
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    SELECT ts, power, current, voltage, kwh
    FROM readings
    WHERE ts BETWEEN ? AND ?
    ORDER BY ts
    """, (start, end))
    rows = c.fetchall()
    conn.close()

    return jsonify([{"ts": ts, "power": p, "current": i, "voltage": v, "kwh": k} for ts, p, i, v, k in rows])

@app.route("/download")
def download_csv():
    return send_file(CSV,
                     mimetype="text/csv",
                     as_attachment=True,
                     download_name="energy_readings.csv")

@app.route("/on")
def power_on():
    turn_on()
    return ("", 204)

@app.route("/off")
def power_off():
    turn_off()
    return ("", 204)

@app.route("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    
    port = int(os.getenv("PORT", 3000))
    # enable debug to see full tracebacks
    app.run(host="0.0.0.0", port=port, debug=True)
