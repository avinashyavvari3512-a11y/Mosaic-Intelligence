"""
Tools for the Mosaic Spend Intelligence GenAI Agent.

These functions are deterministic data tools. The agent uses them as the
trusted source of truth for spend, supplier, contract, risk, and substitution
logic. The GenAI layer should explain these outputs, not invent metrics.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional
import pandas as pd
import networkx as nx


def load_data(data_dir: str = "data") -> Dict[str, pd.DataFrame]:
    """Load all synthetic procurement data tables."""
    return {
        "purchase_orders": pd.read_csv(os.path.join(data_dir, "purchase_orders.csv"), parse_dates=["order_date"]),
        "suppliers": pd.read_csv(os.path.join(data_dir, "suppliers.csv"), keep_default_na=False),
        "sku_catalog": pd.read_csv(os.path.join(data_dir, "sku_catalog.csv")),
        "contracts": pd.read_csv(os.path.join(data_dir, "contracts.csv"), parse_dates=["contract_start", "contract_end"]),
        "disruptions": pd.read_csv(os.path.join(data_dir, "disruptions.csv")),
    }


def enrich_purchase_orders(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join purchase orders to SKU, supplier, and contract master data."""
    po = tables["purchase_orders"].copy()
    suppliers = tables["suppliers"]
    sku = tables["sku_catalog"]
    contracts = tables["contracts"]

    enriched = po.merge(sku, on="sku_id", how="left")
    enriched = enriched.merge(suppliers, on="supplier_id", how="left")
    enriched = enriched.merge(
        contracts[["sku_id", "supplier_id", "contract_price_per_unit", "preferred_supplier"]],
        on=["sku_id", "supplier_id"],
        how="left"
    )

    enriched["contract_price_per_unit"] = enriched["contract_price_per_unit"].fillna(enriched["unit_price"])
    enriched["preferred_supplier"] = enriched["preferred_supplier"].fillna(0).astype(int)
    enriched["price_variance_pct"] = (
        (enriched["unit_price"] - enriched["contract_price_per_unit"]) /
        enriched["contract_price_per_unit"]
    ).round(4)
    enriched["potential_savings"] = (
        (enriched["unit_price"] - enriched["contract_price_per_unit"]).clip(lower=0) * enriched["quantity"]
    ).round(2)
    return enriched


def spend_cube(enriched: pd.DataFrame) -> pd.DataFrame:
    """Aggregate spend by category, supplier, and location."""
    cube = (
        enriched.groupby(["category", "supplier_id", "supplier_name", "location"], dropna=False)
        .agg(
            total_spend=("spend", "sum"),
            total_quantity=("quantity", "sum"),
            avg_unit_price=("unit_price", "mean"),
            potential_savings=("potential_savings", "sum"),
            lines=("po_id", "count"),
        )
        .reset_index()
        .sort_values("total_spend", ascending=False)
    )
    return cube


def detect_price_variance(enriched: pd.DataFrame, threshold: float = 0.20) -> pd.DataFrame:
    """Flag lines where unit price is more than threshold above contract price."""
    flagged = enriched[enriched["price_variance_pct"] > threshold].copy()
    return flagged.sort_values("potential_savings", ascending=False)


def detect_maverick_spend(enriched: pd.DataFrame) -> pd.DataFrame:
    """Flag non-preferred supplier purchases."""
    flagged = enriched[enriched["preferred_supplier"] == 0].copy()
    return flagged.sort_values("spend", ascending=False)


def supplier_scorecard(enriched: pd.DataFrame, disruptions: pd.DataFrame) -> pd.DataFrame:
    """Create supplier-level risk, sustainability, and spend scorecard."""
    active_disruptions = disruptions[disruptions["active"] == 1]
    disrupted_suppliers = set(active_disruptions["supplier_id"].dropna())

    supplier = (
        enriched.groupby(["supplier_id", "supplier_name", "region", "diversity_status", "risk_status"], dropna=False)
        .agg(
            total_spend=("spend", "sum"),
            reliability_score=("reliability_score", "mean"),
            sustainability_score=("sustainability_score", "mean"),
            potential_savings=("potential_savings", "sum"),
            order_lines=("po_id", "count"),
        )
        .reset_index()
    )
    supplier["active_disruption"] = supplier["supplier_id"].isin(disrupted_suppliers)
    supplier["supplier_risk_score"] = (
        (1 - supplier["reliability_score"]) * 0.45 +
        ((100 - supplier["sustainability_score"]) / 100) * 0.20 +
        supplier["active_disruption"].astype(int) * 0.25 +
        (supplier["risk_status"].isin(["watch", "disrupted"]).astype(int)) * 0.10
    ).round(3)
    return supplier.sort_values("supplier_risk_score", ascending=False)


def build_supplier_sku_graph(enriched: pd.DataFrame) -> nx.Graph:
    """Build a bipartite supplier-SKU graph for substitution and concentration analysis."""
    graph = nx.Graph()
    for _, row in enriched.drop_duplicates(["supplier_id", "sku_id"]).iterrows():
        supplier_node = f"supplier:{row['supplier_id']}"
        sku_node = f"sku:{row['sku_id']}"
        graph.add_node(
            supplier_node,
            node_type="supplier",
            supplier_id=row["supplier_id"],
            supplier_name=row["supplier_name"],
            reliability_score=row["reliability_score"],
            sustainability_score=row["sustainability_score"],
            diversity_status=row["diversity_status"],
        )
        graph.add_node(
            sku_node,
            node_type="sku",
            sku_id=row["sku_id"],
            sku_name=row["sku_name"],
            category=row["category"],
            substitution_group=row["substitution_group"],
            criticality=row["criticality"],
        )
        graph.add_edge(supplier_node, sku_node, avg_price=row["unit_price"], category=row["category"])
    return graph


def single_source_skus(graph: nx.Graph) -> List[Dict]:
    """Find SKUs with only one connected supplier."""
    risks = []
    for node, attrs in graph.nodes(data=True):
        if attrs.get("node_type") != "sku":
            continue
        suppliers = [n for n in graph.neighbors(node) if graph.nodes[n].get("node_type") == "supplier"]
        if len(suppliers) <= 1:
            supplier = suppliers[0] if suppliers else None
            supplier_attrs = graph.nodes[supplier] if supplier else {}
            risks.append({
                "sku_id": attrs.get("sku_id"),
                "sku_name": attrs.get("sku_name"),
                "category": attrs.get("category"),
                "substitution_group": attrs.get("substitution_group"),
                "criticality": attrs.get("criticality"),
                "current_supplier_id": supplier_attrs.get("supplier_id"),
                "current_supplier_name": supplier_attrs.get("supplier_name"),
                "supplier_count": len(suppliers),
            })
    return risks


def recommend_alternates_for_sku(sku_id: str, enriched: pd.DataFrame, max_results: int = 5) -> List[Dict]:
    """Recommend alternate SKUs and suppliers in the same substitution group."""
    sku_rows = enriched[enriched["sku_id"] == sku_id]
    if sku_rows.empty:
        return []
    substitution_group = sku_rows.iloc[0]["substitution_group"]
    current_category = sku_rows.iloc[0]["category"]

    candidates = enriched[
        (enriched["substitution_group"] == substitution_group) &
        (enriched["sku_id"] != sku_id)
    ].copy()
    if candidates.empty:
        candidates = enriched[
            (enriched["category"] == current_category) &
            (enriched["sku_id"] != sku_id)
        ].copy()

    if candidates.empty:
        return []

    candidates["candidate_score"] = (
        candidates["reliability_score"] * 0.35 +
        (1 - candidates["unit_price"] / candidates["unit_price"].max()) * 0.35 +
        (candidates["sustainability_score"] / 100) * 0.20 +
        (candidates["diversity_status"].ne("None").astype(int)) * 0.10
    )
    recs = (
        candidates.sort_values("candidate_score", ascending=False)
        .drop_duplicates(["sku_id", "supplier_id"])
        .head(max_results)
    )
    return recs[[
        "sku_id", "sku_name", "supplier_id", "supplier_name", "unit_price",
        "reliability_score", "diversity_status", "sustainability_score", "candidate_score"
    ]].round(3).to_dict("records")


def calculate_savings_summary(enriched: pd.DataFrame) -> Dict:
    """Calculate top-level spend and savings metrics."""
    total_spend = float(enriched["spend"].sum())
    potential_savings = float(enriched["potential_savings"].sum())
    maverick_spend = float(enriched.loc[enriched["preferred_supplier"] == 0, "spend"].sum())
    diverse_spend = float(enriched.loc[enriched["diversity_status"].ne("None"), "spend"].sum())
    return {
        "total_spend": round(total_spend, 2),
        "potential_savings": round(potential_savings, 2),
        "potential_savings_pct": round(potential_savings / total_spend, 4) if total_spend else 0,
        "maverick_spend": round(maverick_spend, 2),
        "maverick_spend_pct": round(maverick_spend / total_spend, 4) if total_spend else 0,
        "diverse_supplier_spend": round(diverse_spend, 2),
        "diverse_supplier_spend_pct": round(diverse_spend / total_spend, 4) if total_spend else 0,
    }
