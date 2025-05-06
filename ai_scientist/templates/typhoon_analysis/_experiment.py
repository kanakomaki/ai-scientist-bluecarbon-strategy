import sys
import pandas as pd

import external_models.TYPHOONTRACK2GRIDPOINT.olango_typhoon_analysis as olango

# tint, decay_typeを手動設定（本来は外から渡すべきだけど、Sakanaルールではコマンド引数は増やせないので固定書き換えになる）
TINT = 1.0  # 例：1時間間隔補間
DECAY_MODEL = "simple"  # 例："simple", "fast", "slow"

# データ読み込みと補間
# ・・・
# full_trackを生成

# グリッドへのマッピング
# ・・・

# 距離減衰モデルの設定
def decay_factor(dist_km, model="simple"):
    if model == "simple":
        if dist_km <= 50:
            return 1.0
        elif dist_km <= 100:
            return 0.5
        elif dist_km <= 200:
            return 0.25
        else:
            return 0.1
    elif model == "fast":
        if dist_km <= 50:
            return 1.0
        elif dist_km <= 150:
            return 0.4
        else:
            return 0.1

# 結果保存
output_dir = sys.argv[sys.argv.index('--out_dir') + 1]
wind_grids_df.to_csv(f"{output_dir}/windspeed_map.csv", index=False)

--------------------------
import subprocess
import os
import json
from ai_scientist.llm import get_response_from_llm  # LLMを使って図の説明を生成

def run_experiment(r_script_path="typhoon_analysis.R", output_fig="figures/typhoon_map.png"):
    # Rスクリプト実行
    subprocess.run(["Rscript", r_script_path], check=True)

    # 図の説明をLLMに生成させる
    prompt = (
        "You are a scientific assistant. The user has generated a typhoon gust duration map using gridded wind speed data. "
        "You see a file named 'typhoon_map.png'. Write a short scientific summary (1-2 sentences) describing what this figure likely represents, assuming it was generated from spatial wind data during a typhoon."
    )
    summary_text, _ = get_response_from_llm(prompt)

    # result_summary.json を保存
    summary = {
        "figures": [
            {
                "filename": os.path.basename(output_fig),
                "summary": summary_text.strip()
            }
        ]
    }
    with open("result_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    os.makedirs("figures", exist_ok=True)
    run_experiment()