"""
build_silver_gold.py

Transforms the synthetic bronze extracts into a Silver (cleaned/standardized)
and Gold (business-ready, dashboard-facing) layer, mirroring a medallion
architecture (Bronze -> Silver -> Gold) commonly implemented with
Azure Data Factory + Databricks + Synapse.

Run after generate_bronze_data.py.
"""

import os
import json
import numpy as np
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..")
BRONZE = os.path.join(BASE, "data", "bronze")
SILVER = os.path.join(BASE, "data", "silver")
GOLD = os.path.join(BASE, "data", "gold")
DASHBOARD_DATA = os.path.join(BASE, "dashboard", "data.json")

os.makedirs(SILVER, exist_ok=True)
os.makedirs(GOLD, exist_ok=True)

# ---------------------------------------------------------------------------
# Load bronze
# ---------------------------------------------------------------------------

trading = pd.read_csv(os.path.join(BRONZE, "trading_spot_extract.csv"))
logistics = pd.read_csv(os.path.join(BRONZE, "logistics_lct_extract.csv"), keep_default_na=False, na_values=[])
product = pd.read_csv(os.path.join(BRONZE, "product_master_sap_extract.csv"))
risk = pd.read_csv(os.path.join(BRONZE, "risk_position_rave_extract.csv"))
cost = pd.read_csv(os.path.join(BRONZE, "freight_duty_cost_extract.csv"))

# ---------------------------------------------------------------------------
# SILVER: standardize field names / types (mirrors the ETL mapping table:
# source field -> common business field)
# ---------------------------------------------------------------------------

silver_contract = trading[[
    "contract_ref", "contract_date", "profit_center", "counterparty_id",
    "counterparty_name", "broker", "incoterms", "payment_terms_id", "status",
]].rename(columns={"incoterms": "incoterm", "payment_terms_id": "payment_term"})

silver_shipment = trading[[
    "shipment_id", "contract_ref", "sales_order", "material_code", "product",
    "quantity_mt", "load_port", "discharge_port", "discharge_port_country",
    "mode_of_transport", "vessel", "shipment_month", "bl_date", "bl_quantity_mt",
]].copy()
silver_shipment["bl_date"] = pd.to_datetime(silver_shipment["bl_date"], errors="coerce")
silver_shipment["bl_available"] = silver_shipment["bl_date"].notna()
silver_shipment["qty_variance_mt"] = (silver_shipment["bl_quantity_mt"] - silver_shipment["quantity_mt"]).round(2)
silver_shipment["qty_variance_pct"] = (silver_shipment["qty_variance_mt"] / silver_shipment["quantity_mt"] * 100).round(2)

silver_invoice = trading[[
    "shipment_id", "contract_ref", "invoice_amount_usd", "price_usd_per_mt", "lc_number",
]].copy()
silver_invoice["lc_available"] = silver_invoice["lc_number"].fillna("").astype(str).str.len() > 0

silver_lct_document = logistics.copy()
doc_flag_cols = [
    "k2_flag", "k2_chit_flag", "customs_release_flag", "customs_official_receipt_flag",
    "certificate_of_origin_flag", "bill_of_lading_flag", "shipment_tender_flag", "loi_flag",
]
for c in doc_flag_cols:
    silver_lct_document[c + "_bool"] = silver_lct_document[c].isin(["Y"])

silver_product_hs = product.copy()
silver_product_hs["has_hs_code"] = silver_product_hs["commodity_code_hs"].fillna("").astype(str).str.len() > 0
silver_product_hs["hs_valid_to"] = pd.to_datetime(silver_product_hs["hs_valid_to"], errors="coerce")
silver_product_hs["hs_expired"] = silver_product_hs["hs_valid_to"] < pd.Timestamp("2026-08-06")

silver_rave_position = risk.copy()

silver_cost = cost.copy()

silver_counterparty = pd.DataFrame(
    trading[["counterparty_id", "counterparty_name", "broker"]].drop_duplicates()
)

silver_tables = {
    "silver_contract": silver_contract,
    "silver_shipment": silver_shipment,
    "silver_invoice": silver_invoice,
    "silver_lct_document": silver_lct_document,
    "silver_product_hs": silver_product_hs,
    "silver_rave_position": silver_rave_position,
    "silver_cost": silver_cost,
    "silver_counterparty": silver_counterparty,
}
for name, df in silver_tables.items():
    df.to_csv(os.path.join(SILVER, f"{name}.csv"), index=False)

# ---------------------------------------------------------------------------
# GOLD 1: Trade Overview (Page 1)
# ---------------------------------------------------------------------------

gold_trade_overview = {
    "total_contract_value_usd": round(trading["invoice_amount_usd"].sum(), 2),
    "total_quantity_mt": round(trading["quantity_mt"].sum(), 1),
    "total_contracts": int(trading["contract_ref"].nunique()),
    "open_contracts": int((trading["status"] == "Open").sum()),
    "by_product": trading.groupby("product")["invoice_amount_usd"].sum().round(2).sort_values(ascending=False).reset_index().to_dict("records"),
    "by_counterparty": trading.groupby("counterparty_name")["invoice_amount_usd"].sum().round(2).sort_values(ascending=False).head(10).reset_index().to_dict("records"),
    "by_incoterm": trading.groupby("incoterms")["contract_ref"].count().reset_index().rename(columns={"contract_ref": "contract_count"}).to_dict("records"),
    "by_port": trading.groupby("discharge_port")["quantity_mt"].sum().round(1).sort_values(ascending=False).head(10).reset_index().to_dict("records"),
    "payment_term_mix": trading.groupby("payment_terms_id")["contract_ref"].count().reset_index().rename(columns={"contract_ref": "contract_count", "payment_terms_id": "payment_term"}).to_dict("records"),
    "lc_transaction_count": int(silver_invoice["lc_available"].sum()),
    "monthly_value": trading.groupby("shipment_month")["invoice_amount_usd"].sum().round(2).reset_index().sort_values("shipment_month").to_dict("records"),
}
with open(os.path.join(GOLD, "gold_trade_overview.json"), "w") as f:
    json.dump(gold_trade_overview, f, indent=2)

# ---------------------------------------------------------------------------
# GOLD 2: Customs Documentation Compliance (Page 2)
# ---------------------------------------------------------------------------

n_doc = len(silver_lct_document)
doc_completion = {}
for c in doc_flag_cols:
    label = c.replace("_flag", "")
    applicable = silver_lct_document[silver_lct_document[c] != "N/A"]
    pct = round(applicable[c].isin(["Y"]).mean() * 100, 1) if len(applicable) else None
    doc_completion[label] = pct

missing_doc_count = int((silver_lct_document[doc_flag_cols].isin(["N"])).sum().sum())

by_stage_gate = silver_lct_document.groupby("stage_gate")["shipment_id"].count().reset_index().rename(columns={"shipment_id": "count"}).to_dict("records")

sap_lct_mismatch = silver_lct_document[
    (silver_lct_document["sap_status"] == "Delivered") & (silver_lct_document["lct_status"] != "Complete")
]

gold_customs_document_compliance = {
    "doc_completion_pct": doc_completion,
    "missing_document_count": missing_doc_count,
    "orders_by_stage_gate": by_stage_gate,
    "sap_complete_lct_open_count": int(len(sap_lct_mismatch)),
    "detail": silver_lct_document[[
        "shipment_id", "contract_ref", "delivery_mode", "stage_gate", "lct_status", "sap_status",
        "k2_flag", "k2_chit_flag", "customs_release_flag", "customs_official_receipt_flag",
        "certificate_of_origin_flag", "bill_of_lading_flag", "shipment_tender_flag", "loi_flag",
        "ocr_confidence_pct",
    ]].to_dict("records"),
}
with open(os.path.join(GOLD, "gold_customs_document_compliance.json"), "w") as f:
    json.dump(gold_customs_document_compliance, f, indent=2)

# ---------------------------------------------------------------------------
# GOLD 3: Shipment & BL Monitoring (Page 3)
# ---------------------------------------------------------------------------

missing_bl_date = int((~silver_shipment["bl_available"]).sum())
qty_variance_exceptions = silver_shipment[silver_shipment["qty_variance_pct"].abs() > 1.5]

gold_shipment_bl_monitoring = {
    "missing_bl_date_count": missing_bl_date,
    "missing_bl_pct": round(missing_bl_date / len(silver_shipment) * 100, 1),
    "qty_variance_exception_count": int(len(qty_variance_exceptions)),
    "avg_qty_variance_pct": round(silver_shipment["qty_variance_pct"].abs().mean(), 2),
    "pending_vessel_sailed": int((silver_lct_document["stage_gate"] != "SG10").sum()),
    "by_load_port": silver_shipment.groupby("load_port")["shipment_id"].count().reset_index().rename(columns={"shipment_id": "count"}).to_dict("records"),
    "detail": silver_shipment[[
        "shipment_id", "contract_ref", "vessel", "load_port", "discharge_port", "shipment_month",
        "bl_date", "bl_quantity_mt", "quantity_mt", "qty_variance_pct", "bl_available",
    ]].fillna("").to_dict("records"),
}
with open(os.path.join(GOLD, "gold_shipment_bl_monitoring.json"), "w") as f:
    json.dump(gold_shipment_bl_monitoring, f, indent=2, default=str)

# ---------------------------------------------------------------------------
# GOLD 4: HS Code / Commodity Code Governance (Page 4)
# ---------------------------------------------------------------------------

hs_coverage_pct = round(silver_product_hs["has_hs_code"].mean() * 100, 1)
volume_by_product = trading.groupby("product")["quantity_mt"].sum().round(1)
prod_hs = silver_product_hs.set_index("product")
high_vol_missing_hs = [
    {"product": p, "quantity_mt": float(v)}
    for p, v in volume_by_product.items()
    if p in prod_hs.index and not prod_hs.loc[p, "has_hs_code"]
]

gold_hs_code_governance = {
    "hs_coverage_pct": hs_coverage_pct,
    "products_missing_hs": int((~silver_product_hs["has_hs_code"]).sum()),
    "products_hs_expired": int(silver_product_hs["hs_expired"].fillna(False).sum()),
    "high_volume_products_missing_hs": high_vol_missing_hs,
    "detail": silver_product_hs.fillna("").astype(str).to_dict("records"),
}
with open(os.path.join(GOLD, "gold_hs_code_governance.json"), "w") as f:
    json.dump(gold_hs_code_governance, f, indent=2, default=str)

# ---------------------------------------------------------------------------
# GOLD 5: Duty / Freight Exposure Proxy (Page 5) — ILLUSTRATIVE ONLY
# ---------------------------------------------------------------------------

merged_cost = cost.merge(trading[["shipment_id", "product", "quantity_mt", "invoice_amount_usd"]], on="shipment_id")
merged_cost["freight_total_usd"] = (merged_cost["freight_cost_usd_per_mt"] * merged_cost["quantity_mt"]).round(2)
merged_cost["port_total_usd"] = (merged_cost["port_cost_usd_per_mt"] * merged_cost["quantity_mt"]).round(2)
merged_cost["est_export_duty_usd"] = (merged_cost["invoice_amount_usd"] * merged_cost["standard_duty_rate_pct"] / 100).round(2)
merged_cost["landed_cost_usd"] = (
    merged_cost["invoice_amount_usd"] + merged_cost["freight_total_usd"]
    + merged_cost["port_total_usd"] + merged_cost["est_export_duty_usd"]
    + merged_cost["documentation_cost_usd"]
).round(2)
merged_cost["freight_duty_pct_of_invoice"] = (
    (merged_cost["freight_total_usd"] + merged_cost["est_export_duty_usd"]) / merged_cost["invoice_amount_usd"] * 100
).round(2)

top_products_burden = merged_cost.groupby("product")["freight_duty_pct_of_invoice"].mean().round(2).sort_values(ascending=False).head(8).reset_index().to_dict("records")
top_lanes_burden = merged_cost.groupby(["discharge_country"])["freight_duty_pct_of_invoice"].mean().round(2).sort_values(ascending=False).head(8).reset_index().to_dict("records")

gold_duty_exposure = {
    "label": "Duty Exposure Proxy / Illustrative Tariff Exposure (not actual customs duty data)",
    "avg_freight_cost_per_mt": round(merged_cost["freight_cost_usd_per_mt"].mean(), 2),
    "avg_export_duty_per_mt": round((merged_cost["est_export_duty_usd"] / merged_cost["quantity_mt"]).mean(), 2),
    "avg_port_cost_per_mt": round(merged_cost["port_cost_usd_per_mt"].mean(), 2),
    "avg_freight_duty_pct_of_invoice": round(merged_cost["freight_duty_pct_of_invoice"].mean(), 2),
    "total_estimated_landed_cost_usd": round(merged_cost["landed_cost_usd"].sum(), 2),
    "top_products_by_burden": top_products_burden,
    "top_lanes_by_burden": top_lanes_burden,
}
with open(os.path.join(GOLD, "gold_duty_exposure.json"), "w") as f:
    json.dump(gold_duty_exposure, f, indent=2)

# ---------------------------------------------------------------------------
# GOLD 6: FTA / Certificate of Origin Opportunity (Page 6) — ILLUSTRATIVE ONLY
# ---------------------------------------------------------------------------

fta_merge = merged_cost.merge(
    silver_lct_document[["shipment_id", "certificate_of_origin_flag"]], on="shipment_id", how="left"
)
fta_merge["fta_eligible"] = fta_merge["fta_scheme"] != "None"
fta_merge["coo_missing"] = fta_merge["certificate_of_origin_flag"].isin(["N"])
fta_merge["potential_saving_usd"] = np.where(
    fta_merge["fta_eligible"],
    (fta_merge["standard_duty_rate_pct"] - fta_merge["preferential_duty_rate_pct"]) / 100 * fta_merge["invoice_amount_usd"],
    0.0,
).round(2)

coo_completion_pct = round((1 - fta_merge["coo_missing"].mean()) * 100, 1)
fta_eligible_shipments = int(fta_merge["fta_eligible"].sum())
missing_coo_fta_eligible = fta_merge[(fta_merge["fta_eligible"]) & (fta_merge["coo_missing"])]
total_potential_savings = round(fta_merge.loc[fta_merge["fta_eligible"], "potential_saving_usd"].sum(), 2)

by_country_opportunity = fta_merge[fta_merge["fta_eligible"]].groupby("discharge_country").agg(
    shipments=("shipment_id", "count"),
    missing_coo=("coo_missing", "sum"),
    potential_saving_usd=("potential_saving_usd", "sum"),
).round(2).reset_index().sort_values("potential_saving_usd", ascending=False).to_dict("records")

gold_fta_opportunity = {
    "caveat": "Tariff and FTA rates are illustrative placeholders and require validation by Customs / Trade Compliance SMEs.",
    "coo_completion_pct": coo_completion_pct,
    "shipments_missing_coo": int(fta_merge["coo_missing"].sum()),
    "fta_eligible_shipments": fta_eligible_shipments,
    "fta_eligible_missing_coo": int(len(missing_coo_fta_eligible)),
    "total_potential_saving_usd": total_potential_savings,
    "by_country_opportunity": by_country_opportunity,
}
with open(os.path.join(GOLD, "gold_fta_opportunity.json"), "w") as f:
    json.dump(gold_fta_opportunity, f, indent=2)

# ---------------------------------------------------------------------------
# GOLD 7: Trade Risk Score (Page 7)
# ---------------------------------------------------------------------------

risk_base = trading[["shipment_id", "contract_ref", "counterparty_name", "product", "discharge_port", "lc_number", "payment_terms_id"]].copy()
risk_base = risk_base.merge(silver_lct_document[["shipment_id"] + doc_flag_cols], on="shipment_id", how="left")
risk_base = risk_base.merge(silver_product_hs[["product", "has_hs_code"]].drop_duplicates("product"), on="product", how="left")
risk_base = risk_base.merge(silver_rave_position[["contract_ref", "limit_utilisation_pct"]], on="contract_ref", how="left")

def score_row(r):
    score = 0
    score += 1 if r["k2_flag"] == "N" else 0
    score += 1 if r["k2_chit_flag"] == "N" else 0
    score += 1 if r["certificate_of_origin_flag"] == "N" else 0
    score += 1 if r["bill_of_lading_flag"] == "N" else 0
    score += 1 if not bool(r["has_hs_code"]) else 0
    score += 1 if ("LC" in str(r["payment_terms_id"]) and (pd.isna(r["lc_number"]) or str(r["lc_number"]).strip() == "")) else 0
    score += 1 if pd.notna(r["limit_utilisation_pct"]) and r["limit_utilisation_pct"] >= 80 else 0
    return score

risk_base["risk_score"] = risk_base.apply(score_row, axis=1)
risk_base["rag"] = pd.cut(risk_base["risk_score"], bins=[-1, 1, 3, 100], labels=["Green", "Amber", "Red"])

high_risk = risk_base[risk_base["rag"] == "Red"]

gold_trade_risk_score = {
    "rag_distribution": risk_base["rag"].value_counts().reindex(["Green", "Amber", "Red"]).fillna(0).astype(int).reset_index().rename(columns={"index": "rag", "rag": "count"} if False else {"count": "count"}).to_dict("records"),
    "high_risk_shipment_count": int(len(high_risk)),
    "high_risk_counterparties": high_risk.groupby("counterparty_name")["shipment_id"].count().sort_values(ascending=False).head(8).reset_index().rename(columns={"shipment_id": "count"}).to_dict("records"),
    "high_risk_products": high_risk.groupby("product")["shipment_id"].count().sort_values(ascending=False).reset_index().rename(columns={"shipment_id": "count"}).to_dict("records"),
    "high_risk_ports": high_risk.groupby("discharge_port")["shipment_id"].count().sort_values(ascending=False).head(8).reset_index().rename(columns={"shipment_id": "count"}).to_dict("records"),
    "near_limit_contracts": int((silver_rave_position["limit_utilisation_pct"] >= 80).sum()),
    "detail": risk_base[["shipment_id", "contract_ref", "counterparty_name", "product", "discharge_port", "risk_score", "rag"]].to_dict("records"),
}
# fix rag_distribution structure properly
rag_counts = risk_base["rag"].value_counts().reindex(["Green", "Amber", "Red"]).fillna(0).astype(int)
gold_trade_risk_score["rag_distribution"] = [{"rag": k, "count": int(v)} for k, v in rag_counts.items()]

with open(os.path.join(GOLD, "gold_trade_risk_score.json"), "w") as f:
    json.dump(gold_trade_risk_score, f, indent=2)

risk_base.to_csv(os.path.join(GOLD, "gold_trade_risk_score_detail.csv"), index=False)

# ---------------------------------------------------------------------------
# Bundle everything the dashboard needs into one JSON for the self-contained HTML
# ---------------------------------------------------------------------------

bundle = {
    "generated_at": "2026-08-06",
    "trade_overview": gold_trade_overview,
    "customs_document_compliance": gold_customs_document_compliance,
    "shipment_bl_monitoring": gold_shipment_bl_monitoring,
    "hs_code_governance": gold_hs_code_governance,
    "duty_exposure": gold_duty_exposure,
    "fta_opportunity": gold_fta_opportunity,
    "trade_risk_score": gold_trade_risk_score,
}

with open(DASHBOARD_DATA, "w") as f:
    json.dump(bundle, f, default=str)

print("Silver + Gold layers built successfully.")
print(f"Dashboard data bundle written to {DASHBOARD_DATA}")
