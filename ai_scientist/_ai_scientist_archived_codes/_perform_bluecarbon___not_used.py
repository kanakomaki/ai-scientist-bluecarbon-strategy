import json
import os
from ai_scientist.llm import create_client, get_response_from_llm  # ← ここ修正！

# 必要であれば system prompt を別ファイル化
SYSTEM_MESSAGE = "You are a strategic advisor AI with expertise in carbon crediting and institutional governance."

MODEL_NAME = "deepseek/deepseek-chat-v3-0324:free" #
MODEL_NAME = "google/gemini-2.5-pro-exp-03-25:free"  # ここは自分のAPI環境に合わせてOK

# ファイルパスの設定
INPUT_PATH = "inputs/project_input_01.json"
PROMPT_PATH = "prompts/strategy_generator.txt"
OUTPUT_PATH = "output/strategy_output.md"

def load_input():
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_prompt():
    with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def save_output(text):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(text)

def perform_bluecarbon():
    project_input = load_input()
    base_prompt = load_prompt()

    full_prompt = base_prompt + "\n\n" + json.dumps(project_input, indent=2)

    # OpenAI クライアントを作成
    client, model = create_client(MODEL_NAME)

    print("Sending prompt to LLM...")
    response_text, _ = get_response_from_llm(
        prompt=full_prompt,
        client=client,
        model=model,
        system_message=SYSTEM_MESSAGE,
        print_debug=True
    )

    print("Writing output to file...")
    save_output(response_text)
    print("Done.")

if __name__ == "__main__":
    perform_bluecarbon()
