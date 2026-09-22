# Automation Machine Dashboard — MVP

Stack:
- Backend: Python + FastAPI + SQLAlchemy + SQLite
- Frontend: React + Vite + Recharts
- Data source: CSV from final inspection station
- UI: dark WIK-style technical dashboard

## Features
- CSV ingestion from configurable folder
- SQLite cache of production records
- Shift summary: OK / NG / Total / Achievement
- Hourly breakdown chart + table
- CRUD: Shift, Target, Station, Station Output Source, Manual Correction
- Manual refresh
- Dark technical UI
- API docs at `/docs`

## CSV format

```csv
Time,Crack,Result
2026/09/21 07:00:07,OK,OK
2026/09/21 07:00:17,OK,OK
2026/09/21 07:00:27,NG,NG
```

## Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Backend:
http://127.0.0.1:8000

## Run frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:
http://127.0.0.1:5173

## Configuration

Backend reads:

`backend/.env`

Example:

```env
DATABASE_URL=sqlite:///./dashboard.db
CSV_FOLDER=./data
CORS_ORIGINS=http://127.0.0.1:5173
```

For a network folder on Windows:

```env
CSV_FOLDER=\\\\SERVER\\Production\\FinalInspection
```

or a local path:

```env
CSV_FOLDER=D:\\ProductionData\\FinalInspection
```

## Important MVP assumption

Output is based on the final station CSV. The MVP does not calculate station-level CT/bottleneck and does not connect directly to PLC/Modbus.

## Default shift

- Shift 1: 07:00–17:00
- Shift 2: 17:00–03:00

The shift engine supports overnight shifts.


## Select CSV from Windows File Explorer

The dashboard now has a **SELECT CSV** button in the top-right header.

Workflow:

1. Start FastAPI.
2. Start React/Vite.
3. Open the dashboard.
4. Click `▣ SELECT CSV`.
5. Windows File Explorer opens.
6. Select the real Hikrobot CSV.
7. The CSV is uploaded to FastAPI and imported into SQLite.
8. The dashboard refreshes its summary.

The browser does not need direct access to the machine's CSV folder. This is useful when the CSV is stored somewhere on the PC/network and the engineer wants to select a specific file manually.

The original `REFRESH FOLDER` button remains available for the configured backend CSV folder.


### CSV selection behavior

When a CSV is selected, the backend returns the minimum/maximum timestamp found in that file. The dashboard automatically changes its date filter to the CSV's data date, so a valid imported file does not appear unchanged simply because the dashboard was still filtered to another date.


## CSV Folder Source

Normal operation can use a configured local or network folder instead of selecting individual CSV files.

1. Open **CSV SOURCE**.
2. Select the final station.
3. Enter a folder path such as:
   - `D:\Hikrobot\ProductionData`
   - `\\SERVER\Production\FinalInspection`
4. Click **TEST CONNECTION**.
5. Click **SAVE & SCAN**.
6. The backend scans all `*.csv` files and imports new records into SQLite.
7. Use **REFRESH DATA** after new CSV data is generated.

Manual **SELECT CSV** remains available in the header for troubleshooting and one-off imports.

## Desktop folder picker (v5)
The frontend now includes an Electron desktop shell. Use the native Windows **SELECT FOLDER** button to choose the Hikrobot CSV directory without typing the path. The selected Windows path is sent to FastAPI and stored in `StationOutputSource` when you click **SAVE & SCAN**.

### Run
1. Start backend:
```powershell
cd "C:\path\to\automation_machine_dashboard\backend"
.\.venv\Scripts\Activate.ps1
python run.py
```
2. In another terminal, install frontend dependencies once:
```powershell
cd "C:\path\to\automation_machine_dashboard\frontend"
npm install
```
3. Start desktop app:
```powershell
npm run desktop
```

For development with Vite hot reload + Electron:
```powershell
npm run desktop:dev
```

The web browser mode remains available with `npm run dev`, but the native Windows folder picker is intended for the desktop version.


### Electron fix v5.1
The Vite build uses a relative base path (`./`) so the packaged Electron app can load React assets correctly from `dist/index.html`.

### Hikrobot recursive CSV source
The CSV Source folder should point to the Hikrobot raw-data root, for example:
`...\09. Log file\00. All Raw data`

The backend recursively scans `*.csv` under that folder, including date folders such as `20260729`, `20260730`, etc. The dashboard uses the `Time`/`Timestamp` column from each CSV record for shift/date calculations.


### Adjustable near-real-time refresh

The Dashboard header has a LIVE refresh selector: OFF, 1s, 2s, 5s, 10s, 30s, or 60s. The selected value is stored locally on the PC. The live refresh endpoint scans only the selected Hikrobot YYYYMMDD folder and the following date folder, so the dashboard does not rescan the entire historical archive every few seconds. The following date is included to support overnight shifts.

## v8 — Non-blocking CSV import
`SAVE & SCAN` now starts the historical import as a background job. The CSV Source screen polls the job status and shows CSV progress, current file, imported records, and a final `IMPORT COMPLETE` state. The importer also loads the existing source keys once instead of querying the whole ProductionRecord table for every CSV file, reducing the cost of importing many historical files.
