import type { StoryCard as StoryCardType } from '../types'
import { Sparkline } from './Sparkline'

interface Props {
  card: StoryCardType
}

function formatMove(move: number): string {
  const sign = move >= 0 ? '+' : ''
  return `${sign}${Math.round(move * 100)}pts`
}

function formatProb(p: number): string {
  return `${Math.round(p * 100)}%`
}

function formatVolume(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  return `$${(v / 1_000).toFixed(0)}K`
}

export function StoryCard({ card }: Props) {
  const isUp = card.probability_move >= 0
  const moveColor = isUp ? 'text-green-400' : 'text-red-400'

  return (
    <article className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-5 flex flex-col gap-4">
      {/* Headline row */}
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-white font-semibold text-base leading-snug">{card.headline}</h2>
        <span className="text-xs text-slate-500 bg-[#12141e] border border-[#2a2d3a] rounded px-2 py-0.5 whitespace-nowrap shrink-0">
          {card.platform}
        </span>
      </div>

      {/* Market + sparkline row */}
      <div className="flex items-center gap-4">
        <Sparkline data={card.sparkline} width={120} height={36} />
        <div className="flex flex-col gap-0.5">
          <div className="flex items-baseline gap-2">
            <span className="text-white font-mono text-lg font-semibold">
              {formatProb(card.current_probability)}
            </span>
            <span className={`font-mono text-sm font-medium ${moveColor}`}>
              {formatMove(card.probability_move)}
            </span>
          </div>
          <span className="text-slate-500 text-xs">{formatVolume(card.volume_usd)} vol</span>
        </div>
      </div>

      {/* Market name */}
      <p className="text-slate-500 text-xs">{card.market_name}</p>

      {/* Summary */}
      <p className="text-slate-300 text-sm leading-relaxed">{card.summary}</p>

      {/* Calibration note */}
      <p className="text-slate-500 text-sm italic border-l-2 border-slate-700 pl-3">
        {card.calibration_note}
      </p>

      {/* Sources */}
      <div className="flex flex-wrap gap-2">
        {card.sources.map((source, i) => (
          <a
            key={i}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-slate-400 bg-[#12141e] border border-[#2a2d3a] rounded-full px-3 py-1 hover:border-slate-500 hover:text-slate-300 transition-colors"
          >
            <span className="text-slate-600">{source.type === 'x' ? '𝕏' : '⊕'}</span>
            <span className="max-w-[200px] truncate">{source.title}</span>
          </a>
        ))}
      </div>
    </article>
  )
}
