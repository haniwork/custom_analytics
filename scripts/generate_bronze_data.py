"""
generate_bronze_data.py

Generates fully SYNTHETIC "bronze" (raw) extracts that mimic the shape and
field names of a palm-oil trading group's source systems:

  - trading.csv       -> mimics a trading/contract system (SPOT-style)
  - logistics_doc.csv -> mimics a logistics document control tower (LCT-style)
  - product_master.csv-> mimics ERP commodity-code / product master data (SAP-style)
  - risk_position.csv -> mimics a trading risk platform (RAVE-style)

IMPORTANT: All company names, counterparties, vessels, values and IDs below
are randomly generated for portfolio/demo purposes. Nothing here is drawn
from, or represents, any real company's production data, credentials, or
infrastructure.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import os

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "bronze")
os.makedirs(OUT_DIR, exist_ok=True)

N_SHIPMENTS = 420

# ---------------------------------------------------------------------------
# Reference lists (synthetic)
# ---------------------------------------------------------------------------

PRODUCTS = [
    ("MAT-1001", "Crude Palm Oil (CPO)", "Crude Oils", "1511.10"),
    ("MAT-1002", "RBD Palm Olein", "Refined Oils", "1511.90"),
    ("MAT-1003", "RBD Palm Stearin", "Refined Oils", "1511.90"),
    ("MAT-1004", "RBD Palm Oil", "Refined Oils", "1511.90"),
    ("MAT-1005", "Palm Kernel Oil (PKO)", "Kernel Oils", "1513.29"),
    ("MAT-1006", "Palm Fatty Acid Distillate (PFAD)", "By-Products", "3823.19"),
    ("MAT-1007", "Palm Methyl Ester Biodiesel (B100)", "Biofuels", "3826.00"),
    ("MAT-1008", "Palm Kernel Expeller (PKE)", "By-Products", "2306.60"),
]

COUNTERPARTIES = [
    ("CP-01", "Ganga Agro Traders", "India", "Broker-A"),
    ("CP-02", "Meridian Oleo Pvt Ltd", "India", "Broker-A"),
    ("CP-03", "Rotterdam Fats & Oils BV", "Netherlands", "Broker-B"),
    ("CP-04", "Nile Delta Vegetable Oils", "Egypt", "Broker-C"),
    ("CP-05", "Karachi Edible Oil Co.", "Pakistan", "Broker-C"),
    ("CP-06", "Shanghai Huifeng Trading", "China", "Broker-D"),
    ("CP-07", "Guangzhou Oleochem Ltd", "China", "Broker-D"),
    ("CP-08", "EuroFat Amsterdam", "Netherlands", "Broker-B"),
    ("CP-09", "Lagos Vegetable Oil Ltd", "Nigeria", "Broker-E"),
    ("CP-10", "Istanbul Bitkisel Yag", "Turkey", "Broker-E"),
    ("CP-11", "Chittagong Oil Refinery", "Bangladesh", "Broker-C"),
    ("CP-12", "PT Nusantara Lipid", "Indonesia", "Broker-F"),
    ("CP-13", "California Biofuels Inc", "USA", "Broker-G"),
    ("CP-14", "Colombo Fats Trading", "Sri Lanka", "Broker-C"),
    ("CP-15", "Jeddah Oils & Fats Co", "Saudi Arabia", "Broker-E"),
]

LOAD_PORTS = ["Port Klang", "Westport", "Pasir Gudang", "Kuantan", "Lahad Datu", "Bintulu"]

DISCHARGE = [
    ("Chennai", "India"), ("Kandla", "India"), ("Rotterdam", "Netherlands"),
    ("Alexandria", "Egypt"), ("Karachi", "Pakistan"), ("Shanghai", "China"),
    ("Guangzhou", "China"), ("Lagos", "Nigeria"), ("Istanbul", "Turkey"),
    ("Chittagong", "Bangladesh"), ("Colombo", "Sri Lanka"), ("Jeddah", "Saudi Arabia"),
    ("Los Angeles", "USA"), ("West Port, Malaysia", "Malaysia"), ("Singapore", "Singapore"),
]

INCOTERMS = ["CIF", "FOB", "CFR", "DAP"]
PAYMENT_TERMS = ["LC at sight", "TT 30 days", "TT 60 days", "LC 90 days", "TT advance"]
MODES = ["Sea", "Land"]

FTA_SCHEMES = {
    "India": "AIFTA",
    "China": "ACFTA",
    "Pakistan": "MPCEPA-like",
    "Turkey": "None",
    "Indonesia": "AFTA",
    "Bangladesh": "None",
    "Sri Lanka": "None",
    "Nigeria": "None",
    "Egypt": "None",
    "Netherlands": "EU MFN",
    "USA": "None",
    "Saudi Arabia": "None",
    "Singapore": "AFTA",
    "Malaysia": "Domestic",
}

VESSEL_NAMES = [
    "MT Kinabalu Spirit", "MT Sabahan Pride", "MT Selangor Star", "MT Pahang Voyager",
    "MT Sarawak Trader", "MT Perak Navigator", "MT Melaka Horizon", "MT Labuan Wave",
]


def rand_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def gen_trading():
    """Mimics SPOT-style trading/contract extract."""
    rows = []
    base_date = datetime(2025, 1, 1)
    for i in range(N_SHIPMENTS):
        contract_date = rand_date(base_date, datetime(2026, 6, 30))
        product = random.choice(PRODUCTS)
        counterparty = random.choice(COUNTERPARTIES)
        discharge_port, discharge_country = random.choice(DISCHARGE)
        load_port = random.choice(LOAD_PORTS)
        qty = round(np.random.uniform(500, 8000), 1)
        price = round(np.random.uniform(650, 1250), 2)  # USD/MT, illustrative
        invoice_amount = round(qty * price, 2)
        incoterm = random.choice(INCOTERMS)
        payment_term = random.choice(PAYMENT_TERMS)
        mode = "Sea" if discharge_country != "Malaysia" else random.choice(MODES)
        shipment_month = (contract_date + timedelta(days=random.randint(10, 45))).strftime("%Y-%m")
        vessel = random.choice(VESSEL_NAMES) if mode == "Sea" else "N/A"
        bl_date = contract_date + timedelta(days=random.randint(15, 50))
        # simulate ~12% missing BL date/qty (fulfilment gaps)
        has_bl = np.random.rand() > 0.12
        rows.append({
            "contract_ref": f"CTR-{2025000+i}",
            "sales_order": f"SO-{500000+i}",
            "shipment_id": f"SHP-{700000+i}",
            "contract_date": contract_date.date().isoformat(),
            "profit_center": random.choice(["PC-Trading-MY", "PC-Trading-SG", "PC-Refining-MY"]),
            "counterparty_id": counterparty[0],
            "counterparty_name": counterparty[1],
            "broker": counterparty[3],
            "material_code": product[0],
            "product": product[1],
            "quantity_mt": qty,
            "price_usd_per_mt": price,
            "invoice_amount_usd": invoice_amount,
            "payment_terms_id": payment_term,
            "incoterms": incoterm,
            "load_port": load_port,
            "discharge_port": discharge_port,
            "discharge_port_country": discharge_country,
            "mode_of_transport": mode,
            "vessel": vessel,
            "shipment_month": shipment_month,
            "bl_date": bl_date.date().isoformat() if has_bl else "",
            "bl_quantity_mt": round(qty * np.random.uniform(0.97, 1.02), 1) if has_bl else np.nan,
            "lc_number": f"LC-{90000+i}" if "LC" in payment_term else "",
            "status": random.choice(["Open", "Fulfilled", "Fulfilled", "Fulfilled", "Cancelled"]),
        })
    return pd.DataFrame(rows)


def gen_logistics_docs(trading_df):
    """Mimics LCT-style document/stage-gate extract."""
    stage_gates = ["SG1", "SG2", "SG3", "SG4", "SG5", "SG6", "SG7", "SG8", "SG9", "SG10"]
    rows = []
    for _, t in trading_df.iterrows():
        # documentation completeness probabilities (illustrative gaps, not tied to
        # any specific real audit event)
        def flag(p_missing):
            return "N" if np.random.rand() < p_missing else "Y"

        is_sea = t["mode_of_transport"] == "Sea"
        k2 = flag(0.18)
        k2_chit = flag(0.22)
        coo = flag(0.28) if is_sea else "N/A"
        cust_release = flag(0.15)
        cust_receipt = flag(0.20)
        bl_flag = "Y" if t["bl_date"] != "" else "N"
        loi = flag(0.6)  # LOI only needed occasionally
        tender = flag(0.10)

        missing_ct = sum(f == "N" for f in [k2, k2_chit, bl_flag, cust_release, cust_receipt] + ([coo] if coo != "N/A" else []))
        if missing_ct >= 3:
            stage = random.choice(stage_gates[2:6])
        elif missing_ct >= 1:
            stage = random.choice(stage_gates[5:9])
        else:
            stage = "SG10"

        rows.append({
            "shipment_id": t["shipment_id"],
            "contract_ref": t["contract_ref"],
            "sales_order": t["sales_order"],
            "delivery_mode": t["mode_of_transport"],
            "stage_gate": stage,
            "lct_status": "Complete" if stage == "SG10" else "In Progress",
            "sap_status": "Delivered" if t["status"] in ("Fulfilled",) else t["status"],
            "k2_flag": k2,
            "k2_chit_flag": k2_chit,
            "customs_release_flag": cust_release,
            "customs_official_receipt_flag": cust_receipt,
            "certificate_of_origin_flag": coo,
            "bill_of_lading_flag": bl_flag,
            "shipment_tender_flag": tender,
            "loi_flag": loi,
            "commercial_invoice_flag": "Y",
            "ocr_confidence_pct": round(np.random.uniform(72, 99), 1),
        })
    return pd.DataFrame(rows)


def gen_product_master():
    """Mimics ERP/SAP-style commodity code & material master extract."""
    rows = []
    for code, name, group, hs in PRODUCTS:
        has_hs = np.random.rand() > 0.15  # ~15% missing/expired HS classification
        valid_from = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 400))
        valid_to = valid_from + timedelta(days=random.randint(365, 900))
        reclass_date = valid_from + timedelta(days=random.randint(30, 300)) if np.random.rand() > 0.5 else None
        rows.append({
            "material_code": code,
            "product": name,
            "product_group": group,
            "commodity_code_hs": hs if has_hs else "",
            "hs_valid_from": valid_from.date().isoformat() if has_hs else "",
            "hs_valid_to": valid_to.date().isoformat() if has_hs else "",
            "reclassification_date": reclass_date.date().isoformat() if reclass_date else "",
            "created_by": "SYS-BATCH",
            "changed_by": random.choice(["analyst01", "analyst02", "trade.compliance"]),
            "last_changed_date": (valid_from + timedelta(days=random.randint(1, 300))).date().isoformat(),
        })
    return pd.DataFrame(rows)


def gen_risk_position(trading_df):
    """Mimics a trading-risk platform (RAVE-style) extract — only open contracts."""
    open_df = trading_df[trading_df["status"] == "Open"].copy()
    rows = []
    for _, t in open_df.iterrows():
        limit = round(np.random.uniform(2_000_000, 15_000_000), 0)
        open_position = round(t["invoice_amount_usd"] * np.random.uniform(0.6, 1.1), 2)
        m2m = round(open_position * np.random.uniform(-0.08, 0.08), 2)
        var = round(abs(m2m) * np.random.uniform(1.2, 2.0), 2)
        utilisation = round(min(open_position / limit * 100, 140), 1)
        rows.append({
            "contract_ref": t["contract_ref"],
            "product": t["product"],
            "counterparty_id": t["counterparty_id"],
            "open_position_usd": open_position,
            "mark_to_market_usd": m2m,
            "var_usd": var,
            "limit_usd": limit,
            "limit_utilisation_pct": utilisation,
            "as_of_date": "2026-06-30",
        })
    return pd.DataFrame(rows)


def gen_cost_freight(trading_df):
    """Illustrative freight/duty/port cost proxy table (not real tariff data)."""
    rows = []
    for _, t in trading_df.iterrows():
        freight_per_mt = round(np.random.uniform(25, 90), 2)
        port_cost_per_mt = round(np.random.uniform(3, 12), 2)
        country = t["discharge_port_country"]
        fta_scheme = FTA_SCHEMES.get(country, "None")
        std_duty_rate = round(np.random.uniform(3, 15), 1)  # % illustrative
        pref_duty_rate = round(std_duty_rate * np.random.uniform(0.2, 0.7), 1) if fta_scheme != "None" else std_duty_rate
        doc_cost = round(np.random.uniform(150, 600), 2)
        rows.append({
            "shipment_id": t["shipment_id"],
            "contract_ref": t["contract_ref"],
            "freight_cost_usd_per_mt": freight_per_mt,
            "port_cost_usd_per_mt": port_cost_per_mt,
            "documentation_cost_usd": doc_cost,
            "forwarding_agent": random.choice(["Agent Alpha Logistics", "Agent Beta Freight", "Agent Gamma Shipping"]),
            "discharge_country": country,
            "fta_scheme": fta_scheme,
            "standard_duty_rate_pct": std_duty_rate,
            "preferential_duty_rate_pct": pref_duty_rate,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    trading_df = gen_trading()
    logistics_df = gen_logistics_docs(trading_df)
    product_df = gen_product_master()
    risk_df = gen_risk_position(trading_df)
    cost_df = gen_cost_freight(trading_df)

    trading_df.to_csv(os.path.join(OUT_DIR, "trading_spot_extract.csv"), index=False)
    logistics_df.to_csv(os.path.join(OUT_DIR, "logistics_lct_extract.csv"), index=False)
    product_df.to_csv(os.path.join(OUT_DIR, "product_master_sap_extract.csv"), index=False)
    risk_df.to_csv(os.path.join(OUT_DIR, "risk_position_rave_extract.csv"), index=False)
    cost_df.to_csv(os.path.join(OUT_DIR, "freight_duty_cost_extract.csv"), index=False)

    print(f"Generated {len(trading_df)} trading rows, {len(logistics_df)} doc rows, "
          f"{len(product_df)} product rows, {len(risk_df)} risk rows, {len(cost_df)} cost rows.")
