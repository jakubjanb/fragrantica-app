### Fragrance World (Streamlit app)

Interactive Streamlit app for exploring perfume ratings and popularity (votes) across brands.

The app loads a pre-cleaned dataset from `Data/all_brands_clean.csv`, lets you select a brand, and visualizes that brand’s fragrances on a Plotly scatter chart (rating vs. votes on a log scale). Clicking a point opens the fragrance’s Fragrantica page (when `url` is present in the dataset).

### Features

- Landing page (`app.py`) with navigation to the explorer
- Explorer page (`pages/fragrance_explorer.py`) with:
  - Brand selector with first-letter filtering
  - Summary metrics (count of fragrances, share with rating ≥ 4.0)
  - Interactive Plotly chart (rating vs votes)
  - Click-to-open fragrance URL (if available)

### Project structure

```text
.
├── app.py
├── pages/
│   └── fragrance_explorer.py
├── src/
│   ├── __init__.py
│   ├── data.py
│   ├── plots.py
│   └── widgets.py
└── Data/
    └── all_brands_clean.csv
```

### Prerequisites

- Python 3.10+ (recommended)

Main Python dependencies used by the code:

- `streamlit`
- `pandas`
- `plotly`

### Setup

Create and activate a virtual environment, then install dependencies.

If you have a `requirements.txt` in your environment, prefer using it:

```bash
pip install -r requirements.txt
```

Otherwise install the core dependencies directly:

```bash
pip install streamlit pandas plotly
```

### Data

The app expects the dataset at:

`Data/all_brands_clean.csv`

Notes:

- The `Data/` directory is ignored by git (`.gitignore` contains `Data/`).
- Required columns (enforced in `src/data.py`): `brand`, `name`, `rating`, `votes`
- Optional column: `url` (enables click-to-open from the chart)

If any required columns are missing, the app will show a friendly message (it will treat the dataset as empty).

### Run the app

From the project root:

```bash
streamlit run app.py
```

Then use the sidebar navigation (or the button on the landing page) to open `Fragrance Explorer`.

### Development notes

- Data loading is cached via `st.cache_data` in `src/data.py`.
- The explorer resolves the dataset path relative to the project root, so running via `streamlit run app.py` from the root directory is the expected workflow.
