# pdf_to_scheme_json.py
# 英文PDF文書（例：REDD+制度ガイドライン）から各項目に最も類似した段落をsemantic similarityで抽出し、JSON形式に変換するPoCスクリプト

import fitz  # PyMuPDF
import json
import os
from sentence_transformers import SentenceTransformer, util
import re
import argparse

# ----------------------
# フィールド別クエリ文（英語）
# ----------------------
SCHEME_QUERIES = {
    "regulatory_frameworks": "Describe the regulatory framework or policy structure of the scheme.",
    "application_methods": "Explain how applicants can apply or participate in the scheme.",
    "main_targets": "What are the main objectives or target activities of the scheme?",
    "stakeholder_names": "List or describe key stakeholders involved in the scheme.",
    "available_fundings": "What types of funding or financial support are available?",
    "conditions_to_get_credits": "What are the eligibility or requirements to receive carbon credits?",
    "expected_periods": "What is the expected duration or project period?",
    "expected_difficulty": "Describe any challenges or complexities in implementing the scheme.",
    "expected_costs": "What are the expected costs or financial burdens?",
    "pros_and_cons": "List the benefits and drawbacks of the scheme.",
    "Advantages_in_Japanese_applicants": "Are there any benefits for Japanese companies or institutions?",
    "other_notes": "Provide any other relevant remarks or considerations."
}

# ----------------------
# PDFからすべての段落を抽出
# ----------------------
def extract_all_paragraphs(pdf_path: str):
    doc = fitz.open(pdf_path)
    paragraphs = []
    for page in doc:
        text = page.get_text("text")  # プレーンテキストで取得
        # 段落分割：2つ以上の連続する改行で区切る
        parts = re.split(r"\n\s*\n", text)
        for p in parts:
            cleaned = p.strip().replace("\n", " ")  # 改行を空白に
            if len(cleaned) > 80:  # 最低文字数を設定（調整可能）
                paragraphs.append(cleaned)
    return paragraphs

# ----------------------
# 類似度にもとづく段落分類
# ----------------------
def extract_by_semantic_similarity(paragraphs: list, query_dict: dict, top_k: int = 3) -> dict:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    para_embeddings = model.encode(paragraphs, convert_to_tensor=True)
    
    results = {}
    for field, query in query_dict.items():
        query_emb = model.encode(query, convert_to_tensor=True)
        cos_scores = util.cos_sim(query_emb, para_embeddings)[0]
        top_indices = cos_scores.argsort(descending=True)[:top_k]
        top_paragraphs = [paragraphs[int(idx)] for idx in top_indices]
        results[field] = top_paragraphs
    return results

# ----------------------
# 保存用JSON生成
# ----------------------
def save_to_json(data: dict, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ----------------------
# PROCESS A SINGLE PDF FILE
# ----------------------
def process_pdf(pdf_path="ai_scientist/experiments/bluecarbon/data/pdfs/redd_guideline_en.pdf", out_path="./outputs/redd_guideline_en.json"):
    paragraphs = extract_all_paragraphs(pdf_path)
    extracted = extract_by_semantic_similarity(paragraphs, SCHEME_QUERIES)
    save_to_json(extracted, out_path)
    print(f"SAVED!: {out_path}")


# ----------------------
# PROCESS ALL PDF FILES
# ----------------------
def process_all_pdfs(input_dir: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(input_dir):
        if not fname.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(input_dir, fname)
        name = os.path.splitext(fname)[0]
        out_path = os.path.join(output_dir, f"{name}.json")
        try:
            process_pdf(pdf_path, out_path)
        except Exception as e:
            print(f"Failed to process {fname}: {e}")

def run_batch_pdf_to_json(input_dir: str, output_dir: str):

    process_all_pdfs(input_dir, output_dir)


# ----------------------
# MAIN FUNCTION
# ----------------------
if __name__ == "__main__":
    os.makedirs("./outputs", exist_ok=True)
    # process_pdf()

    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, default="ai_scientist/experiments/bluecarbon/data/pdfs/")
    parser.add_argument("--output_dir", type=str, default="outputs/shortened_pdfs/")
    args = parser.parse_args()

    run_batch_pdf_to_json(args.input_dir, args.output_dir)
