import { motion } from 'framer-motion'

function nodeKind(ev) {
  if (ev.revision_required) return 'is-revision'
  if (ev.message_type === 'final_memo') return 'is-final'
  return ''
}

function TimelineItem({ ev, index }) {
  return (
    <motion.div
      className="tl-item"
      initial={{ opacity: 0, x: -18 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.45, delay: 0.15 + index * 0.11, ease: 'easeOut' }}
    >
      <motion.div
        className={`tl-node ${nodeKind(ev)}`}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{
          type: 'spring',
          stiffness: 380,
          damping: 18,
          delay: 0.18 + index * 0.11,
        }}
      >
        {ev.step}
      </motion.div>

      <div className="tl-card">
        <div className="tl-top">
          <span className="tl-title">{ev.title}</span>
          <span className="tl-flow">
            <span className="agent-badge">{ev.agent.replace('Agent', '')}</span>
            <span>→</span>
            <span>{ev.target === 'ALL' ? 'ALL' : ev.target.replace('Agent', '')}</span>
          </span>
        </div>
        <div className="tl-summary">{ev.summary}</div>
        {ev.revision_required && (
          <span className="tl-flag">⚠ Revision requested · self-correction triggered</span>
        )}
      </div>
    </motion.div>
  )
}

export default function Timeline({ events }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title">
          <span className="dot" />
          Agent Collaboration Timeline
        </span>
        <span className="panel-tag">{events.length} events</span>
      </div>
      <div className="panel-body">
        <div className="timeline">
          {events.map((ev, i) => (
            <TimelineItem key={ev.step} ev={ev} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
