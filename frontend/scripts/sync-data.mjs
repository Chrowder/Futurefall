// Copies the backend's demo export into the frontend's public folder so the
// dev server / build always serves the latest AI-core output.
//
// Runs automatically via the `predev` / `prebuild` npm hooks. Once the backend
// exposes a live API, drop this script and point useDemoData.js at the endpoint.
import { copyFile, access } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(here, '../../ai_core/demo_output.json')
const DEST = resolve(here, '../public/demo_output.json')

try {
  await access(SRC)
} catch {
  console.warn(
    `[sync-data] backend export not found at ${SRC} — keeping existing public/demo_output.json`
  )
  process.exit(0)
}

try {
  await copyFile(SRC, DEST)
  console.log('[sync-data] synced ai_core/demo_output.json -> public/demo_output.json')
} catch (err) {
  console.error('[sync-data] copy failed:', err.message)
  process.exit(1)
}
