import { useState } from 'react'
import type { Domain } from './types'
import { useFeed } from './hooks/useFeed'
import { StoryCard } from './components/StoryCard'

const DOMAINS: { id: Domain; label: string }[] = [
  { id: 'politics', label: 'Politics' },
  { id: 'world', label: 'World' },
  { id: 'sports', label: 'Sports' },
]

export default function App() {
  const [domain, setDomain] = useState<Domain>('politics')
  const { cards, loading, error } = useFeed(domain)

  return (
    <div className="min-h-screen bg-[#0f1117] text-slate-100">
      {/* Header */}
      <header className="border-b border-[#2a2d3a]">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-baseline gap-3">
          <h1 className="text-white font-bold text-xl tracking-tight">PredictionNews</h1>
          <span className="text-slate-600 text-xs">News that moved the market</span>
        </div>
      </header>

      {/* Tab nav */}
      <nav className="border-b border-[#2a2d3a]">
        <div className="max-w-2xl mx-auto px-6 flex gap-1">
          {DOMAINS.map((d) => (
            <button
              key={d.id}
              onClick={() => setDomain(d.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                domain === d.id
                  ? 'border-white text-white'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Feed */}
      <main className="max-w-2xl mx-auto px-6 py-6">
        {loading && (
          <div className="flex justify-center py-16 text-slate-600 text-sm">Loading...</div>
        )}
        {error && (
          <div className="bg-red-950 border border-red-800 rounded-lg p-4 text-red-300 text-sm">
            Failed to load feed: {error}
          </div>
        )}
        {!loading && !error && (
          <div className="flex flex-col gap-4">
            {cards.map((card) => (
              <StoryCard key={card.id} card={card} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
