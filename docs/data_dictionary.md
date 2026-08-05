# Data Dictionary

All values below are synthetically generated (see `scripts/generate_bronze_data.py`, seed = 42).

## Bronze layer

### `trading_spot_extract.csv` (Trading / Contract system)

| Field | Description |
|---|---|
| contract_ref | Unique contract reference |
| sales_order | Linked sales order number |
| shipment_id | Unique shipment identifier |
| contract_date | Date contract was booked |
| profit_center | Business unit / profit center |
| counterparty_id / counterparty_name | Trading counterparty |
| broker | Broker facilitating the deal |
| material_code / product | Product traded |
| quantity_mt | Contracted quantity, metric tons |
| price_usd_per_mt | Contract price, USD/MT (illustrative) |
| invoice_amount_usd | Contract value |
| payment_terms_id | Payment terms (LC / TT variants) |
| incoterms | Incoterm (CIF/FOB/CFR/DAP) |
| load_port / discharge_port / discharge_port_country | Logistics lane |
| mode_of_transport | Sea or Land |
| vessel | Vessel name (sea shipments) |
| shipment_month | Planned shipment month |
| bl_date / bl_quantity_mt | Bill of Lading date/quantity (blank if not yet issued) |
| lc_number | Letter of Credit number, if applicable |
| status | Open / Fulfilled / Cancelled |

### `logistics_lct_extract.csv` (Logistics Control Tower)

| Field | Description |
|---|---|
| shipment_id / contract_ref / sales_order | Keys back to trading extract |
| delivery_mode | Sea / Land |
| stage_gate | Current stage gate (SG1–SG10, order receipt → vessel sailed / complete) |
| lct_status / sap_status | Workflow status per system (used to flag cross-system mismatches) |
| k2_flag, k2_chit_flag, customs_release_flag, customs_official_receipt_flag, certificate_of_origin_flag, bill_of_lading_flag, shipment_tender_flag, loi_flag | Document-availability flags: `Y` / `N` / `N/A` |
| commercial_invoice_flag | Always `Y` in this simulation |
| ocr_confidence_pct | Simulated OCR confidence score for document capture |

### `product_master_sap_extract.csv` (ERP / Commodity Code Master)

| Field | Description |
|---|---|
| material_code / product / product_group | Product identity |
| commodity_code_hs | HS/commodity code (blank = missing classification) |
| hs_valid_from / hs_valid_to | Classification validity window |
| reclassification_date | Date of most recent reclassification, if any |
| created_by / changed_by / last_changed_date | Audit fields |

### `risk_position_rave_extract.csv` (Trading Risk Platform)

| Field | Description |
|---|---|
| contract_ref / product / counterparty_id | Keys |
| open_position_usd | Open position value |
| mark_to_market_usd | M2M value |
| var_usd | Value-at-Risk |
| limit_usd / limit_utilisation_pct | Risk limit and utilization |

### `freight_duty_cost_extract.csv` (Illustrative cost/tariff reference)

| Field | Description |
|---|---|
| shipment_id / contract_ref | Keys |
| freight_cost_usd_per_mt / port_cost_usd_per_mt | Illustrative logistics cost |
| documentation_cost_usd | Illustrative doc handling cost |
| forwarding_agent | Simulated forwarding agent |
| discharge_country / fta_scheme | Destination and applicable FTA scheme (if any) |
| standard_duty_rate_pct / preferential_duty_rate_pct | Illustrative duty rates (NOT real tariff schedule data) |

## Silver layer

Cleaned/standardized versions of the above (`silver_contract`, `silver_shipment`, `silver_invoice`, `silver_lct_document`, `silver_product_hs`, `silver_rave_position`, `silver_cost`, `silver_counterparty`) — field names harmonized across sources, booleans derived (`bl_available`, `has_hs_code`, `hs_expired`, `lc_available`), and quantity variance computed (`qty_variance_mt`, `qty_variance_pct`).

## Gold layer (dashboard-facing)

| Table | Feeds dashboard page |
|---|---|
| `gold_trade_overview.json` | 1 — Executive Trade Overview |
| `gold_customs_document_compliance.json` | 2 — Customs Documentation Compliance |
| `gold_shipment_bl_monitoring.json` | 3 — Shipment & BL Monitoring |
| `gold_hs_code_governance.json` | 4 — HS Code Governance |
| `gold_duty_exposure.json` | 5 — Duty / Freight Exposure Proxy |
| `gold_fta_opportunity.json` | 6 — FTA / COO Opportunity |
| `gold_trade_risk_score.json` (+ `.csv` detail) | 7 — Trade Risk Score |

`dashboard/data.json` is the single bundled file (all seven gold tables) embedded directly into `dashboard/index.html` for a self-contained, dependency-free dashboard.
