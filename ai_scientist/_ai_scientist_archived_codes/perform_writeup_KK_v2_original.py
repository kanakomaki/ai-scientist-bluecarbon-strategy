# Originally written by K.K. arranged from ai_scientist/perform_writeup.py

# 2024APR30: Changed the small model from GPT to OPENROUTER models (small_model = "meta-llama/llama-3.3-70b-instruct")
# 2024APR30: Changed the big model from GPT to OPENROUTER models (big_model = "meta-llama/llama-3.3-70b-instruct")
# 2024APR30: Modified by K.K. to work with CORE SEARCH API, NOT SEMANTIC SCHOLAR (as I was not able to get the API key)
# - combined_summary.md を idea_text として読み込み、LLM に渡す
# - combined_figures/ を対象に図とVLM説明を生成
# - combined_result_summary.json は補助的に summaries に読み込み

# writeup_prompt（戦略提案型構成）
# - 構成：Executive Summary, Context, Strategy, Insights, Recommendations...
# - より深い考察と提案を誘導するためにプロンプトを再設計

import argparse
import json
import os
import os.path as osp
import re
import shutil
import subprocess
import traceback
import unicodedata
import uuid
import datetime
from pathlib import Path

from ai_scientist.llm import (
    get_response_from_llm,
    extract_json_between_markers,
    create_client,
    AVAILABLE_LLMS,
)

#from ai_scientist.tools.semantic_scholar import search_for_papers
from ai_scientist.tools.coresearch_scholar import search_core_api_semanticformat as search_for_papers

from ai_scientist.perform_vlm_review import generate_vlm_img_review
#from ai_scientist.vlm import create_client as create_vlm_client
from ai_scientist.llm import create_vlm_client as create_vlm_client # changed by KK 2024APR30)


writeup_prompt = """
You are tasked with writing a strategic proposal report based on a combination of scientific analysis and social-institutional context. 
This report is intended as a Proof of Concept submission for an AI/strategy research position.

Please follow the structure below and fully utilize the information provided to create a compelling, logically structured, and insightful document.

---

We begin with the **preliminary contextual strategy idea** (JSON):
```json
{preidea_text}
```

And we have designed the following **research-oriented execution plan** (JSON):
```json
{idea_text}
```

We also have the following experimental summaries (markdown):
```markdown
{summaries}
```

Available plot files to use:
```
{plot_list}
```

VLM-based descriptions of those plots:
```
{plot_descriptions}
```

Here is your current LaTeX draft:
```latex
{latex_writeup}
```

---

**Target Report Structure** (adapted for strategy-driven PoC):

1. **Executive Summary**
   - Briefly summarize the proposed strategy, motivation, and major outcomes.

2. **Context & Objective**
   - Explain the broader motivation (e.g., SMEs, blue carbon credits).
   - State clearly what this PoC aims to explore or prove.

3. **Strategic Framework & Idea**
   - Introduce the preliminary idea and rationale.
   - Link social-institutional analysis with the direction of your PoC.

4. **Experimental Insights**
   - Present the scientific background and context.
   - Rewrite the provided experimental summaries.
   - Present experimental findings using the provided experimental summaries and figures and explain well.
   - For each experiment:
     - Describe what was done.
     - Interpret the result.
     - Discuss its **significance**, **implications**, and **limitations**.
     - Connect it to strategic decisions.

5. **Strategic Recommendations**
   - Based on the above insights, outline actionable next steps:
     - Which institutional pathway to prioritize (e.g., REDD++ vs J-Blue)?
     - What areas to target for intervention?
     - Which stakeholders to engage?
     - Draft initial PoC roadmap.

6. **Limitations & Future Work**
   - Note uncertainties, data limitations, or institutional barriers.
   - Suggest improvements, expansions, or technical next steps.

7. **References**

8. **Appendix** (optional)
   - Supplementary figures, code details, or extended methods.

---

**Instructions**
- Use the experimental summaries and figures to drive concrete strategic insights.
- Each figure should be accompanied by its description and interpretation.
- Connect science to decision-making: how does this result affect what should be done?
- Focus not just on what was done, but on what should be done next.

Return a fully rewritten LaTeX file for `template.tex` with all sections filled in.
Respond in a fenced markdown block:
```latex
<UPDATED CODE>
```
"""

writeup_system_message_template = """"You are an ambitious AI researcher who is looking to deliver a report to our client who wants the best strategies to get blue carbon credits. 
Ensure that the paper is scientifically accurate, objective, and truthful. Accurately report the experimental results, even if they are negative or inconclusive.
The report should follow:
- The main paper should be {page_limit} pages, including all figures and tables, but excluding references, the impact statement, and optional appendices. In general, try to use the available space and include all relevant information.
- The main paper should be double-column format, while the appendices can be in single-column format. When in double column format, make sure that tables and figures are correctly placed.
- Avoid using bullet points unless absolutely necessary. Use complete paragraphs and detailed narrative style to explain each idea.""" 

_writeup_system_message_template = """You are an ambitious AI researcher who is looking to deliver a report that will contribute significantly to the field and your clients.
Ensure that the paper is scientifically accurate, objective, and truthful. Accurately report the experimental results, even if they are negative or inconclusive.
You are planning to submit to our important client who wants us to find and suggest the best strategies to obtain blue carbon credits. The report should fullfill strict guidelines:
- The main paper is limited to {page_limit} pages, including all figures and tables, but excluding references, the impact statement, and optional appendices. In general, try to use the available space and include all relevant information.
- The main paper should be double-column format, while the appendices can be in single-column format. When in double column format, make sure that tables and figures are correctly placed.
- Do not remove the \\graphicspath directive or no figures will be found.

Here are some tips for each section of the paper:

- **Title**:
  - Title should be catchy and informative. It should give a good idea of what the paper is about.
  - Try to keep it under 2 lines.

- **Abstract**:
  - TL;DR of the paper.
  - What are we trying to do and why is it relevant?
  - Make sure the abstract reads smoothly and is well-motivated. This should be one continuous paragraph.

- **Introduction**:
  - Longer version of the Abstract, i.e., an overview of the entire paper.
  - Provide context to the study and explain its relevance.
  - If results are inconclusive or negative, present them frankly; if they are positive, you may highlight how the approach effectively addresses the research question or problem.
  - Summarize your contributions, highlighting pertinent findings, insights, or proposed methods.

- **Related Work**:
  - Academic siblings of our work, i.e., alternative attempts in literature at trying to address the same or similar problems.
  - Compare and contrast their approach with yours, noting key differences or similarities.
  - Ensure proper citations are provided.

- **Background**:
  - Present foundational concepts or prior work needed to understand your method.
  - This should include necessary definitions, the problem setting, or relevant theoretical constructs.

- **Method**:
  - Clearly detail what you propose to do and why. If your study aims to address certain hypotheses, describe them and how your method is constructed to test them.
  - If results are negative or inconclusive, you may suggest improvements or discuss possible causes.

- **Experimental Setup**:
  - Explain how you tested your method or hypothesis.
  - Describe necessary details such as data, environment, and baselines, but omit hardware details unless explicitly mentioned.

- **Experiments**:
  - Present the results truthfully according to the data you have. If outcomes are not as expected, discuss it transparently.
  - Include comparisons to baselines if available, and only include analyses supported by genuine data.
  - Try to include all relevant plots and tables. Consider combining multiple plots into one figure if they are related.
  - For each experiment result, include not only what was done but also its interpretation, significance, and potential implications.
  - Explain what this result means, and how it informs the strategy.

- **Conclusion**:
  - Summarize the entire paper, including key strengths or findings.
  - If results are strong, highlight how they might address the research problem.
  - If results are negative or inconclusive, highlight potential improvements or reasons and propose future directions.

- **Appendix**:
  - Place for supplementary material that did not fit in the main paper.

Ensure you are always writing good compilable LaTeX code. Common mistakes that should be fixed include:
- LaTeX syntax errors (unenclosed math, unmatched braces, etc.).
- Duplicate figure labels or references.
- Unescaped special characters: & % $ # _ {{ }} ~ ^ \\
- Proper table/figure closure.
- Do not hallucinate new citations or any results not in the logs.
"""


def compile_latex(latex_folder, pdf_path):
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "template.tex"],
            cwd=latex_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")

        print("LaTeX STDOUT:\n", stdout)
        print("LaTeX STDERR:\n", stderr)

        if not os.path.exists(osp.join(latex_folder, "template.pdf")):
            raise RuntimeError("PDF was not generated.")

        shutil.copy(osp.join(latex_folder, "template.pdf"), pdf_path)

    except subprocess.TimeoutExpired:
        print("LaTeX compilation timed out.")
    except Exception as e:
        print("LaTeX compilation failed.")
        print(traceback.format_exc())


def detect_pages_before_impact(latex_folder, timeout=30):
    """
    Temporarily copy the latex folder, compile, and detect on which page
    the phrase "Impact Statement" appears.
    Returns a tuple (page_number, line_number) if found, otherwise None.
    """
    temp_dir = osp.join(latex_folder, f"_temp_compile_{uuid.uuid4().hex}")
    try:
        shutil.copytree(latex_folder, temp_dir, dirs_exist_ok=True)

        # Compile in the temp folder
        commands = [
            ["pdflatex", "-interaction=nonstopmode", "template.tex"],
            ["bibtex", "template"],
            ["pdflatex", "-interaction=nonstopmode", "template.tex"],
            ["pdflatex", "-interaction=nonstopmode", "template.tex"],
        ]
        for command in commands:
            try:
                subprocess.run(
                    command,
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                )
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                return None

        temp_pdf_file = osp.join(temp_dir, "template.pdf")
        if not osp.exists(temp_pdf_file):
            return None

        # Try page-by-page extraction to detect "Impact Statement"
        for i in range(1, 51):
            page_txt = osp.join(temp_dir, f"page_{i}.txt")
            subprocess.run(
                [
                    "pdftotext",
                    "-f",
                    str(i),
                    "-l",
                    str(i),
                    "-q",
                    temp_pdf_file,
                    page_txt,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if not osp.exists(page_txt):
                break
            with open(page_txt, "r", encoding="utf-8", errors="ignore") as fp:
                page_content = fp.read()
            lines = page_content.split("\n")
            for idx, line in enumerate(lines):
                if "Impact Statement" in line:
                    return (i, idx + 1)
        return None
    except Exception:
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def perform_writeup(
    exp_outputs_base_folder,
    preliminary_ideas,
    idea_dir,
    no_writing=False,
    num_cite_rounds=20,
    small_model="meta-llama/llama-3.3-70b-instruct",
    big_model="anthropic/claude-3.5-sonnet",
    n_writeup_reflections=5,
    page_limit=20,
):
    compile_attempt = 0
    base_folder = exp_outputs_base_folder # experiments results folder

    base_pdf_file = osp.join(base_folder, f"{osp.basename(base_folder)}")
    pdfname = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    print("base_pdf_file", base_pdf_file, pdfname)
    latex_folder = osp.join(base_folder, "latex")

    if osp.exists(latex_folder):
        shutil.rmtree(latex_folder)

    try:
        # === Load preliminary idea text ===
        #preidea_path = "/home/kana/psnl/sakana/prob01/AI-Scientist-v2/pre_ideas/bluecarbon/prompt_preideas_02.json" 
        preidea_path = preliminary_ideas
        print("preidea_path", preidea_path)
        if osp.exists(preidea_path):
            with open(preidea_path, "r") as f:
                preidea_text = f.read()
                #print("preidea_text", preidea_text)

        # === Load idea text ===
        #idea_path = "/home/kana/psnl/sakana/prob01/AI-Scientist-v2/ideas/ideas_saved.json" 
        idea_path = idea_dir
        if osp.exists(idea_path):
            with open(idea_path, "r") as f:
                idea_text = f.read()

        # === Load combined_summary.md as summaries ===
        summary_path = osp.join(base_folder, "combined_summary.md")
        if osp.exists(summary_path):
            with open(summary_path, "r") as f:
                combined_summaries_str = f.read()
        else:
            combined_summaries_str = "No combined summary found."

        # === Prepare LaTeX template ===
        if not osp.exists(osp.join(latex_folder, "template.tex")):
            shutil.copytree(
                #"ai_scientist/experiments/blank_icml_latex",
                "ai_scientist/blank_icbinb_latex",
                latex_folder,
                dirs_exist_ok=True,
            )

        writeup_file = osp.join(latex_folder, "template.tex")
        with open(writeup_file, "r") as f:
            writeup_text = f.read()

        # === Collect figures ===
        figures_dir = osp.join(base_folder, "combined_figures")
        plot_names = []
        if osp.exists(figures_dir):
            for fplot in os.listdir(figures_dir):
                if fplot.lower().endswith(".png"):
                    plot_names.append(fplot)

        aggregator_code = "No aggregator script found."

        if no_writing:
            compile_latex(latex_folder, base_pdf_file + pdfname + ".pdf")
            return osp.exists(base_pdf_file + pdfname + ".pdf")

        # === Copy figures to latex / so LaTeX can find them ===
        for pf in plot_names:
            src_path = osp.join(figures_dir, pf)
            dst_path = osp.join(latex_folder, pf)
            shutil.copy(src_path, dst_path)

        # === Generate VLM-based figure descriptions ===
        try:
            desc_map = {}
            vlm_client, vlm_model = create_vlm_client("openai/gpt-4.1-nano")
            print("-------------------------------", vlm_client, vlm_model)
            for pf in plot_names:
                try:
                    img_path = osp.join(figures_dir, pf)
                    print("-------img_path: ",img_path, "figures_dir: ",figures_dir, "pf: ",pf)
                    if not osp.exists(img_path):
                        print(f" Image not found: {img_path}")
                        desc_map[pf] = "Image missing"
                        continue

                    img_dict = {"images": [img_path], "caption": "No direct caption"}
                    review_data = generate_vlm_img_review(img_dict, vlm_model, vlm_client)
                    if not review_data or not isinstance(review_data, dict):
                        raise ValueError("Invalid VLM response (None or not dict)")
                    desc = review_data.get("Img_description") or "No description available."
                    desc_map[pf] = desc

                except Exception as e:
                    print(f" Failed to process {pf}: {e}")
                    desc_map[pf] = "Failed to generate description"

            plot_descriptions_str = "\n".join([f"combined_figures/{fname}: {desc_map.get(fname, 'No description')}" for fname in plot_names])
        except Exception:
            print("VLM figure description generation failed.")
            plot_descriptions_str = "No descriptions available."



        # === Generate full LaTeX via big model ===
        big_model_system_message = writeup_system_message_template.format(page_limit=page_limit)
        big_client, big_client_model = create_client(big_model)

        combined_prompt = writeup_prompt.format(
            preidea_text=preidea_text,
            idea_text=idea_text,
            summaries=combined_summaries_str,
            aggregator_code=aggregator_code,
            plot_list=", ".join(plot_names),
            latex_writeup=writeup_text,
            plot_descriptions=plot_descriptions_str,
        )

        response, _ = get_response_from_llm(
            prompt=combined_prompt,
            client=big_client,
            model=big_client_model,
            system_message=big_model_system_message,
            print_debug=False,
        )

        latex_code_match = re.search(r"```latex(.*?)```", response, re.DOTALL)
        if not latex_code_match:
            return False
        updated_latex_code = latex_code_match.group(1).strip()
        with open(writeup_file, "w") as f:
            f.write(updated_latex_code)

        compile_latex(latex_folder, base_pdf_file + pdfname + ".pdf")


        # === Reflection loop ===
        compile_attempt += 1
        for i in range(n_writeup_reflections):
            reflection_prompt = f"""
Now let's reflect and improve the LaTeX document.
The generated LaTeX is too short (only ~4 pages). Your target is at least 10 pages in double-column format.

Please reflect and improve the document by:
- Expanding each section with more analysis and interpretation
- Adding more detailed methodology and data discussion
- Including a Related Work section and longer Appendix
- Use all plots and describe their implications in depth

Issues also to consider:
1. Are there oversized figures overflowing the page?
2. Are any plots missing or not clearly described?
3. Are there LaTeX syntax/style issues?
4. Add more detailed interpretation, connect ideas more deeply, and include new strategic insights.

Please rewrite the LaTeX to address these issues.

Do not change the document class or preamble. Preserve the LaTeX template structure exactly as in the original.
Only edit the body text between \begin and \end. Do not invent new sections or change the order of content.
Please return the full LaTeX document enclosed in triple backticks. Do not alter document structure unnecessarily.
Avoid Markdown-like syntax (e.g. -, *, #) unless correctly mapped to LaTeX. Escape any special characters. Return only valid LaTeX code.

If no changes are needed, say "I am done."""
            
        #     full_prompt = reflection_prompt + "\n\n" + updated_latex_code
        #     reflection_response, _ = get_response_from_llm(
        #         prompt=full_prompt,
        #         client=big_client,
        #         model=big_client_model,
        #         system_message="You are a scientific LaTeX assistant."
        #     )
        #     match = re.search(r"```latex(.*?)```", reflection_response, re.DOTALL)
        #     if match:
        #         updated_latex_code = match.group(1).strip()
        #         Path(writeup_file).write_text(updated_latex_code)
        #         compile_latex(latex_folder, base_pdf_file + pdfname + f"_{compile_attempt}.pdf")
        #     else:
        #         break
        # # === Final compilation ===
        # # 最終的なLaTeXの有無を確認して返す
        # return osp.exists(base_pdf_file + pdfname + f"_{compile_attempt-1}.pdf")

            full_prompt = reflection_prompt + "\n\n" + updated_latex_code
            reflection_response, _ = get_response_from_llm(
                prompt=full_prompt,
                client=big_client,
                model=big_client_model,
                system_message="You are a scientific LaTeX assistant."
            )
            match = re.search(r"```latex(.*?)```", reflection_response, re.DOTALL)
            if match:
                reflected_latex_code = match.group(1).strip()
                # latex clearnup
                final_text = reflected_latex_code
                cleanup_map = {
                    "</end": r"\\end",
                    "</begin": r"\\begin",
                    "’": "'",
                }
                for bad_str, repl_str in cleanup_map.items():
                    final_text = final_text.replace(bad_str, repl_str)
                # escape %
                final_text = re.sub(r"(\d+(?:\.\d+)?)%", r"\1\\%", final_text)
                # escape special characters
                specials = {
                    "&": r"\&",
                    "#": r"\#",
                    "_": r"\_",
                    "$": r"\$",
                }
                for bad_str, repl_str in specials.items():
                    final_text = final_text.replace(bad_str, repl_str)
                # save the final text
                Path(writeup_file).write_text(final_text)
                compile_latex(latex_folder, base_pdf_file + pdfname + f"_{compile_attempt}.pdf")
            else:
                break
        # === Final compilation ===
        return osp.exists(base_pdf_file + pdfname + f"_{compile_attempt-1}.pdf")


    except Exception:
        print("EXCEPTION in perform_writeup_KK:")
        print(traceback.format_exc())
        return False





if __name__ == "__main__":

    base_folder = "experiments_outputs/combined_20250501_063438/"
    preliminary_ideas = "pre_ideas/bluecarbon/prompt_preideas_02.json"
    idea_dir = "ideas/ideas_saved.json"
    num_cite_rounds=20
    n_writeup_reflections = 3
    page_limit = 20

    perform_writeup(
                exp_outputs_base_folder=base_folder,
                preliminary_ideas=preliminary_ideas,
                idea_dir=idea_dir,
                num_cite_rounds=num_cite_rounds,
                small_model="meta-llama/llama-3.3-70b-instruct",
                big_model="meta-llama/llama-3.3-70b-instruct",
                n_writeup_reflections=n_writeup_reflections,
                page_limit=page_limit,
                )

