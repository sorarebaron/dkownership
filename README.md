# DraftKings NFL Showdown Ownership

A Streamlit app that ingests a **DraftKings NFL Showdown** contest standings CSV
and produces a tweet-ready ownership graphic in DraftKings' brand colors.

The graphic lists every rostered player with their **Captain (CPT)** and
**FLEX** ownership side by side:

```
PLAYER | CPT DRAFT% | FLEX DRAFT%
```

Players are sorted first by **CPT ownership** (largest to smallest); players
who were never captained fall to the bottom, sorted by **FLEX ownership**.

## Usage

1. **Upload CSV** — the contest standings/results CSV DraftKings provides at
   contest lock.
2. **Download report** — a PNG ready to tweet.

## How it reads the file

DraftKings' Showdown standings export carries the ownership data in three
columns: `Player`, `Roster Position` (`CPT` / `FLEX`), and `%Drafted`. Each
player can appear twice — once as CPT and once as FLEX — each with its own
`%Drafted`. The app pivots these into a single row per player with separate
CPT% and FLEX% values. It matches columns by name, falling back to DraftKings'
fixed positional layout (columns H / I / J).

> Note: this standings file does not contain football positions
> (QB/RB/WR/TE/K/DST), so the graphic intentionally omits a POS column.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Deployed on Streamlit Community Cloud, pulling from this repo, with `app.py` as
the entrypoint.

## Optional branding

- Drop a `DK-Ownership-Header.png` in the repo root to show a banner logo at the
  top of the app (otherwise a styled text header is used).
- Drop a `tips.png` to show a tip-jar image in the footer.
