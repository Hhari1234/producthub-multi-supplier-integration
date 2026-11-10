# ProductHub Final Demo Guide

## 1. Start the isolated PostgreSQL verification database

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\createdb.exe' -h localhost -p 5433 -U postgres producthub_verify
```

## 2. Start the backend against PostgreSQL

```powershell
Set-Location 'c:\Users\harir\Downloads\yottaflex-hackathon-project\backend'
$env:PYTHONPATH='c:\Users\harir\Downloads\yottaflex-hackathon-project\backend'
$env:DATABASE_URL='postgresql+psycopg://postgres@localhost:5433/producthub_verify'
python -m uvicorn app.main:app --host 0.0.0.0 --port 8123
```

## 3. Start the frontend

```powershell
Set-Location 'c:\Users\harir\Downloads\yottaflex-hackathon-project\frontend'
npm install
npm run dev -- --host 0.0.0.0
```

Open the app in the browser at the Vite port shown in the terminal, typically `http://localhost:4173`.

## 4. Upload the demo datasets

Use the files in `docs/demo-data`:

- `supplier_a_demo.csv` for Supplier A
- `supplier_b_demo.json` for Supplier B
- `supplier_c_demo.csv` for Supplier C

### API upload commands

```powershell
$base = 'http://localhost:8123/api/v1'
$suppliers = Invoke-RestMethod -Uri "$base/suppliers" -Method Get
$supplierA = ($suppliers | Where-Object { $_.supplier_code -eq 'SUPPLIER_A' }).id
$supplierB = ($suppliers | Where-Object { $_.supplier_code -eq 'SUPPLIER_B' }).id
$supplierC = ($suppliers | Where-Object { $_.supplier_code -eq 'SUPPLIER_C' }).id

curl.exe -F "supplier_id=$supplierA" -F "file=@docs/demo-data/supplier_a_demo.csv" "$base/ingestion/upload"
curl.exe -F "supplier_id=$supplierB" -F "file=@docs/demo-data/supplier_b_demo.json" "$base/ingestion/upload"
curl.exe -F "supplier_id=$supplierC" -F "file=@docs/demo-data/supplier_c_demo.csv" "$base/ingestion/upload"
```

## 5. Run the publishing pipeline

```powershell
Invoke-RestMethod -Uri "$base/pipeline/run?supplier_id=$supplierA" -Method Post
Invoke-RestMethod -Uri "$base/pipeline/run?supplier_id=$supplierB" -Method Post
Invoke-RestMethod -Uri "$base/pipeline/run?supplier_id=$supplierC" -Method Post
```

## 6. Expected results

- Overlapping records such as `Alpha Phone`, `Audio Bud`, `Office Chair`, and `Gateway Monitor` match across suppliers.
- Lower valid price wins during conflict resolution.
- Product name and brand are normalized to canonical values.
- Invalid rows are stored as rejects with reasons such as `invalid_price`, `unknown_category`, or `missing_brand`.
- Same-file and repeat uploads are idempotent and do not create duplicate raw rows or products.
- Product traceability includes original source payloads and supplier mapping information.
- Reconciliation totals align with valid and rejected records.

## 7. Verify in the UI

Open the following tabs and confirm the data is populated:

- Dashboard
- Suppliers
- Upload
- Catalogue
- Traceability
- Quality
- Pipeline
- Reports

## 8. Confirmation points

Use these API checks:

```powershell
Invoke-RestMethod -Uri "$base/products" -Method Get
Invoke-RestMethod -Uri "$base/dashboard" -Method Get
Invoke-RestMethod -Uri "$base/quality/rejects" -Method Get
Invoke-RestMethod -Uri "$base/pipeline/runs" -Method Get
Invoke-RestMethod -Uri "$base/reports/reconciliation" -Method Get
```

## 9. Architecture summary for judges

ProductHub ingests supplier data from CSV and JSON feeds, normalizes each row to a canonical schema, validates quality rules, and stores raw source records for traceability. The pipeline then matches records across suppliers using deterministic rules, resolves conflicts such as pricing and stock differences, and publishes a single unified catalogue. Data quality rejects and pipeline history are kept so operators can audit every decision. The backend is built with FastAPI and PostgreSQL, while the frontend is a React dashboard for live operational monitoring.
