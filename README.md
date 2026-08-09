# 🧭 Trade Compliance & Customs Analytics Control Tower

**A portfolio project demonstrating how fragmented trading, logistics, ERP and trading-risk data can be consolidated into a customs readiness & trade-risk control tower — built for Customs/Trade Data Analyst and Analytics Engineer roles.**

> ⚠️ **All data in this repository is synthetically generated.** Contract references, counterparties, vessels, quantities, prices, tariff rates and FTA schemes are randomly simulated for demonstration purposes only. Nothing here is extracted from, or represents, any real employer's production systems, credentials, or infrastructure. Duty and FTA figures are illustrative proxies and would require Customs/Trade Compliance SME validation before any real business use.

---

## 1. Why this project

Global manufacturers with mature customs functions (e.g. large multinational chemical/industrial groups) run dedicated customs data analytics — HS code governance, FTA utilization, duty optimization, and global KPI reporting, often on top of platforms like SAP GTS.

Most commodity trading organizations aren't there yet. Their customs-relevant data is usually scattered across a **trading/contract system**, a **logistics document control tower**, an **ERP / commodity-code master**, and a **trading-risk platform** — each built for its own purpose, none of them a dedicated customs system.

This project asks: *if none of those systems were designed for customs analytics, can the data they already produce still be combined into something useful?*

The answer built here is a **Trade Compliance & Customs Analytics Control Tower** — a self-initiated analytics MVP that consolidates four source-system archetypes into one Power-BI-style dashboard covering customs documentation compliance, HS code governance, shipment/BL monitoring, tariff exposure, FTA opportunity, and trade risk scoring.

**This is deliberately not a claim of SAP GTS-level customs optimization.** It's a demonstration of the data modeling, ETL, KPI design and dashboarding skills needed to build toward that maturity.

## 2. Source systems modeled (synthetic)

| Role | What it typically holds |
|---|---|
| **Trading / Contract system** | Contract terms, counterparties, product, quantity, price, Incoterm, payment term, vessel, load/discharge port, BL date & quantity, LC details |
| **Logistics Control Tower** | Stage-gated workflow over sales orders (order receipt → gate-in/out → customs handover → vessel sailed), and the mandatory document set per shipment (K2, K2 Chit, Certificate of Origin, Bill of Lading, Customs Release, Customs Official Receipt, Shipment Tender, LOI) |
| **ERP / Commodity Code Master** | Product classification, HS/commodity codes, classification validity windows, reclassification history |
| **Trading Risk Platform** | Open position, mark-to-market, Value-at-Risk, and limit utilization per contract |

All four are generated as independent synthetic extracts and then joined the way a real ETL pipeline would join them — by contract reference, sales order, or shipment ID — which is the same integration challenge a real customs control tower would face (inconsistent keys, different field names for the same business concept, partial coverage).

## 3. Dashboard pages

[->Click here for dashboard <-](claude.ai/code/artifact/2647fd37-2e05-4d79-8fb4-b97aba26d9e4)

| # | Page | Purpose |
|---|---|---|
| 1 | **Executive Trade Overview** | Contract value, volume, and mix by product / counterparty / Incoterm / port |
| 2 | **Customs Documentation Compliance** | K2, COO, BL, Customs Release/Receipt completion %, missing-document counts, stage-gate backlog |
| 3 | **Shipment & BL Monitoring** | Missing BL dates, quantity variance exceptions, shipments stuck before final stage |
| 4 | **HS Code / Commodity Code Governance** | HS coverage %, missing/expired classifications, high-volume products without HS codes |
| 5 | **Duty / Freight Exposure Proxy** *(illustrative)* | Freight, port cost and estimated duty as a % of invoice value, by product and by lane |
| 6 | **FTA / Certificate of Origin Opportunity** *(illustrative)* | COO completion, FTA-eligible shipments missing COO, estimated preferential-duty savings opportunity; plus a shipment-level HS Code + FTA optimization table (Country of Origin per Rules of Origin, destination, HS code, duty paid, FTA availability looked up from an origin–destination–HS master, and the resulting saving opportunity) |
| 7 | **Trade Risk Score** | A composite Red/Amber/Green score combining missing documents, missing HS codes, missing/expired LCs, and high risk-limit utilization |

Pages 5 and 6 are explicitly labeled as **illustrative proxies** in the dashboard itself — the point is to demonstrate the analytical framework, not to assert real tariff/duty figures.

### Trade Risk Score logic

```
risk_score =
    + 1 if K2 missing
    + 1 if K2 Chit missing
    + 1 if Certificate of Origin missing
    + 1 if Bill of Lading missing
    + 1 if HS code missing
    + 1 if LC required but missing
    + 1 if risk-limit utilization >= 80%

RAG:  0–1 = Green   2–3 = Amber   4+ = Red
```

## 4. Architecture

Modeled on a standard Azure medallion architecture:

```
Source systems (Trading / Logistics / ERP / Risk / Reference tariff table)
        │
        ▼
Azure Data Factory  ──  ingest raw extracts
        │
        ▼
ADLS Gen2  (Bronze)  ──  raw CSV / Excel / SQL extracts
        │
        ▼
Azure Databricks  ──  clean, standardize, validate, join, derive flags
        │
        ▼
ADLS Gen2  (Silver / Gold)  ──  curated trade & customs model
        │
        ▼
Azure Synapse  ──  SQL serving views
        │
        ▼
Power BI / Web dashboard  ──  KPIs & storytelling
```

In this repo, the same layering is implemented with Python/pandas (Bronze → Silver → Gold) and the Gold layer feeds a self-contained interactive HTML dashboard instead of a `.pbix`, so it's viewable directly in a browser with no software install — see [`/dashboard`](dashboard/index.html).

## 5. Data model

```
Fact_TradeShipment
 ├─ Contract Ref, Sales Order, Shipment ID
 ├─ Product Key, Counterparty Key, Date Key
 ├─ Quantity MT, Invoice Amount, Freight Cost, Duty Cost
 └─ BL Date, Incoterm, Payment Term

Dim_Product          Dim_Counterparty        Dim_Logistics
 ├─ Material Code      ├─ Counterparty         ├─ Load / Discharge Port
 ├─ Product            ├─ Broker               ├─ Vessel
 ├─ HS Code            └─ Country              ├─ Incoterm / Payment Term
 └─ HS Valid From/To                            └─ Mode of Transport

Fact_DocumentCompliance          Fact_RAVEExposure
 ├─ Shipment ID                   ├─ Contract Ref, Product
 ├─ K2 / K2 Chit / COO / BL /     ├─ Open Position, M2M, VaR
 │  COR / LOI flags               └─ Limit Utilization %
 └─ OCR Confidence Level
```

## 6. Repo structure

```
trade-compliance-customs-control-tower/
├── README.md
├── requirements.txt
├── data/
│   ├── bronze/     raw synthetic source extracts (per system)
│   ├── silver/     cleaned, standardized tables
│   └── gold/       business-ready KPI tables (JSON + CSV) feeding the dashboard
├── scripts/
│   ├── generate_bronze_data.py   creates the synthetic source data
│   └── build_silver_gold.py      runs the Bronze → Silver → Gold transform + KPI/risk scoring
├── dashboard/
│   ├── index_template.html       dashboard shell (Plotly.js, vanilla JS)
│   ├── plotly.min.js             vendored Plotly.js (no CDN dependency at runtime)
│   ├── data.json                 Gold-layer data bundle embedded into the dashboard
│   └── index.html                final, self-contained dashboard (open directly, or serve via GitHub Pages)
└── docs/
    └── data_dictionary.md        field-level reference for every table
```

## 7. Running it locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python scripts/generate_bronze_data.py     # regenerate synthetic bronze extracts
python scripts/build_silver_gold.py        # rebuild silver/gold + dashboard/data.json

# then rebuild the static dashboard (inlines Plotly.js + the data bundle,
# so the result is a single self-contained file with no CDN dependency):
python3 -c "
data = open('dashboard/data.json').read()
plotly_js = open('dashboard/plotly.min.js').read()
tpl = open('dashboard/index_template.html').read()
out = tpl.replace('__PLOTLY_JS__', plotly_js).replace('__DATA_JSON__', data)
open('dashboard/index.html', 'w').write(out)
"
```

Open `dashboard/index.html` directly in a browser, or enable **GitHub Pages** on this repo (Settings → Pages → Deploy from branch → `/dashboard`) to get a shareable link.


## 8. Glossary

- **Customs vs. Duty vs. Levy** — Customs is the government process controlling cross-border goods movement; duty is the tax on imported/exported goods; a levy is a broader government charge, not always customs-related.
- **K2** — Malaysia's export customs declaration form, evidence goods were declared to customs.
- **BL (Bill of Lading)** — proof of loading, contract of carriage, and document of title.
- **LOI (Letter of Indemnity)** — a legal undertaking to compensate a party for losses arising from a non-standard instruction (e.g. releasing cargo before the original BL is available).
- **LC (Letter of Credit)** — a bank payment undertaking, paid when documents comply with the LC's terms.
- **TT (Telegraphic Transfer)** — a bank-to-bank payment.
- **Turnover / Revenue / Sales** — used interchangeably.
- **Profit vs. Margin** — profit is an amount; margin is a percentage.

## 10. License

MIT — see [LICENSE](LICENSE). Synthetic data only; no warranty of accuracy or fitness for real customs/tariff decision-making.

---

Built by **Hani Ihsanuddin** · [LinkedIn](https://linkedin.com/in/haniihsanuddin) · haniihsanuddin@gmail.com
