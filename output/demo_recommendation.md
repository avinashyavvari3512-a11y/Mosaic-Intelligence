# Mosaic Spend Intelligence Recommendation

Mosaic Spend Intelligence Recommendation

Analyzed $450,111.95 in synthetic procurement spend. The current rules identify $42,992.20 in potential savings, equal to 9.55% of analyzed spend.
Maverick or non-preferred supplier spend is $55,111.97, or 12.24% of spend.
Diverse supplier spend is $79,819.68, or 17.73% of spend.

Detected 10 high price-variance examples, 10 maverick examples, and 4 single-source SKU risks in the top result sets.
Top variance issue: Chicken Breast from Emergency Food Brokerage at Stadium Location D is 61.7% above contract, with $1,263.80 in potential savings.
Highest supplier risk: Emergency Food Brokerage has risk score 0.593 and $55,111.97 in spend exposure.
Recommended substitution: review replacing or supplementing Chicken Breast with Turkey Strips from Regional Protein Supply. This alternate has reliability 0.86 and unit price $7.20.

Next actions: validate flagged lines with buyers, move eligible spend back to preferred contracts, review single-source SKUs, and prioritize diverse or high-sustainability suppliers when price and reliability are comparable.

## Parsed Constraints

```json
{
  "category": "Protein",
  "location": null,
  "price_variance_threshold": 0.2,
  "focus": [
    "maverick_spend",
    "supplier_risk",
    "savings",
    "supplier_diversity"
  ]
}
```

## GenAI Prompt Template

```text
You are Mosaic Spend Intelligence, a procurement analytics copilot.

Use only the structured tool results below. Do not invent prices, suppliers,
savings, diversity status, risk levels, or substitution options.

User request:

    Analyze Protein spend for price variance over 20%, maverick spend,
    supplier risk, and substitution opportunities. Prefer reliable suppliers
    and include diverse supplier opportunities when comparable.
    

Parsed constraints:
{
  "category": "Protein",
  "location": null,
  "price_variance_threshold": 0.2,
  "focus": [
    "maverick_spend",
    "supplier_risk",
    "savings",
    "supplier_diversity"
  ]
}

Trusted tool results:
{
  "savings_summary": {
    "total_spend": 450111.95,
    "potential_savings": 42992.2,
    "potential_savings_pct": 0.0955,
    "maverick_spend": 55111.97,
    "maverick_spend_pct": 0.1224,
    "diverse_supplier_spend": 79819.68,
    "diverse_supplier_spend_pct": 0.1773
  },
  "spend_cube_top10": [
    {
      "category": "Protein",
      "supplier_id": "S004",
      "supplier_name": "Sea Harvest Supply",
      "location": "University Dining A",
      "total_spend": 48059.99,
      "total_quantity": 3313,
      "avg_unit_price": 14.44,
      "potential_savings": 5487.7,
      "lines": 27
    },
    {
      "category": "Protein",
      "supplier_id": "S002",
      "supplier_name": "Regional Protein Supply",
      "location": "Remote Campus E",
      "total_spend": 35681.82,
      "total_quantity": 3858,
      "avg_unit_price": 9.29,
      "potential_savings": 1797.8,
      "lines": 36
    },
    {
      "category": "Protein",
      "supplier_id": "S002",
      "supplier_name": "Regional Protein Supply",
      "location": "University Dining A",
      "total_spend": 33554.45,
      "total_quantity": 3695,
      "avg_unit_price": 9.05,
      "potential_savings": 2450.28,
      "lines": 31
    },
    {
      "category": "Protein",
      "supplier_id": "S002",
      "supplier_name": "Regional Protein Supply",
      "location": "Stadium Location D",
      "total_spend": 33053.39,
      "total_quantity": 3789,
      "avg_unit_price": 8.85,
      "potential_savings": 1713.88,
      "lines": 29
    },
    {
      "category": "Protein",
      "supplier_id": "S004",
      "supplier_name": "Sea Harvest Supply",
      "location": "Stadium Location D",
      "total_spend": 32145.68,
      "total_quantity": 2345,
      "avg_unit_price": 13.71,
      "potential_savings": 2087.92,
      "lines": 21
    },
    {
      "category": "Protein",
      "supplier_id": "S002",
      "supplier_name": "Regional Protein Supply",
      "location": "Hospital Cafe B",
      "total_spend": 31662.63,
      "total_quantity": 3345,
      "avg_unit_price": 9.33,
      "potential_savings": 2175.78,
      "lines": 30
    },
    {
      "category": "Protein",
      "supplier_id": "S004",
      "supplier_name": "Sea Harvest Supply",
      "location": "Remote Campus E",
      "total_spend": 31516.52,
      "total_quantity": 2370,
      "avg_unit_price": 13.29,
      "potential_savings": 1406.0,
      "lines": 18
    },
    {
      "category": "Protein",
      "supplier_id": "S002",
      "supplier_name": "Regional Protein Supply",
      "location": "Corporate HQ C",
      "total_spend": 29929.89,
      "total_quantity": 3207,
      "avg_unit_price": 9.08,
      "potential_savings": 1994.08,
      "lines": 28
    },
    {
      "category": "Protein",
      "supplier_id": "S003",
      "supplier_name": "Plant Forward Fo
```
