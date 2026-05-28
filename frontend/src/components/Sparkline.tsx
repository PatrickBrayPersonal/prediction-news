import type { SparklinePoint } from '../types'

interface Props {
  data: SparklinePoint[]
  height?: number
}

const VB_WIDTH = 200

export function Sparkline({ data, height = 48 }: Props) {
  if (data.length < 2) return null

  const probs = data.map((d) => d.probability)
  const min = Math.min(...probs)
  const max = Math.max(...probs)
  const range = max - min || 0.01

  const pad = 2
  const w = VB_WIDTH - pad * 2
  const h = height - pad * 2

  const points = data.map((d, i) => {
    const x = pad + (i / (data.length - 1)) * w
    const y = pad + (1 - (d.probability - min) / range) * h
    return `${x},${y}`
  })

  const isUp = data[data.length - 1].probability >= data[0].probability
  const color = isUp ? '#4ade80' : '#f87171'

  return (
    <svg
      width="80%"
      height={height}
      viewBox={`0 0 ${VB_WIDTH} ${height}`}
      preserveAspectRatio="none"
      className="block mx-auto"
    >
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}
