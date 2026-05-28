export interface SparklinePoint {
  date: string
  probability: number
}

export interface Source {
  title: string
  url: string
  type: 'rss' | 'x'
}

export interface StoryCard {
  id: string
  domain: string
  headline: string
  platform: string
  market_name: string
  current_probability: number
  probability_move: number
  volume_usd: number
  sparkline: SparklinePoint[]
  summary: string
  calibration_note: string
  sources: Source[]
}

export type Domain = 'politics' | 'world' | 'sports'
