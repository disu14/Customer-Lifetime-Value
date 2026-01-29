"""
FastAPI backend: CSV upload + CLV analysis.
Run from project root: uvicorn backend.app:app --reload
"""
import io
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data
from lifetimes.utils import ConvergenceError

app = FastAPI(title="CLV Analysis API")

# Required CSV columns
REQUIRED_COLS = ["customer_id", "transaction_date", "monetary_value"]


def run_clv_analysis(df: pd.DataFrame) -> dict:
    """Run lifetimes summary + BGF + GGF + CLV. Returns dict for JSON."""
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], dayfirst=True)

    summary = summary_data_from_transaction_data(
        df,
        customer_id_col="customer_id",
        datetime_col="transaction_date",
        monetary_value_col="monetary_value",
        observation_period_end=df["transaction_date"].max(),
    )

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(summary["frequency"], summary["recency"], summary["T"])

    summary["pred_purchases_30d"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        30,
        summary["frequency"],
        summary["recency"],
        summary["T"],
    )

    nonzero = summary[summary["frequency"] > 0].copy()
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(nonzero["frequency"], nonzero["monetary_value"])

    nonzero["clv_12m"] = ggf.customer_lifetime_value(
        bgf,
        nonzero["frequency"],
        nonzero["recency"],
        nonzero["T"],
        nonzero["monetary_value"],
        time=12,
        discount_rate=0.01,
        freq="D",
    )

    # Merge CLV back so all customers appear; CLV NaN for frequency=0
    summary["clv_12m"] = summary.index.map(
        lambda c: nonzero.loc[c, "clv_12m"] if c in nonzero.index else None
    )

    out = summary.reset_index()
    out["customer_id"] = out["customer_id"].astype(str)
    for col in ["pred_purchases_30d", "clv_12m", "monetary_value", "frequency", "recency", "T"]:
        if col in out.columns:
            out[col] = out[col].apply(
                lambda x: round(float(x), 4) if pd.notna(x) and str(x) != "" else None
            )
    records = out.to_dict(orient="records")

    return {
        "rows_uploaded": len(df),
        "customers": len(summary),
        "summary": records,
    }


@app.post("/api/analyze")
async def analyze_csv(file: UploadFile = File(...)):
    """Accept CSV with customer_id, transaction_date, monetary_value. Returns CLV results."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")

    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Could not read file: {e}")

    try:
        df = pd.read_csv(io.BytesIO(raw), parse_dates=["transaction_date"], dayfirst=True)
    except Exception as e:
        raise HTTPException(400, f"Invalid CSV: {e}")

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise HTTPException(
            400,
            f"CSV must have columns: {', '.join(REQUIRED_COLS)}. Missing: {', '.join(missing)}.",
        )

    try:
        result = run_clv_analysis(df)
        return {"ok": True, **result}
    except ConvergenceError as e:
        raise HTTPException(422, f"Model did not converge. Try different data or larger penalizer: {e}")
    except Exception as e:
        raise HTTPException(500, str(e))


# Serve frontend
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
index_file = frontend_path / "index.html"


@app.get("/")
def index():
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not found. Put index.html in frontend/."}
