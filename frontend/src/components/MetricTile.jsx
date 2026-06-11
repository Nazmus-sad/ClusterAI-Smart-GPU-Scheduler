export default function MetricTile({ label, value, unit = '', icon, color = '#6d28d9', trend }) {
  return (
    <div className="glass-card p-4 flex items-center gap-4 hover:border-white/10 transition-all duration-300">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
        style={{ background: `${color}18`, border: `1px solid ${color}30` }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <div className="flex items-end gap-1 leading-none">
          <span className="font-mono text-2xl font-bold text-white tabular-nums">
            {typeof value === 'number' ? value.toFixed(value % 1 === 0 ? 0 : 1) : value}
          </span>
          {unit && <span className="text-xs text-slate-500 mb-0.5">{unit}</span>}
          {trend !== undefined && (
            <span className={`text-xs mb-0.5 ml-1 font-semibold ${trend >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {trend >= 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}%
            </span>
          )}
        </div>
        <div className="text-xs text-slate-500 uppercase tracking-widest mt-0.5 truncate">{label}</div>
      </div>
    </div>
  )
}
