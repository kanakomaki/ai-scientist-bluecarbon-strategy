# extract_japan_carbon_projects.py
# 日本および国際的なカーボンクレジット関連制度（JCM, J-Blue, 環境省委託事業, 国会図書館, Verra, REDD+）からプロジェクト情報を抽出
# 初期バージョンではスクレイピングまたはPDF/API検索リンク生成までを行う

import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

# --------------------
# 環境省 公募結果ページ（例）
# --------------------
def scrape_moe_grants(base_url="https://www.env.go.jp/guide/budget/" ):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, "html.parser")
    links = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if href and any(word in href for word in ["jcm", "ブルーカーボン", "カーボン", "補助", "公募", "採択"]):
            links.append(urljoin(base_url, href))
    return {"source": "環境省予算情報", "project_links": links[:10]}  # 仮に最大10件

# --------------------
# JCM日本ページ
# --------------------
def get_jcm_project_links(base_url="https://www.jcm.go.jp/"):
    links = [
        "https://www.jcm.go.jp/ph-jp/projects",
        "https://www.jcm.go.jp/jp-jp/projects",
        "https://www.jcm.go.jp/th-jp/projects",
    ]
    return {"source": "JCM公式", "project_pages": links}

# --------------------
# 国会図書館 リサーチナビ（検索リンク生成）
# --------------------
def generate_ndl_search_links():
    base = "https://rnavi.ndl.go.jp/books/search.php?"
    keywords = ["カーボンクレジット", "ブルーカーボン", "JCM", "J-Blue"]
    links = [f"{base}query={kw}" for kw in keywords]
    return {"source": "国会図書館検索リンク", "search_queries": links}

# --------------------
# JBE公式（現時点では手動対応が現実的）
# --------------------
def jblue_info():
    return {
        "source": "JBE公式ページ",
        "url": "https://www.blueeconomy.jp/credit",
        "note": "掲載プロジェクト数は少ないが、将来的には拡充の可能性あり。PDFダウンロードと人手抽出が現実的。"
    }

# --------------------
# Verra Registry（国際認証プロジェクト）
# --------------------
def verra_registry_links():
    return {
        "source": "Verra Registry",
        "url": "https://registry.verra.org/app/search/VCS",
        "note": "プロジェクト名、国、クレジット量、認証状況などを検索・表示可能。CSVエクスポートも対応。"
    }

# --------------------
# REDD+ Project Database（国際REDD事業）
# --------------------
def redd_project_db():
    return {
        "source": "REDD+ Project Database",
        "url": "https://www.reddprojectsdatabase.org/",
        "note": "国・資金提供者・プロジェクト名でフィルタ可能。プロジェクト概要や関係者の構造分析に有効。"
    }

# --------------------
# 総合実行
# --------------------
def extract_all_sources():
    return {
        "moe_grants": scrape_moe_grants(),
        "jcm_projects": get_jcm_project_links(),
        "ndl_links": generate_ndl_search_links(),
        "jblue_page": jblue_info(),
        "verra_registry": verra_registry_links(),
        "redd_projects": redd_project_db()
    }

if __name__ == "__main__":
    results = extract_all_sources()
    with open("japan_carbon_project_sources.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("✅ 日本および国際のカーボンクレジット関連リンクを japan_carbon_project_sources.json に保存しました")
