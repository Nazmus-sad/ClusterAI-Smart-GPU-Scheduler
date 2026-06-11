// Returns Tailwind color classes based on metric value and thresholds
export function getStatusColor(status) {
  switch (status) {
    case 'critical': return 'rose'
    case 'busy': return 'amber'
    case 'normal': return 'cyan'
    case 'idle': return 'emerald'
    default: return 'slate'
  }
}

export function getStatusLabel(status) {
  switch (status) {
    case 'critical': return 'CRITICAL'
    case 'busy': return 'BUSY'
    case 'normal': return 'NORMAL'
    case 'idle': return 'IDLE'
    default: return 'UNKNOWN'
  }
}

export function getTempColor(temp) {
  if (temp >= 88) return '#fb7185'
  if (temp >= 75) return '#fbbf24'
  if (temp >= 55) return '#22d3ee'
  return '#34d399'
}

export function getUsageColor(usage) {
  if (usage >= 90) return '#fb7185'
  if (usage >= 65) return '#fbbf24'
  if (usage >= 30) return '#22d3ee'
  return '#34d399'
}

export function getMemColor(mem) {
  if (mem >= 85) return '#fb7185'
  if (mem >= 65) return '#fbbf24'
  return '#818cf8'
}

export function formatUptime(seconds) {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

export function gpuDisplayName(id) {
  const names = {
    'gpu-0': 'RTX 4090',
    'gpu-1': 'A100 80GB',
    'gpu-2': 'H100 SXM5',
  }
  return names[id] || id
}
