# Experimental Template: Typhoon Impact Analysis

This template performs a spatial analysis of typhoon-induced gust durations using gridded wind speed data. The goal is to visualize and summarize wind impact patterns over a specific region during a historical typhoon event.

## Source Code (`src/`)

The main analysis is written in R. The core script is:
`src/olango_typhoon_analysis.r`

This script processes input data, computes gust duration per grid cell, and generates a heatmap figure.

Additional functions are organized in:
`src/source_functions.r`

## Input Data

Input CSV file is located in:
`templates/tyhoon_analysis/inputs/parsed_typhoon_data.csv`

This file contains pre-processed wind speed data (e.g., sustained and gust speeds over time and location), which are used to compute gust durations.

## Output

The following outputs are generated:

- A PNG figure showing the gust duration map.
- A JSON summary (`result_summary.json`) including a brief explanation of the figure.

All outputs are saved in a time-stamped subdirectory under:
`experiments_outputs/typhoon_analysis/`

Example:
`experiments_outputs/typhoon_analysis/run_20250501_031730/`

## R and Python Integration

This module is called via a Python script:
`experiment.py`

Python handles:

- Executing the R script with appropriate arguments
- Calling an LLM to summarize the generated figure
- Saving the summary in JSON format

## Python and R Environment

This module uses both Python and R.

### Dependencies

- R (including packages: `ggplot2`, `viridis`, etc.)
- Python (with `rpy2`, `openai`, or other LLM client libraries)

### Recommended setup

It is recommended to use the `conda` environment file that includes both Python and R dependencies:

```bash
conda env create -f environment_full.yml
```

---

## License and Credits
Original code licensed under the terms of the [TYPHOONTRACK2GRIDPOINT repository](https://github.com/rodekruis/TYPHOONTRACK2GRIDPOINT#). Please refer to that repository for license details.
