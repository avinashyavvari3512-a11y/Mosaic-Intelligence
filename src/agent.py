"""
Mosaic Spend Intelligence GenAI Agent.

This agent is inspired by an enterprise procurement intelligence system.
It combines deterministic data tools with a GenAI-style narrative layer.
The LLM is not the source of truth. The tools calculate spend, variance,
risk, and substitutions; the narrative layer explains the recommendation.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict

import pandas as pd

try:
    from .tools import (
        load_data,
        enrich_purchase_orders,
        spend_cube,
        detect_price_variance,
        detect_maverick_spend,
        supplier_scorecard,
        build_supplier_sku_graph,
        single_source_skus,
        recommend_alternates_for_sku,
        calculate_savings_summary,
    )
except ImportError:  # Allows `python src/run_demo.py` from the project root.
    from tools import (
        load_data,
        enrich_purchase_orders,
        spend_cube,
        detect_price_variance,
        detect_maverick_spend,
        supplier_scorecard,
        build_supplier_sku_graph,
        single_source_skus,
        recommend_alternates_for_sku,
        calculate_savings_summary,
    )


class MosaicSpendIntelligenceAgent:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.tables = load_data(data_dir)
        self.enriched = enrich_purchase_orders(self.tables)

    def parse_request(self, user_request: str) -> Dict:
        """Simple deterministic parser for procurement analyst requests."""
        text = user_request.lower()
        category = None
        for option in ["protein", "produce", "grain", "dairy"]:
            if option in text:
                category = option.title()
                break

        location = None
        for loc in self.enriched["location"].dropna().unique():
            if loc.lower() in text:
                location = loc
                break

        threshold_match = re.search(r"(\d+)%", text)
        price_variance_threshold = 0.20
        if threshold_match:
            price_variance_threshold = float(threshold_match.group(1)) / 100

        focus = []
        if "maverick" in text or "off contract" in text:
            focus.append("maverick_spend")
        if "risk" in text or "disruption" in text or "single source" in text:
            focus.append("supplier_risk")
        if "savings" in text or "save" in text or "price" in text:
            focus.append("savings")
        if "diverse" in text or "inclusive" in text:
            focus.append("supplier_diversity")
        if not focus:
            focus = ["savings", "maverick_spend", "supplier_risk"]

        return {
            "category": category,
            "location": location,
            "price_variance_threshold": price_variance_threshold,
            "focus": focus,
        }

    def apply_constraints(self, constraints: Dict) -> pd.DataFrame:
        """Filter enriched purchase orders by parsed request constraints."""
        df = self.enriched.copy()
        if constraints.get("category"):
            df = df[df["category"] == constraints["category"]]
        if constraints.get("location"):
            df = df[df["location"] == constraints["location"]]
        return df

    def run_tools(self, constraints: Dict) -> Dict:
        """Run deterministic tools and return trusted facts."""
        filtered = self.apply_constraints(constraints)
        threshold = constraints["price_variance_threshold"]

        cube = spend_cube(filtered)
        variance = detect_price_variance(filtered, threshold=threshold)
        maverick = detect_maverick_spend(filtered)
        scorecard = supplier_scorecard(filtered, self.tables["disruptions"])
        graph = build_supplier_sku_graph(filtered)
        single_source = single_source_skus(graph)
        savings = calculate_savings_summary(filtered)

        # Build substitution recommendations for risky or disrupted SKUs
        risky_skus = []
        if not variance.empty:
            risky_skus.extend(variance.head(5)["sku_id"].tolist())
        risky_skus.extend([x["sku_id"] for x in single_source[:5]])
        risky_skus = list(dict.fromkeys(risky_skus))

        substitutions = []
        for sku_id in risky_skus[:5]:
            alternatives = recommend_alternates_for_sku(sku_id, filtered)
            if alternatives:
                sku_name = filtered.loc[filtered["sku_id"] == sku_id, "sku_name"].iloc[0]
                substitutions.append({
                    "sku_id": sku_id,
                    "sku_name": sku_name,
                    "alternatives": alternatives[:3],
                })

        return {
            "savings_summary": savings,
            "spend_cube_top10": cube.head(10).round(2).to_dict("records"),
            "price_variance_top10": variance.head(10).round(3).to_dict("records"),
            "maverick_spend_top10": maverick.head(10).round(3).to_dict("records"),
            "supplier_scorecard_top10": scorecard.head(10).round(3).to_dict("records"),
            "single_source_skus": single_source[:10],
            "substitution_recommendations": substitutions,
        }

    def generate_prompt(self, request: str, constraints: Dict, tool_results: Dict) -> str:
        """Create a prompt for an optional LLM narrative layer."""
        return f"""
You are Mosaic Spend Intelligence, a procurement analytics copilot.

Use only the structured tool results below. Do not invent prices, suppliers,
savings, diversity status, risk levels, or substitution options.

User request:
{request}

Parsed constraints:
{json.dumps(constraints, indent=2)}

Trusted tool results:
{json.dumps(tool_results, indent=2, default=str)[:12000]}

Write an executive procurement recommendation with:
1. Total spend and savings opportunity
2. Top price variance or maverick spend issues
3. Supplier risk and single-source concerns
4. Recommended supplier or SKU substitutions
5. Immediate next actions for procurement
""".strip()

    def deterministic_narrative(self, constraints: Dict, tool_results: Dict) -> str:
        """Offline GenAI-style summary when no API key is available."""
        summary = tool_results["savings_summary"]
        variance_count = len(tool_results["price_variance_top10"])
        maverick_count = len(tool_results["maverick_spend_top10"])
        risk_count = len(tool_results["single_source_skus"])
        substitutions = tool_results["substitution_recommendations"]

        lines = []
        lines.append("Mosaic Spend Intelligence Recommendation")
        lines.append("")
        lines.append(
            f"Analyzed ${summary['total_spend']:,.2f} in synthetic procurement spend. "
            f"The current rules identify ${summary['potential_savings']:,.2f} in potential savings, "
            f"equal to {summary['potential_savings_pct'] * 100:.2f}% of analyzed spend."
        )
        lines.append(
            f"Maverick or non-preferred supplier spend is ${summary['maverick_spend']:,.2f}, "
            f"or {summary['maverick_spend_pct'] * 100:.2f}% of spend."
        )
        lines.append(
            f"Diverse supplier spend is ${summary['diverse_supplier_spend']:,.2f}, "
            f"or {summary['diverse_supplier_spend_pct'] * 100:.2f}% of spend."
        )
        lines.append("")
        lines.append(f"Detected {variance_count} high price-variance examples, {maverick_count} maverick examples, and {risk_count} single-source SKU risks in the top result sets.")

        if tool_results["price_variance_top10"]:
            top = tool_results["price_variance_top10"][0]
            lines.append(
                f"Top variance issue: {top['sku_name']} from {top['supplier_name']} at {top['location']} "
                f"is {top['price_variance_pct'] * 100:.1f}% above contract, with ${top['potential_savings']:,.2f} in potential savings."
            )

        if tool_results["supplier_scorecard_top10"]:
            risky = tool_results["supplier_scorecard_top10"][0]
            lines.append(
                f"Highest supplier risk: {risky['supplier_name']} has risk score {risky['supplier_risk_score']} "
                f"and ${risky['total_spend']:,.2f} in spend exposure."
            )

        if substitutions:
            sub = substitutions[0]
            alt = sub["alternatives"][0]
            lines.append(
                f"Recommended substitution: review replacing or supplementing {sub['sku_name']} "
                f"with {alt['sku_name']} from {alt['supplier_name']}. This alternate has reliability "
                f"{alt['reliability_score']} and unit price ${alt['unit_price']:.2f}."
            )

        lines.append("")
        lines.append("Next actions: validate flagged lines with buyers, move eligible spend back to preferred contracts, review single-source SKUs, and prioritize diverse or high-sustainability suppliers when price and reliability are comparable.")
        return "\n".join(lines)

    def run(self, user_request: str, use_llm: bool = False) -> Dict:
        constraints = self.parse_request(user_request)
        tool_results = self.run_tools(constraints)
        prompt = self.generate_prompt(user_request, constraints, tool_results)

        narrative = self.deterministic_narrative(constraints, tool_results)
        llm_status = "offline_deterministic_narrative"

        # Optional LLM hook. Kept inactive unless the user adds an API key and dependency.
        if use_llm and os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                client = OpenAI()
                response = client.responses.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                    input=prompt,
                )
                narrative = response.output_text
                llm_status = "openai_response_generated"
            except Exception as exc:
                narrative += f"\n\nLLM call failed, using deterministic narrative. Error: {exc}"
                llm_status = "llm_failed_fallback_used"

        return {
            "status": "success",
            "llm_status": llm_status,
            "constraints": constraints,
            "tool_results": tool_results,
            "genai_prompt": prompt,
            "operator_summary": narrative,
        }
