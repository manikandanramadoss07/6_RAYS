# Jeeva Setu — Backend

Offline-first biomedical health monitoring backend for rural/underserved areas.
Flask REST API + SQLite. Pairs with the `4.html` frontend built by the team.

## Folder structure

```
jeeva-setu-backend/
├── app.py            # Flask API — all endpoints
├── database.py       # SQLite schema + connection helper
├── risk.py           # Per-parameter risk scoring logic
├── requirements.txt
├── README.md
└── 4.html            # (add your teammate's frontend file here)
```

## Local setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Server runs at `http://localhost:5000`. First run auto-creates `jeeva_setu.db`.

## Key endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/request-otp` | Generate OTP (returned directly in demo mode) |
| POST | `/api/auth/verify-otp` | Verify OTP and log in |
| POST | `/api/patients` | Register a patient |
| GET | `/api/patients` | List all patients |
| GET | `/api/patients/<id>` | Get one patient |
| POST | `/api/parameters` | Record a health reading |
| GET | `/api/patients/<id>/history` | Full reading history |
| GET | `/api/patients/<id>/risk` | Risk score from latest readings |
| POST | `/api/patients/<id>/notes` | Add a doctor's note |
| GET | `/api/patients/<id>/notes` | Get notes |
| POST | `/api/sync` | Batch sync offline-collected data |
| GET | `/api/health` | Health check |

## Testing quickly with curl

```bash
# 1. Request OTP
curl -X POST http://localhost:5000/api/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9999999999"}'

# 2. Verify OTP (use the otp returned above)
curl -X POST http://localhost:5000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9999999999", "otp": "123456"}'

# 3. Register a patient
curl -X POST http://localhost:5000/api/patients \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "P001", "name": "Test Patient", "age": 45, "gender": "F", "village": "Sample Village"}'

# 4. Add a reading
curl -X POST http://localhost:5000/api/parameters \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "P001", "parameter_name": "SPO2", "value": 92, "unit": "%", "date": "2026-08-25", "time": "10:00"}'

# 5. Check risk score
curl http://localhost:5000/api/patients/P001/risk

# 6. Offline sync
curl -X POST http://localhost:5000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"parameters": [{"patient_id": "P001", "parameter_name": "HEART_RATE", "value": 110, "date": "2026-08-25", "time": "11:00"}]}'
```

## Pushing to GitHub

```bash
# from inside the jeeva-setu-backend folder
git init
git add .
git commit -m "Jeeva Setu backend: OTP login, sync API, risk scoring"

# create a new empty repo on github.com first (no README/gitignore), then:
git branch -M main
git remote add origin https://github.com/<your-username>/jeeva-setu.git
git push -u origin main
```

Add a `.gitignore` with at least:
```
venv/
__pycache__/
*.db
```

## Notes

- OTP is returned in the API response only because `DEMO_MODE = True` in `app.py` —
  flip this off and wire up an SMS gateway (Twilio/MSG91) for production.
- Risk score averages a per-parameter risk (0/1/2), not raw parameter values —
  see `risk.py` for the normal ranges used.
- This is a web app (browser + local Flask server), not a native mobile app.
