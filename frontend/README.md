# Futurefall · Frontend

A clean, dark **blue financial-research** workbench that visualizes a full
multi-agent research run produced by the Python AI core. It turns the
backend's JSON export into an animated, human-readable view of how the
agents collaborated and what the final memo concluded.

> Research support tooling — **not investment advice.**

---

## Tech stack

| Concern    | Choice                          |
| ---------- | ------------------------------- |
| Framework  | React 18                        |
| Build tool | Vite 6                          |
| Animation  | framer-motion 11                |
| Styling    | Hand-rolled CSS (design tokens) |
| Data       | Static `demo_output.json` (no backend required yet) |

No UI/component library — the theme lives in `src/index.css` as CSS
variables (`--brand`, `--panel`, severity colors, etc.) so it's easy to
restyle in one place.

---

## Quick start

```bash
cd frontend
npm install
npm run dev          # opens http://localhost:5173
```

Other scripts:

```bash
npm run build        # static production bundle -> dist/
npm run preview      # serve the built bundle locally
npm run sync-data    # copy the latest backend export into public/
```

`predev` and `prebuild` run `sync-data` automatically, so the dev server
and production build always pick up the newest `ai_core/demo_output.json`.

---

## What you see

- **Score bar** — faithfulness score, citation coverage, hallucination
  risk, and whether the self-correction (revision) loop ran. Numbers count
  in and progress bars animate on load.
- **Agent Collaboration Timeline** (left) — the 8 agent events stream in
  step by step. The revision request is flagged amber; the final memo node
  is green.
- **Final Research Memo** (right) — **Bull / Bear / Risk** tabs with an
  animated indicator, each claim tagged with its evidence citation
  (`E1`–`E6`) and a confidence meter. A standing "human review required"
  flag and disclaimer are always shown.

---

## Project structure

```
frontend/
├─ public/
│  ├─ demo_output.json     # backend export (auto-synced; served statically)
│  └─ favicon.svg
├─ scripts/
│  └─ sync-data.mjs        # copies ai_core/demo_output.json -> public/
├─ src/
│  ├─ main.jsx             # React entry
│  ├─ App.jsx              # layout: header + score bar + timeline + memo
│  ├─ index.css            # theme tokens + all styling
│  ├─ data/
│  │  └─ useDemoData.js    # data layer — the only file to change for a live API
│  └─ components/
│     ├─ ScoreBar.jsx
│     ├─ Timeline.jsx
│     ├─ Memo.jsx
│     └─ RiskPill.jsx
├─ index.html
└─ vite.config.js
```

---

## Data contract

The UI reads the backend export shape (produced by
`ai_core/export_demo_output.py`). The fields it depends on:

| Field                 | Used for                                    |
| --------------------- | ------------------------------------------- |
| `case_id`, `ticker`   | Header                                      |
| `final_evaluation`    | Score bar (faithfulness, coverage, risk)    |
| `initial_evaluation`  | Detecting whether a revision round ran      |
| `frontend_timeline[]` | The timeline (step, agent, target, title, summary, revision_required) |
| `final_memo`          | Memo tabs (bull_case, bear_case, risk_flags, summary, disclaimer) |

---

## Connecting a live backend

Today the data is a static snapshot synced from the Python repo. When the
backend exposes an HTTP endpoint, the swap is **one file**:

1. Replace the `fetch('/demo_output.json')` in
   `src/data/useDemoData.js` with the real endpoint (e.g.
   `fetch('/api/cases/' + caseId)`).
2. Remove the `predev` / `prebuild` hooks and `scripts/sync-data.mjs`.

Everything downstream already consumes the same shape, so no component
changes are needed.
