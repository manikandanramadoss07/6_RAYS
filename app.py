import random
import string
from datetime import datetime, timedelta

from flask import Flask, request, jsonify

from database import get_connection, init_db
from risk import calculate_risk_score

app = Flask(__name__)

try:
    from flask_cors import CORS
    CORS(app)
except ImportError:
    # flask-cors not installed — fine for local testing with the same-origin
    # setup, but install it (`pip install flask-cors`) if the frontend is
    # served from a different origin/port than the API.
    pass

DEMO_MODE = True  # returns OTP directly in the response for hackathon demo


# ---------------------------------------------------------------
# OTP LOGIN
# ---------------------------------------------------------------

@app.route("/api/auth/request-otp", methods=["POST"])
def request_otp():
    data = request.get_json()
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "phone is required"}), 400

    otp = "".join(random.choices(string.digits, k=6))
    expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()

    conn = get_connection()
    conn.execute(
        "INSERT INTO otp_codes (phone, otp, expires_at) VALUES (?, ?, ?)",
        (phone, otp, expires_at)
    )
    conn.commit()
    conn.close()

    response = {"message": "OTP generated", "expires_in_minutes": 5}
    if DEMO_MODE:
        response["otp"] = otp  # demo only — never do this in production

    return jsonify(response), 200


@app.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    phone = data.get("phone")
    otp = data.get("otp")
    if not phone or not otp:
        return jsonify({"error": "phone and otp are required"}), 400

    conn = get_connection()
    row = conn.execute(
        """SELECT * FROM otp_codes WHERE phone = ? AND otp = ?
           ORDER BY created_at DESC LIMIT 1""",
        (phone, otp)
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Invalid OTP"}), 401

    if datetime.now() > datetime.fromisoformat(row["expires_at"]):
        conn.close()
        return jsonify({"error": "OTP expired"}), 401

    conn.execute("UPDATE otp_codes SET verified = 1 WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()

    return jsonify({"message": "Login successful", "phone": phone}), 200


# ---------------------------------------------------------------
# PATIENTS
# ---------------------------------------------------------------

@app.route("/api/patients", methods=["POST"])
def create_patient():
    data = request.get_json()
    required = ["patient_id", "name"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO patients (patient_id, name, age, gender, phone, village, registered_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data["patient_id"], data["name"], data.get("age"), data.get("gender"),
             data.get("phone"), data.get("village"), data.get("registered_by"))
        )
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400
    conn.close()
    return jsonify({"message": "Patient registered", "patient_id": data["patient_id"]}), 201


@app.route("/api/patients", methods=["GET"])
def list_patients():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM patients ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200


@app.route("/api/patients/<patient_id>", methods=["GET"])
def get_patient(patient_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Patient not found"}), 404
    return jsonify(dict(row)), 200


# ---------------------------------------------------------------
# PARAMETERS (health readings)
# ---------------------------------------------------------------

@app.route("/api/parameters", methods=["POST"])
def add_parameter():
    data = request.get_json()
    required = ["patient_id", "parameter_name", "value", "date", "time"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    conn = get_connection()
    conn.execute(
        """INSERT INTO parameters (patient_id, parameter_name, value, unit, date, time, device_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (data["patient_id"], data["parameter_name"], data["value"], data.get("unit"),
         data["date"], data["time"], data.get("device_id"))
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Parameter recorded"}), 201


@app.route("/api/patients/<patient_id>/history", methods=["GET"])
def get_history(patient_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT parameter_name, value, unit, date, time
           FROM parameters WHERE patient_id = ?
           ORDER BY date DESC, time DESC""",
        (patient_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200


@app.route("/api/patients/<patient_id>/risk", methods=["GET"])
def get_risk(patient_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT parameter_name, value FROM parameters
           WHERE patient_id = ? AND date = (
               SELECT MAX(date) FROM parameters WHERE patient_id = ?
           )""",
        (patient_id, patient_id)
    ).fetchall()
    conn.close()

    if not rows:
        return jsonify({"error": "No readings found for this patient"}), 404

    latest_values = {r["parameter_name"].upper().replace(" ", "_"): r["value"] for r in rows}
    result = calculate_risk_score(latest_values)
    return jsonify(result), 200


# ---------------------------------------------------------------
# NOTES
# ---------------------------------------------------------------

@app.route("/api/patients/<patient_id>/notes", methods=["POST"])
def add_note(patient_id):
    data = request.get_json()
    note = data.get("note")
    if not note:
        return jsonify({"error": "note is required"}), 400

    conn = get_connection()
    conn.execute(
        "INSERT INTO notes (patient_id, note, added_by) VALUES (?, ?, ?)",
        (patient_id, note, data.get("added_by"))
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Note added"}), 201


@app.route("/api/patients/<patient_id>/notes", methods=["GET"])
def get_notes(patient_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notes WHERE patient_id = ? ORDER BY created_at DESC",
        (patient_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200


# ---------------------------------------------------------------
# OFFLINE SYNC — batch upload of locally stored records
# ---------------------------------------------------------------

@app.route("/api/sync", methods=["POST"])
def sync_data():
    """
    Expected body:
    {
      "patients": [ {patient_id, name, age, gender, phone, village, registered_by}, ... ],
      "parameters": [ {patient_id, parameter_name, value, unit, date, time, device_id}, ... ],
      "notes": [ {patient_id, note, added_by}, ... ]
    }
    Each list is optional. Existing patient_ids are skipped (not overwritten).
    """
    data = request.get_json() or {}
    conn = get_connection()
    cur = conn.cursor()

    synced_counts = {"patients": 0, "parameters": 0, "notes": 0, "skipped_patients": 0}

    for p in data.get("patients", []):
        existing = cur.execute(
            "SELECT patient_id FROM patients WHERE patient_id = ?", (p["patient_id"],)
        ).fetchone()
        if existing:
            synced_counts["skipped_patients"] += 1
            continue
        cur.execute(
            """INSERT INTO patients (patient_id, name, age, gender, phone, village, registered_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (p["patient_id"], p["name"], p.get("age"), p.get("gender"),
             p.get("phone"), p.get("village"), p.get("registered_by"))
        )
        synced_counts["patients"] += 1

    for param in data.get("parameters", []):
        cur.execute(
            """INSERT INTO parameters (patient_id, parameter_name, value, unit, date, time, device_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (param["patient_id"], param["parameter_name"], param["value"], param.get("unit"),
             param["date"], param["time"], param.get("device_id"))
        )
        synced_counts["parameters"] += 1

    for n in data.get("notes", []):
        cur.execute(
            "INSERT INTO notes (patient_id, note, added_by) VALUES (?, ?, ?)",
            (n["patient_id"], n["note"], n.get("added_by"))
        )
        synced_counts["notes"] += 1

    conn.commit()
    conn.close()

    return jsonify({"message": "Sync complete", "synced": synced_counts}), 200


# ---------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "Jeeva Setu backend"}), 200


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
