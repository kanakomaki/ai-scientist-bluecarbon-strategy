# project_extractor.py
# プロジェクト情報のPDFからステークホルダーに関するデータを抽出し、既に作った制度graphマップに統合するスクリプト

import os
import json
import fitz  # PyMuPDF
import re
from typing import List, Dict
from sentence_transformers import SentenceTransformer, util
from ai_scientist.llm import create_client, get_response_from_llm
import networkx as nx
from pyvis.network import Network

SYSTEM_PROMPT = """
You are a professional analyst of carbon credit projects. Given text from project documents,
you will extract relationships between stakeholders involved in carbon credit projects.
Your output should be a list of structured relationships with roles and interactions.
"""



PROMPT_TEMPLATE = """
Extract all meaningful relationships with key stakeholders from the following project list text.

Project list text:
{text}


Output JSON format:
```json
[
  {{ "from": "Stakeholder A", "to": "Stakeholder B", "relation": "short description" }},
  ...
]
```

Only return the JSON array in a single code block. Do not include any additional text.
"""




def extract_paragraphs_from_pdf(pdf_path: str) -> List[str]:
    doc = fitz.open(pdf_path)
    paragraphs = []
    for page in doc:
        text = page.get_text("text")
        parts = re.split(r"\n\s*\n", text)
        for p in parts:
            cleaned = p.strip().replace("\n", " ")
            if len(cleaned) > 100:
                paragraphs.append(cleaned)
    return paragraphs

def extract_project_relationships(paragraphs: List[str], model_name: str) -> List[Dict]:
    model, model_str = create_client(model_name)
    relationships = []
    for para in paragraphs:
        prompt = PROMPT_TEMPLATE.format(text=para[:1500])  # truncate if needed
        try:
            response = get_response_from_llm(prompt=prompt, client=model, model=model_str, system_message=SYSTEM_PROMPT)
            if isinstance(response, tuple):
                response = response[0]
            match = re.search(r"```json\s*(\[.*?\])\s*```", response, flags=re.DOTALL)
            if match:
                parsed = json.loads(match.group(1))
                relationships.extend(parsed)
            else:
                print("No JSON found in LLM response, skipping...")
        except Exception as e:
            print(f"Error extracting from paragraph: {str(e)}")
    return relationships


def merge_into_existing_graph(graph_path: str, relationships: List[Dict], output_path: str):
    G = nx.read_graphml(graph_path)
    for rel in relationships:
        G.add_node(rel["from"], type="project")
        G.add_node(rel["to"], type="project")
        G.add_edge(rel["from"], rel["to"], relation=rel["relation"], type="project")
    nx.write_graphml(G, output_path)
    print(f" Merged graph saved to {output_path}")
    return G

def export_interactive_graph(G, output_html="tmp/merged_stakeholder_graph.html"):
    net = Network(height="800px", width="100%", directed=True, notebook=False)
    for node, attrs in G.nodes(data=True):
        net.add_node(node, label=node, title=f"Scheme: {attrs.get('scheme', '')}")
    for src, dst, attrs in G.edges(data=True):
        net.add_edge(src, dst, title=attrs.get("relation", ""), label=attrs.get("relation", ""))
    net.show(output_html) # Show & Save the graph as an HTML file
    print(f" Interactive HTML graph saved to {output_html}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", type=str, default="ai_scientist/template_social_db/inputs/pdfs_projects")
    parser.add_argument("--graphml", type=str, default="experiments_outputs_social_db/stakeholder_graph.graphml")
    parser.add_argument("--output", type=str, default="experiments_outputs_social_db/merged_project_graph.graphml")
    parser.add_argument("--model", type=str, default="meta-llama/llama-3.3-70b-instruct")
    args = parser.parse_args()

    all_relationships = []
    for fname in os.listdir(args.pdf_dir):
        if fname.endswith(".pdf"):
            print(f" Processing: {fname}")
            pdf_path = os.path.join(args.pdf_dir, fname)
            paras = extract_paragraphs_from_pdf(pdf_path)
            rels = extract_project_relationships(paras, args.model)
            all_relationships.extend(rels)

    G = merge_into_existing_graph(args.graphml, all_relationships, args.output)

    export_interactive_graph(G)

if __name__ == "__main__":
    main()