import { motion } from 'framer-motion'
import { useDemoData } from './data/useDemoData.js'
import ScoreBar from './components/ScoreBar.jsx'
import Timeline from './components/Timeline.jsx'
import Memo from './components/Memo.jsx'

function Header({ memo, caseId }) {
  return (
    <motion.header
      className="header"
      initial={{ opacity: 0, y: -14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="brand">
        <div className="brand-mark">
          <svg viewBox="0 0 32 32">
            <path
              d="M6 23 L13 14 L18 18 L26 8"
              fill="none"
              stroke="#fff"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="26" cy="8" r="2.8" fill="#fff" />
          </svg>
        </div>
        <div>
          <div className="brand-name">Futurefall</div>
          <div className="brand-sub">AI Research Workbench</div>
        </div>
      </div>

      <div className="ticker-chip">
        <div>
          <div className="ticker-symbol">{memo.ticker}</div>
          <div className="ticker-company">{memo.company}</div>
        </div>
        <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 14 }}>
          <div className="ticker-company">Case</div>
          <div className="ticker-case">{caseId}</div>
        </div>
      </div>
    </motion.header>
  )
}

export default function App() {
  const { data, error } = useDemoData()

  if (error) {
    return (
      <div className="app">
        <div className="center-state">
          <div>
            <div style={{ fontSize: 18, marginBottom: 8 }}>Failed to load demo data</div>
            <div style={{ color: 'var(--text-faint)', fontSize: 13 }}>{error}</div>
            <div style={{ color: 'var(--text-faint)', fontSize: 13, marginTop: 6 }}>
              Expected <code>/demo_output.json</code> in the public folder.
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="app">
        <div className="center-state">
          <div>
            <div className="spinner" />
            Loading research case…
          </div>
        </div>
      </div>
    )
  }

  const revised = data.final_memo.evaluation_summary.revision_required === false
    && data.initial_evaluation.revision_required === true

  return (
    <div className="app">
      <Header memo={data.final_memo} caseId={data.case_id} />

      <ScoreBar evaluation={data.final_evaluation} revised={revised} />

      <div className="grid">
        <Timeline events={data.frontend_timeline} />
        <Memo memo={data.final_memo} />
      </div>

      <div className="footer">
        Futurefall · multi-agent research support · {data.frontend_timeline.length} agent
        events · not investment advice
      </div>
    </div>
  )
}
