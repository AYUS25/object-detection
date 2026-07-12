import React, { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

const MemorySearch = ({ sessionId }) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Also load default recent objects on mount
  useEffect(() => {
    handleSearch()
  }, [])

  const handleSearch = async (e) => {
    if (e) e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await axios.get(`${API_BASE}/search`, {
        params: { query }
      })
      setResults(res.data.results || [])
    } catch (err) {
      console.error(err)
      setError("Failed to execute search.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto">
      <div className="max-w-6xl mx-auto w-full space-y-6">
        
        {/* Header & Search */}
        <div className="card p-6 bg-card">
          <h2 className="text-xl font-semibold mb-2">Memory Search Engine</h2>
          <p className="text-text-muted text-sm mb-4">
            Search session history using natural language (e.g. "Show all Dell laptops", "stationary objects").
          </p>
          
          <form onSubmit={handleSearch} className="flex gap-3">
            <input 
              type="text" 
              placeholder="Query memory..." 
              className="flex-1 bg-bg border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-accent"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            <button 
              type="submit"
              disabled={loading}
              className="bg-accent text-bg font-semibold px-6 py-2 rounded-lg text-sm hover:opacity-90 disabled:opacity-50 transition"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </form>
        </div>
        
        {/* Error */}
        {error && (
          <div className="p-4 bg-warning/20 border border-warning/50 text-warning rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Results Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {results.map((r, i) => (
            <div key={r.track_id} className="card bg-card border border-border p-4 animate-fade-in flex flex-col gap-3">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-text-primary text-sm truncate w-48" title={r.inferred_label}>
                    #{r.track_id} {r.inferred_label}
                  </h3>
                  <p className="text-xs text-text-muted">{r.category} {r.brand ? `• ${r.brand}` : ''}</p>
                </div>
                <span className="badge badge-accent text-xs">{(r.confidence * 100).toFixed(0)}%</span>
              </div>
              
              {/* Snapshot images (first/best/last) */}
              <div className="flex gap-2 h-20">
                <img 
                  src={`${API_BASE}/snapshots/${sessionId}/${r.track_id}_first.jpg`}
                  alt="First seen"
                  className="w-1/3 h-full object-cover rounded border border-border/50 bg-bg"
                  onError={(e) => { e.target.style.display = 'none' }}
                  title="First Seen"
                />
                <img 
                  src={`${API_BASE}/snapshots/${sessionId}/${r.track_id}_best.jpg`}
                  alt="Best view"
                  className="w-1/3 h-full object-cover rounded border border-border/50 bg-bg"
                  onError={(e) => { e.target.style.display = 'none' }}
                  title="Best View"
                />
                <img 
                  src={`${API_BASE}/snapshots/${sessionId}/${r.track_id}_last.jpg`}
                  alt="Last seen"
                  className="w-1/3 h-full object-cover rounded border border-border/50 bg-bg"
                  onError={(e) => { e.target.style.display = 'none' }}
                  title="Last Seen"
                />
              </div>

              <div className="grid grid-cols-2 gap-y-1 text-xs mt-1">
                <span className="text-text-muted">OCR Text:</span>
                <span className="text-blue-400 truncate text-right">{r.ocr_text || '—'}</span>
                
                <span className="text-text-muted">First Seen:</span>
                <span className="text-text-secondary text-right">{r.first_seen.split('T')[1].split('.')[0]}</span>
                
                <span className="text-text-muted">Duration:</span>
                <span className="text-text-secondary text-right">{r.duration.toFixed(1)}s</span>
              </div>
              
              {/* Events */}
              {r.events && r.events.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border/50">
                  <p className="text-[10px] uppercase text-text-muted mb-1">Recent Events</p>
                  <div className="flex flex-wrap gap-1">
                    {r.events.map((e, idx) => (
                      <span key={idx} className="badge badge-muted text-[10px]" title={e.at}>
                        {e.type}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          
          {!loading && results.length === 0 && (
            <div className="col-span-full py-12 text-center text-text-muted text-sm">
              No historical objects match your search.
            </div>
          )}
        </div>
        
      </div>
    </div>
  )
}

export default MemorySearch
