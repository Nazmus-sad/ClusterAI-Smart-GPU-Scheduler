import { useState, useRef, useEffect } from 'react'
import { useGPUData } from './hooks/useGPUData'
import GPUCard from './components/GPUCard'
import JobSubmitter from './components/JobSubmitter'
import JobHistory from './components/JobHistory'
import MetricTile from './components/MetricTile'
import { UsageChart, TempChart, QueueChart } from './components/Charts'

const MAX_HISTORY = 30

function formatTime(date) {
  if (!date) return '--'
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function App() {
  const { gpus, metrics, jobs, loading, error, lastUpdated, refetch } = useGPUData(2500)
  const [recommendedGpu, setRecommendedGpu] = useState(null)
  const [chartHistory, setChartHistory] = useState([])
  const tickRef = useRef(0)

  // Build chart history from live telemetry
  useEffect(() => {
    if (!gpus?.length) return
    tickRef.current += 1
    const timeLabel = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    setChartHistory(prev => {
      const next = [
        ...prev,
        {
          time: timeLabel,
          'RTX 4090': +gpus[0]?.usage.toFixed(1),
          'A100 80G': +gpus[1]?.usage.toFixed(1),
          'H100 SXM': +gpus[2]?.usage.toFixed(1),
          temp_RTX4090: +gpus[0]?.temperature.toFixed(1),
          'temp_A100 80G': +gpus[1]?.temperature.toFixed(1),
          'temp_H100 SXM': +gpus[2]?.temperature.toFixed(1),
        }
      ]
      return next.slice(-MAX_HISTORY)
    })
  }, [gpus])

  function handleJobScheduled(result) {
    setRecommendedGpu(result.recommended_gpu)
    setTimeout(() => setRecommendedGpu(null), 8000)
    refetch()
  }

  const isConnected = !error && !loading

  return (
    <div className="min-h-screen bg-gradient-animated">
      {/* ── Header ── */}
      <header className="sticky top-0 z-50 backdrop-blur-xl border-b border-white/5 bg-dark-950/80">
        <div className="max-w-screen-2xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-500/30 border border-brand-400/30 flex items-center justify-center text-lg">
              ⚡
            </div>
            <div>
              <h1 className="text-white font-bold text-base tracking-tight leading-none">ClusterAI</h1>
              <p className="text-slate-500 text-xs">Smart GPU Scheduler</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Live indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-dark-800/60">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : error ? 'bg-rose-400' : 'bg-amber-400 animate-pulse'}`} />
              <span className="text-xs text-slate-400">
                {error ? 'Disconnected' : loading ? 'Connecting...' : 'Live'}
              </span>
            </div>

            {lastUpdated && (
              <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-600">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {formatTime(lastUpdated)}
              </div>
            )}

            <button
              id="refresh-btn"
              onClick={refetch}
              className="w-8 h-8 rounded-lg bg-dark-700 border border-white/10 hover:border-white/20 flex items-center justify-center text-slate-400 hover:text-white transition-all"
              title="Refresh"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto px-6 py-6 space-y-6">

        {/* ── Error banner ── */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-500/40 bg-rose-500/10 flex items-center gap-3 animate-slide-in">
            <span className="text-rose-400 text-xl">⚠</span>
            <div>
              <p className="text-rose-400 font-semibold text-sm">Backend Unreachable</p>
              <p className="text-rose-400/70 text-xs mt-0.5">{error} — Make sure the FastAPI server is running on port 8000.</p>
            </div>
          </div>
        )}

        {/* ── Cluster Metrics Strip ── */}
        {metrics && (
          <section aria-label="Cluster Overview">
            <p className="section-title">Cluster Overview</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <MetricTile icon="📊" label="Avg Utilization" value={metrics.avg_usage} unit="%" color="#22d3ee" />
              <MetricTile icon="🌡" label="Avg Temperature" value={metrics.avg_temperature} unit="°C" color="#fbbf24" />
              <MetricTile icon="😴" label="Idle GPUs" value={metrics.idle_gpu_count} color="#34d399" />
              <MetricTile icon="🚀" label="Jobs Scheduled" value={metrics.jobs_scheduled} color="#818cf8" />
              <MetricTile icon="💰" label="Cost Savings" value={metrics.estimated_cost_savings_pct} unit="%" color="#34d399" />
              <MetricTile icon="🎯" label="Efficiency" value={metrics.scheduling_efficiency_pct} unit="%" color="#6d28d9" />
            </div>
          </section>
        )}

        {/* ── GPU Cards Grid ── */}
        <section aria-label="GPU Cluster">
          <p className="section-title">GPU Cluster — {gpus.length} Nodes</p>
          {loading && !gpus.length ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[0, 1, 2].map(i => (
                <div key={i} className="glass-card p-5 animate-pulse h-64">
                  <div className="h-4 w-32 bg-white/5 rounded mb-4" />
                  <div className="h-20 bg-white/5 rounded mb-4" />
                  <div className="space-y-3">
                    <div className="h-2 bg-white/5 rounded" />
                    <div className="h-2 bg-white/5 rounded" />
                    <div className="h-2 bg-white/5 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {gpus.map(gpu => (
                <GPUCard
                  key={gpu.id}
                  gpu={gpu}
                  highlighted={gpu.id === recommendedGpu}
                />
              ))}
            </div>
          )}
        </section>

        {/* ── Charts + Job Submitter ── */}
        <section aria-label="Analytics and Scheduling">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Charts column */}
            <div className="lg:col-span-2 space-y-4">
              <UsageChart history={chartHistory} />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <TempChart history={chartHistory} />
                <QueueChart gpus={gpus} />
              </div>
            </div>

            {/* Right column: submit + history */}
            <div className="flex flex-col gap-4">
              <JobSubmitter onJobScheduled={handleJobScheduled} />
              <JobHistory jobs={jobs} />
            </div>
          </div>
        </section>

      </main>

      {/* ── Footer ── */}
      <footer className="mt-8 pb-6 text-center text-xs text-slate-700">
        <p>ClusterAI — GPU Scheduler MVP · Powered by FastAPI + Scikit-learn + React</p>
      </footer>
    </div>
  )
}
