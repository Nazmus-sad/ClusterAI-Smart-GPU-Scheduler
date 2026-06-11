import { useState } from 'react'
import { api } from '../api'

const TASK_TYPES = [
  { value: 'inference', label: '⚡ Inference', desc: 'Low-latency model serving' },
  { value: 'training', label: '🧠 Training', desc: 'Large model fine-tuning' },
  { value: 'data_processing', label: '📊 Data Processing', desc: 'Batch ETL workloads' },
]

export default function JobSubmitter({ onJobScheduled }) {
  const [taskType, setTaskType] = useState('inference')
  const [memory, setMemory] = useState(4)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await api.scheduleJob(taskType, parseFloat(memory))
      setResult(res)
      onJobScheduled?.(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const GPU_NAMES = { 'gpu-0': 'RTX 4090', 'gpu-1': 'A100 80GB', 'gpu-2': 'H100 SXM5' }
  const GPU_COLORS = { 'gpu-0': '#22d3ee', 'gpu-1': '#818cf8', 'gpu-2': '#34d399' }

  return (
    <div className="glass-card p-5 h-full">
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 rounded-lg bg-brand-500/20 flex items-center justify-center text-brand-400">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <h2 className="font-semibold text-white text-sm">Submit Job</h2>
          <p className="text-xs text-slate-500">AI will select the optimal GPU</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Task type */}
        <div>
          <label className="metric-label block mb-2">Task Type</label>
          <div className="space-y-2">
            {TASK_TYPES.map(t => (
              <label
                key={t.value}
                className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all duration-200
                  ${taskType === t.value
                    ? 'border-brand-400/50 bg-brand-500/10 text-white'
                    : 'border-white/5 bg-dark-900/50 text-slate-400 hover:border-white/15'
                  }`}
              >
                <input
                  type="radio"
                  name="taskType"
                  value={t.value}
                  checked={taskType === t.value}
                  onChange={() => setTaskType(t.value)}
                  className="sr-only"
                />
                <div className={`w-3 h-3 rounded-full border-2 transition-all ${taskType === t.value ? 'border-brand-400 bg-brand-400' : 'border-slate-600'}`} />
                <div>
                  <div className="text-sm font-medium">{t.label}</div>
                  <div className="text-xs text-slate-500">{t.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Memory */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="metric-label">Required VRAM</label>
            <span className="font-mono text-sm font-semibold text-brand-400">{memory} GB</span>
          </div>
          <input
            id="memory-slider"
            type="range"
            min="1"
            max="24"
            step="0.5"
            value={memory}
            onChange={e => setMemory(e.target.value)}
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(90deg, #6d28d9 ${((memory - 1) / 23) * 100}%, rgba(255,255,255,0.08) ${((memory - 1) / 23) * 100}%)`,
            }}
          />
          <div className="flex justify-between text-xs text-slate-600 mt-1">
            <span>1 GB</span>
            <span>24 GB</span>
          </div>
        </div>

        <button
          id="submit-job-btn"
          type="submit"
          disabled={loading}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Scheduling...
            </>
          ) : (
            <>
              <span>🚀</span> Schedule Job
            </>
          )}
        </button>
      </form>

      {/* Result */}
      {result && (
        <div className="mt-4 p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 animate-slide-in">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-emerald-400 text-lg">✓</span>
            <span className="text-sm font-semibold text-emerald-400">Job Scheduled!</span>
            <span className="ml-auto font-mono text-xs text-slate-500">{result.job_id}</span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-400">Assigned To</span>
              <span
                className="font-mono text-sm font-bold"
                style={{ color: GPU_COLORS[result.recommended_gpu] || '#22d3ee' }}
              >
                {result.recommended_gpu?.toUpperCase()} — {GPU_NAMES[result.recommended_gpu]}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-slate-400">ML Confidence</span>
              <span className="font-mono text-sm font-semibold text-slate-300">
                {(result.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 animate-slide-in">
          <p className="text-sm text-rose-400">⚠ {error}</p>
        </div>
      )}
    </div>
  )
}
