import argparse
import json
import os.path as osp
import re
import traceback
from typing import Any, Dict, List
import os

# This script is changed for producing 3 tiered proposals (1: social systems analysis, 2: science proposals and prototype research by AI scientist, 3: best approaches to solve the problems)

from ai_scientist.llm import (
    AVAILABLE_LLMS,
    create_client,
    get_response_from_llm,
)

# from ai_scientist.tools.semantic_scholar import SemanticScholarSearchTool
from ai_scientist.tools.base_tool import BaseTool
from ai_scientist.tools.coresearch_scholar import CoreSearchTool # added by KK

def perform_ideation():

    # Create tool instances
    core_tool = CoreSearchTool() # added by KK
    #semantic_scholar_tool = SemanticScholarSearchTool()

    # Define tools at the top of the file
    tools = [
        core_tool, # added by KK
        #semantic_scholar_tool,
        {
            "name": "FinalizeIdea",
            "description": """Finalize your idea by providing the idea details.

    The IDEA JSON should include the following fields:
    - "Name": A short descriptor of the idea. Lowercase, no spaces, underscores allowed.
    - "Title": A catchy and informative title for the proposal.
    - "Short Hypothesis": A concise statement of the main hypothesis or research question. Clarify the need for this specific direction, ensure this is the best setting to investigate this idea, and there are not obvious other simpler ways to answer the question.
    - "Related Work": A brief discussion of the most relevant related work and how the proposal clearly distinguishes from it, and is not a trivial extension.
    - "Abstract": An abstract that summarizes the proposal in conference format (approximately 250 words).
    - "Experiments": A list of experiments that would be conducted to validate the proposal. Ensure these are simple and feasible. Be specific in exactly how you would test the hypothesis, and detail precise algorithmic changes. Include the evaluation metrics you would use.
    - "Risk Factors and Limitations": A list of potential risks and limitations of the proposal.""",
        },
    ]

    # Create a tools dictionary for easy lookup
    tools_dict = {tool.name: tool for tool in tools if isinstance(tool, BaseTool)}

    # Create a string with the tool descriptions
    tool_descriptions = "\n\n".join(
        (
            f"- **{tool.name}**: {tool.description}"
            if isinstance(tool, BaseTool)
            else f"- **{tool['name']}**: {tool['description']}"
        )
        for tool in tools
    )

    # Extract tool names for the prompt
    tool_names = [
        f'"{tool.name}"' if isinstance(tool, BaseTool) else f'"{tool["name"]}"'
        for tool in tools
    ]
    tool_names_str = ", ".join(tool_names)


    system_prompt = f"""You are an experienced AI strategist and applied researcher. Your role is to help design a practical and impactful strategy (not a research paper) for implementing a real-world Proof of Concept (PoC) based on the user's structured task description.

    The task is composed of three parts:

    1. Social and strategic aspects (e.g., legal scheme selection, stakeholder mapping, administrative feasibility)
    2. Scientific/technical aspects (e.g., literature review on monitoring methods, preliminary data analysis using open tools)
    3. Integration of both parts into a feasible step-by-step execution plan for a small to mid-sized organization

    Your goal is to propose ideas or strategies for each of the above parts. Be realistic, implementation-focused, and pragmatic. Your proposal should aim to:
    - Minimize administrative burden and cost
    - Leverage existing tools and publicly available datasets
    - Be executable by a small organization (e.g., an SME or NGO) within 3 years

    You have access to the following tools:

    {tool_descriptions}

    Respond in the following format:

    THOUGHT:
    <Describe your reasoning for each part of the task, such as strategic insights, stakeholder logic, or relevant technical methods. Be structured.>

    ACTION:
    <The action to take, exactly one of {tool_names_str}>

    ARGUMENTS:
    <If ACTION is "SearchCORE", provide the search query as {{"query": "your search query"}}. If ACTION is "FinalizeIdea", provide the idea details as {{"idea": {{ ... }}}} with the IDEA JSON specified below.>

    If you choose to finalize your idea, provide the IDEA JSON in the arguments:

    IDEA JSON:
    ```json
    {{
        "Name": "...",
        "Title": "...",
        "Short Hypothesis": "...",
        "Related Work": "...",
        "Abstract": "...",
        "Experiments": ["..."],
        "Risk Factors and Limitations": ["..."]
    }}

    Ensure the JSON is properly formatted for automatic parsing.

    Note: Before finalizing your idea, perform at least one literature search using "SearchCORE" to verify that your plan aligns with existing knowledge and fills a practical gap. """



    # Define the initial idea generation prompt
    idea_generation_prompt = """{task_description}

    
    Here are the proposals that you have already generated:

    '''
    {prev_ideas_string}
    '''

    Begin by generating an interestingly new high-level research proposal that differs from what you have previously proposed.
    """


    # Define the reflection prompt
    idea_reflection_prompt = """Round {current_round}/{num_reflections}.

    In your thoughts, first carefully consider the quality, novelty, and feasibility of the proposal you just created.
    Include any other factors that you think are important in evaluating the proposal.
    Ensure the proposal is clear and concise, and the JSON is in the correct format.
    Do not make things overly complicated.
    In the next attempt, try to refine and improve your proposal.
    Stick to the spirit of the original idea unless there are glaring issues.

    If you have new information from tools, such as literature search results, incorporate them into your reflection and refine your proposal accordingly.

    If ACTION is "FinalizeIdea", do not forget to provide the idea details as {{"idea": {{ ... }}}} with the IDEA JSON.

    Results from your last action (if any):

    {last_tool_results}
    """
    return tools_dict, system_prompt, idea_generation_prompt, idea_reflection_prompt


def generate_ideas(
    project_name: str,
    base_dir: str,
    preliminary_ideas: str,
    client: Any,
    model: str,
    skip_generation: bool = False,
    max_num_generations: int = 20,
    num_reflections: int = 5,
    tools_dict=None, 
    system_prompt=None, 
    idea_generation_prompt=None,
    idea_reflection_prompt=None
) -> List[Dict]:
    if skip_generation:
        # Load existing ideas from file
        try:
            with open(osp.join(base_dir, "ideas.json"), "r") as f:
                ideas = json.load(f)
            print("Loaded existing proposals:")
            for idea in ideas:
                print(idea)
            return ideas
        except FileNotFoundError as e:
            print("No existing proposals found:")
            traceback.print_exc()
            print("Generating new proposals.")
        except json.JSONDecodeError as e:
            print("Error decoding existing proposals:")
            traceback.print_exc()
            print("Generating new proposals.")

    idea_str_archive = []

    # Load the preliminary ideas from the JSON file
    with open(osp.join(base_dir, preliminary_ideas), "r") as f:
        prompt = json.load(f)
        print(f"preidea: Loaded pre-generated idea from {base_dir}/{preliminary_ideas}")
    print(f"Preidea title: {prompt['project_title']}")

    task_description = prompt["task_description"]
#    print("-----------------------------")
#    print(f"TASK DESCRIPTION {task_description}")
#    print("-----------------------------")


    for gen_idx in range(max_num_generations):
        print()
        print(f"Generating proposal {gen_idx + 1}/{max_num_generations}")
        try:
            prev_ideas_string = "\n\n".join(idea_str_archive)

            last_tool_results = ""
            idea_finalized = False
            msg_history = []

            for reflection_round in range(num_reflections):
                if reflection_round == 0:
                    # Use the initial idea generation prompt
                    prompt_text = idea_generation_prompt.format(
                        task_description=task_description,
                        #code=code,
                        prev_ideas_string=prev_ideas_string,
                    )
                else:
                    # Use the reflection prompt, including tool results if any
                    prompt_text = idea_reflection_prompt.format(
                        current_round=reflection_round + 1,
                        num_reflections=num_reflections,
                        last_tool_results=last_tool_results or "No new results.",
                    )

    
                # keep only the last two turns to avoid token overflow added by KK
                msg_history = msg_history[-4:]  # 2 user-assistant pairs added by KK
                response_text, msg_history = get_response_from_llm(
                    #msg=prompt_text, # deleted by KK
                    prompt=prompt_text,
                    client=client,
                    model=model,
                    system_message=system_prompt,
                    print_debug=False,
                    msg_history=msg_history,
                    temperature=0.7,
                )

                # Parse the LLM's response
                try:
                    # Use regular expressions to extract the components
                    thought_pattern = r"THOUGHT:\s*(.*?)\s*ACTION:"
                    action_pattern = r"ACTION:\s*(.*?)\s*ARGUMENTS:"
                    arguments_pattern = r"ARGUMENTS:\s*(.*?)(?:$|\nTHOUGHT:|\n$)"

                    thought_match = re.search(
                        thought_pattern, response_text, re.DOTALL | re.IGNORECASE
                    )
                    action_match = re.search(
                        action_pattern, response_text, re.DOTALL | re.IGNORECASE
                    )
                    arguments_match = re.search(
                        arguments_pattern, response_text, re.DOTALL | re.IGNORECASE
                    )

                    if not all([thought_match, action_match, arguments_match]):
                        raise ValueError("Failed to parse the LLM response.")

                    thought = thought_match.group(1).strip()
                    action = action_match.group(1).strip()
                    arguments_text = arguments_match.group(1).strip()
                    # --------- Remove markdown code block markers if present ------- added by KK
                    if arguments_text.startswith("```json"):
                        arguments_text = re.sub(r"^```json\s*", "", arguments_text)
                        arguments_text = re.sub(r"\s*```$", "", arguments_text)
                    # --------- to prevent json errors ------- added by KK
                   # match = re.search(r"\{.*?\}", arguments_text, re.DOTALL)
                    match = re.search(r"\{.*\}", arguments_text, re.DOTALL)
                    if match:
                        json_part = match.group(0)
                        arguments_json = json.loads(json_part)
                    # ------------------------------------------- added by KK
                    # print(f"Thought:\n{thought}\n")
                    # print(f"Action: {action}")
                    # print(f"Arguments: {arguments_text}")

                    # Process the action and arguments
                    if action in tools_dict:
                        # It's a tool we have defined
                        tool = tools_dict[action]
                        # Parse arguments
                        try:
                            arguments_json = json.loads(json_part)
                        except json.JSONDecodeError:
                            # print("=== ARGUMENTS TEXT ===")
                            # print(arguments_text)
                            raise ValueError(f"Invalid arguments JSON for {action}.")

                        # Use the tool
                        try:
                            # Assuming the arguments match the parameters of the tool
                            result = tool.use_tool(**arguments_json)
                            last_tool_results = result
                        except Exception as e:
                            last_tool_results = f"Error using tool {action}: {str(e)}"
                    elif action == "FinalizeIdea":
                        # Parse arguments
                        try:
                            # arguments_json = json.loads(arguments_text)
                            arguments_json = json.loads(json_part)
                            idea = arguments_json.get("idea")
                            if not idea:
                                raise ValueError("Missing 'idea' in arguments.")

                            # Append the idea to the archive
                            idea_str_archive.append(json.dumps(idea))
                            #print(f"Proposal finalized: {idea}")
                            idea_finalized = True
                            break
                        except json.JSONDecodeError:
                            #print("=== ARGUMENTS TEXT ===")
                            #print(arguments_text)
                            raise ValueError("Invalid arguments JSON for FinalizeIdea.")
                    else:
                        print(
                            "Invalid action. Please specify one of the available tools."
                        )
                        print(f"Available actions are: {tool_names_str}")
                except Exception as e:
                    print(
                        f"Failed to parse LLM response. Response text:\n{response_text}"
                    )
                    traceback.print_exc()
                    break  # Exit the loop if parsing fails

            if idea_finalized:
                continue  # Move to the next idea

        except Exception as e:
            print("Failed to generate proposal:")
            traceback.print_exc()
            continue

    # Save ideas
    ideas = [json.loads(idea_str) for idea_str in idea_str_archive]

    new_dir = "ideas/"+ project_name
    os.makedirs(new_dir, exist_ok=True)
    with open(osp.join(new_dir, f"{preliminary_ideas}_ideas.json"), "w") as f:
        json.dump(ideas, f, indent=4)

    return ideas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate AI scientist proposals")
    parser.add_argument("--project_name", type=str, default="bluecarbon",
                                            help="Project name to run the AI Scientist PoC flow")
    parser.add_argument(
        "--preliminary_ideas",
        type=str,
        default="preideas_02.json",
        help="Preliminary idea folder name to run AI Scientist's perform_deation.py on.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="meta-llama/llama-3.3-70b-instruct",
        choices=AVAILABLE_LLMS,
        help="Model to use for AI Scientist.",
    )
    parser.add_argument(
        "--skip-idea-generation",
        action="store_true",
        default=False,
        help="Skip proposal generation and use existing proposals.",
    )
    parser.add_argument(
        "--max-num-generations",
        type=int,
        default=2,
        help="Maximum number of proposal generations.",
    )
    parser.add_argument(
        "--num-reflections",
        type=int,
        default=2,
        help="Number of reflection rounds per proposal.",
    )
    args = parser.parse_args()

    # Create the LLM client
    client, client_model = create_client(args.model)

    # Set a Literature Search API & a prompt for the LLM
    tools_dict, system_prompt, idea_generation_prompt, idea_reflection_prompt = perform_ideation()
    
    # set the base directory for preliminary ideas 
    base_dir = osp.join("pre_ideas", args.project_name)
    # Generate ideas 

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

