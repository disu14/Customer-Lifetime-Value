## Customer Lifetime Value Estimation (Demo)

This folder contains a small Python package (`lifetimes/`) for **customer lifetime value (CLV)** and **repeat-purchase** modeling using standard “buy ’til you die” models (e.g., BG/NBD + Gamma-Gamma).

### What you can do with it

- Build RFM-style features from transaction logs
- Predict expected future purchases per customer
- Estimate customer lifetime value over a chosen horizon

Example dataset: `data/transactions.csv`

### Web app (upload CSV, see results in browser)

**Option A – No extra install (stdlib server)**  
1. From project root, start the server:
   ```bash
   python backend/serve.py
   ```
   Or double‑click **`run_server.bat`** in the project folder.  
2. Open **http://localhost:8000** in your browser. Upload a CSV with columns `customer_id`, `transaction_date`, `monetary_value` and click **Analyze** to get CLV and predictions in a table.

**Option B – With FastAPI (if you have Python 3.11/3.12)**  
1. Install: `pip install -r requirements.txt` and `pip install -r backend/requirements.txt`  
2. Run: `uvicorn backend.app:app --reload`  
3. Open **http://localhost:8000** and use the same upload flow.

### Note on licensing / attribution

This codebase includes components derived from an MIT-licensed upstream project.  
The required license notice is preserved in `LICENSE.txt`.
# Customer-Lifetime-Value-Estimation
