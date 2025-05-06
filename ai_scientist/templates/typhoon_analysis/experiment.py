import os
import json
import inspect
import argparse

from ai_scientist.llm import get_response_from_llm
from ai_scientist.llm import (
    AVAILABLE_LLMS,
    create_client,
    get_response_from_llm,
)

import datetime
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
import subprocess

def make_prompt_for_plot(fn_name, source_code):
    prompt = f"""
You are an ambicious earth science PhD researcher. 

The following Python source_code is used to generate typhoon speed and passage maps using historical wind speed data:
Map name: `{fn_name}`

```python
{source_code}
```

Please summarize what this map means in 2-3 sentences. Focus on what kind of input it uses, what the output means, and what purpose it serves in the context of a typhoon disaster analysis.
"""
    return prompt

def run_experiment(data_path=None, r_script_path=None, output_path=None, summary_path=None, llm_model=None):
    # read the R script
    with open(r_script_path, "r") as f:
        source_code = f.read()
 
    # run the R script
    output_path = os.path.abspath(output_path)
    subprocess.run(["Rscript", r_script_path, f"--out_dir={output_path}"], cwd="ai_scientist/templates/typhoon_analysis/", check=True)

    # Create the LLM client
    client, LLM_model = create_client(llm_model)

    # Send to LLM for summarization
    prompts = [
            ("max_wind_heatmap1.png", make_prompt_for_plot("max_wind_heatmap", source_code)),
            ("typhoon_passage_count.png", make_prompt_for_plot("typhoon_passage_count", source_code)),
            ("typhoon_impact_500km_count.png", make_prompt_for_plot("typhoon_impact_500km_count", source_code)),
    ]

    summary = {"figures": []}

    for filename, prompt in prompts:
        desc, _ = get_response_from_llm(
            prompt=prompt,
            client=client,
            model=LLM_model,
            system_message="",
            print_debug=False,
        )
        summary["figures"].append({
            "filename": filename,
            "summary": desc.strip()
        })


    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)




if __name__ == "__main__":

    base_dir = os.path.dirname(__file__)

    parser = argparse.ArgumentParser(description="Experiment: Typhoon Analysis")
    parser.add_argument(
        "--llm_model",
        type=str,
        default="meta-llama/llama-3.3-70b-instruct",
        choices=AVAILABLE_LLMS,
        help="Model to use for AI Scientist.",
    )
    args = parser.parse_args()


    timenow = datetime.datetime.now()
    output_path=f"experiments_outputs/typhoon_analysis/run_{timenow:%Y%m%d_%H%M%S}/"
    os.makedirs(output_path, exist_ok=True)


    r_script_path = os.path.join(base_dir, "src", "olango_typhoon_analysis.r")

    run_experiment(
        data_path="ai_scientist/templates/typhoon_analysis/inputs/parsed_typhoon_data.csv",
        r_script_path=r_script_path,
        output_path=output_path,
        summary_path=f"{output_path}/result_summary.json",
        llm_model=args.llm_model
    )
