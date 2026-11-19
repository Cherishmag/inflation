"""D3.js visualization builder for the Ireland HICP Inflation Dashboard."""

from __future__ import annotations
import json
import math
from pathlib import Path
import pandas as pd
from inflation_dashboard.data import load_inflation_data

PALETTE = [
    "#FF4B6E","#00D4AA","#3B82F6","#F59E0B","#A855F7",
    "#06B6D4","#EC4899","#10B981","#F97316","#6366F1",
    "#14B8A6","#8B5CF6","#FBBF24",
]

def _safe(val):
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 3)
    except (TypeError, ValueError):
        return None


def load_viz_data(data_path: str | Path) -> dict:
    src = load_inflation_data(str(data_path))
    broad = src["commodity_code"].astype(str).str.strip().str.fullmatch(r"CP\d{2}")
    src = src[broad].copy()
    all_metrics = src["statistic_label"].dropna().unique().tolist()
    wide = (
        src.pivot_table(
            index=["date","commodity_code","commodity"],
            columns="statistic_label", values="value", aggfunc="mean",
        ).reset_index()
    )
    wide.columns.name = None
    wide["date"] = pd.to_datetime(wide["date"])
    valid = [m for m in all_metrics if m in wide.columns]

    primary = next(
        (m for m in valid if any(k in m.lower() for k in ("rate","change","annual"))),
        valid[0] if valid else None,
    )
    avg_order = (
        wide.groupby("commodity")[primary].mean()
        .sort_values(ascending=False).index.tolist()
        if primary else wide["commodity"].unique().tolist()
    )
    cat_colors = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(avg_order)}

    metric_labels, metric_desc = {}, {}
    for m in valid:
        is_rate = any(k in m.lower() for k in ("rate","change","annual"))
        metric_labels[m] = "Annual Rate of Change (%)" if is_rate else "HICP Index Level (2025=100)"
        metric_desc[m] = (
            "Year-over-year % change in consumer prices. Positive = inflation, negative = deflation."
            if is_rate else
            "Cumulative HICP index where 2025 baseline = 100. Shows price levels over time."
        )

    def to_frames(df, freq=None):
        if freq:
            d = df.copy()
            d["period"] = d["date"].dt.to_period(freq)
            d = (d.groupby(["period","commodity_code","commodity"], observed=True)[valid]
                 .mean().reset_index())
            d["date"] = d["period"].dt.to_timestamp(how="end").dt.normalize()
            d = d.drop(columns="period")
        else:
            d = df.copy()
        dates = sorted(d["date"].dropna().unique())
        if freq == "Y":
            dlabels = [pd.Timestamp(dt).strftime("%Y") for dt in dates]
        elif freq == "Q":
            dlabels = [f"Q{pd.Timestamp(dt).quarter} {pd.Timestamp(dt).year}" for dt in dates]
        else:
            dlabels = [pd.Timestamp(dt).strftime("%b %Y") for dt in dates]
        frame_values = d.pivot(
            index="date", columns="commodity", values=valid
        )
        mdata = {}
        for m in valid:
            values = frame_values[m].reindex(index=dates, columns=avg_order)
            mdata[m] = [
                [_safe(value) for value in row]
                for row in values.to_numpy()
            ]
        return {
            "dates": [pd.Timestamp(dt).strftime("%Y-%m-%d") for dt in dates],
            "dateLabels": dlabels,
            "metrics": mdata,
        }

    cp00 = wide[wide["commodity_code"] == "CP00"].sort_values("date")
    kpis = {}
    for m in valid:
        if m not in cp00.columns: continue
        vdf = cp00.dropna(subset=[m])
        if vdf.empty: continue
        lat, prv = vdf.iloc[-1], (vdf.iloc[-2] if len(vdf) >= 2 else vdf.iloc[-1])
        pk, lo = vdf.loc[vdf[m].idxmax()], vdf.loc[vdf[m].idxmin()]
        kpis[m] = {
            "latest": {"v": _safe(lat[m]),  "d": pd.Timestamp(lat["date"]).strftime("%b %Y")},
            "peak":   {"v": _safe(pk[m]),   "d": pd.Timestamp(pk["date"]).strftime("%b %Y")},
            "low":    {"v": _safe(lo[m]),   "d": pd.Timestamp(lo["date"]).strftime("%b %Y")},
            "delta":  _safe(float(lat[m]) - float(prv[m])),
        }

    xr = {}
    for m in valid:
        v = wide[m].dropna()
        if v.empty: xr[m] = [-2, 15]; continue
        pad = max(float(v.max() - v.min()) * 0.08, 0.5)
        xr[m] = [min(0.0, round(float(v.min()) - pad, 1)), round(float(v.max()) + pad, 1)]

    return {
        "metadata": {
            "source": "CSO Ireland · HICP Series",
            "dateMin": wide["date"].min().strftime("%b %Y"),
            "dateMax": wide["date"].max().strftime("%b %Y"),
        },
        "metrics": valid,
        "metricLabels": metric_labels,
        "metricDesc": metric_desc,
        "primaryMetric": primary,
        "categories": avg_order,
        "categoryColors": cat_colors,
        "xRanges": xr,
        "kpis": kpis,
        "quarterly": to_frames(wide, "Q"),
        "yearly":    to_frames(wide, "Y"),
    }


def generate_viz_html(data: dict) -> str:
    json_str = json.dumps(data, default=str, separators=(",", ":"))
    return _HTML.replace("__DATA__", json_str)


# ─── HTML Template ────────────────────────────────────────────────────────────
_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Ireland's Inflation Journey · HICP</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
:root{
  color-scheme:light;
  --bg:#F1EFF6;--bg2:#FCFAF4;--surf:#F8F5FB;--surf2:#ECE9F4;
  --bdr:#DDD9E8;--bdr2:#BDB7D0;
  --txt:#37354B;--muted:#66647A;--dim:#77748C;
  --pos:#C85E72;--pos-d:rgba(200,94,114,.22);--pos-g:rgba(200,94,114,.35);
  --neg:#3F8C7A;--neg-d:rgba(63,140,122,.2);--neg-g:rgba(63,140,122,.35);
  --acc:#6B83C2;--acc-d:rgba(107,131,194,.18);--acc-g:rgba(107,131,194,.35);
  --acc-strong:#4F639B;--gold:#B88138;
  --null:rgba(92,88,111,.2);--grid-line:rgba(86,82,108,.12);
  --grid-strong:rgba(86,82,108,.22);--zero-line:rgba(111,98,137,.65);
  --year-mark:rgba(107,131,194,.13);--chart-dot-stroke:#FCFAF4;
  --slider-track:rgba(86,82,108,.18);
  --tip-bg:rgba(252,250,244,.98);--tip-shadow:0 8px 32px rgba(49,43,69,.18);
  --title-start:#3B3652;--title-end:#527E79;
  --event-bg:#F8E8EB;--event-border:#C85E72;--event-text:#784250;--event-badge-text:#4F2930;
  --play-a:#7287C5;--play-b:#5A9B8C;
  --r:12px;--rf:999px;
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#20212B;--bg2:#292A37;--surf:#2D2E3C;--surf2:#383948;
  --bdr:#454657;--bdr2:#626378;
  --txt:#EEEAF2;--muted:#C0BBCB;--dim:#A49EAF;
  --pos:#E28A99;--pos-d:rgba(226,138,153,.22);--pos-g:rgba(226,138,153,.35);
  --neg:#78BBA9;--neg-d:rgba(120,187,169,.2);--neg-g:rgba(120,187,169,.35);
  --acc:#A2B1E3;--acc-d:rgba(162,177,227,.18);--acc-g:rgba(162,177,227,.35);
  --acc-strong:#C5CFF0;--gold:#E3BC78;
  --null:rgba(231,225,239,.18);--grid-line:rgba(231,225,239,.08);
  --grid-strong:rgba(231,225,239,.15);--zero-line:rgba(196,180,220,.62);
  --year-mark:rgba(162,177,227,.1);--chart-dot-stroke:#292A37;
  --slider-track:rgba(231,225,239,.16);
  --tip-bg:rgba(38,39,52,.98);--tip-shadow:0 8px 32px rgba(0,0,0,.4);
  --title-start:#F2EEF5;--title-end:#B7D8CF;
  --event-bg:#46313A;--event-border:#E28A99;--event-text:#F0CBD1;--event-badge-text:#302228;
  --play-a:#7788C5;--play-b:#5A9B8C;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--txt);font-family:'Inter','Segoe UI',system-ui,sans-serif;
  height:100%;overflow:hidden;font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
#app{width:100%;height:100vh;max-width:none;margin:0 auto;padding:8px 18px 10px;
  display:flex;flex-direction:column;overflow:hidden}

/* HEADER */
.hdr{display:flex;justify-content:space-between;align-items:flex-start;
  flex:0 0 auto;padding:8px 0 12px;border-bottom:1px solid var(--bdr);margin-bottom:10px}
.hdr-l{display:flex;gap:16px;align-items:center}
.flag{font-size:2rem;line-height:1;filter:drop-shadow(0 2px 8px rgba(0,0,0,.14))}
.hdr h1{font-size:clamp(1.55rem,2.6vw,2.1rem);font-weight:800;letter-spacing:-.04em;
  background:linear-gradient(135deg,var(--title-start) 0%,var(--title-end) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1}
.hdr p{font-size:.95rem;color:var(--muted);margin-top:6px}
.hdr-r{display:flex;flex-direction:row;align-items:center;gap:8px}
.pill{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--rf);
  padding:6px 15px;font-size:.8rem;font-weight:600;letter-spacing:.06em;color:var(--muted)}
.pill.acc{background:var(--acc-d);border-color:var(--bdr2);color:var(--acc-strong);font-size:.78rem}
.theme-toggle{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--rf);
  color:var(--txt);padding:8px 14px;font-size:.86rem;font-weight:700;
  font-family:inherit;cursor:pointer;transition:background .18s,border-color .18s}
.theme-toggle:hover{background:var(--surf2);border-color:var(--acc)}

/* 70/30 presentation layout */
.dashboard-grid{display:grid;grid-template-columns:minmax(0,7fr) minmax(320px,3fr);
  gap:16px;flex:1;min-height:0}
.graph-panel,.side-panel{min-width:0;min-height:0;height:100%;overflow:auto;overscroll-behavior:contain}
.graph-panel{padding-right:4px}
.side-panel{display:flex;flex-direction:column;gap:12px;padding:2px 2px 8px}
.panel-heading{font-size:.76rem;font-weight:800;letter-spacing:.1em;
  text-transform:uppercase;color:var(--dim)}
.chart-heading{margin:2px 0 10px}
.chart-heading h2{font-size:1.15rem;font-weight:800;letter-spacing:-.02em;color:var(--txt)}
.chart-heading p{font-size:.84rem;color:var(--muted);margin-top:2px}

/* KPI STRIP */
.kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.kpi{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);
  padding:11px 12px;transition:border-color .2s,box-shadow .2s;cursor:default}
.kpi:hover{border-color:var(--bdr2);box-shadow:0 0 28px rgba(0,0,0,.35)}
.kpi-lbl{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  color:var(--dim);margin-bottom:6px}
.kpi-val{font-size:1.55rem;font-weight:800;letter-spacing:-.03em;line-height:1}
.kpi-sub{font-size:.75rem;font-weight:600;margin-top:6px;color:var(--muted)}
.kpi-sub.p{color:var(--pos)}.kpi-sub.n{color:var(--neg)}.kpi-sub.a{color:var(--acc)}

/* CONTROLS */
.ctrls{display:flex;flex-direction:column;align-items:stretch;gap:12px;
  background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);
  padding:14px}
.cg{display:flex;flex-direction:column;gap:6px}
.clbl{font-size:.76rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:var(--dim)}
.bg{display:flex;gap:5px;flex-wrap:wrap}
.tbtn{background:transparent;border:1px solid var(--bdr);color:var(--muted);
  padding:8px 16px;border-radius:var(--rf);font-size:.9rem;font-weight:600;
  cursor:pointer;transition:all .18s;font-family:inherit}
.tbtn:hover{background:var(--surf2);color:var(--txt);border-color:var(--bdr2)}
.tbtn.on{background:var(--acc-d);border-color:var(--acc);color:var(--acc-strong)}
.msel{background:var(--surf);border:1px solid var(--bdr);border-radius:8px;color:var(--txt);
  padding:8px 32px 8px 12px;font-size:.9rem;font-weight:500;font-family:inherit;
  cursor:pointer;outline:none;appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239BA3AF' stroke-width='2.5'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;width:100%;min-width:0}
.msel:focus{border-color:var(--acc)}
.msel option{background:var(--bg2);color:var(--txt)}
.cat-picker{position:relative}
.cat-picker summary{list-style:none;background:var(--surf);border:1px solid var(--bdr);
  border-radius:8px;color:var(--txt);padding:8px 12px;font-size:.9rem;font-weight:600;width:100%;
  cursor:pointer;white-space:nowrap}
.cat-picker summary::-webkit-details-marker{display:none}
.cat-picker[open] summary{border-color:var(--acc);color:var(--acc-strong)}
.cat-options{position:absolute;top:calc(100% + 6px);right:0;z-index:40;
  min-width:260px;max-height:280px;overflow:auto;padding:8px;
  background:var(--bg2);border:1px solid var(--bdr2);border-radius:10px;
  box-shadow:0 12px 28px rgba(49,43,69,.2)}
.cat-option{display:flex;align-items:center;gap:9px;padding:6px 8px;
  border-radius:6px;color:var(--txt);font-size:.88rem;cursor:pointer}
.cat-option:hover{background:var(--surf2)}
.cat-option input{accent-color:var(--acc)}
.order-note{font-size:.76rem;color:var(--dim);line-height:1.4}

/* METRIC DESC */
.mdesc{font-size:.84rem;color:var(--muted);padding:10px 12px;
  background:var(--acc-d);border-left:3px solid var(--acc);
  border-radius:0 8px 8px 0}

/* EVENT BANNER */
.evbanner{display:none;align-items:center;gap:12px;
  border:1px solid var(--event-border);border-left:7px solid var(--event-border);
  border-radius:12px;padding:9px 14px;margin-bottom:8px;
  color:var(--event-text);background:var(--event-bg);
  box-shadow:0 5px 18px rgba(49,43,69,.12);
  font-size:1rem;font-weight:700;animation:slideIn .3s ease}
.ev-year{display:inline-flex;align-items:center;justify-content:center;
  min-width:68px;padding:5px 10px;border-radius:9px;
  background:var(--event-border);color:var(--event-badge-text);font-size:1.15rem;font-weight:800;
  letter-spacing:.02em}
.ev-emoji{font-size:1.65rem;line-height:1}
.ev-kicker{display:block;margin-bottom:2px;font-size:.72rem;font-weight:800;
  letter-spacing:.11em;text-transform:uppercase;opacity:.8}
.ev-copy{line-height:1.25}
@keyframes slideIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}

/* CHART CARD */
.chart-card{background:var(--bg2);border:1px solid var(--bdr);border-radius:18px;
  padding:8px;margin-bottom:8px;position:relative;overflow:visible}
.chart-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--acc-g),transparent)}
#chart-wrap svg{display:block}
.x-axis text,.y-axis text{fill:var(--muted);font-family:'Inter',sans-serif}
.x-axis .domain{stroke:var(--grid-strong)}
.y-axis .domain,.x-axis .tick line,.y-axis .tick line{stroke:none}

/* TIMELINE */
.tline-sec{background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r);
  position:sticky;top:0;z-index:30;
  padding:10px 12px;margin-bottom:0;box-shadow:0 3px 14px rgba(49,43,69,.12)}
.pbrow{display:flex;align-items:center;gap:10px;margin-bottom:14px}
#btn-play{display:flex;align-items:center;gap:8px;
  background:linear-gradient(135deg,var(--play-a),var(--play-b));color:#fff;border:none;
  border-radius:var(--rf);padding:10px 24px;font-size:.88rem;font-weight:700;
  font-family:inherit;cursor:pointer;transition:all .2s;
  box-shadow:0 4px 16px var(--acc-g)}
#btn-play:hover{transform:translateY(-1px);box-shadow:0 6px 20px var(--acc-g)}
#btn-play:active{transform:translateY(0)}
#btn-play.paused{background:linear-gradient(135deg,var(--play-b),var(--play-a))}
.cbtn{background:var(--surf);border:1px solid var(--bdr);color:var(--muted);
  border-radius:var(--rf);padding:9px 18px;font-size:.82rem;font-weight:600;
  font-family:inherit;cursor:pointer;transition:all .18s}
.cbtn:hover{background:var(--surf2);color:var(--txt);border-color:var(--bdr2)}
.ddisp{margin-left:auto;font-size:1rem;font-weight:700;
  background:var(--acc-d);border:1px solid var(--bdr2);
  border-radius:8px;padding:6px 14px;min-width:100px;text-align:center}
.ttrack{display:flex;align-items:center;gap:12px}
.tlbl{font-size:.82rem;color:var(--dim);font-weight:600;white-space:nowrap}
.swrap{flex:1;position:relative}
.tmarks{position:absolute;top:-16px;left:0;right:0;height:14px;pointer-events:none}
.tmk{position:absolute;width:6px;height:6px;border-radius:50%;transform:translateX(-50%);top:6px}
.tmlbl{position:absolute;font-size:.72rem;font-weight:700;transform:translateX(-50%);top:0;white-space:nowrap}
input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:4px;
  background:var(--slider-track);border-radius:2px;outline:none;cursor:pointer}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;
  background:var(--acc);border-radius:50%;border:2.5px solid var(--chart-dot-stroke);
  box-shadow:0 0 12px var(--acc-g);cursor:pointer;transition:transform .15s,box-shadow .15s}
input[type=range]::-webkit-slider-thumb:hover{transform:scale(1.25);box-shadow:0 0 20px var(--acc-g)}
input[type=range]::-moz-range-thumb{width:16px;height:16px;background:var(--acc);
  border-radius:50%;border:2px solid var(--chart-dot-stroke);cursor:pointer}

/* TOOLTIP */
#tip{position:fixed;pointer-events:none;background:var(--tip-bg);
  border:1px solid var(--bdr2);border-radius:var(--r);padding:12px 16px;
  font-size:.92rem;box-shadow:var(--tip-shadow);
  opacity:0;transition:opacity .15s;z-index:9999;max-width:230px}
#tip.vis{opacity:1}
.tn{font-weight:700;margin-bottom:4px}
.tv{font-size:1.3rem;font-weight:800;line-height:1.2}
.td{font-size:.84rem;color:var(--muted);margin-top:4px}

/* LEGEND */
.legend{display:flex;gap:20px;flex-wrap:wrap;padding:10px 0;
  border-top:1px solid var(--bdr);margin-top:4px}
.li{display:flex;align-items:center;gap:9px;font-size:.9rem;color:var(--muted);font-weight:500}
.ls{width:13px;height:13px;border-radius:50%}

/* FOOTER */
.ftr{display:flex;flex-direction:column;gap:4px;
  padding:10px 2px 0;border-top:1px solid var(--bdr);
  font-size:.76rem;color:var(--dim);margin-top:auto}

@media(max-width:1050px){
  html,body{height:auto;min-height:100%;overflow:auto}
  #app{height:auto;min-height:100vh;overflow:visible;padding:10px 14px}
  .hdr{align-items:flex-start;gap:10px;flex-wrap:wrap}
  .hdr-r{flex-wrap:wrap;justify-content:flex-start}
  .dashboard-grid{display:flex;flex-direction:column;overflow:visible}
  .side-panel{order:-1;height:auto;overflow:visible}
  .graph-panel{height:auto;overflow:visible}
  .tline-sec{top:0}
}

::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--bdr2);border-radius:3px}
</style>
</head>
<body>
<div id="app">

<header class="hdr">
  <div class="hdr-l">
    <div class="flag">🇮🇪</div>
    <div>
      <h1>Ireland's Inflation Journey</h1>
      <p>Harmonised Index of Consumer Prices · CSO Ireland · Animated Category Comparison</p>
    </div>
  </div>
  <div class="hdr-r">
    <div class="pill">CSO IRELAND · HICP</div>
    <div class="pill acc" id="date-pill">Loading…</div>
    <button class="theme-toggle" id="theme-toggle" type="button" aria-pressed="false">
      ☾ Dark mode
    </button>
  </div>
</header>

<div class="dashboard-grid">
  <main class="graph-panel">
    <div class="evbanner" id="evbanner">
      <span class="ev-year" id="ev-year"></span>
      <span class="ev-emoji" id="ev-emoji"></span>
      <span class="ev-copy"><span class="ev-kicker">Key historical moment</span><span id="ev-txt"></span></span>
    </div>
    <div class="chart-card">
      <div id="chart-wrap"></div>
    </div>
  </main>

  <aside class="side-panel">
    <div class="panel-heading">Key indicators</div>
    <div class="kpis">
      <div class="kpi" id="kpi-latest">
        <div class="kpi-lbl">Latest All-Items</div>
        <div class="kpi-val">—</div>
        <div class="kpi-sub">—</div>
      </div>
      <div class="kpi" id="kpi-peak">
        <div class="kpi-lbl">Historical Peak</div>
        <div class="kpi-val">—</div>
        <div class="kpi-sub">Highest recorded</div>
      </div>
      <div class="kpi" id="kpi-low">
        <div class="kpi-lbl">Historical Low</div>
        <div class="kpi-val">—</div>
        <div class="kpi-sub">Lowest recorded</div>
      </div>
      <div class="kpi" id="kpi-now">
        <div class="kpi-lbl">Viewing Period</div>
        <div class="kpi-val" id="kv-period">—</div>
        <div class="kpi-sub a" id="ks-period">Press ▶ Play to animate</div>
      </div>
    </div>

    <div class="tline-sec">
      <div class="pbrow">
        <button id="btn-play">▶ Play</button>
        <button class="cbtn" id="btn-reset">↺ Reset</button>
        <div class="ddisp" id="cur-date">—</div>
      </div>
      <div class="ttrack">
        <span class="tlbl" id="d-start">—</span>
        <div class="swrap">
          <div class="tmarks" id="tmarks"></div>
          <input type="range" id="slider" min="0" max="100" value="0">
        </div>
        <span class="tlbl" id="d-end">—</span>
      </div>
    </div>

    <div class="panel-heading">Dashboard controls</div>
    <div class="ctrls">
      <div class="cg">
        <div class="clbl">Metric</div>
        <select class="msel" id="msel"></select>
      </div>
      <div class="cg">
        <div class="clbl">Categories</div>
        <details class="cat-picker">
          <summary id="cat-summary">All categories</summary>
          <div class="cat-options" id="cat-options"></div>
        </details>
        <div class="order-note">Category order is fixed by average annual inflation across the full dataset.</div>
      </div>
      <div class="cg">
        <div class="clbl">Interval</div>
        <div class="bg" id="igrp">
          <button class="tbtn on" data-iv="yearly">Yearly</button>
          <button class="tbtn" data-iv="quarterly">Quarterly</button>
        </div>
      </div>
      <div class="cg">
        <div class="clbl">Speed</div>
        <div class="bg" id="sgrp">
          <button class="tbtn" data-sp="1200">Slow</button>
          <button class="tbtn on" data-sp="500">Medium</button>
          <button class="tbtn" data-sp="150">Fast</button>
        </div>
      </div>
    </div>
    <div class="mdesc" id="mdesc">—</div>
    <div class="legend">
      <div class="li"><div class="ls" style="background:var(--pos);box-shadow:0 0 7px var(--pos-g)"></div>
        <span>Positive inflation — prices rising above zero</span></div>
      <div class="li"><div class="ls" style="background:var(--neg);box-shadow:0 0 7px var(--neg-g)"></div>
        <span>Deflation — prices falling below zero</span></div>
      <div class="li"><div class="ls" style="background:var(--gold)"></div>
        <span>★ Key economic event year</span></div>
    </div>

    <footer class="ftr">
      <span>📊 Ireland's HICP Inflation Dashboard</span>
      <span id="ftr-src">Data: CSO Ireland · Harmonised Index of Consumer Prices</span>
      <span>Powered by D3.js v7 — Zero server lag</span>
    </footer>
  </aside>
</div>
</div>

<div id="tip"><div class="tn" id="tn"></div><div class="tv" id="tv"></div><div class="td" id="td"></div></div>

<script>
const DATA = __DATA__;

const themeColor=name=>getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const TR=340;

const EVENTS={
  2008:{label:'Global Financial Crisis',   emoji:'🏦',color:'#B58445'},
  2009:{label:'Post-Crisis Recession',     emoji:'📉',color:'#BE805C'},
  2010:{label:'European Debt Crisis',      emoji:'🏦',color:'#9E83B4'},
  2020:{label:'COVID-19 Pandemic',         emoji:'🦠',color:'#C46B77'},
  2021:{label:'Post-Pandemic Recovery',    emoji:'💉',color:'#D28854'},
  2022:{label:'Energy & Food Price Surge', emoji:'⚡',color:'#C85E72'},
  2023:{label:'Gradual Disinflation',      emoji:'📉',color:'#659781'},
};

let st={iv:'yearly',metric:DATA.primaryMetric||DATA.metrics[0],fi:0,playing:false,spms:500,timer:null,
        categories:DATA.categories.slice()};

// ── Helpers ──────────────────────────────────────────────────
const idata=()=>DATA[st.iv];
const total=()=>idata().dates.length;
const dlabel=i=>idata().dateLabels[i]||'';
const yearOf=i=>{const m=dlabel(i).match(/\\d{4}/);return m?+m[0]:0;};
const isRate=()=>/rate|change|annual/i.test(st.metric);
const fmt=v=>{
  if(v===null||v===undefined)return '—';
  return isRate()?`${v>0?'+':''}${v.toFixed(1)}%`:v.toFixed(1);
};
const trunc=(s,n)=>s.length>n?s.slice(0,n-1)+'…':s;

function getVals(fi){
  const frames=idata().metrics[st.metric];
  if(!frames||!frames[fi])return{};
  const v=frames[fi],out={};
  DATA.categories.forEach((c,i)=>{out[c]=v[i];});
  return out;
}

function initCategoryPicker(){
  const options=document.getElementById('cat-options');
  DATA.categories.forEach(category=>{
    const label=document.createElement('label');
    label.className='cat-option';
    const input=document.createElement('input');
    input.type='checkbox';input.checked=true;
    input.addEventListener('change',()=>{
      const selected=[...options.querySelectorAll('input:checked')].map(el=>el.value);
      if(!selected.length){input.checked=true;return;}
      st.categories=selected;
      document.getElementById('cat-summary').textContent=
        selected.length===DATA.categories.length?'All categories':`Categories (${selected.length})`;
      initChart();updateChart(st.fi,false);
    });
    input.value=category;
    label.append(input,document.createTextNode(category));
    options.appendChild(label);
  });
}

// ── Chart ─────────────────────────────────────────────────────
const MAR={t:12,r:155,b:58,l:235},ROW=34;
let svg,g,xSc,ySc,stemSel,dotSel,lblSel,yearMark,prevVals={};

function cW(){return document.getElementById('chart-wrap').clientWidth-MAR.l-MAR.r;}
function cH(){return DATA.categories.length*ROW;}

function mkXScale(){
  const xr=DATA.xRanges[st.metric]||[-2,15];
  xSc=d3.scaleLinear().domain([xr[0],xr[1]+2.5]).range([0,cW()]).nice();
}

function initChart(){
  d3.select('#chart-wrap').selectAll('*').remove();
  const W=cW(),H=cH();
  svg=d3.select('#chart-wrap').append('svg')
    .attr('width',W+MAR.l+MAR.r).attr('height',H+MAR.t+MAR.b)
    .style('overflow','visible');
  g=svg.append('g').attr('transform',`translate(${MAR.l},${MAR.t})`);

  // Fixed Y scale — domain never changes
  ySc=d3.scaleBand().domain(st.categories).range([0,H])
    .paddingInner(.44).paddingOuter(.1);
  mkXScale();

  // SVG defs: gradients
  const defs=svg.append('defs');
  const pg=defs.append('linearGradient').attr('id','gpos');
  pg.append('stop').attr('offset','0%').attr('stop-color',themeColor('--pos')).attr('stop-opacity',.06);
  pg.append('stop').attr('offset','100%').attr('stop-color',themeColor('--pos')).attr('stop-opacity',.4);
  const ng=defs.append('linearGradient').attr('id','gneg');
  ng.append('stop').attr('offset','0%').attr('stop-color',themeColor('--neg')).attr('stop-opacity',.4);
  ng.append('stop').attr('offset','100%').attr('stop-color',themeColor('--neg')).attr('stop-opacity',.06);

  // Grid
  renderGrid();

  // Zero line
  g.append('line').attr('id','zl')
    .attr('y1',-MAR.t).attr('y2',H+10)
    .attr('stroke',themeColor('--zero-line')).attr('stroke-width',1.8)
    .attr('stroke-dasharray','5,4');

  // Axes
  g.append('g').attr('class','x-axis').attr('transform',`translate(0,${H})`);
  g.append('g').attr('class','y-axis')
    .call(d3.axisLeft(ySc).tickSize(0).tickPadding(14).tickFormat(d=>trunc(d,30)))
    .call(a=>a.select('.domain').remove())
    .call(a=>a.selectAll('text').style('font-size','14px').style('font-weight','500')
      .style('fill',themeColor('--muted')));

  // Year watermark
  yearMark=g.append('text').attr('x',W-6).attr('y',H-8).attr('text-anchor','end')
    .style('font-size','104px').style('font-weight','900')
    .style('fill',themeColor('--year-mark')).style('font-family',"'Inter',sans-serif")
    .style('letter-spacing','-.05em').style('pointer-events','none');

  // Stems
  stemSel=g.selectAll('.stem').data(st.categories,d=>d).enter()
    .append('rect').attr('class','stem')
    .attr('y',d=>ySc(d)+ySc.bandwidth()/2-2.5).attr('height',5).attr('rx',2.5)
    .attr('x',xSc(0)).attr('width',0).attr('fill',themeColor('--null'))
    .style('cursor','pointer')
    .on('mouseover',onOver).on('mousemove',onMove).on('mouseout',onOut);

  // Dots
  dotSel=g.selectAll('.dot').data(st.categories,d=>d).enter()
    .append('circle').attr('class','dot').attr('r',11)
    .attr('cy',d=>ySc(d)+ySc.bandwidth()/2).attr('cx',xSc(0))
    .attr('fill',themeColor('--null')).attr('stroke',themeColor('--chart-dot-stroke')).attr('stroke-width',2.5)
    .style('cursor','pointer')
    .on('mouseover',onOver).on('mousemove',onMove).on('mouseout',onOut);

  // Labels
  lblSel=g.selectAll('.lbl').data(st.categories,d=>d).enter()
    .append('text').attr('class','lbl')
    .attr('y',d=>ySc(d)+ySc.bandwidth()/2+4.5)
    .style('font-size','13px').style('font-weight','700')
    .style('font-family',"'Inter',sans-serif");

  renderAxes();
  updateZL();
}

function renderGrid(){
  g.selectAll('.gl').remove();
  g.selectAll('.gl').data(xSc.ticks(6)).enter().append('line').attr('class','gl')
    .attr('x1',d=>xSc(d)).attr('x2',d=>xSc(d)).attr('y1',0).attr('y2',cH())
    .attr('stroke',themeColor('--grid-line')).attr('stroke-width',1);
}
function renderAxes(){
  g.select('.x-axis').call(
    d3.axisBottom(xSc).ticks(6)
      .tickFormat(d=>isRate()?`${d>0?'+':''}${d}%`:d)
  ).call(a=>a.select('.domain').attr('stroke',themeColor('--grid-strong')))
   .call(a=>a.selectAll('text').style('font-size','14px').style('fill',themeColor('--muted')))
   .call(a=>a.selectAll('.tick line').attr('stroke',themeColor('--grid-line')).attr('y2',6));
}
function updateZL(){g.select('#zl').attr('x1',xSc(0)).attr('x2',xSc(0));}

// ── Update ────────────────────────────────────────────────────
function updateChart(fi,anim=true){
  if(fi<0||fi>=total())return;
  st.fi=fi;
  const dur=anim?Math.min(TR,Math.round(st.spms*.8)):0;
  const ease=d3.easeCubicInOut;
  const vals=getVals(fi),yr=yearOf(fi);

  stemSel.transition().duration(dur).ease(ease)
    .attr('x',d=>{const v=vals[d];if(v==null)return xSc(0);return v>=0?xSc(0):xSc(v);})
    .attr('width',d=>{const v=vals[d];if(v==null)return 0;return Math.max(0,Math.abs(xSc(v)-xSc(0)));})
    .attr('fill',d=>{const v=vals[d];if(v==null)return themeColor('--null');return v>=0?'url(#gpos)':'url(#gneg)';});

  dotSel.transition().duration(dur).ease(ease)
    .attr('cx',d=>xSc(vals[d]!=null?vals[d]:0))
    .attr('fill',d=>{const v=vals[d];if(v==null)return themeColor('--null');return v>=0?themeColor('--pos'):themeColor('--neg');})
    .attr('r',d=>vals[d]==null?6:11);

  lblSel.transition().duration(dur).ease(ease)
    .attr('x',d=>{const v=vals[d];if(v==null)return xSc(0)+10;return xSc(v)+(v>=0?16:-16);})
    .attr('text-anchor',d=>{const v=vals[d];return(v==null||v>=0)?'start':'end';})
    .attr('fill',d=>{const v=vals[d];if(v==null)return themeColor('--null');return v>=0?themeColor('--pos'):themeColor('--neg');})
    .text(d=>{const v=vals[d];return v==null?'':fmt(v);});

  yearMark.transition().duration(dur*.5).ease(ease)
    .text(yr>0?String(yr):'');

  // UI
  document.getElementById('cur-date').textContent=dlabel(fi);
  const sl=document.getElementById('slider');
  sl.value=fi;
  const pct=total()>1?(fi/(total()-1))*100:0;
  sl.style.background=`linear-gradient(to right,${themeColor('--acc')} ${pct}%,${themeColor('--slider-track')} ${pct}%)`;

  // Event banner
  const ev=EVENTS[yr];
  const bn=document.getElementById('evbanner');
  if(ev){
    document.getElementById('ev-year').textContent=String(yr);
    document.getElementById('ev-emoji').textContent=ev.emoji;
    document.getElementById('ev-txt').textContent=ev.label;
    bn.style.display='flex';
  } else {bn.style.display='none';}

  document.getElementById('kv-period').textContent=dlabel(fi);
  prevVals=vals;
}

// ── Metric / Interval / Speed ─────────────────────────────────
function switchMetric(m){
  st.metric=m;mkXScale();renderGrid();renderAxes();updateZL();
  document.getElementById('mdesc').textContent=DATA.metricDesc[m]||'';
  renderKPIs();updateChart(0,false);
}
function switchInterval(iv){
  const was=st.playing;if(was)pause();
  st.iv=iv;st.fi=0;
  const sl=document.getElementById('slider');
  sl.max=total()-1;sl.value=0;
  renderEdges();renderMarkers();updateChart(0,false);
  if(was)play();
}

// ── Play / Pause / Reset ──────────────────────────────────────
function play(){
  if(st.fi>=total()-1)st.fi=0;
  st.playing=true;
  const btn=document.getElementById('btn-play');
  btn.textContent='⏸ Pause';btn.classList.add('paused');
  st.timer=setInterval(()=>{
    if(st.fi<total()-1){updateChart(st.fi+1,true);}
    else{pause();}
  },st.spms);
}
function pause(){
  clearInterval(st.timer);st.timer=null;st.playing=false;
  const btn=document.getElementById('btn-play');
  btn.textContent='▶ Play';btn.classList.remove('paused');
}
function reset(){pause();updateChart(0,false);}

// ── KPIs ──────────────────────────────────────────────────────
function renderKPIs(){
  const k=DATA.kpis[st.metric];if(!k)return;
  const el=id=>document.getElementById(id);
  el('kpi-latest').querySelector('.kpi-val').textContent=fmt(k.latest.v);
  const d=k.delta,sg=d>0?'▲':'▼',cls=d>0?'p':'n';
  el('kpi-latest').querySelector('.kpi-sub').textContent=`${sg} ${Math.abs(d).toFixed(2)} vs prior · ${k.latest.d}`;
  el('kpi-latest').querySelector('.kpi-sub').className=`kpi-sub ${cls}`;
  el('kpi-peak').querySelector('.kpi-val').textContent=fmt(k.peak.v);
  el('kpi-peak').querySelector('.kpi-sub').textContent=k.peak.d;
  el('kpi-peak').querySelector('.kpi-sub').className='kpi-sub p';
  el('kpi-low').querySelector('.kpi-val').textContent=fmt(k.low.v);
  el('kpi-low').querySelector('.kpi-sub').textContent=k.low.d;
  el('kpi-low').querySelector('.kpi-sub').className='kpi-sub n';
}

// ── Timeline ──────────────────────────────────────────────────
function renderEdges(){
  const lb=idata().dateLabels;
  document.getElementById('d-start').textContent=lb[0]||'';
  document.getElementById('d-end').textContent=lb[lb.length-1]||'';
}
function renderMarkers(){
  const c=document.getElementById('tmarks');c.innerHTML='';
  const tot=total();
  for(const[yr,ev]of Object.entries(EVENTS)){
    const idx=idata().dates.findIndex(d=>d.startsWith(yr));
    if(idx<0)continue;
    const pct=(idx/Math.max(tot-1,1))*100;
    const dot=document.createElement('div');
    dot.className='tmk';dot.style.left=`${pct}%`;
    dot.style.background=ev.color;dot.style.boxShadow=`0 0 5px ${ev.color}`;
    dot.title=`${ev.emoji} ${ev.label}`;
    c.appendChild(dot);
    if(['2008','2020','2022'].includes(yr)){
      const lbl=document.createElement('div');
      lbl.className='tmlbl';lbl.style.left=`${pct}%`;
      lbl.style.color=ev.color;lbl.textContent=yr;
      c.appendChild(lbl);
    }
  }
}

// ── Tooltip ───────────────────────────────────────────────────
function onOver(e,d){
  const v=getVals(st.fi)[d],pv=prevVals[d];
  document.getElementById('tn').textContent=d;
  document.getElementById('tv').textContent=fmt(v);
  document.getElementById('tv').style.color=(v!=null&&v>=0)?themeColor('--pos'):themeColor('--neg');
  document.getElementById('td').textContent=(v!=null&&pv!=null)?
    `${dlabel(st.fi)} · Δ ${(v-pv)>0?'+':''}${(v-pv).toFixed(2)} from previous period`:
    dlabel(st.fi);
  document.getElementById('tip').classList.add('vis');
}
function onMove(e){
  const t=document.getElementById('tip'),px=12;
  let tx=e.clientX+px,ty=e.clientY+px;
  if(tx+240>window.innerWidth)tx=e.clientX-240-px;
  if(ty+110>window.innerHeight)ty=e.clientY-110-px;
  t.style.left=tx+'px';t.style.top=ty+'px';
}
function onOut(){document.getElementById('tip').classList.remove('vis');}

function applyTheme(theme){
  document.documentElement.dataset.theme=theme;
  const button=document.getElementById('theme-toggle');
  const dark=theme==='dark';
  button.textContent=dark?'☀ Light mode':'☾ Dark mode';
  button.setAttribute('aria-pressed',String(dark));
  button.setAttribute('aria-label',`Switch to ${dark?'light':'dark'} theme`);
  if(svg){initChart();updateChart(st.fi,false);}
}

// ── Bootstrap ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded',()=>{
  const themeToggle=document.getElementById('theme-toggle');
  themeToggle.addEventListener('click',()=>{
    const current=document.documentElement.dataset.theme||'light';
    applyTheme(current==='dark'?'light':'dark');
  });
  applyTheme('light');
  initCategoryPicker();
  // Metric selector
  const msel=document.getElementById('msel');
  DATA.metrics.forEach(m=>{
    const o=document.createElement('option');
    o.value=m;o.textContent=DATA.metricLabels[m]||m;
    if(m===st.metric)o.selected=true;
    msel.appendChild(o);
  });
  msel.addEventListener('change',e=>switchMetric(e.target.value));

  // Interval buttons
  document.querySelectorAll('#igrp .tbtn').forEach(b=>{
    b.addEventListener('click',()=>{
      document.querySelectorAll('#igrp .tbtn').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');switchInterval(b.dataset.iv);
    });
  });

  // Speed buttons
  document.querySelectorAll('#sgrp .tbtn').forEach(b=>{
    b.addEventListener('click',()=>{
      document.querySelectorAll('#sgrp .tbtn').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');st.spms=+b.dataset.sp;
      if(st.playing){pause();play();}
    });
  });

  document.getElementById('btn-play').addEventListener('click',()=>{
    if(st.playing)pause();else play();
  });
  document.getElementById('btn-reset').addEventListener('click',reset);

  const sl=document.getElementById('slider');
  sl.max=total()-1;
  sl.addEventListener('input',e=>{
    if(st.playing)pause();
    updateChart(+e.target.value,false);
  });

  document.getElementById('date-pill').textContent=
    `📅 ${DATA.metadata.dateMin} – ${DATA.metadata.dateMax}`;
  document.getElementById('mdesc').textContent=DATA.metricDesc[st.metric]||'';
  document.getElementById('ftr-src').textContent=
    `Data: ${DATA.metadata.source} · ${DATA.metadata.dateMin} – ${DATA.metadata.dateMax}`;

  renderKPIs();renderEdges();renderMarkers();
  initChart();

  // Start at 2022 (peak drama)
  const initFi=idata().dateLabels.findIndex(l=>l.includes('2022'));
  updateChart(initFi>=0?initFi:0,false);

  window.addEventListener('resize',()=>{
    initChart();updateChart(st.fi,false);renderMarkers();
  });
});
</script>
</body>
</html>"""
