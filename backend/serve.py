"""
Stdlib-only backend: CSV upload + CLV analysis.
No FastAPI/Flask needed. Run from project root: python backend/serve.py
"""
import io
import json
import os
import re
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data
from lifetimes.utils import ConvergenceError

REQUIRED_COLS = ["customer_id", "transaction_date", "monetary_value"]
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
INDEX_HTML = FRONTEND / "index.html"


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
    # Calculate probability alive (retention/churn)
    summary["prob_alive"] = bgf.conditional_probability_alive(
        summary["frequency"], summary["recency"], summary["T"]
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
    for col in ["pred_purchases_30d", "clv_12m", "monetary_value", "frequency", "recency", "T", "prob_alive"]:
        if col in out.columns:
            out[col] = out[col].apply(
                lambda x: round(float(x), 4) if pd.notna(x) and str(x) != "" else None
            )
    records = out.to_dict(orient="records")
    # Calculate overall retention and churn rates
    retention_rate = float(summary["prob_alive"].mean())
    churn_rate = 1.0 - retention_rate
    return {
        "rows_uploaded": len(df),
        "customers": len(summary),
        "summary": records,
        "retention_rate": round(retention_rate, 4),
        "churn_rate": round(churn_rate, 4),
    }


def send_json(handler, data, status=200):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode())


def parse_multipart_file(body: bytes, content_type: str):
    """Parse multipart/form-data body; return (filename, file_bytes) or (None, None)."""
    m = re.search(r'boundary=([^;\s]+)', content_type)
    if not m:
        return None, None
    boundary = m.group(1).strip().encode()
    if boundary.startswith(b'"') and boundary.endswith(b'"'):
        boundary = boundary[1:-1]
    parts = body.split(b"--" + boundary)
    for part in parts:
        if not part.strip() or part.strip() == b"--":
            continue
        head, _, rest = part.partition(b"\r\n\r\n")
        if not rest:
            continue
        disp = head.decode("latin-1", errors="replace")
        if "name=\"file\"" not in disp and "name='file'" not in disp:
            continue
        fn_m = re.search(r'filename="([^"]*)"|filename\*=([^;\s]+)', disp)
        filename = (fn_m.group(1) or fn_m.group(2) or "").strip()
        return filename or "upload.csv", rest.rstrip(b"\r\n")
    return None, None


def send_file_response(handler, path, content_type="text/html"):
    path = Path(path)
    if not path.exists():
        send_json(handler, {"message": "Not found"}, 404)
        return
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.end_headers()
    handler.wfile.write(path.read_bytes())


class CLVHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            send_file_response(self, INDEX_HTML)
        else:
            send_json(self, {"detail": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/api/analyze":
            send_json(self, {"detail": "Not found"}, 404)
            return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            send_json(self, {"detail": "Expect multipart/form-data"}, 400)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            raw = self.rfile.read(length)
        except Exception as e:
            send_json(self, {"detail": str(e)}, 400)
            return
        filename, raw = parse_multipart_file(raw, content_type)
        if not filename or not raw:
            send_json(self, {"detail": "No file in request"}, 400)
            return
        if not filename.lower().endswith(".csv"):
            send_json(self, {"detail": "Please upload a CSV file."}, 400)
            return
        try:
            df = pd.read_csv(io.BytesIO(raw), parse_dates=["transaction_date"], dayfirst=True)
        except Exception as e:
            send_json(self, {"detail": f"Invalid CSV: {e}"}, 400)
            return
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            send_json(self, {"detail": f"CSV must have columns: {', '.join(REQUIRED_COLS)}. Missing: {', '.join(missing)}."}, 400)
            return
        try:
            result = run_clv_analysis(df)
            send_json(self, {"ok": True, **result})
        except ConvergenceError as e:
            send_json(self, {"detail": str(e)}, 422)
        except Exception as e:
            send_json(self, {"detail": str(e)}, 500)


def main():
    os.chdir(ROOT)
    port = 8000
    server = HTTPServer(("", port), CLVHandler)
    print(f"CLV server: http://localhost:{port}")
    print("Upload CSV at http://localhost:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
