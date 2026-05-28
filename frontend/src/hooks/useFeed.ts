import { useState, useEffect } from 'react'
import type { StoryCard, Domain } from '../types'

export function useFeed(domain: Domain) {
  const [cards, setCards] = useState<StoryCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetch(`/api/feeds/${domain}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => {
        setCards(data)
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }, [domain])

  return { cards, loading, error }
}
