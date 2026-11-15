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
