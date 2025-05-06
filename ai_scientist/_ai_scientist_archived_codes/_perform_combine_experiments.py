import os
import json
from pathlib import Path
from shutil import copyfile
import argparse

def combine_results(base_dir):
    base_dir = Path(base_dir)
    experiments_dir = base_dir
    combined_md_path = base_dir / "combined_summary.md"
    combined_json_path = base_dir / "combined_result_summary.json"
    combined_fig_dir = base_dir / "combined_figures"
    combined_fig_dir.mkdir(exist_ok=True)

    combined_md_lines = ["# Combined Experiment Summary\n\n"]
    combined_json = {}

    for exp_parent in experiments_dir.iterdir():
        if not exp_parent.is_dir():
            continue

        exp_name = exp_parent.name

        # search sub directories starting with run_xxx 
        run_dirs = sorted([d for d in exp_parent.iterdir() if d.is_dir() and d.name.startswith("run_")])
        if not run_dirs:
            print(f"No run_* folders in {exp_name}, skipping.")
            continue

        # get the newest run directory
        exp_dir = run_dirs[-1]
        combined_md_lines.append(f"## {exp_name}\n\n")

        json_file = exp_dir / "result_summary.json"
        md_file = exp_dir / "result_summary.md"
        fig_candidates = list((exp_dir / "figures").glob("*.png")) + list(exp_dir.glob("*.png"))

        # --- case: JSON summary ---
        if json_file.exists():
            with open(json_file, "r") as f:
                summary_data = json.load(f)
                combined_json[exp_name] = summary_data

            for fig in summary_data.get("figures", []):
                fig_name = fig.get("filename")
                summary = fig.get("summary", "No summary provided.")
                src_path = exp_dir / "figures" / fig_name if (exp_dir / "figures" / fig_name).exists() else exp_dir / fig_name
                new_fig_name = f"{exp_name}_{fig_name}"
                dst_path = combined_fig_dir / new_fig_name
                if src_path.exists():
                    copyfile(src_path, dst_path)
                    combined_md_lines.append(f"### {fig_name}\n\n")
                    combined_md_lines.append(f"![{fig_name}](combined_figures/{new_fig_name})\n\n")
                    combined_md_lines.append(f"*{summary}*\n\n")
                else:
                    combined_md_lines.append(f"*Missing image for {fig_name}*\n\n")

        # --- case: Markdown summary (e.g., graph_strategy) ---
        elif md_file.exists():
            combined_md_lines.append(f"*Raw summary below (no JSON):*\n\n")
            with open(md_file, "r") as f:
                combined_md_lines.extend(f.readlines())
            combined_md_lines.append("\n")

            for fig_path in fig_candidates:
                new_fig_name = f"{exp_name}_{fig_path.name}"
                copyfile(fig_path, combined_fig_dir / new_fig_name)
                combined_md_lines.append(f"![{fig_path.name}](combined_figures/{new_fig_name})\n\n")

        else:
            combined_md_lines.append("*No summary found.*\n\n")

    # save combined results
    with open(combined_md_path, "w") as f:
        f.writelines(combined_md_lines)

    with open(combined_json_path, "w") as f:
        json.dump(combined_json, f, indent=2)




if __name__ == "__main__":
    script_dir = Path(os.path.dirname(__file__)).resolve()
    base_dir = script_dir.parent / "experiments_outputs"
    combine_results(base_dir)
