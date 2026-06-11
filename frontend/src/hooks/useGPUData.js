import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

export function useGPUData(intervalMs = 2000) {
  const [gpus, setGPUs] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchAll = useCallback(async () => {
    try {
      const [gpuData, metricsData, jobsData] = await Promise.all([
        api.getGPUs(),
        api.getMetrics(),
        api.getJobs(),
      ])
      setGPUs(gpuData)
      setMetrics(metricsData)
      setJobs(jobsData)
      setError(null)
      setLastUpdated(new Date())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, intervalMs)
    return () => clearInterval(interval)
  }, [fetchAll, intervalMs])

  return { gpus, metrics, jobs, loading, error, lastUpdated, refetch: fetchAll }
}
