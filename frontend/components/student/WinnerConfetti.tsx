"use client"

import type { CSSProperties } from "react"

const COLORS = ["#f59e0b", "#22c55e", "#0ea5e9", "#ef4444", "#f97316", "#14b8a6", "#eab308", "#8b5cf6"]
const PIECES = 36

export default function WinnerConfetti() {
  return (
    <div aria-hidden className="winner-confetti pointer-events-none absolute inset-0 overflow-hidden">
      {Array.from({ length: PIECES }).map((_, index) => {
        const left = ((index * 97) % PIECES) * (100 / PIECES)
        const drift = (index % 2 === 0 ? 1 : -1) * (20 + (index % 7) * 8)
        const size = 5 + (index % 4) * 2
        const duration = 2.5 + (index % 5) * 0.3
        const delay = (index % 12) * 0.08
        const style = {
          left: `${left}%`,
          width: `${size}px`,
          height: `${size * 0.45 + 5}px`,
          backgroundColor: COLORS[index % COLORS.length],
          animationDelay: `${delay}s`,
          animationDuration: `${duration}s`,
          "--confetti-drift": `${drift}px`,
          "--confetti-rotate": `${(index % 2 === 0 ? 1 : -1) * (420 + (index % 4) * 120)}deg`,
        } as CSSProperties

        return <span key={index} className="winner-confetti-piece" style={style} />
      })}
    </div>
  )
}
