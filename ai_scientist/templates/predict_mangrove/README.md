# Experimental Template: Mangrove Prediction

This experimental template uses a modified version of the open-source repository [MangroveClassification](https://github.com/nkinnaird/MangroveClassification) for mangrove presence prediction using satellite imagery.

## Repository Structure

### References
This module is based on the GitHub repository [MangroveClassification](https://github.com/nkinnaird/MangroveClassification).

The original repository was cloned in: 
external_models/MangroveClassification/

### `src/`
Modified and essential code copied from `MangroveClassification` is located in:
templates/predict_mangrove/src/


### Image Data
Test image is located in: 
templates/predict_mangrove/models/
- It is a satellite image near **Olango Island, Cebu, Philippines**, prepared using **Google Earth Engine (GEE)**.

### Prediction Models
Models are stored in:
templates/predict_mangrove/models/
- A non-trained model is included by default.
- You can also place trained models in this folder for inference.

### Output Directory
All prediction outputs will be saved in:
experiments_outputs/predict_mangrove/

### Python Environment

This module requires `gdal`, which is often difficult to install via `pip`.

> **Recommended:**  
> Use the pre-defined conda environment file:
environment.yml
located at the root of this repository.

---

## License and Credits
Original code licensed under the terms of the [MangroveClassification repository](https://github.com/nkinnaird/MangroveClassification). Please refer to that repository for license details.


