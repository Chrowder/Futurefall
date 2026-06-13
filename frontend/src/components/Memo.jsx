import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

function Confidence({ value }) {
  return (
    <div className="conf-row">
      <span className="conf-label">Confidence</span>
      <div className="conf-track">
        <motion.div
          className="conf-fill"
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="conf-num">{value.toFixed(2)}</span>
    </div>
  )
}

function fadeList(i) {
  return {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.35, delay: i * 0.06 },
  }
}

function BullView({ bull }) {
  return (
    <div>
      <p className="thesis">{bull.bull_thesis}</p>
      <Confidence value={bull.confidence} />
      {bull.revision_note && (
        <div className="memo-summary" style={{ marginBottom: 16 }}>
          ✎ {bull.revision_note}
        </div>
      )}
      <div className="section-label">Supporting points</div>
      {bull.supporting_points.map((p, i) => (
        <motion.div className="point" key={i} {...fadeList(i)}>
          <span className="point-icon">▲</span>
          <span className="point-claim">{p.claim}</span>
          <span className="cite">{p.citation_id}</span>
        </motion.div>
      ))}
      <div className="section-label">Key assumptions</div>
      {bull.key_assumptions.map((a, i) => (
        <motion.div className="point" key={i} {...fadeList(i)}>
          <span className="point-icon">◇</span>
          <span className="point-sub">{a}</span>
        </motion.div>
      ))}
    </div>
  )
}

function BearView({ bear }) {
  return (
    <div>
      <p className="thesis">{bear.bear_thesis}</p>
      <Confidence value={bear.confidence} />
      <div className="section-label">Attack points</div>
      {bear.attack_points.map((p, i) => (
        <motion.div className="point" key={i} {...fadeList(i)}>
          <span className="point-icon" style={{ color: 'var(--neg)' }}>▼</span>
          <div>
            <div className="point-claim">{p.critique}</div>
            <div className="point-sub">↳ targets: {p.target_claim}</div>
          </div>
          <span className="cite">{p.citation_id}</span>
        </motion.div>
      ))}
      <div className="section-label">Missed risks</div>
      {bear.missed_risks.map((r, i) => (
        <motion.div className="point" key={i} {...fadeList(i)}>
          <span className="point-icon" style={{ color: 'var(--warn)' }}>!</span>
          <span className="point-sub">{r.risk}</span>
          <span className="cite">{r.citation_id}</span>
        </motion.div>
      ))}
    </div>
  )
}

function RiskView({ flags }) {
  return (
    <div>
      <div className="section-label" style={{ marginTop: 4 }}>
        Risk flags ({flags.length})
      </div>
      {flags.map((f, i) => (
        <motion.div className="risk-row" key={i} {...fadeList(i)}>
          <span className={`sev ${f.severity}`}>{f.severity}</span>
          <div>
            <div className="point-claim">{f.risk}</div>
          </div>
          <span className="cite">{f.citation_id}</span>
        </motion.div>
      ))}
    </div>
  )
}

const TABS = [
  { key: 'bull', label: 'Bull' },
  { key: 'bear', label: 'Bear' },
  { key: 'risk', label: 'Risk' },
]

export default function Memo({ memo }) {
  const [tab, setTab] = useState('bull')

  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title">
          <span className="dot" />
          Final Research Memo
        </span>
        {memo.human_review_required && (
          <span className="panel-tag" style={{ color: 'var(--warn)' }}>
            human review required
          </span>
        )}
      </div>
      <div className="panel-body">
        <div className="memo-summary">{memo.summary}</div>

        <div className="tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`tab ${tab === t.key ? 'active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {tab === t.key && (
                <motion.span className="tab-ind" layoutId="tab-ind" transition={{ type: 'spring', stiffness: 400, damping: 30 }} />
              )}
              <span style={{ position: 'relative', zIndex: 1 }}>{t.label}</span>
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
          >
            {tab === 'bull' && <BullView bull={memo.bull_case} />}
            {tab === 'bear' && <BearView bear={memo.bear_case} />}
            {tab === 'risk' && <RiskView flags={memo.risk_flags} />}
          </motion.div>
        </AnimatePresence>

        <div className="disclaimer">⚖ {memo.disclaimer}</div>
      </div>
    </section>
  )
}
