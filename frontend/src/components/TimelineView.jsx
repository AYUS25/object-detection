import React, { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

const TimelineView = ({ connected }) => {
  const [timeline, setTimeline] = useState([])

  useEffect(() => {
    if (!connected) return
    const fetchTimeline = async () => {
      try {
        const res = await axios.get(`${API_BASE}/timeline`)
        setTimeline(res.data.timeline || [])
      } catch (err) {
        console.error(err)
      }
    }
    
    fetchTimeline()
    const interval = setInterval(fetchTimeline, 5000)
    return () => clearInterval(interval)
  }, [connected])

  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <div className="max-w-4xl mx-auto space-y-4">
        <h2 className="text-xl font-semibold mb-4 text-text-primary">Session Timeline</h2>
        
        {timeline.length === 0 ? (
          <p className="text-sm text-text-muted">No events yet.</p>
        ) : (
          <div className="space-y-3">
            {timeline.map((ev, i) => (
              <div key={i} className="flex gap-4 items-start card p-3">
                <div className="text-xs text-text-muted w-16 pt-1">
                  {ev.time.split('T')[1].split('.')[0]}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="badge badge-accent text-xs">{ev.type}</span>
                    <span className="text-sm font-semibold text-text-primary">
                      #{ev.track_id} {ev.label}
                    </span>
                  </div>
                  {ev.extra && (
                    <p className="text-xs text-text-secondary mt-1">{ev.extra}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default TimelineView
