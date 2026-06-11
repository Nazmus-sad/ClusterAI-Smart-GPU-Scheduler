const BASE = '/api'

async function fetchJSON(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getGPUs: () => fetchJSON('/gpus'),
  getMetrics: () => fetchJSON('/metrics'),
  getJobs: () => fetchJSON('/jobs'),
  scheduleJob: (taskType, requiredMemory) =>
    fetchJSON('/schedule', {
      method: 'POST',
      body: JSON.stringify({ task_type: taskType, required_memory: requiredMemory }),
    }),
}
