# Product API Sprint - Day 1

## Setup

Use Python 3.12.3 or another supported stable Python release.

From the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
```

## Run from backend/

```powershell
python -m uvicorn main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Test from backend/

```powershell
python -m pytest -q
```

## API Features

- Create products.
- Retrieve a product by ID.
- List and filter products.
- Update product details.
- Delete products.
- View product summary.
- Find products with low stock.

## Scope

Local, unauthenticated, single-worker, in-memory catalog.

Restart clears records. No database, auth or payment integration yet.

Price/filter amounts use integer minor units of one chosen currency.

## Evidence

See docs/day01.md for checks, defects, explanations and actual time.

# Persistent Product API - Day 2

## Requirements

Python 3.12+, Git and the packages in backend/requirements.txt.
SQLite is accessed through Python's standard-library sqlite3 module.

## Setup from the repository root

cd backend
Create .venv with py -3 -m venv .venv on Windows,
or python3 -m venv .venv on macOS/Linux.
Activate with .\.venv\Scripts\Activate.ps1 in PowerShell,
or source .venv/bin/activate in bash/zsh.
python -m pip install -r requirements.txt

## Run from backend/

python -m uvicorn main:app --reload
Open http://127.0.0.1:8000/docs
Default database: backend/data/catalog.sqlite3
Optional CATALOG_DB selects a different file before startup.

## Verify from backend/

python -m pytest -q
python sql_lab.py
Create a product, restart the server and fetch its saved ID.
Try a batch with a duplicate; confirm no partial rows remain.

## Scope

Local, unauthenticated SQL/persistence exercise.
Initialization creates missing tables; it is not a migration system.
The final e-commerce rebuild still targets Firebase/Firestore.
