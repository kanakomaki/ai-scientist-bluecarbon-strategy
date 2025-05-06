import os
import requests
import argparse
from typing import List


def search_core_api(query: str, api_key: str, max_results: int = 2) -> List[str]:
    url = "https://api.core.ac.uk/v3/search/outputs/"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"q": f"fullText:'{query}'", "limit": 10}

    print(f"Sending request to CORE API for query: '{query}'")
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return []

    results = response.json().get("results", [])
    summaries = []
    print(len(results))

    for i, item in enumerate(results):
        print(item)
        title = item.get("title", "No title")
        # authors リストが dict のリストであるため "name" を取得
        authors_list = item.get("authors", [])
        authors = ", ".join([a.get("name", "Unknown") for a in authors_list])
        #authors = ", ".join(item.get("authors", []))
        year = item.get("publishedDate", "Unknown")
        year = year.split("T")[0] if year else "Unknown"
        abstract = item.get("abstract", "No abstract available.")
        if len(abstract) > 800:
            abstract = abstract[:800] + "..."
        url = item.get("fullTextLink", "No link available")
        summaries.append(
          #  f"{i+1}. {title}\nAuthors: {authors}\nYear: {year}\nAbstract: {abstract}\nLink: {url}\n"
            f"{i+1}. {title}\nAuthors: {authors}\nYear: {year}\nAbstract: {abstract}\n"  # for shortening 
        )

    return summaries


def save_results_to_txt(results: List[str], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in results:
            f.write(entry + "\n\n")
    print(f"Saved {len(results)} results to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, required=True, help="Search query for CORE API")
    parser.add_argument("--output", type=str, default="core_results.txt", help="Output file path")
    parser.add_argument("--max-results", type=int, default=5, help="Number of search results to fetch")
    args = parser.parse_args()

    api_key = os.getenv("CORE_API_KEY")
    if not api_key:
        raise ValueError("CORE_API_KEY environment variable not set.")

    results = search_core_api(args.query, api_key, args.max_results)
    if results:
        save_results_to_txt(results, args.output)
    else:
        print("No results found or error occurred.")
