# Stakeholder Mapping (Graph DB) with json data and LLM, and visualize them with networkx and pyvis.
# 
# 構造化された制度要約（merged_summaries.json）をもとに、ステークホルダー間の関係性をLLMで抽出し、networkx形式に変換・可視化

import argparse
import json
import networkx as nx
import re
from datetime import datetime
from ai_scientist.llm import create_client, get_response_from_llm
import matplotlib.pyplot as plt
from pyvis.network import Network


SYSTEM_PROMPT = """
You are an AI expert in blue carbon credit systems. Your task is to extract stakeholder relationships from regulatory summaries.

Each input text describes stakeholders and their interactions in a carbon offsetting scheme.

Extract direct relationships between stakeholders in the form of structured triples.
"""

PROMPT_TEMPLATE = """
Given the following guideline summary for the scheme '{scheme}', extract key stakeholder relationships.

Text:
{text}

Output JSON format:
```json
[
  {{ "from": "Stakeholder A", "to": "Stakeholder B", "relation": "short description" }},
  ...
]
```

Only output the JSON block. Do not include explanations.
"""

def clean_llm_response(text: str):
    if isinstance(text, tuple):
        text = text[0]
    match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON block found in response")
    return json.loads(match.group(1))


def extract_relationships_llama_ver02(summary_json: str, model: str):
    with open(summary_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    client, client_model = create_client(model)
    print(f"Using model: {client_model}")

    schemes = ["Verra", "Gold Standard", "J-Blue", "JCM"]

    all_relationships = []
    MAX_TEXT_LENGTH = 1500

    for doc_name, entries in data.items():
        if isinstance(entries, dict) and "data" in entries:
            matched_scheme = next(
                (s for s in schemes if s in entries["category"]),
                ""
            )
            scheme = matched_scheme if matched_scheme else ""
            entries = entries["data"]

        if not isinstance(entries, list):
            print(f"Unexpected structure in {scheme}, skipping.")
            continue

        for item in entries:
            if not isinstance(item, dict):
                print(f"Skipping non-dict entry in {scheme}: {item}")
                continue
            parts = []
            for key in ["stakeholder_names", "application_methods", "conditions_to_get_credits"]:
                if item.get(key):
                    parts.append(f"{key}: {item[key]}")
            combined_text = "\n".join(parts)

            # 長さ制限を追加
            if len(combined_text) > MAX_TEXT_LENGTH:
                print(f"Prompt text too long for {scheme}, truncating to {MAX_TEXT_LENGTH} characters.")
                combined_text = combined_text[:MAX_TEXT_LENGTH]

            prompt = PROMPT_TEMPLATE.format(scheme=scheme, text=combined_text)
            response = get_response_from_llm(prompt=prompt, client=client, model=client_model, system_message=SYSTEM_PROMPT)
            try:
                rels = clean_llm_response(response)
                for r in rels:
                    r["scheme"] = scheme
                    all_relationships.append(r)
            except Exception as e:
                print(f"Failed to parse: {scheme} entry: {e}")

    return all_relationships



def build_networkx_graph(relationships):
    G = nx.DiGraph()
    for r in relationships:
        scheme_field = r.get("scheme", "")
        scheme_names = re.split(r"[,\/]+", scheme_field)  # , / で分割

        # スキームノード（複数）を明示的に追加
        for scheme in scheme_names:
            scheme = scheme.strip()
            if scheme:
                G.add_node(scheme, type="scheme")

        # ステークホルダーノード
        G.add_node(r["from"], type="actor")
        G.add_node(r["to"], type="actor")

        # スキームごとにステークホルダーと結ぶ
        for scheme in scheme_names:
            scheme = scheme.strip()
            if scheme:
                G.add_edge(r["from"], scheme, relation="participates_in")
                G.add_edge(r["to"], scheme, relation="participates_in")

        # ステークホルダー間の元の関係も保持
        G.add_edge(r["from"], r["to"], relation=r["relation"], scheme=scheme_field)
    return G




def visualize_graph(G, output_img="tmp/stakeholder_graph.png"):
    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(12, 10))
    nx.draw(G, pos, with_labels=True, node_size=2000, node_color="lightblue", font_size=10, font_weight="bold", edge_color="gray")
    edge_labels = nx.get_edge_attributes(G, 'relation')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9)
    plt.title("Stakeholder Relationship Graph")
    plt.tight_layout()
    plt.savefig(output_img)
    print(f" Graph visualization saved to {output_img}")
    plt.close()

def export_interactive_graph(G, output_html="tmp/stakeholder_graph.html"):
    net = Network(height="800px", width="100%", directed=True, notebook=False)
    for node, attrs in G.nodes(data=True):
        net.add_node(node, label=node, title=f"Scheme: {attrs.get('scheme', '')}")
    for src, dst, attrs in G.edges(data=True):
        net.add_edge(src, dst, title=attrs.get("relation", ""), label=attrs.get("relation", ""))
    net.show(output_html)
    print(f" Interactive HTML graph saved to {output_html}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="meta-llama/llama-3.3-70b-instruct")
    parser.add_argument("--input", type=str, default="experiments_outputs_social_db/20250416_112225_merged_summaries.json")
    parser.add_argument("--output", type=str, default="experiments_outputs_social_db/stakeholder_graph.graphml")
    args = parser.parse_args()

    relationships = extract_relationships_llama_ver02(args.input, args.model)
    G = build_networkx_graph(relationships)

    nx.write_graphml(G, args.output)
    print(f"Graph saved to {args.output}")

    visualize_graph(G)

    export_interactive_graph(G)

if __name__ == "__main__":
    main()