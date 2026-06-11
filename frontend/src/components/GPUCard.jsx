import { getTempColor, getUsageColor, getMemColor } from '../utils/colors'

// SVG arc gauge
function ArcGauge({ value, max = 100, color, size = 80, strokeWidth = 7, label, sublabel }) {
  const r = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * r
  const pct = Math.min(Math.max(value / max, 0), 1)
  const dashOffset = circumference * (1 - pct * 0.75) // 3/4 arc
  const startAngle = 135
  const endAnglePct = 270 * pct

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="overflow-visible">
        {/* Track */}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
          strokeDashoffset={0}
          transform={`rotate(135 ${size / 2} ${size / 2})`}
        />
        {/* Fill */}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference * 0.75 * pct} ${circumference * (1 - 0.75 * pct)}`}
          strokeDashoffset={0}
          transform={`rotate(135 ${size / 2} ${size / 2})`}
          style={{
            filter: `drop-shadow(0 0 4px ${color}80)`,
            transition: 'stroke-dasharray 0.6s ease',
          }}
        />
        {/* Center text */}
        <text
          x={size / 2} y={size / 2 + 1}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={color}
          fontSize={size * 0.22}
          fontFamily="JetBrains Mono, monospace"
          fontWeight="600"
        >
          {Math.round(value)}
        </text>
        {sublabel && (
          <text
            x={size / 2} y={size / 2 + size * 0.18}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="rgba(148,163,184,0.8)"
            fontSize={size * 0.13}
            fontFamily="Inter, sans-serif"
          >
            {sublabel}
          </text>
        )}
      </svg>
      {label && <span className="text-xs text-slate-500 uppercase tracking-widest">{label}</span>}
    </div>
  )
}

// Linear bar metric
function BarMetric({ label, value, max = 100, color, unit = '%', icon }) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100)
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-xs text-slate-500 flex items-center gap-1.5">
          {icon && <span>{icon}</span>}
          {label}
        </span>
        <span className="font-mono text-xs font-semibold" style={{ color }}>
          {typeof value === 'number' ? value.toFixed(1) : value}{unit}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}80, ${color})`,
            boxShadow: `0 0 6px ${color}60`,
          }}
        />
      </div>
    </div>
  )
}

const STATUS_STYLES = {
  critical: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  busy: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  normal: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  idle: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
}

const STATUS_DOT = {
  critical: 'bg-rose-400 shadow-rose-400/60',
  busy: 'bg-amber-400 shadow-amber-400/60',
  normal: 'bg-cyan-400 shadow-cyan-400/60',
  idle: 'bg-emerald-400 shadow-emerald-400/60',
}

const BORDER_GLOW = {
  critical: 'border-rose-500/40 shadow-rose-500/10',
  busy: 'border-amber-500/30 shadow-amber-500/10',
  normal: 'border-white/10 shadow-brand-400/5',
  idle: 'border-emerald-500/20 shadow-emerald-500/5',
}

export default function GPUCard({ gpu, highlighted = false }) {
  const tempColor = getTempColor(gpu.temperature)
  const usageColor = getUsageColor(gpu.usage)
  const memColor = getMemColor(gpu.memory_usage)

  const borderClass = BORDER_GLOW[gpu.status] || 'border-white/10'

  return (
    <div
      className={`
        relative rounded-2xl p-5 border bg-dark-800/60 backdrop-blur-md
        transition-all duration-500
        ${highlighted ? 'ring-2 ring-brand-400/60 shadow-xl shadow-brand-400/20' : ''}
        ${borderClass}
        ${gpu.status === 'critical' ? 'critical-glow' : ''}
      `}
    >
      {/* Highlighted badge */}
      {highlighted && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-brand-500 rounded-full text-xs font-bold text-white shadow-lg shadow-brand-400/40 animate-bounce">
          ✦ RECOMMENDED
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <div className={`w-2 h-2 rounded-full shadow-lg ${STATUS_DOT[gpu.status] || 'bg-slate-400'} ${gpu.status === 'critical' ? 'animate-ping' : ''}`} />
            <span className="font-mono text-xs text-slate-400">{gpu.id.toUpperCase()}</span>
          </div>
          <h3 className="font-semibold text-white text-sm leading-tight">{gpu.name}</h3>
        </div>
        <span className={`status-badge border ${STATUS_STYLES[gpu.status] || 'bg-slate-700 text-slate-300 border-slate-600'}`}>
          {gpu.status}
        </span>
      </div>

      {/* Arc Gauges */}
      <div className="flex justify-around mb-5">
        <ArcGauge value={gpu.usage} color={usageColor} size={72} label="Usage" sublabel="%" />
        <ArcGauge value={gpu.temperature} max={100} color={tempColor} size={72} label="Temp" sublabel="°C" />
        <ArcGauge value={gpu.memory_usage} color={memColor} size={72} label="VRAM" sublabel="%" />
      </div>

      {/* Bar Metrics */}
      <div className="space-y-3 mb-4">
        <BarMetric label="GPU Utilization" value={gpu.usage} color={usageColor} icon="⚡" />
        <BarMetric label="Temperature" value={gpu.temperature} max={100} color={tempColor} unit="°C" icon="🌡" />
        <BarMetric label="Memory Used" value={gpu.memory_usage} color={memColor} icon="💾" />
      </div>

      {/* Footer stats */}
      <div className="grid grid-cols-2 gap-2 pt-3 border-t border-white/5">
        <div className="text-center">
          <div className="font-mono text-lg font-bold text-slate-200">{gpu.queue_length}</div>
          <div className="text-xs text-slate-500">Queue</div>
        </div>
        <div className="text-center">
          <div className="font-mono text-lg font-bold text-slate-200">{gpu.available_memory_gb?.toFixed(1)}</div>
          <div className="text-xs text-slate-500">Free GB</div>
        </div>
      </div>
    </div>
  )
}
