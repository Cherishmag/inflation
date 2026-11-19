# Ireland's Inflation Journey

An interactive, single-chart story about Ireland's HICP prices, built from the
CSO dataset. Compare the price-index paths of broad consumer categories over
time, play the animated timeline, or drag its slider to inspect a particular
period.

## Run on Windows

The cleaned dataset is included at `data/inflation_clean.parquet` and is read
locally. The dashboard loads D3.js and the Inter font from public CDNs, so an
internet connection is needed to load those browser assets.

1. Open PowerShell in this project folder.
2. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Start the dashboard:

   ```powershell
   python -m streamlit run app.py
   ```

5. Open `http://localhost:8501`. Press `Ctrl+C` in PowerShell to stop the app.

Streamlit may also print a **Network URL**. That is the same app made available
to other devices on your local Wi-Fi; use `localhost` on the computer running
the project.

## Rebuild the cleaned data

If you receive a new source CSV, prepare its offline Parquet file with:

```powershell
python -m scripts.clean_data --input "C:\path\to\CPM23.20261114065311.csv"
```

The script reports usable input rows, relevant HICP rows, invalid index
outliers removed, final row count, date coverage, and output size. The dashboard
automatically uses `data/inflation_clean.parquet`; set `INFLATION_DATA_PATH` to
override it with another CSV or Parquet file.

The cleaner retains the HICP index and annual-rate series and removes index
observations above 10,000, which are impossible placeholder values in this
source (for example, 2,777,777.78). It does not treat the rate series as a
spending weight.

## Story controls

- **Metric:** the selector switches between annual rate of change (year-over-year
  percent change) and HICP index level (2025=100). These are the two HICP
  statistic series retained in the cleaned dataset; the first shows how quickly
  prices are changing, while the second shows the cumulative price level.
- **Category order:** categories stay in a fixed order based on their average
  annual inflation across the full dataset; they are not reranked for each year.
- **Categories:** all broad HICP categories are shown by default; use the
  category picker to filter them.
- **Timeline:** play or pause the animation, reset it, or drag the slider to inspect
  a particular period. The controls are above the graph for quick access.
  Choose yearly or quarterly steps and slow, medium, or fast playback.
- **Appearance:** use the header switch to toggle between the pastel light theme
  and the muted dark theme. Text and chart labels are sized for projection.
- **Presentation layout:** a 70/30 split gives the graph most of the width and
  keeps KPIs and selectors together in a side panel. Playback stays pinned
  within the side panel; historical event highlights sit in the chart header
  without covering data.
- **Chart details:** hover over any dot or horizontal stem to see its category,
  metric value, period, and change from the previous period. The vertical zero
  line is the fixed baseline for comparing category values.
- **Performance:** Streamlit loads the dashboard once; D3 updates the chart and
  runs playback in the browser without rerunning the Python app for each frame.
- **Events:** highlighted years identify historical reference points, not
  causal explanations.
