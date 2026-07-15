from pathlib import Path

import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    path = ROOT / "data" / "transactions.csv"
    df = pd.read_csv(path, parse_dates=["transaction_date"], dayfirst=True)
    print("Loaded rows:", len(df))
    print("\nRaw data head:")
    print(df.head())

    summary = summary_data_from_transaction_data(
        df,
        customer_id_col="customer_id",
        datetime_col="transaction_date",
        monetary_value_col="monetary_value",
        observation_period_end=df["transaction_date"].max(),
    )
    print("\nSummary head:")
    print(summary.head())

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

    print("\nResult (first 10 customers with CLV):")
    print(nonzero[["frequency", "monetary_value", "pred_purchases_30d", "clv_12m"]].head(10))


if __name__ == "__main__":
    main()

