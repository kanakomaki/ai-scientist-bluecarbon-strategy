# コードを改修して繰り返す実験のとき
import os
import shutil
import json
from datetime import datetime
from ai_scientist.llm import create_client, get_response_from_llm
from ai_scientist.perform_experiments import perform_experiments
import re

SYSTEM_PROMPT = """
You are an AI expert in policy-oriented graph strategy analysis.
"""

EXPERIMENT_PROMPT = """
We are working on the following research idea with our client of a Japanese SME:
    {
        "Name": "mangrove_blue_carbon",
        "Title": "Mangrove Blue Carbon Credits for Japanese SMEs: A Strategic Plan",
        "Short Hypothesis": "Japanese SMEs can effectively utilize mangroves in the Philippines for Blue Carbon credits, contributing to climate change mitigation and sustainable development, by developing a strategic plan that incorporates stakeholder mapping, literature review on monitoring methods, and preliminary data analysis using open tools.",
        "Related Work": "The proposal builds on existing research on blue carbon initiatives and payment for ecosystem service programs, while addressing the lack of functioning projects supported by carbon finance and the need for policies and frameworks to achieve this.",
        "Abstract": "This proposal outlines a strategic plan for Japanese SMEs to utilize mangroves in the Philippines for Blue Carbon credits, incorporating stakeholder mapping, literature review on monitoring methods, and preliminary data analysis using open tools. The plan aims to contribute to climate change mitigation and sustainable development, while addressing the constraints of limited budget and lack of experience in international certification and administrative procedures.",
        "Experiments": [
            "Conduct stakeholder mapping to identify key players and their roles in the Blue Carbon credit market",
            "Review literature on monitoring methods for mangrove ecosystems and Blue Carbon credits",
            "Analyze preliminary data using open tools, such as Google Earth Engine, to assess the potential for mangrove restoration and conservation in the Philippines"
        ],
        "Risk Factors and Limitations": [
            "Limited budget and lack of experience in international certification and administrative procedures",
            "Complexity of stakeholder engagement and coordination",
            "Uncertainty in carbon credit markets and pricing"
        ]
    }

Please fully revise the provided Python script `experiment.py` to be a focused experimental module.

Your output script must:
- Recommend the optimal carbon credit scheme for the SME (e.g. Verra, J-Blue) based on stakeholder graph data
- Load the graph from a `merged_project_graph.graphml` file and inject a SME node with user preferences
- Calculate and use:
  - shortest paths from SME to certification nodes
  - degree centrality per stakeholder and grouped by scheme
- Justify recommendations in a markdown report with a LLM model in terms of:
  - pros and cons
  - stakeholder support pathway
  - suggested next steps
- Write final output to a markdown file

You must:
- Replace the original code logic if necessary
- Avoid including explanations
- Only return valid Python inside a single ```python code block

Put the date/time at the end of the code.
"""

def extract_python_code_from_response(response):
    if isinstance(response, tuple):
        response = response[0]
    if response is None:
        raise ValueError("Response is None")

    # Remove non-code preambles like === RAW RESPONSE === など
    code_block_matches = re.findall(r"```(?:python)?\s*\n(.*?)```", response, re.DOTALL)
    if code_block_matches:
        return code_block_matches[0]
    else:
        raise ValueError("No python code block found in LLM response")


def main():
    model = "meta-llama/llama-3.3-70b-instruct"
    base_template = "ai_scientist/templates/graph_strategy"
    results_dir = "ai_scientist/results"
    os.makedirs(results_dir, exist_ok=True)

    # 1. Set up result folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    idea_name = f"{timestamp}_graph_strategy"
    idea_dir = os.path.join(results_dir, idea_name)
    shutil.copytree(base_template, idea_dir)

    # 2. Load original experiment
    exp_path = os.path.join(idea_dir, "experiment.py")
    with open(exp_path, "r") as f:
        original_code = f.read()

    # 3. Edit using LLM
    client, model_name = create_client(model)

    prompt = f"Here is the original code:\n```python\n{original_code}\n```\n\n{EXPERIMENT_PROMPT}"
    response = get_response_from_llm(system_message=SYSTEM_PROMPT, prompt=prompt, client=client, model=model_name)
    new_code = extract_python_code_from_response(response)
    print("=== Modified Code Preview ===\n", new_code)

    # Overwrite experiment.py
    with open(exp_path, "w") as f:
        f.write(new_code)

    # 4. Run experiment
    print("\U0001F501 Running experiment...")
    try:
        results = perform_experiments(None, idea_dir, None, baseline_results={})
    except Exception as e:
        print("\u274C Error during experiment:", e)
        return

    print(f"\u2705 Experiment completed. Results saved to: {idea_dir}")

if __name__ == "__main__":
    main()
