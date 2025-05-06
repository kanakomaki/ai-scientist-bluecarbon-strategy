import argparse
import os
import os.path as osp

from ai_scientist.llm import create_client, get_response_from_llm, AVAILABLE_LLMS

from ai_scientist.template_social_db.perform_research_regulatory import (fetch_documents_via_core, download_documents, 
                                                                        run_batch_pdf_to_json, summarize_json_documents_batch)
from ai_scientist.template_social_db.perform_stakeholder_mapping import (extract_relationships_llama_ver02, build_networkx_graph, 
                                                                         visualize_graph, export_interactive_graph, nx)
from ai_scientist.template_social_db.perform_project_extractor import (export_interactive_graph, extract_paragraphs_from_pdf, 
                                                                       extract_project_relationships, merge_into_existing_graph)

def perform_experiments_socialDB(args):
    # Step 2: perform_experiments_social_db.py
    # 1. perform regulatory research
    # 2. perform stakeholder mapping
    # 3. perform project extraction

    print("=== Step 2: STARTED ===")
    # set the base directory: run with launch_aiscient.py, the base directory is set to the root directory!!!

    print("=== Step 2-1: perform_regulatory research ===")
    print("=== Step 2-1: search regulatory documents via CoreSearch, download them, summarize the documents  ===")
    # 1: search documents via CoreSearch, and download them
    output_file_name = fetch_documents_via_core()
    # download_documents(output_path)  
    #   #      ! I needed to download the files manually instead of using this method,
    #   #      ! because CORE-SEARCH does not always return the correct URLs and the linked PDF files may not be accessible.
    # 2: Using Tool, fetch the necessary parts from the downloaded documents
    print(args.input_dir_21, args.output_dir_21)
    run_batch_pdf_to_json(args.input_dir_21, args.output_dir_21)
    # 3: summarize the documents
    summarize_json_documents_batch(args.model, args.input_dir_summarize_21, args.output_dir_summarize_21)


    print('=== Step 2-2: perform stakeholder mapping ===')
    print("=== Step 2-2: extract social relationships from the collected documents, and save a GraphDB  ===")
    relationships = extract_relationships_llama_ver02(args.input_22, args.model)
    G = build_networkx_graph(relationships)
    nx.write_graphml(G, args.output_22)
    print(f"Graph saved to {args.output_22}")
    visualize_graph(G)
    export_interactive_graph(G)


    print("=== Step 2-3: perform project extraction ===")
    print("=== Step 2-3: extend the GraphDB with external projects data ===")
    all_relationships = []
    for fname in os.listdir(args.pdf_dir_23):
        if fname.endswith(".pdf"):
            print(f" Processing: {fname}")
            pdf_path = os.path.join(args.pdf_dir_23, fname)
            paras = extract_paragraphs_from_pdf(pdf_path)
            rels = extract_project_relationships(paras, args.model)
            all_relationships.extend(rels)
    G = merge_into_existing_graph(args.graphml_23, all_relationships, args.output_23)
    export_interactive_graph(G)


    print("=== Step 2: COMPLETED ===")





if __name__ == "__main__":
    print("=== Step 2: STARTED ===")

    # set the base directory: run with perform_experiments_social_db.py (if run with launch_aiscient.py, the base directory is set to the root directory!!!)
    script_dir = osp.dirname(os.path.abspath(__file__))
    parent_dir = osp.dirname(script_dir)
    base_dir = script_dir
    template_dir = osp.join(script_dir, "template_social_db")
    experiment_dir = osp.join(parent_dir, "experiments_outputs_social_db")
    print(f"Base directory: {base_dir}")
    print(f"Template directory: {template_dir}")
    print(f"Experiment directory: {experiment_dir}")



    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="meta-llama/llama-3.3-70b-instruct", choices=AVAILABLE_LLMS)

    parser.add_argument("--input_dir_21", type=str, default = template_dir + "/inputs/pdfs_regulatories/")
    parser.add_argument("--output_dir_21", type=str, default = experiment_dir + "/shortened_pdfs/")
    parser.add_argument("--input_dir_summarize_21", type=str, default = experiment_dir + "/shortened_pdfs/")
    parser.add_argument("--output_dir_summarize_21", type=str, default = experiment_dir)

    parser.add_argument("--input_22", type=str, default = experiment_dir + "/20250416_112225_merged_summaries.json")
    parser.add_argument("--output_22", type=str, default = experiment_dir + "/___tmp___stakeholder_graph.graphml")

    parser.add_argument("--pdf_dir_23", type=str, default = template_dir + "/inputs/pdfs_projects")
    parser.add_argument("--graphml_23", type=str, default = experiment_dir + "/___tmp___stakeholder_graph.graphml")
    parser.add_argument("--output_23", type=str, default = experiment_dir + "/___tmp___merged_project_graph.graphml")

    args = parser.parse_args()

    print("=== Step 2-1: perform_regulatory research ===")
    print("=== Step 2-1: search regulatory documents via CoreSearch, download them, summarize the documents  ===")
    # 1: search documents via CoreSearch, and download them
    output_file_name = fetch_documents_via_core()
    # download_documents(output_path)  
    #   #      ! I needed to download the files manually instead of using this method,
    #   #      ! because CORE-SEARCH does not always return the correct URLs and the linked PDF files may not be accessible.
    # 2: Using Tool, fetch the necessary parts from the downloaded documents
    print(args.input_dir_21, args.output_dir_21)
    run_batch_pdf_to_json(args.input_dir_21, args.output_dir_21)
    # 3: summarize the documents
    summarize_json_documents_batch(args.model, args.input_dir_summarize_21, args.output_dir_summarize_21)


    print('=== Step 2-2: perform stakeholder mapping ===')
    print("=== Step 2-2: extract social relationships from the collected documents, and save a GraphDB  ===")
    relationships = extract_relationships_llama_ver02(args.input_22, args.model)
    G = build_networkx_graph(relationships)
    nx.write_graphml(G, args.output_22)
    print(f"Graph saved to {args.output_22}")
    visualize_graph(G)
    export_interactive_graph(G)


    print("=== Step 2-3: perform project extraction ===")
    print("=== Step 2-3: extend the GraphDB with external projects data ===")
    all_relationships = []
    for fname in os.listdir(args.pdf_dir_23):
        if fname.endswith(".pdf"):
            print(f" Processing: {fname}")
            pdf_path = os.path.join(args.pdf_dir_23, fname)
            paras = extract_paragraphs_from_pdf(pdf_path)
            rels = extract_project_relationships(paras, args.model)
            all_relationships.extend(rels)
    G = merge_into_existing_graph(args.graphml_23, all_relationships, args.output_23)
    export_interactive_graph(G)


    print("=== Step 2: COMPLETED ===")