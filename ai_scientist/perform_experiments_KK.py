# This script is a "wrapper" kind of code used to run the experiments for the AI scientist project.

import subprocess
import os

def run_script(script_path, log_path=None, input_text=None):
    print(f"=====Step 3: Running script = {script_path} ======")
    try:
        result = subprocess.run(["python", script_path], input=input_text, capture_output=True, text=True, check=False)
        if log_path:
            with open(log_path, "w") as f:
                f.write(result.stdout)
                f.write("\n\nSTDERR:\n" + result.stderr)

        if result.returncode != 0:
            print(f"[some warnings from the log] {script_path}.  Check log for details.")
    except Exception as e:
        print(f"[EXCEPTION] Failed to run {script_path}: {e}")


if __name__ == "__main__":
    
    # experiment scripts ~ currently 3 kinds of experiments in "templates" folder
    # you can add more experiments here
    # each experiment should create outputs in "experiments_outputs" folder
    # the outputs should contain any of "md", "json", and "png" files

    print(f"=====Step 3: STARTED =====================")

    scripts = {
        "graph_strategy": {
            "script": "ai_scientist/templates/graph_strategy/experiment.py",
            "log": "experiments_outputs/graph_strategy/experiment_log.txt",
            "input_text": "yes\nyes\nyes\nyes\n"  # CLI input for the script (some questions for the user)
        },
        "predict_mangrove": {
            "script": "ai_scientist/templates/predict_mangrove/experiment.py",
            "log": "experiments_outputs/predict_mangrove/experiment_log.txt",
            "input_text": None
        },
        "typhoon_analysis": {
            "script": "ai_scientist/templates/typhoon_analysis/experiment.py",
            "log": "experiments_outputs/typhoon_analysis/experiment_log.txt",
            "input_text": None
        },
    }

    for name, config in scripts.items():
        print(f"===== Step 3: ===== Running experiment: {name} =====")
        run_script(config["script"], config["log"], config["input_text"])
