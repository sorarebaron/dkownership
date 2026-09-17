import io
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.patches import Rectangle

# ----------------------------------------------------------------------------
# DraftKings NFL Showdown Ownership Report
# Ingests a DraftKings NFL Showdown contest standings CSV and builds a
# tweet-ready ownership graphic: PLAYER | CPT DRAFT% | FLEX DRAFT%
# ----------------------------------------------------------------------------

# ---- Brand palette (DraftKings) ----
BG = "#0e1015"          # near-black background
STRIPE = "#1c2029"      # alternating row shade
ORANGE = "#F6770E"      # DK orange  -> CPT
GREEN = "#61B50E"       # DK green   -> FLEX
ORANGE_TXT = "#f4a259"  # softened orange for values
GREEN_TXT = "#a6d95b"   # softened green for values
WHITE = "#FFFFFF"
MUTED = "#7d859680"     # dash / empty value
MUTED_TXT = "#8b93a3"   # header sub-labels
LINE = "#2c313c"

MAX_NAME_LENGTH = 17

st.set_page_config(page_title="DK NFL Showdown Ownership", page_icon="🏈", layout="centered")


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
def load_ownership(uploaded_file):
    """Read a DK Showdown standings CSV and return one row per player with
    separate CPT% and FLEX% ownership.

    The relevant fields are Player (col H), Roster Position (col I, holds
    CPT/FLEX) and %Drafted (col J). We prefer to match by header name and
    fall back to positional indices if the headers differ.
    """
    df = pd.read_csv(uploaded_file)

    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    player_c = cols_lower.get("player")
    role_c = cols_lower.get("roster position")
    pct_c = cols_lower.get("%drafted")
    if player_c is None or role_c is None or pct_c is None:
        # Fall back to DK's fixed layout: H=7 (Player), I=8 (Roster Position), J=9 (%Drafted)
        player_c, role_c, pct_c = df.columns[7], df.columns[8], df.columns[9]

    sub = df[[player_c, role_c, pct_c]].copy()
    sub.columns = ["PLAYER", "ROLE", "PCT"]
    sub = sub.dropna(subset=["PLAYER", "ROLE"])
    sub["PLAYER"] = sub["PLAYER"].astype(str).str.strip()
    sub["ROLE"] = sub["ROLE"].astype(str).str.strip().str.upper()
    sub["PCT"] = (
        sub["PCT"].astype(str).str.replace("%", "", regex=False).str.strip()
    )
    sub["PCT"] = pd.to_numeric(sub["PCT"], errors="coerce")
    sub = sub.dropna(subset=["PCT"])

    cpt = sub[sub["ROLE"] == "CPT"].groupby("PLAYER")["PCT"].max()
    flex = sub[sub["ROLE"] == "FLEX"].groupby("PLAYER")["PCT"].max()

    players = set(cpt.index) | set(flex.index)
    out = pd.DataFrame(
        [{"PLAYER": p, "CPT": cpt.get(p), "FLEX": flex.get(p)} for p in players]
    )

    # Drop players who weren't meaningfully rostered: keep a player only if their
    # CPT or FLEX ownership rounds to at least 0.01% (anything that displays as
    # 0.00% reads as a dash and counts as not owned).
    rostered = out.apply(
        lambda r: _shown(r["CPT"]) or _shown(r["FLEX"]), axis=1
    )
    out = out[rostered]

    # Sort: players with real CPT ownership first by CPT desc, then everyone
    # whose CPT shows a dash (missing or 0.00%) by FLEX desc. Secondary keys
    # break ties deterministically (FLEX desc, then name).
    has_cpt = out["CPT"].apply(_shown)
    g1 = out[has_cpt].sort_values(
        ["CPT", "FLEX", "PLAYER"], ascending=[False, False, True]
    )
    g2 = out[~has_cpt].sort_values(
        ["FLEX", "PLAYER"], ascending=[False, True]
    )
    return pd.concat([g1, g2]).reset_index(drop=True)


def _abbreviate(name):
    if len(name) > MAX_NAME_LENGTH:
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}. {' '.join(parts[1:])}"
    return name


def _shown(v):
    """True when an ownership value displays as a real (non-zero) percentage.
    A missing value, or one DraftKings rounds to 0.00%, is treated as 'not
    owned' — it shows as a dash and doesn't keep a player on the graphic.
    """
    return pd.notna(v) and f"{v:.2f}" != "0.00"


def _fmt(v):
    return f"{v:.2f}%" if _shown(v) else "—"


# ----------------------------------------------------------------------------
# Graphic
# ----------------------------------------------------------------------------
def build_graphic(df):
    n = len(df)
    half = (n + 1) // 2
    cols = [df.iloc[:half].reset_index(drop=True), df.iloc[half:].reset_index(drop=True)]
    rows_per = max(half, 1)
    cpt_max = df["CPT"].max()
    flex_max = df["FLEX"].max()

    fig_h = 1.1 + rows_per * 0.42
    fig, ax = plt.subplots(figsize=(13, fig_h), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Top margin (inches) leaves room for the column-header row above the table.
    top = 1 - 0.55 / fig_h

    bottom = 0.28 / fig_h
    row_h = (top - bottom) / rows_per
    panels = [{"x0": 0.035, "w": 0.445}, {"x0": 0.520, "w": 0.445}]

    for pi, panel in enumerate(panels):
        x0, w = panel["x0"], panel["w"]
        name_x = x0 + 0.008
        cpt_cell_l = x0 + 0.44 * w
        cpt_r = x0 + 0.70 * w
        flex_cell_l = x0 + 0.72 * w
        flex_r = x0 + 0.99 * w

        hy = top + row_h * 0.55
        ax.text(name_x, hy, "PLAYER", color=MUTED_TXT, fontsize=12.5, fontweight="bold", ha="left", va="center")
        ax.text(cpt_r, hy, "CPT%", color=ORANGE, fontsize=12.5, fontweight="bold", ha="right", va="center")
        ax.text(flex_r, hy, "FLEX%", color=GREEN, fontsize=12.5, fontweight="bold", ha="right", va="center")
        ax.plot([x0, x0 + w], [top + row_h * 0.12, top + row_h * 0.12], color=LINE, lw=1.2)

        cdf = cols[pi]
        for i in range(len(cdf)):
            yc = top - (i + 0.5) * row_h
            if i % 2 == 0:
                ax.add_patch(Rectangle((x0, yc - row_h / 2), w, row_h, color=STRIPE, zorder=0))
            bar_h = row_h * 0.52
            cpt_v, flex_v = cdf.at[i, "CPT"], cdf.at[i, "FLEX"]
            if not pd.isna(cpt_v) and cpt_max > 0:
                cw = (cpt_r - cpt_cell_l) * (cpt_v / cpt_max)
                ax.add_patch(Rectangle((cpt_r - cw, yc - bar_h / 2), cw, bar_h, color=ORANGE, alpha=0.30, zorder=1))
            if not pd.isna(flex_v) and flex_max > 0:
                fw = (flex_r - flex_cell_l) * (flex_v / flex_max)
                ax.add_patch(Rectangle((flex_r - fw, yc - bar_h / 2), fw, bar_h, color=GREEN, alpha=0.30, zorder=1))
            ax.text(name_x, yc, _abbreviate(cdf.at[i, "PLAYER"]), color=WHITE, fontsize=13.5, ha="left", va="center", zorder=3)
            ax.text(cpt_r, yc, _fmt(cpt_v), color=ORANGE_TXT if _shown(cpt_v) else MUTED,
                    fontsize=12.5, ha="right", va="center", zorder=3)
            ax.text(flex_r, yc, _fmt(flex_v), color=GREEN_TXT if _shown(flex_v) else MUTED,
                    fontsize=12.5, ha="right", va="center", zorder=3)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor=BG, pad_inches=0.28)
    plt.close(fig)
    buf.seek(0)
    return buf


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
# Optional branded header image if one is dropped into the repo; else styled text.
if os.path.exists("DK-Ownership-Header.png"):
    st.image("DK-Ownership-Header.png", use_container_width=True)
else:
    st.markdown(
        "<h1 style='text-align:center; margin-bottom:0;'>"
        "<span style='color:#F6770E;'>DraftKings</span> "
        "<span style='color:#61B50E;'>NFL Showdown</span></h1>"
        "<p style='text-align:center; color:#8b93a3; font-size:20px; "
        "letter-spacing:2px; margin-top:4px;'>OWNERSHIP REPORT</p>",
        unsafe_allow_html=True,
    )

uploaded_file = st.file_uploader("", type=["csv"])
if uploaded_file:
    try:
        df = load_ownership(uploaded_file)
        if df.empty:
            st.warning("No CPT/FLEX ownership rows found in this file. Is it a DK Showdown standings CSV?")
        else:
            image_buf = build_graphic(df)
            st.image(image_buf)
            st.download_button(
                "Download Ownership Report",
                data=image_buf,
                file_name="nfl_showdown_ownership.png",
                mime="image/png",
            )
    except Exception as e:
        st.error(f"Error processing file: {e}")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<p style='font-size:26px; color:#F6770E;'>step 1: upload CSV<br>"
    "<span style='color:#61B50E;'>step 2: download report</span></p>",
    unsafe_allow_html=True,
)

st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(
    "<p style='font-size:18px; color:#aaa;'>no shoes / no shirts / no tips</p>",
    unsafe_allow_html=True,
)

if os.path.exists("tips.png"):
    st.image("tips.png", use_container_width=True)
