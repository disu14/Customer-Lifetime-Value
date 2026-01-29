"""
Flask backend: CSV upload + CLV analysis.
Run from project root: python -m flask --app backend.app_flask run --port 8000
"""
import io
from pathlib import Path

import pandas as pd
from flask import Flask, request, jsonify, send_file

from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data
from lifetimes.utils import ConvergenceError

app = Flask(__name__, static_folder=None)

REQUIRED_COLS = ["customer_id", "transaction_date", "monetary_value"]


def run_clv_analysis(df: pd.DataFrame) -> dict:
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
        30, summary["frequency"], summary["recency"], summary["T"],
    )

    nonzero = summary[summary["frequency"] > 0].copy()
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(nonzero["frequency"], nonzero["monetary_value"])

    nonzero["clv_12m"] = ggf.customer_lifetime_value(
        bgf, nonzero["frequency"], nonzero["recency"], nonzero["T"],
        nonzero["monetary_value"], time=12, discount_rate=0.01, freq="D",
    )

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
    return {"rows_uploaded": len(df), "customers": len(summary), "summary": records}


@app.route("/api/analyze", methods=["POST"])
def analyze_csv():
    if "file" not in request.files:
        return jsonify({"detail": "No file part"}), 400
    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".csv"):
        return jsonify({"detail": "Please upload a CSV file."}), 400
    try:
        raw = file.read()
        df = pd.read_csv(io.BytesIO(raw), parse_dates=["transaction_date"], dayfirst=True)
    except Exception as e:
        return jsonify({"detail": f"Invalid CSV: {e}"}), 400
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        return jsonify({"detail": f"CSV must have columns: {', '.join(REQUIRED_COLS)}. Missing: {', '.join(missing)}."}), 400
    try:
        result = run_clv_analysis(df)
        return jsonify({"ok": True, **result})
    except ConvergenceError as e:
        return jsonify({"detail": str(e)}), 422
    except Exception as e:
        return jsonify({"detail": str(e)}), 500


_frontend = Path(__file__).resolve().parent.parent / "frontend"
_index = _frontend / "index.html"


@app.route("/")
def index():
    if _index.exists():
        return send_file(_index)
    return jsonify({"message": "Frontend not found. Put index.html in frontend/."})
