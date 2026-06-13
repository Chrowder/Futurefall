# Futurefall · Frontend

Visualizes the multi-agent research run produced by the Python AI core
(`ai_core/export_demo_output.py` → `demo_output.json`).

- **Stack:** React 18 + Vite + framer-motion
- **Style:** dark blue financial-research theme, animated timeline + memo

## Run

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

`npm run build` outputs a static bundle to `dist/`.

## Data source

The app reads `public/demo_output.json` (a copy of the backend's export).
To wire up a live backend later, replace the fetch in
`src/data/useDemoData.js` with the real API endpoint — the rest of the UI
already consumes the same shape (`frontend_timeline`, `final_memo`,
`final_evaluation`).

## Layout

- **Score bar** — faithfulness, citation coverage, hallucination risk, revision loop
- **Timeline** — animated step-by-step agent collaboration (left)
- **Memo** — Bull / Bear / Risk tabs with citations + confidence (right)
