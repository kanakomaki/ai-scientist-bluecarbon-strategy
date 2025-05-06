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

from tensorflow import keras
from keras.models import load_model
import datetime
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from firstNN_KK import predictOnImage, plotNVDIBand, plotMangroveBand, plotDifference

# Some constants setup:
main_bands = [i+1 for i in range(0,7)]
ndvi_band = 9
labels_band = 8
input_bands = ndvi_band
print('Analyzing bands: ', input_bands)
if input_bands == ndvi_band: nBands = 1
else: nBands = len(main_bands)
print('nBands: ', nBands)



def select_model(model_path,model_name):
    # when using pre-trained models you need to adust the number of input band parameters at the top of the script
    models = {"basicNN_1": model_path + "basicNN_Model_TrainingImages_1_5_6_7_Epochs10.h5",
                "basicNN_2": model_path + "basicNN_Model_TrainingImages_3_5_6_7_Epochs10_2.h5",
                "CNN": model_path + "CNN_Model_F1_0.914_AUC_0.993.h5",
              }
    model = load_model(models[model_name])

    # when using a custom model you do not need to adjust the input shape
    model = keras.Sequential([
    keras.layers.Flatten(input_shape=(1, nBands)),
    # keras.layers.Dense(10, activation='relu'),
    keras.layers.Dense(10, activation='relu'),
    keras.layers.Dense(2, activation='softmax')])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

    return model

def make_prompt_for_plot(fn_name, source_code):
    prompt = f"""
You are an ambicious earth science PhD researcher. 

The following Python function is used to predict mangrove presence from satellite imagery:
Function name: `{fn_name}`

```python
{source_code}
```

Please summarize what this function does in 2-3 sentences. Focus on what kind of input it uses, what the output means, and what purpose it serves in the context of a mangrove analysis.
"""
    return prompt


def run_experiment(model_path, model_name, image_path, output_path=None, summary_path="result_summary.json", llm_model=None):
    """
    Run mangrove prediction experiment using a pre-trained model on a given satellite image.
    Generate a figure and auto-generate a summary using LLM based on the predictOnImage() function.
    """
    # Load model and run prediction
    model = select_model(model_path, model_name)
    predictOnImage(model, image_path, output_path)

    # Extract and summarize the source code of predictOnImage
    source_code = inspect.getsource(predictOnImage)

    # Create the LLM client
    client, LLM_model = create_client(llm_model)

    # Send to LLM for summarization
    prompts = [
            ("plotNVDIBand.png", make_prompt_for_plot("plotNVDIBand", inspect.getsource(plotNVDIBand))),
            ("plotMangroveBand.png", make_prompt_for_plot("plotMangroveBand", inspect.getsource(plotMangroveBand))),
            ("plotNVDIBand.png", make_prompt_for_plot("plotNVDIBand", inspect.getsource(plotDifference))),
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

    parser = argparse.ArgumentParser(description="Experiment: Predict Mangrove")
    parser.add_argument(
        "--llm_model",
        type=str,
        default="meta-llama/llama-3.3-70b-instruct",
        choices=AVAILABLE_LLMS,
        help="Model to use for AI Scientist.",
    )
    args = parser.parse_args()


    timenow = datetime.datetime.now()
    output_path=f"experiments_outputs/predict_mangrove/run_{timenow:%Y%m%d_%H%M%S}/"
    os.makedirs(output_path, exist_ok=True)

    run_experiment(
        model_path="ai_scientist/templates/predict_mangrove/models/",
        model_name="basicNN_1",
        image_path="ai_scientist/templates/predict_mangrove/inputs/Olango_2_2020_L8_L7ordered_scaled.tif",
        output_path=output_path,
        summary_path=f"{output_path}/result_summary.json",
        llm_model=args.llm_model,
    )
