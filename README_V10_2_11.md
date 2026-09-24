# V10.2.11 — V10.2 Baseline + PID Termination

Baseline: V10.2 backend-sync project.

Only change from V10.2 baseline: Electron backend shutdown now terminates the exact spawned backend PID/process tree on Windows using `taskkill /PID <pid> /T /F`.

No CSV Source UI, mapping, SQLite, dashboard, or import behavior is intentionally changed in this version.

This does NOT scan/kill arbitrary processes or clean port 8000 at startup.
