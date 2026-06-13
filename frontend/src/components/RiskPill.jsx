export default function RiskPill({ level }) {
  const cls = `pill risk-${level}`
  return (
    <span className={cls}>
      <span className="pill-dot" />
      {level} risk
    </span>
  )
}
