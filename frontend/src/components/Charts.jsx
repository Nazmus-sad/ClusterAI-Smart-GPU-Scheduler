import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-card px-3 py-2 text-xs border-white/10">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.name} className="font-mono font-semibold" style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
        </p>
      ))}
    </div>
  )
}

const GPU_COLORS = ['#22d3ee', '#818cf8', '#34d399']
const GPU_LABELS = ['RTX 4090', 'A100 80G', 'H100 SXM']

export function UsageChart({ history }) {
  return (
    <div className="glass-card p-4">
      <h3 className="section-title">GPU Utilization Over Time</h3>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            {GPU_COLORS.map((color, i) => (
              <linearGradient key={i} id={`grad${i}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="time" tick={{ fill: '#475569', fontSize: 10 }} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fill: '#475569', fontSize: 10 }} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend formatter={v => <span style={{ color: '#94a3b8', fontSize: 11 }}>{v}</span>} />
          {GPU_LABELS.map((label, i) => (
            <Area
              key={label}
              type="monotone"
              dataKey={label}
              stroke={GPU_COLORS[i]}
              strokeWidth={2}
              fill={`url(#grad${i})`}
              dot={false}
              activeDot={{ r: 4, fill: GPU_COLORS[i] }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export function TempChart({ history }) {
  return (
    <div className="glass-card p-4">
      <h3 className="section-title">Temperature Trends (°C)</h3>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="time" tick={{ fill: '#475569', fontSize: 10 }} tickLine={false} />
          <YAxis domain={[30, 100]} tick={{ fill: '#475569', fontSize: 10 }} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend formatter={v => <span style={{ color: '#94a3b8', fontSize: 11 }}>{v}</span>} />
          {/* Danger zone reference */}
          {GPU_LABELS.map((label, i) => (
            <Line
              key={label}
              type="monotone"
              dataKey={`temp_${label}`}
              name={label}
              stroke={GPU_COLORS[i]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function QueueChart({ gpus }) {
  if (!gpus?.length) return null
  const data = gpus.map((g, i) => ({
    name: GPU_LABELS[i] || g.id,
    queue: g.queue_length,
    usage: Math.round(g.usage),
  }))
  return (
    <div className="glass-card p-4">
      <h3 className="section-title">Queue Depth &amp; Utilization</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }} barGap={4}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} />
          <YAxis tick={{ fill: '#475569', fontSize: 10 }} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend formatter={v => <span style={{ color: '#94a3b8', fontSize: 11 }}>{v}</span>} />
          <Bar dataKey="queue" name="Queue Depth" fill="#818cf8" radius={[4, 4, 0, 0]} opacity={0.8} />
          <Bar dataKey="usage" name="Utilization %" fill="#22d3ee" radius={[4, 4, 0, 0]} opacity={0.6} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
