import json
import os

try:
    from .agent import MosaicSpendIntelligenceAgent
except ImportError:  # Allows `python src/run_demo.py` from the project root.
    from agent import MosaicSpendIntelligenceAgent


def main():
    project_root = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(project_root, "data")
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    request = """
    Analyze Protein spend for price variance over 20%, maverick spend,
    supplier risk, and substitution opportunities. Prefer reliable suppliers
    and include diverse supplier opportunities when comparable.
    """

    agent = MosaicSpendIntelligenceAgent(data_dir=data_dir)
    result = agent.run(request, use_llm=False)

    json_path = os.path.join(output_dir, "demo_recommendation.json")
    md_path = os.path.join(output_dir, "demo_recommendation.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Mosaic Spend Intelligence Recommendation\n\n")
        f.write(result["operator_summary"])
        f.write("\n\n## Parsed Constraints\n\n")
        f.write("```json\n")
        f.write(json.dumps(result["constraints"], indent=2))
        f.write("\n```\n")
        f.write("\n## GenAI Prompt Template\n\n")
        f.write("```text\n")
        f.write(result["genai_prompt"][:3500])
        f.write("\n```\n")

    print(result["operator_summary"])
    print(f"\nSaved JSON output to {json_path}")
    print(f"Saved Markdown output to {md_path}")


if __name__ == "__main__":
    main()
