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

## Background: Lifetimes project status

This demo relies on the ideas and APIs popularized by the "lifetimes" library. The upstream project has moved to maintenance/archived mode, so new features are unlikely there. A successor project in this space is often cited as PyMC‑Marketing; consider exploring it if you need more advanced Bayesian/marketing modeling.

## Introduction

Lifetimes-style models analyze users under a few assumptions:

- Users interact with you when they are "alive".
- Users may "die" (churn) after some period of time.

These terms are abstract: use your own definitions of "alive" and "die" (similar to survival analysis). Whenever individuals repeat occurrences (purchases, logins, visits), these models help understand behavior.

## Applications

- Predict how often a visitor will return to your website. (Alive = visiting; Die = stops visiting)
- Understand how frequently a patient may return to a hospital. (Alive = visiting; Die = moved away, etc.)
- Detect churn from an app using only usage history. (Alive = logins; Die = removed the app)
- Predict repeat purchases. (Alive = actively purchasing; Die = disinterested)
- Estimate the lifetime value of your customers.

## Specific application: Customer Lifetime Value (CLV)

As emphasized by Peter Fader and Bruce Hardie, understanding and acting on CLV is critical. This demo computes 30‑day expected purchases and 12‑month CLV using BG/NBD + Gamma‑Gamma.

## Documentation and tutorials

- Official lifetimes documentation: http://lifetimes.readthedocs.io/en/latest/

## Main articles

- "Counting Your Customers: Who Are They and What Will They Do Next?" (Schmittlein, Morrison, Colombo)
- "“Counting Your Customers” the Easy Way: An Alternative to the Pareto/NBD Model" (Fader, Hardie, Lee)

## More information

- Roberto Medri’s CLV talk at Etsy (O’Reilly Strata link)
- Bruce Hardie’s website and notes (derivations and practical guidance)
- R implementation: BTYD (Buy ’Til You Die)
