"""Small yfinance response snapshots captured on 2026-11-07.

These are provider examples, not maintained current quotes or recommendations.
They keep presentation tests offline and make no attempt to estimate missing data.
"""

import pandas as pd


def _statement(periods, revenue, operating_income, net_income, diluted_eps):
    return pd.DataFrame(
        [revenue, operating_income, net_income, diluted_eps],
        index=["Total Revenue", "Operating Income", "Net Income", "Diluted EPS"],
        columns=pd.to_datetime(periods),
    )


RESEARCH_RESPONSES = {
    "AMZN": {
        "info": {
            "shortName":"Amazon.com, Inc.", "marketCap":2803846610944,
            "trailingPE":20.962004, "revenueGrowth":0.121,
            "profitMargins":0.16900998, "operatingMargins":0.13903,
            "returnOnEquity":0.27416,
        },
        "quarterly_income_stmt":_statement(
            ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31"],
            [201944000000, None, 181519000000, 213386000000],
            [28076000000, None, 23852000000, 24977000000],
            [20685000000, None, 30255000000, 21192000000],
            [1.89, 5.75, 2.78, 1.95],
        ),
        "analyst_price_targets":{
            "current":259.3, "high":405.0, "low":230.0,
            "mean":326.99017, "median":330.0,
        },
        "recommendations_summary":pd.DataFrame([{
            "period":"0m", "strongBuy":14, "buy":44, "hold":3, "sell":0, "strongSell":0,
        }]),
        "eps_revisions":pd.DataFrame([{
            "upLast7days":0, "upLast30days":10, "downLast30days":17,
            "downLast7Days":2, "currency":"USD", "methodology":"gaap",
        }], index=["0q"]),
    },
    "MSFT": {
        "info": {
            "shortName":"Microsoft Corporation", "marketCap":3940412817408,
            "trailingPE":27.693632, "revenueGrowth":0.188,
            "profitMargins":0.41169998, "operatingMargins":0.49757,
            "returnOnEquity":0.34221,
        },
        "quarterly_income_stmt":_statement(
            ["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31"],
            [92279000000, 90007000000, 82886000000, 81273000000],
            [45915000000, 40603000000, 38398000000, 38275000000],
            [36629000000, 35766000000, 31778000000, 38458000000],
            [4.92, 4.81, 4.27, 5.16],
        ),
        "analyst_price_targets":{
            "current":530.61, "high":870.0, "low":440.0,
            "mean":634.14276, "median":631.0,
        },
        "recommendations_summary":pd.DataFrame([{
            "period":"0m", "strongBuy":12, "buy":41, "hold":5, "sell":0, "strongSell":0,
        }]),
        "eps_revisions":pd.DataFrame([{
            "upLast7days":14, "upLast30days":13, "downLast30days":2,
            "downLast7Days":4, "currency":"USD", "methodology":"normalized",
        }], index=["0q"]),
    },
    "NVDA": {
        "info": {
            "shortName":"NVIDIA Corporation", "marketCap":4506795900928,
            "trailingPE":23.59545, "revenueGrowth":1.059,
            "profitMargins":0.63663, "operatingMargins":0.66236997,
            "returnOnEquity":1.17211,
        },
        "quarterly_income_stmt":_statement(
            ["2026-07-31", "2026-04-30", "2026-01-31", "2025-10-31"],
            [96221000000, 81615000000, 68127000000, 57006000000],
            [63734000000, 53536000000, 44299000000, 36010000000],
            [59688000000, 58321000000, 42960000000, 31910000000],
            [2.46, 2.39, 1.76, 1.3],
        ),
        "analyst_price_targets":{
            "current":186.64, "high":515.0, "low":180.0,
            "mean":327.1431, "median":315.0,
        },
        "recommendations_summary":pd.DataFrame([{
            "period":"0m", "strongBuy":10, "buy":49, "hold":2, "sell":1, "strongSell":0,
        }]),
        "eps_revisions":pd.DataFrame([{
            "upLast7days":0, "upLast30days":0, "downLast30days":1,
            "downLast7Days":1, "currency":"USD", "methodology":"normalized",
        }], index=["0q"]),
    },
}
