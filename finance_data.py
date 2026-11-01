from __future__ import annotations

import random
from datetime import date

import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def generate_demo_data(seed: int = 42) -> pd.DataFrame:
    """Create a 12-month consumer-electronics case with growth and margin compression."""
    rng = random.Random(seed)
    channels = ["Amazon", "DTC", "Retail", "TikTok"]
    channel_factor = {"Amazon": 1.22, "DTC": 0.86, "Retail": 0.72, "TikTok": 0.58}
    channel_growth = {"Amazon": 0.30, "DTC": 0.12, "Retail": -0.04, "TikTok": 0.62}
    channel_discount = {"Amazon": 0.09, "DTC": 0.055, "Retail": 0.13, "TikTok": 0.15}
    channel_fee = {"Amazon": 0.15, "DTC": 0.032, "Retail": 0.07, "TikTok": 0.12}
    channel_marketing = {"Amazon": 0.075, "DTC": 0.13, "Retail": 0.035, "TikTok": 0.18}
    channel_return = {"Amazon": 0.095, "DTC": 0.062, "Retail": 0.047, "TikTok": 0.14}

    categories = {
        "Laptops": {"price": 1099, "cost": 0.61, "freight": 18.0, "return": 0.025},
        "Monitors": {"price": 369, "cost": 0.54, "freight": 21.0, "return": 0.018},
        "Gaming": {"price": 189, "cost": 0.48, "freight": 7.0, "return": 0.032},
        "Networking": {"price": 159, "cost": 0.45, "freight": 5.5, "return": 0.014},
        "Components": {"price": 249, "cost": 0.57, "freight": 6.5, "return": 0.022},
        "Accessories": {"price": 69, "cost": 0.34, "freight": 2.4, "return": 0.016},
    }
    sku_rows = []
    category_names = list(categories)
    for i in range(100):
        category = category_names[i % len(category_names)]
        cfg = categories[category]
        price = cfg["price"] * rng.uniform(0.72, 1.34)
        sku_rows.append(
            {
                "sku": f"{category[:3].upper()}-{i + 1:03d}",
                "product": f"{category[:-1] if category.endswith('s') else category} {i + 1:02d}",
                "category": category,
                "list_price": round(price, 2),
                "unit_cost": round(price * cfg["cost"] * rng.uniform(0.94, 1.08), 2),
                "freight_unit": cfg["freight"] * rng.uniform(0.88, 1.16),
                "category_return": cfg["return"],
                "velocity": rng.uniform(0.55, 1.55),
            }
        )

    last_month = pd.Timestamp(date.today().replace(day=1))
    months = pd.date_range(end=last_month, periods=12, freq="MS")
    rows = []
    for month_idx, month in enumerate(months):
        season = 1.23 if month.month in (10, 11, 12) else (0.90 if month.month in (1, 2) else 1.0)
        for item in sku_rows:
            for channel in channels:
                growth = 1 + channel_growth[channel] * month_idx / 11
                units = max(1, round(12 * item["velocity"] * channel_factor[channel] * growth * season * rng.uniform(0.72, 1.27)))
                price = item["list_price"] * rng.uniform(0.985, 1.015)
                gross_sales = units * price
                discount_rate = max(0, channel_discount[channel] + 0.006 * month_idx / 11 + rng.uniform(-0.012, 0.012))
                discount = gross_sales * discount_rate
                pre_return_sales = gross_sales - discount
                return_rate = max(0, channel_return[channel] + item["category_return"] + 0.012 * month_idx / 11 + rng.uniform(-0.01, 0.01))
                returns = pre_return_sales * min(return_rate, 0.28)
                net_revenue = pre_return_sales - returns
                product_cost = units * item["unit_cost"] * (1 + 0.035 * month_idx / 11)
                freight = units * item["freight_unit"] * (1 + 0.30 * month_idx / 11)
                tariff = product_cost * (0.035 + 0.032 * month_idx / 11)
                platform_fee = net_revenue * channel_fee[channel]
                marketing_spend = net_revenue * channel_marketing[channel] * (1 + 0.08 * month_idx / 11)
                gross_profit = net_revenue - product_cost - freight - tariff
                contribution_profit = gross_profit - platform_fee - marketing_spend
                inventory_units = max(1, round(units * rng.uniform(1.4, 4.9) * (1.12 if item["category"] in ("Monitors", "Components") else 1)))
                inventory_value = inventory_units * item["unit_cost"]
                rows.append(
                    {
                        "date": month,
                        "sku": item["sku"],
                        "product": item["product"],
                        "category": item["category"],
                        "channel": channel,
                        "units": units,
                        "list_price": price,
                        "gross_sales": gross_sales,
                        "discount": discount,
                        "returns": returns,
                        "net_revenue": net_revenue,
                        "product_cost": product_cost,
                        "freight": freight,
                        "tariff": tariff,
                        "platform_fee": platform_fee,
                        "marketing_spend": marketing_spend,
                        "gross_profit": gross_profit,
                        "contribution_profit": contribution_profit,
                        "inventory_units": inventory_units,
                        "inventory_value": inventory_value,
                    }
                )
    return pd.DataFrame(rows)


def normalize_uploaded_data(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    aliases = {
        "order date": "date", "order_date": "date", "month": "date", "日期": "date",
        "sales": "net_revenue", "revenue": "net_revenue", "amount": "net_revenue", "销售额": "net_revenue",
        "gross revenue": "gross_sales", "销售总额": "gross_sales", "discounts": "discount", "折扣": "discount",
        "return amount": "returns", "退货": "returns", "cost": "product_cost", "cogs": "product_cost",
        "product cost": "product_cost", "产品成本": "product_cost", "shipping": "freight",
        "freight cost": "freight", "运费": "freight", "tariffs": "tariff", "关税": "tariff",
        "platform fees": "platform_fee", "平台费": "platform_fee", "marketing": "marketing_spend",
        "marketing cost": "marketing_spend", "营销费用": "marketing_spend", "stock": "inventory_units",
        "inventory": "inventory_units", "库存": "inventory_units", "inventory balance": "inventory_value",
        "库存金额": "inventory_value", "product category": "category", "产品类别": "category",
        "渠道": "channel", "产品": "product", "数量": "units",
    }
    df.columns = [aliases.get(str(c).strip().lower(), str(c).strip().lower()) for c in df.columns]
    if "date" not in df.columns or "net_revenue" not in df.columns:
        raise ValueError("CSV 至少需要 date/日期 和 revenue/销售额 两列。")
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    df["net_revenue"] = pd.to_numeric(df["net_revenue"], errors="coerce")
    df = df.dropna(subset=["date", "net_revenue"]).copy()
    if df.empty:
        raise ValueError("没有找到有效的日期和销售额数据。 / No valid date and revenue rows found.")

    for column, default in {"sku": "UNSPECIFIED", "product": "Unspecified", "category": "Unspecified", "channel": "Unspecified"}.items():
        if column not in df:
            df[column] = default
    numeric_defaults = {
        "units": 1.0, "list_price": 0.0, "gross_sales": df["net_revenue"], "discount": 0.0, "returns": 0.0,
        "product_cost": df["net_revenue"] * 0.55, "freight": df["net_revenue"] * 0.04,
        "tariff": df["net_revenue"] * 0.025, "platform_fee": df["net_revenue"] * 0.08,
        "marketing_spend": df["net_revenue"] * 0.08, "inventory_units": 0.0,
        "inventory_value": df["net_revenue"] * 0.15,
    }
    for column, default in numeric_defaults.items():
        if column not in df:
            df[column] = default
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    df["gross_profit"] = df["net_revenue"] - df["product_cost"] - df["freight"] - df["tariff"]
    df["contribution_profit"] = df["gross_profit"] - df["platform_fee"] - df["marketing_spend"]
    columns = [
        "date", "sku", "product", "category", "channel", "units", "list_price", "gross_sales", "discount",
        "returns", "net_revenue", "product_cost", "freight", "tariff", "platform_fee", "marketing_spend",
        "gross_profit", "contribution_profit", "inventory_units", "inventory_value",
    ]
    return df[columns]

