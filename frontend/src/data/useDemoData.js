import { useEffect, useState } from 'react'

/**
 * Loads the AI-core demo output produced by the backend
 * (ai_core/export_demo_output.py -> demo_output.json).
 *
 * The file is served statically from /public so the frontend can be
 * developed independently of the Python backend. Swap this for a real
 * API fetch (e.g. `/api/cases/:id`) once the backend exposes one.
 */
export function useDemoData() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    fetch('/demo_output.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((json) => {
        if (alive) setData(json)
      })
      .catch((err) => {
        if (alive) setError(err.message)
      })
    return () => {
      alive = false
    }
  }, [])

  return { data, error }
}
