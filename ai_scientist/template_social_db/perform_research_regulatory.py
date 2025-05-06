# Regulatory data gathering & research 
# 制度に関する情報収集リサーチ
import argparse
import json
import os.path as osp
import re
import traceback
from typing import Any, Dict, List

import os
import requests

from ai_scientist.llm import (
    AVAILABLE_LLMS,
    create_client,
    get_response_from_llm,
)

#from ai_scientist.tools.semantic_scholar import SemanticScholarSearchTool
from ai_scientist.tools.base_tool import BaseTool
from ai_scientist.tools.coresearch_scholar import CoreSearchTool # added by KK

from datetime import datetime

from ai_scientist.tools.pdf_to_scheme_json import run_batch_pdf_to_json

def clean_llm_response(response: str) -> dict:
    if isinstance(response, tuple):
        response = response[0]
    #print("Raw response preview:\n", response[:300])

    # get format JSON blocks / JSONブロックの正規表現抽出
    match = re.search(r"```json\s*(\{.*?\})\s*```", response, flags=re.DOTALL)
    if not match:
        print("JSON block not found.")
#        print("Full response:\n", response)
        raise ValueError("JSON code block not found in LLM response.")

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print("JSON decoding failed. Content:\n", match.group(1)[:300])
        raise e
    


system_prompt = """あなたは、ブルーカーボンのREDD++やVerra等に関する制度比較をおこなうAIリサーチャーです。
これから情報収集とリサーチをします。できるだけ正確な情報をより具体的に提供してください。
"""

prompt_summarize = """
各PDFファイルやガイドラインのURLの文書を読み込み、以下の情報を英語で要点を抑えつつ必要な情報をできるだけ具体的に詳細にそれぞれの小項目ごとに500 words程度でまとめてください：
- 想定される文書の対象内容（例：申請条件、算定方式、プロジェクト要件 など）

please reformat the same information in valid JSON format with the following JSON schema:
```json
{
  "Verra": [
    {
      "regulatory_frameworks": "...",
      "application_methods": "...",
      "main_targets": "...",
      "stakeholder_names": "...",
      "available_fundings": "...",
      "conditions_to_get_credits": "..."
      "expected_periods": "...",
      "expected_difficulty": "..."
      "expected_costs": "...",
      "pros_and_cons": "...",
      "Advantages_in_Japanese_applicants": "...",
      "other_notes": "...",
    },
    ...
  ],
  "JCM": [ ... ],
  "J-Blue": [ ... ],
  "REDD+": [ ... ],
  "Gold Standard": [ ... ],
}

Respond only with a single JSON block. Ensure the JSON is properly formatted for automatic parsing."""

prompt_json_summarize = """
You are a professional analyst. The following input contains extracted text fragments grouped by field, from REDD+/Verra/J-Blue guidelines.

Some text entries may include section titles, tables of contents, or heading-only entries such as:
"2.1 GENERAL REQUIREMENTS" or "3.2.9 SAFEGUARDS".
These items should be **ignored** unless followed by explanatory content.

Your task:
- Summarize the content of each field into clear, specific, and informative English with more than 100 words for each.
- DO NOT invent or supplement missing information.
- Use only the given text content (do not use external knowledge).
- If no meaningful content is found in a field, respond with: `"No substantial content found."`
- Add closest "category" from Verra, J-Blue, JCM, or other credit certification schemes. to the output JSON by assuming from the contents.

Format your output in valid JSON:
```json
{"category": "...",
 data: [
{
  "regulatory_frameworks": "...",
  "application_methods": "...",
  "main_targets": "...",
  "stakeholder_names": "...",
  "available_fundings": "...",
  "conditions_to_get_credits": "...",
  "expected_periods": "...",
  "expected_difficulty": "...",
  "expected_costs": "...",
  "pros_and_cons": "...",
  "Advantages_in_Japanese_applicants": "...",
  "other_notes": "..."
}
]
}

Respond only with a single JSON block enclosed in triple backticks like this:

```json
{ ... }

"""


def fetch_documents_via_core():
    tool = CoreSearchTool()
    topics = [
        ("blue carbon guidelines", "blue carbon"),
        ("Verra VCS guidelines", "Verra"),
        ("REDD+ guidelines", "REDD+"),
        ("Japan blue carbon credit guidelines", "J-Blue"),
        ("JCM guidelines", "JCM"),
        ("Gold Standard guidelines", "Gold Standard"),
    ]
    results = {}
    for query, label in topics:
        result_block = tool.use_tool(query)
        results[label] = result_block
        results[label] = [
            {
                "title": r.split("\n")[0][:120],
                "url": "No direct link" if "http" not in r else "http" + r.split("http")[1].split("\n")[0],
                "issuer": label,
                "expected_content": r[:500]
            }
            for r in result_block
        ]
    # to save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_name = "tmp/" +f"{timestamp}_core_refs.json"
    with open(output_file_name, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return output_file_name

# ----------------------------
# Save linked PDFs, HTMLs: 
# Caution!!! The API does not always return the correct URLs and the linked PDF files may not be accessible or readible.
# So, I will download the files and check them manually after this process.
# ----------------------------
def download_documents(ref_json_path: str, save_dir: str = "downloads"):
    os.makedirs(save_dir, exist_ok=True)
    with open(ref_json_path, "r", encoding="utf-8") as f:
        refs = json.load(f)
    for category, items in refs.items():
        for idx, item in enumerate(items):
            url = item.get("url", "")
            if not url.startswith("http"):
                continue
            try:
                resp = requests.get(url, timeout=10)
                ext = ".pdf" if "pdf" in url.lower() else ".html"
                fname = f"{category}_{idx+1}{ext}"
                path = os.path.join(save_dir, fname)
                with open(path, "wb") as out:
                    out.write(resp.content)
                print(f"Downloaded: {fname}")
            except Exception as e:
                print(f"Failed to download {url}: {e}")

def fetch_documents():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="gpt-4", choices=AVAILABLE_LLMS)
    parser.add_argument("--output", type=str, default="pdf_reference_list.json")
    args = parser.parse_args()

    try:
        client, client_model = create_client(args.model)
        print(client_model) 

        response = get_response_from_llm(
            prompt=prompt_fetchdocs,
            client=client,
            model=client_model,
            system_message=system_prompt,
        )
        parsed = clean_llm_response(response)
        print(parsed["Verra"][0]["title"])  # → VCS Program Guide

    except Exception as e:
        print("Error occurred:")
        traceback.print_exc()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{timestamp}_{args.output}"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
    return output_path

# refs format ~  { "Verra": [...], "REDD++": [...], ... } 
def format_prompt_summarize_from_refs(refs: Dict[str, List[Dict]]) -> str:
    return (
        f"{prompt_json_summarize}\n\n"
        + json.dumps(refs)  # 元のプロンプトに追加する
    )

def format_prompt_summarize_from_refs_ver2(refs: Dict[str, List[Dict]]) -> str:
    doclist = []
    for category, items in refs.items():
        doclist.append(f"### {category} references:")
        for item in items:
            doclist.append(f"- {item['title']} ({item['issuer']}) → {item['url']}")
    joined_docs = "\n".join(doclist)
    
    return (
        f"{joined_docs}\n\n"
        + prompt_summarize  # 元のプロンプトに追加する
    )


# ----------------------
# From resource urls, extract the necessary information by LLM w/ prompt_summarize --> THIS DOES NOT WORK AS LLMs CANNOT ACCESS the URLS
# ----------------------
def summarize_documents_OLD():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="gpt-4", choices=AVAILABLE_LLMS)
    parser.add_argument("--input", type=str, default="outputs/redd_guideline_en.json")
    parser.add_argument("--output", type=str, default="redd_summary.json")
    args = parser.parse_args()

    input_path = args.input
    with open(input_path, "r", encoding="utf-8") as f:
        refs = json.load(f)
    # プロンプトを動的生成
    prompt_summarize = format_prompt_summarize_from_refs(refs)


    try:
#        client = create_client(args.model)
        client, client_model = create_client(args.model)
        print(client_model) 

        response = get_response_from_llm(
            prompt=prompt_summarize,
            client=client,
            model=client_model,
            system_message=system_prompt,
        )
        parsed = clean_llm_response(response)
        print(parsed["Verra"][0]["regulatory_frameworks"])

    except Exception as e:
        print("Error occurred:")
        traceback.print_exc()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{timestamp}_{args.output}"
    with open("outputs"+output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)


# ----------------------
# From resource JSON, extract the necessary information by LLM w/ prompt_summarize 
# ----------------------
def summarize_json_documents_single():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="gpt-4", choices=AVAILABLE_LLMS)
    parser.add_argument("--input", type=str, default="outputs/redd_guideline_en.json")
    parser.add_argument("--output", type=str, default="redd_summary.json")
    args = parser.parse_args()

    input_path = args.input
    with open(input_path, "r", encoding="utf-8") as f:
        refs = json.load(f)
    # プロンプトを動的生成
    prompt_summarize = format_prompt_summarize_from_refs(refs)
    print(prompt_summarize)

    try:
#        client = create_client(args.model)
        client, client_model = create_client(args.model)
        print(client_model) 

        response = get_response_from_llm(
            prompt=prompt_summarize,
            client=client,
            model=client_model,
            system_message=system_prompt,
        )
        parsed = clean_llm_response(response)
        #print(parsed["Verra"][0]["regulatory_frameworks"])

    except Exception as e:
        print("Error occurred:")
        traceback.print_exc()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"outputs/{timestamp}_{args.output}"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)



def summarize_json_documents_batch(model, input_dir_summarize, output_dir_summarize):

    client, client_model = create_client(model)
    print(f"Using model: {client_model}")
    
    combined_summaries = {}

    for fname in os.listdir(input_dir_summarize):
        if not fname.endswith(".json"):
            continue

        scheme_name = os.path.splitext(fname)[0]
        input_path = os.path.join(input_dir_summarize, fname)

        with open(input_path, "r", encoding="utf-8") as f:
            refs = json.load(f)

        prompt_summarize = format_prompt_summarize_from_refs(refs)

        try:
            response = get_response_from_llm(
                prompt=prompt_summarize,
                client=client,
                model=client_model,
                system_message=system_prompt,
            )
            parsed = clean_llm_response(response)
            combined_summaries[scheme_name] = parsed

        except Exception as e:
            print(f"Error processing {fname}:")
            traceback.print_exc()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{output_dir_summarize}/{timestamp}_merged_summaries.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined_summaries, f, ensure_ascii=False, indent=2)

    print(f"\n Merged summaries saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="meta-llama/llama-3.3-70b-instruct", choices=AVAILABLE_LLMS)
    parser.add_argument("--input_dir", type=str, default="ai_scientist/template_social_db/inputs/pdfs_regulatories/")
    parser.add_argument("--output_dir", type=str, default="experiments_outputs_social_db/shortened_pdfs/")
    parser.add_argument("--input_dir_summarize", type=str, default="experiments_outputs_social_db/shortened_pdfs/")
    parser.add_argument("--output_dir_summarize", type=str, default="experiments_outputs_social_db/")
    args = parser.parse_args()


    # 1: search documents via CoreSearch, and download them
    output_file_name = fetch_documents_via_core()

    # download_documents(output_path)  # I needed to download the files and check them manually instead of using this as CORESEARCH does not always return the correct URLs and the linked PDF files may not be accessible.

    # 2: Using Tool, fetch the necessary parts from the downloaded documents
    run_batch_pdf_to_json(args.input_dir, args.output_dir)

    # 3: summarize the documents
    summarize_json_documents_batch(args.model, args.input_dir_summarize, args.output_dir_summarize)
