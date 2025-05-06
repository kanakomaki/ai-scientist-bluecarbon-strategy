import os
import requests
from typing import Dict, List, Optional

from ai_scientist.tools.base_tool import BaseTool

import os
import requests
from typing import Dict, List, Optional

from ai_scientist.tools.base_tool import BaseTool

from datetime import datetime

import backoff
import requests
from requests.exceptions import RequestException

class CoreSearchTool(BaseTool):
    def __init__(
        self,
        name: str = "SearchCORE",
        description: str = (
            "Search for relevant open-access literature using the CORE API. "
            "Provide a search query to find relevant papers. API key must be set in CORE_API_KEY env variable."
        ),
        max_results: int = 3,  # トークン削減のため小さめに設定
    ):
        parameters = [
            {
                "name": "query",
                "type": "str",
                "description": "The search query to find relevant papers.",
            }
        ]
        super().__init__(name, description, parameters)
        self.max_results = max_results
        self.api_key = os.getenv("CORE_API_KEY")
        if not self.api_key:
            raise ValueError("CORE API key not found. Set CORE_API_KEY environment variable.")

    def use_tool(self, query: str) -> Optional[str]:
        results = self.search_core_api(query)
        if results:
            return results
        return "No papers found."


    @backoff.on_exception(
        backoff.expo,
        RequestException,
        max_tries=5,
        jitter=backoff.full_jitter,
    )
    def search_core_api(self, query: str) -> List[str]:
        url = "https://api.core.ac.uk/v3/search/outputs/"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"q": f"fullText:'{query}'", "limit": 10}

        print(f"Sending request to CORE API for query: '{query}'")
        response = requests.get(url, headers=headers, params=params)

        # if response.status_code != 200:
        #     print(f"Error: {response.status_code} - {response.text}")
        #     return []
        if response.status_code == 429:
            raise RequestException("Rate limit hit (429)")
        elif not response.ok:
            raise RequestException(f"Request failed with status {response.status_code}")

        results = response.json().get("results", [])
        summaries = []
        print(len(results))

        for i, item in enumerate(results):
            #print(item)
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
            url = item.get("urls", "No link available")
            summaries.append(
              f"{i+1}. {title}\nAuthors: {authors}\nYear: {year}\nAbstract: {abstract}\nLink: {url}\n"
            #    f"{i+1}. {title}\nAuthors: {authors}\nYear: {year}\nAbstract: {abstract}\n"  # for shortening 
            )

        # self.save_results_to_txt(summaries)
        return summaries


    @backoff.on_exception(
        backoff.expo,
        RequestException,
        max_tries=5,
        jitter=backoff.full_jitter,
    )
    def search_core_api_semanticformat(self, query: str) -> List[dict]:
        url = "https://api.core.ac.uk/v3/search/outputs/"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"q": f"fullText:'{query}'", "limit": 10}

        print(f"Sending request to CORE API for query: '{query}'")
        response = requests.get(url, headers=headers, params=params)

        # if response.status_code != 200:
        #     print(f"Error: {response.status_code} - {response.text}")
        #     return []
        if response.status_code == 429:
            raise RequestException("Rate limit hit (429)")
        elif not response.ok:
            raise RequestException(f"Request failed with status {response.status_code}")
        
        results = response.json().get("results", [])
        papers = []

        for item in results:
            title = item.get("title", "No title")
            authors_list = item.get("authors", [])
            authors = ", ".join([a.get("name", "Unknown") for a in authors_list])
            year = item.get("publishedDate", "Unknown")
            year = year.split("T")[0] if year else "Unknown"
            abstract = item.get("abstract", "No abstract available.")
            if len(abstract) > 800:
                abstract = abstract[:800] + "..."
            venue = item.get("source", {}).get("title", "Unknown venue")

            papers.append({
                "title": title,
                "authors": authors,
                "venue": venue,
                "year": year,
                "abstract": abstract,
                "citationStyles": {
                    "bibtex": f"@article{{{authors.split(',')[0]}{year},\n"
                            f"  title={{ {title} }},\n"
                            f"  author={{ {authors} }},\n"
                            f"  journal={{ {venue} }},\n"
                            f"  year={{ {year} }}\n}}"
                }
            })

        return papers


    @staticmethod
    def save_results_to_txt(results: List[str], output_path: str = "core_results.txt"):
        output_path = "core_results" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in results:
                f.write(entry + "\n\n")
        print(f"Saved {len(results)} results to {output_path}")


# wrapper function for CoreSearchTool
_core_tool = CoreSearchTool()
def search_core_api_semanticformat(query: str, result_limit: int = 5) -> List[str]:
    return _core_tool.search_core_api_semanticformat(query)


