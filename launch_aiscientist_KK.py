# Arranged from AI-Scientist-v2: Launch AI Scientist
# THIS CODE IS FOR RUNNING THE FULL AI SCIENTIST PROOF OF CONCEPT (POC) FLOW
#    preidea --> idea -> social review -> experiment 1 -> experiment 2 -> experiment 3 -> writeup

import argparse
import os
import shutil
import json
from datetime import datetime
import os.path as osp
from pathlib import Path

from ai_scientist.llm import create_client,AVAILABLE_LLMS

from ai_scientist.perform_ideation_KK import perform_ideation, generate_ideas  # CORE API is requred

from ai_scientist.perform_experiments_social_db import perform_experiments_socialDB

from ai_scientist.perform_experiments_KK import run_script as perform_experiments_run_script

from ai_scientist.perform_combine_experiments import combine_results

from ai_scientist.perform_writeup_KK_v2 import perform_writeup
# from ai_scientist.perform_icbinb_writeup_KK import (
#     perform_writeup as perform_icbinb_writeup,
#     gather_citations,
# )

from ai_scientist.perform_llm_review import perform_review, load_paper
from ai_scientist.perform_vlm_review import perform_imgs_cap_ref_review

from ai_scientist.utils.token_tracker import token_tracker


def save_token_tracker(idea_dir):
    with open(osp.join(idea_dir, "token_tracker.json"), "w") as f:
        json.dump(token_tracker.get_summary(), f)
    with open(osp.join(idea_dir, "token_tracker_interactions.json"), "w") as f:
        json.dump(token_tracker.get_interactions(), f)

def find_pdf_path_for_review(idea_dir):
    pdf_files = [f for f in os.listdir(idea_dir) if f.endswith(".pdf")]
    reflection_pdfs = [f for f in pdf_files if "reflection" in f]
    print(f"pdfs: {pdf_files}, Reflection PDFs: {reflection_pdfs}")
    if reflection_pdfs:
        # First check if there's a final version
        #final_pdfs = [f for f in reflection_pdfs if "final" in f.lower()]
        final_pdfs = pdf_files # arranged by KK 2025
        if final_pdfs:
            # Use the final version if available
            sorted_by_name = sorted(final_pdfs, reverse=True)
            pdf_path = osp.join(idea_dir, final_pdfs[0])
    else:
        # if no reflection number, use the most recent one
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in {idea_dir}. Please check the directory.")
        sorted_by_name = sorted(pdf_files, reverse=True)
        pdf_path = osp.join(idea_dir, sorted_by_name[0]) # newest file
    print(f"PDF path for review: {pdf_path}")
    return pdf_path

def merge_experiment_outputs(base_dir_list, combined_dir):
    """
    Merge multiple experiment outputs into a single combined folder.
    
    Args:
        base_dir_list (list): List of experiment output folders (e.g., ['experiments/stakeholder', ...])
        combined_dir (str): Destination combined directory (e.g., 'experiments/combined')
    """
    if not os.path.exists(combined_dir):
        os.makedirs(combined_dir)

    figures_dir = os.path.join(combined_dir, "figures")
    if not os.path.exists(figures_dir):
        os.makedirs(figures_dir)

    # Merge idea.md and summaries
    for base_dir in base_dir_list:
        # Copy figures
        fig_path = os.path.join(base_dir, "figures")
        if os.path.exists(fig_path):
            for figfile in os.listdir(fig_path):
                src_fig = os.path.join(fig_path, figfile)
                dst_fig = os.path.join(figures_dir, figfile)
                shutil.copy(src_fig, dst_fig)

        # (Optional) Merge summaries
        log_path = os.path.join(base_dir, "logs", "0-run", "baseline_summary.json")
        if os.path.exists(log_path):
            dst_log = os.path.join(combined_dir, f"summary_{os.path.basename(base_dir)}.json")
            shutil.copy(log_path, dst_log)

    print(f"Merged {len(base_dir_list)} experiments into {combined_dir}")







def main(args):

    # === Step 1: Perform Ideation ===
    # This step needs a preliminary idea (client's needs and project goals) file to run perform_ideation_KK.py
    print("\n=== Step 1: Perform Ideation STARTED ===\n")
    # Create the LLM client
    client, client_model = create_client(args.model)
    # Set a Literature Search API & a prompt for the LLM
    tools_dict, system_prompt, idea_generation_prompt, idea_reflection_prompt = perform_ideation()    
    # set the base directory for preliminary ideas 
    base_dir = osp.join("pre_ideas/", args.project_name) 
    ideas = generate_ideas(
        project_name=args.project_name,
        base_dir=base_dir,
        preliminary_ideas=args.preliminary_ideas,
        client=client,
        model=client_model,
        skip_generation=args.skip_idea_generation,
        max_num_generations=args.max_num_generations,
        num_reflections=args.num_reflections,
        tools_dict=tools_dict,
        system_prompt=system_prompt,
        idea_generation_prompt=idea_generation_prompt,
        idea_reflection_prompt=idea_reflection_prompt,
    )
    print("=== Step 1: Perform Ideation COMPLETED ===\n")


    print("\n=== Step 2: Perform Experiments [Social DB] STARTED ===\n")
    #---- This step does literature reviews and creates "GraphDB" essential for the social experiments ----#
    #---- You can skip this step if you want to use the existing GraphDB or if you do not conduct "graph strategy" experiment in Step 3----#
    perform_experiments_socialDB(args)
    print("=== Step 2: Perform Experiments [Social DB] COMPLETED ===\n")




    print("\n=== Step 3: Perform Experiments [Social & Science] STARTED ===\n")
    #---- This step conducts some experiments from templates [currently 3 experiments settings] ----#
    #---- You can pick some of them or all of them ----#
    #---- The results will be comibed in the next step ----#
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
        perform_experiments_run_script(config["script"], config["log"], config["input_text"])
    print("=== Step 3: Perform Experiments [Social & Science] COMPLETED ===\n")



    print("\n === Step 4: Perform Combine [Social & Science Experiments Results] STARTED ===\n")
    # This step combines the results of the experiments into a single folder (original script)
    combine_results(args.base_dir_4)
    print("=== Step 4: Perform Combine [Social & Science Experiments Results] COMPLETED ===\n")



    print("\n=== Step 5: Perform Writeup STARTED ===\n")
    # This step generates a writeup of the experiments and ideas (modified script from AI-Scientist)
    if not args.skip_writeup:
        writeup_success = False
        for attempt in range(args.writeup_retries):
            print(f"Writeup attempt {attempt+1} of {args.writeup_retries}")
            writeup_success = perform_writeup(
                exp_outputs_base_folder=args.exp_outputs_base_folder,
                preliminary_ideas=args.preidea_dir,
                idea_dir=args.idea_dir,
                no_writing=False,
                num_cite_rounds=20,
                small_model="meta-llama/llama-3.3-70b-instruct",
                big_model="anthropic/claude-3.5-sonnet",
                n_writeup_reflections=5,
                page_limit=10,
            )
        if not writeup_success:
            print("Writeup process did not complete successfully after all retries.")
    print("\n=== Step 5: Perform Writeup COMPLETED ===\n")



    print("\n=== Step 6: Perform Review STARTED ===\n")
    # This step performs a review of the generated PDF paper (modified script from AI-Scientist)
    if not args.skip_review and not args.skip_writeup:
        # Perform paper review if the paper exists
        pdf_path = find_pdf_path_for_review(args.exp_outputs_base_folder)
        if os.path.exists(pdf_path):
            print("Paper found at: ", pdf_path)
            paper_content = load_paper(pdf_path)

            client, client_model = create_client(args.model_review)

            review_text = perform_review(paper_content, client_model, client)

            review_img_cap_ref = perform_imgs_cap_ref_review(
                client, client_model, pdf_path
            )
            with open(osp.join(args.exp_outputs_base_folder, "review_text.txt"), "w") as f:
                f.write(json.dumps(review_text, indent=4))
            with open(osp.join(args.exp_outputs_base_folder, "review_img_cap_ref.json"), "w") as f:
                json.dump(review_img_cap_ref, f, indent=4)
    print("\n=== Step 6: Perform Review COMPLETED ===\n")




    print("\n=== ALL SELECTED STEPS COMPLETED ===")




if __name__ == "__main__":

    # parameters for the AI Scientist PoC flow
    script_dir = osp.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Launch full AI Scientist PoC flow.")

    # -- 0: general parameters --    
    project_name = "bluecarbon"
    parser.add_argument("--project_name", type=str, default=project_name,
                                            help="Project name to run the AI Scientist PoC flow")

    # -- 1: perform_ideation --
    parser.add_argument("--preliminary_ideas", type=str, default="preideas_02.json",
                                            help="Preliminary idea (client's needs and project goals) file to run perform_ideation_KK.py in [pre_ideas]/[project_name] folder")
    parser.add_argument("--model",type=str, default="meta-llama/llama-3.3-70b-instruct",choices=AVAILABLE_LLMS,
                                            help="Model to use for AI Scientist.")
    parser.add_argument("--skip-idea-generation", action="store_true",default=False,
                                            help="Skip proposal generation and use existing proposals.")
    parser.add_argument("--max-num-generations", type=int,default=2,help="Maximum number of proposal generations.")
    parser.add_argument("--num-reflections", type=int,default=2,help="Number of reflection rounds per proposal.")

    # -- 2: perform_experiments_social_DB --
    template_dir = osp.join(script_dir, "ai_scientist/template_social_db")
    experiment_dir = osp.join(script_dir, "experiments_outputs_social_db")
    print(f"Template directory: {template_dir}")
    print(f"Experiment directory: {experiment_dir}")
    parser.add_argument("--input_dir_21", type=str, default = template_dir + "/inputs/pdfs_regulatories/")
    parser.add_argument("--output_dir_21", type=str, default = experiment_dir + "/shortened_pdfs/")
    parser.add_argument("--input_dir_summarize_21", type=str, default = experiment_dir + "/shortened_pdfs/")
    parser.add_argument("--output_dir_summarize_21", type=str, default = experiment_dir)
    parser.add_argument("--input_22", type=str, default = experiment_dir + "/20250416_112225_merged_summaries.json")
    parser.add_argument("--output_22", type=str, default = experiment_dir + "/___tmp___stakeholder_graph.graphml")
    parser.add_argument("--pdf_dir_23", type=str, default = template_dir + "/inputs/pdfs_projects")
    parser.add_argument("--graphml_23", type=str, default = experiment_dir + "/___tmp___stakeholder_graph.graphml")
    parser.add_argument("--output_23", type=str, default = experiment_dir + "/___tmp___merged_project_graph.graphml")

    # -- 3: perform_experiments --

    # ---4: perform_combine_experiments ---
    parser.add_argument("--base_dir_4", type=str, required=False, default=script_dir)

    # -- 5: perform_writeup --
    parser.add_argument('--writeup', action='store_true', help="Generate writeup")
    parser.add_argument("--skip_writeup", action="store_true", help="If set, skip the writeup process")
    parser.add_argument('--exp_outputs_base_folder', type=str, default="experiments_outputs/combined_20250501_063438/", 
                                       help="Path to the experiments result files that will be used for writeup")
    parser.add_argument('--preidea_dir', type=str, default=f"pre_ideas/{project_name}/preideas_02.json", 
                                       help="Path to the generated idea file [json] by Step1 that will be used for writeup")
    parser.add_argument('--idea_dir', type=str, default="ideas/bluecarbon/ideas_saved.json", 
                                       help="Path to the generated idea file [json] by Step1 that will be used for writeup")
    parser.add_argument("--writeup-retries",type=int, default=1, help="Number of retries for LaTeX writeup generation.") # added by KK 2025APR30
    parser.add_argument("--num_cite_rounds", type=int,default=3, help="Number of citation rounds to perform")

    # -- 6: perform_review --
    parser.add_argument("--skip_review", action="store_true", help="If set, skip the review process")
    parser.add_argument("--model_review",type=str, default="openai/gpt-4.1-nano", choices=AVAILABLE_LLMS,
                                                   help="Model to use for AI Scientist.")

    args = parser.parse_args()
    print(f"args =  ",args)
    print("==============================")
    print("=== SETTING args COMPLETED ===")
    print("==============================")
    # ------------------------------------------------------------------------------------------



    main(args)
