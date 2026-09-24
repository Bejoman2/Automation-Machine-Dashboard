# WIK Automation Machine Dashboard — V10

## V10 focus: CSV Header Auto-Detect + Dropdown Mapping

V10 removes the hard dependency on fixed CSV column names for the production output importer.
The application reads the header of the latest CSV file and lets the engineer select which columns represent:

- **Timestamp Column** — production timestamp
- **Output Result Column** — the final inspection result used for OK/NG counting
- **Crack / Defect Column** — optional field retained in the normalized record
- **OK Value** — the exact value in the Output Result column that is treated as OK

All other CSV columns remain in the source file but are not required by the MVP importer.

### Example source CSV

```csv
DateTime,Model,Inspection,FinalResult,Crack,NG_Code
2026/09/22 07:30:01,A,X,PASS,OK,0
2026/09/22 07:30:02,A,X,FAIL,NG,CRACK
```

The UI can map:

```text
Timestamp Column   = DateTime
Output Result      = FinalResult
Crack / Defect     = Crack
OK Value           = PASS
```

The dashboard then counts `FinalResult=PASS` as OK and every other imported result as NG.

## V10 workflow

```text
Hikrobot CSV folder
        ↓
Read latest CSV header
        ↓
Auto-detect recommended mapping
        ↓
Engineer selects columns from dropdowns
        ↓
Save mapping to SQLite
        ↓
Initial historical import
        ↓
Near-real-time refresh
        ↓
Shift / hourly dashboard
```

## Backend

Stack:
- Python
- FastAPI
- SQLAlchemy
- SQLite
- Native Python CSV parser

Run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

API:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Windows EXE

The repository includes `build_windows.ps1` for:

1. PyInstaller backend EXE
2. React/Vite production build
3. Electron Windows NSIS installer

Run from the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

Installer output:

```text
frontend\release\
```

The packaged application starts the FastAPI backend automatically.

## CSV Source screen

Go to:

```text
MASTER DATA → CSV SOURCE
```

Then:

1. Select final station.
2. Select Hikrobot root folder.
3. Click **TEST CONNECTION + READ HEADER**.
4. Verify the detected header and sample rows.
5. Select **TIMESTAMP COLUMN**.
6. Select **OUTPUT RESULT COLUMN**.
7. Optionally select **CRACK / DEFECT COLUMN**.
8. Enter the value that means OK, e.g. `OK`, `PASS`, or `PASSED`.
9. Click **SAVE MAPPING & SCAN**.

The mapping is stored per CSV source in SQLite.

## V10 data model addition

`csv_column_mappings`:

```text
id
source_id
 timestamp_column
output_column
crack_column
ok_value
```

This is intentionally separated from `station_output_sources`, so an existing V9 database can create the new mapping table without requiring a destructive database reset.

## Important limitation in V10

V10 stores the selected output value in `ProductionRecord.final_result`. It does not yet classify individual NG causes into a master classification table.

The planned next layer is:

```text
NG Code / NG Value
        ↓
NG Classification Master
        ↓
Crack / Missing / Dimension / Leak / Other
        ↓
Pareto + Trend + Shift breakdown
```

That is the intended V11 direction.


## V10.2 packaging note

This build includes `GET /api/csv/headers` for CSV Header Auto-Detect and `GET /api/build-info` for verifying that the packaged backend matches the frontend. If an installed machine returns 404 for `/api/csv/headers`, rebuild the backend and installer from this source; the frontend must not be paired with an older backend EXE.
