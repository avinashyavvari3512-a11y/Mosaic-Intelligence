# Mosaic Spend Intelligence GenAI Agent

## Project purpose

This project is an Aramark inspired GenAI procurement intelligence agent. It is modeled after the public idea of Mosaic and Avendra style spend intelligence: harmonizing supplier, SKU, contract, purchase order, risk, and substitution data so procurement teams can find savings, reduce maverick spend, manage supplier risk, and support responsible sourcing.

The project uses only synthetic data. It does not use proprietary Aramark data.

## Business problem

Enterprise food and hospitality procurement has several recurring problems:

1. Purchases happen outside preferred contracts.
2. Unit prices drift above contract prices.
3. Critical SKUs become single source risks.
4. Supplier disruptions create service and menu risk.
5. Diverse and sustainable supplier opportunities are hard to measure.
6. Buyers need a clear explanation of what to fix first.

This agent turns procurement data into a structured recommendation.

## GenAI design principle

The LLM is not the source of truth.

The deterministic data layer calculates:

- Spend by category, supplier, and location
- Contract price variance
- Maverick spend
- Supplier risk score
- Single source SKU risk
- Substitution recommendations
- Supplier diversity and sustainability indicators

The GenAI layer explains the trusted data outputs in buyer friendly language.

## Architecture

```text
Natural language procurement request
        ↓
Request parser
        ↓
Deterministic procurement tools
        ↓
Trusted tool result JSON
        ↓
Optional LLM narrative layer
        ↓
Buyer recommendation and action plan
```

## Folder structure

```text
mosaic_spend_intelligence_genai_agent/
  data/
    purchase_orders.csv
    suppliers.csv
    sku_catalog.csv
    contracts.csv
    disruptions.csv
    procurement_policy.md
  src/
    tools.py
    agent.py
    run_demo.py
  output/
    demo_recommendation.json
    demo_recommendation.md
  docs/
  README.md
  requirements.txt
```

## Data model

### purchase_orders.csv
Synthetic line level purchase order data.

Key columns:

- po_id
- order_date
- location
- sku_id
- supplier_id
- quantity
- unit_price
- spend

### suppliers.csv
Supplier master data.

Key columns:

- supplier_id
- supplier_name
- region
- reliability_score
- diversity_status
- sustainability_score
- risk_status

### sku_catalog.csv
SKU master data.

Key columns:

- sku_id
- sku_name
- category
- substitution_group
- unit
- criticality

### contracts.csv
Contract pricing and preferred supplier data.

Key columns:

- contract_id
- sku_id
- supplier_id
- contract_price_per_unit
- preferred_supplier
- contract_start
- contract_end

### disruptions.csv
Synthetic active disruption signals.

Key columns:

- disruption_id
- supplier_id
- sku_id
- issue
- severity
- active

## How to run

From the project root:

```bash
pip install -r requirements.txt
python src/run_demo.py
```

The demo writes:

```text
output/demo_recommendation.json
output/demo_recommendation.md
```

## Example request

```text
Analyze Protein spend for price variance over 20%, maverick spend,
supplier risk, and substitution opportunities. Prefer reliable suppliers
and include diverse supplier opportunities when comparable.
```

## What the agent does

1. Parses the request into constraints.
2. Filters purchase orders by category or location if specified.
3. Enriches purchase orders with SKU, supplier, and contract data.
4. Calculates price variance versus contract price.
5. Flags purchases above the variance threshold.
6. Flags non preferred supplier purchases as maverick spend.
7. Builds a supplier risk scorecard.
8. Builds a supplier SKU graph to detect single source risk.
9. Recommends alternate SKUs or suppliers in the same substitution group.
10. Produces a buyer friendly GenAI style recommendation.

## Main code files

### src/tools.py
Contains deterministic procurement tools:

- load_data
- enrich_purchase_orders
- spend_cube
- detect_price_variance
- detect_maverick_spend
- supplier_scorecard
- build_supplier_sku_graph
- single_source_skus
- recommend_alternates_for_sku
- calculate_savings_summary

### src/agent.py
Contains the MosaicSpendIntelligenceAgent class:

- parse_request
- apply_constraints
- run_tools
- generate_prompt
- deterministic_narrative
- run

### src/run_demo.py
Runs the demo request and writes output files.

## How this becomes a real enterprise GenAI agent

A production version would use:

- Azure Data Factory for ingestion
- Databricks or Synapse for lakehouse processing
- Delta tables for Bronze, Silver, Gold layers
- Unity Catalog for governance
- MLflow for risk and savings model tracking
- Vector search for procurement policy and supplier notes
- OpenAI or Azure OpenAI for grounded recommendations
- Power BI for dashboards

## Interview framing

Use this explanation:

> I built a Mosaic inspired GenAI procurement agent that analyzes synthetic purchase orders, supplier master data, SKU catalogs, contract prices, and disruption signals. The system flags maverick spend, contract price leakage, supplier risk, and single source SKU exposure. The LLM is not calculating the facts. The deterministic tools calculate the trusted procurement metrics, and the GenAI layer explains them as a buyer action plan. This keeps the system auditable and enterprise ready.

## Guardrails

- Do not invent supplier availability.
- Do not invent contract prices.
- Do not recommend suppliers that are not in the supplier data.
- Do not present synthetic savings as real company savings.
- Always label the project as synthetic and public problem inspired.

