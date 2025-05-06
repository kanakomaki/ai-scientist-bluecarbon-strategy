import matplotlib.pyplot as plt
from keras.models import load_model
from firstNN import predictOnImage  # assume predictOnImage is defined in firstNN.py


def run_experiment(model_path, image_path, output_path=None):
    """
    Run mangrove prediction experiment using a pre-trained model on a given satellite image.

    Parameters:
    - model_path: path to the trained model (.h5 file)
    - image_path: path to the scaled GeoTIFF image
    - output_path: path to save the predicted output (PNG)
    """
    model = load_model(model_path)
    predictOnImage(model, image_path, output_path)


if __name__ == "__main__":
    run_experiment(
        model_path="model_save.h5",
        image_path="../SatelliteImages/Olango_2_2020_L8_L7ordered_scaled.tif",
        output_path="predicted_mangrove.png"
    )



----------------------------------------------------------
import json
import os
from keras.models import load_model
from firstNN import predictOnImage  # assume predictOnImage is defined in firstNN.py

def run_experiment(model_path, image_path, output_path=None):
    """
    Run mangrove prediction experiment using a pre-trained model on a given satellite image.

    Parameters:
    - model_path: path to the trained model (.h5 file)
    - image_path: path to the scaled GeoTIFF image
    - output_path: path to save the predicted output (PNG)
    """
    model = load_model(model_path)
    predictOnImage(model, image_path, output_path)

    # Save summary about the output
    if output_path:
        summary_data = {
            "figures": [
                {
                    "filename": os.path.basename(output_path),
                    "summary": (
                        "Predicted mangrove coverage using pre-trained neural network model applied to "
                        "Landsat imagery. Higher intensity regions likely indicate denser mangrove biomass."
                    )
                }
            ]
        }
        with open("result_summary.json", "w") as f:
            json.dump(summary_data, f, indent=2)


if __name__ == "__main__":
    run_experiment(
        model_path="model_save.h5",
        image_path="../SatelliteImages/Olango_2_2020_L8_L7ordered_scaled.tif",
        output_path="predicted_mangrove.png"
    )
----------------------------
import os
import json
import inspect
from keras.models import load_model
from firstNN import predictOnImage
from ai_scientist.llm import get_response_from_llm  # 必要に応じて修正


def run_experiment(model_path, image_path, output_path=None, summary_path="result_summary.json"):
    """
    Run mangrove prediction experiment using a pre-trained model on a given satellite image.
    Generate a figure and auto-generate a summary using LLM based on the predictOnImage() function.
    """
    # Load model and run prediction
    model = load_model(model_path)
    predictOnImage(model, image_path, output_path)

    # Extract and summarize the source code of predictOnImage
    source_code = inspect.getsource(predictOnImage)

    # Send to LLM for summarization
    prompt = f"""
You are a helpful assistant. The following Python function is used to predict mangrove presence from satellite imagery:

```python
{source_code}
```

Please summarize what this function does in 2-3 sentences. Focus on what kind of input it uses, what the output means, and what purpose it serves in the context of a mangrove analysis.
"""
    description, _ = get_response_from_llm(prompt=prompt)

    # Save summary with figure reference
    summary = {
        "figures": [
            {
                "filename": os.path.basename(output_path),
                "summary": description.strip()
            }
        ]
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    run_experiment(
        model_path="model_save.h5",
        image_path="../SatelliteImages/Olango_2_2020_L8_L7ordered_scaled.tif",
        output_path="predicted_mangrove.png",
        summary_path="result_summary.json"
    )