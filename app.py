import os
from pathlib import Path

import streamlit as st

from inflation_dashboard.viz import generate_viz_html, load_viz_data


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "data" / "inflation_clean.parquet"

st.set_page_config(
    page_title="Ireland's Inflation Journey",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: #F1EFF6 !important;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {
        display: none;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: none !important;
        padding: 0 !important;
    }
    [data-testid="stIFrame"] {
        width: 100% !important;
        height: calc(100vh - 16px) !important;
    }
    [data-testid="stIFrame"] iframe {
        display: block;
        width: 100% !important;
        height: calc(100vh - 16px) !important;
        border: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def build_dashboard(data_path: str) -> tuple[str, int]:
    data = load_viz_data(data_path)
    height = max(1200, 900 + 44 * len(data["categories"]))
    return generate_viz_html(data), height


data_path = Path(os.environ.get("INFLATION_DATA_PATH", DEFAULT_DATA))
if not data_path.is_file():
    st.error(
        f"**Data file not found.**\n\nExpected: `{data_path}`\n\n"
        "Ensure `inflation_clean.parquet` exists in the `data/` folder."
    )
    st.stop()

dashboard_html, dashboard_height = build_dashboard(str(data_path))
st.iframe(
    dashboard_html,
    height=dashboard_height,
    alt="Interactive D3.js dashboard for Ireland's HICP inflation data",
)
