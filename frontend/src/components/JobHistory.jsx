const GPU_NAMES = { 'gpu-0': 'RTX 4090', 'gpu-1': 'A100 80GB', 'gpu-2': 'H100 SXM5' }
const GPU_COLORS = { 'gpu-0': '#22d3ee', 'gpu-1': '#818cf8', 'gpu-2': '#34d399' }

function timeAgo(ts) {
  const diff = (Date.now() / 1000) - ts
  if (diff < 60) return `${Math.round(diff)}s ago`
  return `${Math.floor(diff / 60)}m ago`
}

export default function JobHistory({ jobs }) {
  if (!jobs?.length) {
    return (
      <div className="glass-card p-5">
        <h3 className="section-title">Scheduling History</h3>
        <div className="text-center py-8 text-slate-600">
          <div className="text-3xl mb-2">📭</div>
          <p className="text-sm">No jobs scheduled yet</p>
        </div>
      </div>
    )
  }

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title mb-0">Scheduling History</h3>
        <span className="text-xs text-slate-600 font-mono">{jobs.length} jobs</span>
      </div>
      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {jobs.map((job, i) => (
          <div
            key={job.job_id}
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-dark-900/50 border border-white/5 hover:border-white/10 transition-all duration-200 animate-fade-in"
          >
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: GPU_COLORS[job.recommended_gpu] || '#94a3b8', boxShadow: `0 0 6px ${GPU_COLORS[job.recommended_gpu] || '#94a3b8'}80` }}
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-slate-500">{job.job_id}</span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-dark-700 text-slate-400 capitalize">{job.task_type}</span>
              </div>
              <div className="flex items-center gap-1 mt-0.5">
                <span className="text-xs text-slate-400">→</span>
                <span
                  className="text-xs font-semibold font-mono"
                  style={{ color: GPU_COLORS[job.recommended_gpu] || '#94a3b8' }}
                >
                  {job.recommended_gpu?.toUpperCase()} ({GPU_NAMES[job.recommended_gpu]})
                </span>
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="font-mono text-xs font-semibold text-slate-300">
                {(job.confidence * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-slate-600">{timeAgo(job.timestamp)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
