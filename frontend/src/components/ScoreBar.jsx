import { motion } from 'framer-motion'
import RiskPill from './RiskPill.jsx'

function AnimatedNumber({ value, decimals = 0, suffix = '' }) {
  return (
    <motion.span
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {value.toFixed(decimals)}
      {suffix}
    </motion.span>
  )
}

function MeterCard({ label, value, meta, percent, delay }) {
  return (
    <motion.div
      className="score-card"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay }}
    >
      <div className="score-label">{label}</div>
      <div className="score-value">{value}</div>
      {meta && <div className="score-meta">{meta}</div>}
      {percent != null && (
        <div className="score-track">
          <motion.div
            className="score-fill"
            initial={{ width: 0 }}
            animate={{ width: `${percent}%` }}
            transition={{ duration: 0.9, delay: delay + 0.2, ease: 'easeOut' }}
          />
        </div>
      )}
    </motion.div>
  )
}

export default function ScoreBar({ evaluation, revised }) {
  const faith = evaluation.faithfulness_score ?? 0
  const coverage = evaluation.citation_coverage ?? 0
  const risk = evaluation.hallucination_risk ?? 'low'

  return (
    <div className="scorebar">
      <MeterCard
        label="Faithfulness"
        value={<AnimatedNumber value={faith} decimals={2} />}
        meta="evidence-grounded score"
        percent={faith * 100}
        delay={0.05}
      />
      <MeterCard
        label="Citation Coverage"
        value={<AnimatedNumber value={coverage * 100} decimals={0} suffix="%" />}
        meta="claims with valid citation"
        percent={coverage * 100}
        delay={0.12}
      />
      <motion.div
        className="score-card"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.19 }}
      >
        <div className="score-label">Hallucination</div>
        <div className="score-value" style={{ fontSize: 22, marginTop: 12 }}>
          <RiskPill level={risk} />
        </div>
        <div className="score-meta">post-evaluation verdict</div>
      </motion.div>
      <motion.div
        className="score-card"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.26 }}
      >
        <div className="score-label">Revision Loop</div>
        <div className="score-value" style={{ fontSize: 22, marginTop: 12 }}>
          <span className={`pill ${revised ? 'risk-medium' : 'risk-low'}`}>
            <span className="pill-dot" />
            {revised ? '1 round run' : 'not needed'}
          </span>
        </div>
        <div className="score-meta">self-correction stage</div>
      </motion.div>
    </div>
  )
}
