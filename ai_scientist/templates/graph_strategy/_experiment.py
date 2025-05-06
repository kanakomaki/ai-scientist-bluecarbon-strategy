# experiment.py for AI Scientist: Strategy Recommendation from GraphDB
# Purpose: Integrated experiment module to suggest carbon credit project strategies based on stakeholder graphs

import networkx as nx
from ai_scientist.llm import create_client, get_response_from_llm
import os
from datetime import datetime
import argparse

SYSTEM_PROMPT = """
You are a strategist helping a small Japanese SME find the most efficient path to launch a successful carbon credit project
using stakeholder relationships represented in a graph.
Use real computed paths and influence scores to justify your recommendations.
"""

PROMPT_TEMPLATE = """
Given the following stakeholder relationship network:

### Shortest Paths to Certification Bodies:
{path_summary}

### Node Centrality Scores (Top Influencers):
{centrality_summary}

Client profile:
- Type: Small Japanese SME
- Budget: Limited (self-funded or with small grants)
- Experience: No prior international certification experience
- Japanese government support: {local_support}
- Regional focus: Philippines
- Project type: Blue carbon (e.g., mangrove restoration)

Their goal is to launch a blue carbon project and obtain carbon credits efficiently.

Please:
1. Recommend the most appropriate certification scheme (e.g. J-Blue, Verra).
2. Suggest 2-3 potential collaboration paths with key stakeholders.
3. Identify likely administrative bottlenecks and how to navigate them.
4. Provide a step-by-step plan for initial actions.

Return the output in well-structured markdown.
"""

def summarize_paths(G: nx.Graph, start: str, targets: list, max_paths=9):
    summaries = []
    for target in targets:
        if target not in G: continue
        try:
            path = nx.shortest_path(G, source=start, target=target)
            summaries.append(f"- {start} → {' → '.join(path[1:])} (length: {len(path) - 1})")
        except nx.NetworkXNoPath:
            summaries.append(f"- {start} → {target}: No path found")
    return "\n".join(summaries)

def summarize_centrality(G: nx.Graph, top_n=7):
    centrality = nx.degree_centrality(G)
    sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return "\n".join([f"- {node}: {score:.3f}" for node, score in sorted_nodes])


def ask_sme_connections():
    print("-----Please answer the following questions about your SME client's situation:------------")
    support = input("1. Do you have support from Japanese government? (yes/no): ").strip().lower()
    connects_to = []
    if input("2. Do you intend to collaborate with NGOs? (yes/no): ").strip().lower() == "yes":
        connects_to.append("NGO")
    if input("3. Will you seek funding from GCF or UNDP? (yes/no): ").strip().lower() == "yes":
        connects_to.extend(["GCF", "UNDP"])
    if input("4. Will you need verification partners? (yes/no): ").strip().lower() == "yes":
        connects_to.append("Verifier")
    return support, connects_to

def inject_sme_node(G: nx.Graph, support: str, connects_to: list):
    G.add_node("SME")
    if support.startswith("y"):
        if "Japanese  government" in G:
            G.add_edge("SME", "Japanese government", relation="supported by")
    for node in connects_to:
        if node in G:
            G.add_edge("SME", node, relation="wishes to connect to")

def find_nodes_matching_keywords(G: nx.Graph, keywords: list) -> dict:
    matches = {k: [] for k in keywords}
    for node in G.nodes(data=True):
        node_id, attrs = node
        values_to_check = [node_id] + list(attrs.values())
        for k in keywords:
            if any(k.lower() in str(v).lower() for v in values_to_check):
                matches[k].append(node_id)
    return matches

def run_experiment(output_dir, config):
    graphml_path = config.get("graphml", "merged_project_graph.graphml")
    model_name = config.get("model", "meta-llama/llama-3.3-70b-instruct")

    G = nx.read_graphml(graphml_path)
    local_support, connects_to = ask_sme_connections()
    inject_sme_node(G, local_support, connects_to)

    # スキーム候補に一致するノードを柔軟に検索
    scheme_keywords = ["Gold Standard", "Verra", "J-Blue", "JCM"]
    matched_scheme_nodes = find_nodes_matching_keywords(G, scheme_keywords)
    representative_targets = [nodes[0] for nodes in matched_scheme_nodes.values() if nodes]

    path_summary = summarize_paths(G, start="SME", targets=representative_targets)
    centrality_summary = summarize_centrality(G)

    client, model_str = create_client(model_name)
    prompt = PROMPT_TEMPLATE.format(
        path_summary=path_summary,
        centrality_summary=centrality_summary,
        local_support=local_support
    )

    response = get_response_from_llm(
        prompt=prompt,
        client=client,
        model=model_str,
        system_message=SYSTEM_PROMPT
    )


    output_text = response[0] if isinstance(response, tuple) else response
    output_path = os.path.join(output_dir, "strategy_result.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_text + "\n\n---\n")
        f.write("#### path summary\n" + path_summary+ "\n\n---\n")
        f.write("#### centrality summary\n" + centrality_summary)

    return {
        "output_markdown": output_path,
        "path_summary": path_summary,
        "centrality_summary": centrality_summary,
    }


def main():
    base_dir = os.path.dirname(__file__)

    parser = argparse.ArgumentParser(description="AI Scientist: Strategy Recommendation from GraphDB")
    parser.add_argument("--output_dir", type=str, default="ai_scientist/results", help="Directory to save output files")
    parser.add_argument("--graphml", type=str, default="merged_project_graph.graphml", help="Input GraphML file")
    parser.add_argument("--model", type=str, default="meta-llama/llama-3.3-70b-instruct", help="LLM model name")
    args = parser.parse_args()

    config = {
        "graphml": args.graphml,
        "model": args.model,
        "output_dir": args.output_dir,
    }

    os.makedirs(args.output_dir, exist_ok=True)
    result = run_experiment(args.output_dir, config)
    print(f"Strategy recommendation saved to {result['output_markdown']}")
    print(result["path_summary"])
    print(result["centrality_summary"])




if __name__ == "__main__":
    main()
