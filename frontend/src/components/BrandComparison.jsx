import React, { useState } from 'react'
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from 'recharts'

const BRAND_COLORS = [
  '#4f6ef7', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4',
]

const ASPECTS = ['wheels', 'handle', 'zipper', 'material', 'durability', 'size', 'lock', 'weight']

function AspectCell({ score }) {
  if (score == null) return <td className="px-3 py-2.5 text-center text-gray-300 text-xs">—</td>
  const pct = ((score + 1) / 2) * 100
  const bg = pct >= 70 ? 'bg-emerald-100 text-emerald-700' :
             pct >= 50 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-600'
  return (
    <td className={`px-3 py-2.5 text-center text-xs font-medium ${bg}`}>
      {score >= 0 ? '+' : ''}{score.toFixed(2)}
    </td>
  )
}

export default function BrandComparison({ brands }) {
  const [selectedBrands, setSelectedBrands] = useState(brands.slice(0, 4).map(b => b.brand_key))

  const visible = brands.filter(b => selectedBrands.includes(b.brand_key))

  // Radar chart data — normalise each metric to 0–100
  const maxPrice = Math.max(...brands.map(b => b.pricing.avg_price || 0))
  const radarData = [
    { metric: 'Sentiment', full: 100 },
    { metric: 'Rating', full: 100 },
    { metric: 'Value', full: 100 },
    { metric: 'Popularity', full: 100 },
    { metric: 'Discount', full: 100 },
  ].map(row => {
    const obj = { metric: row.metric }
    visible.forEach(b => {
      if (row.metric === 'Sentiment') obj[b.brand_name] = b.sentiment.score || 0
      if (row.metric === 'Rating') obj[b.brand_name] = ((b.ratings.avg_rating || 0) / 5) * 100
      if (row.metric === 'Value') {
        const p = b.pricing.avg_price || maxPrice
        obj[b.brand_name] = Math.round((1 - p / maxPrice) * 70 + b.sentiment.score * 0.3)
      }
      if (row.metric === 'Popularity') {
        const maxRev = Math.max(...brands.map(b2 => b2.ratings.total_reviews || 0))
        obj[b.brand_name] = Math.min(100, ((b.ratings.total_reviews || 0) / maxRev) * 100)
      }
      if (row.metric === 'Discount') obj[b.brand_name] = Math.min(100, (b.pricing.avg_discount_pct || 0) * 2)
    })
    return obj
  })

  // Sentiment distribution stacked bar
  const distData = visible.map(b => ({
    name: b.brand_name,
    positive: b.sentiment.positive_pct,
    neutral: b.sentiment.neutral_pct,
    negative: b.sentiment.negative_pct,
  }))

  return (
    <div className="space-y-6">
      {/* Brand toggle pills */}
      <div className="glass-card rounded-2xl p-6">
        <p className="text-xs font-medium text-slate-500 mb-4 uppercase tracking-widest">Select brands to compare (max 4)</p>
        <div className="flex flex-wrap gap-2">
          {brands.map((b, i) => {
            const active = selectedBrands.includes(b.brand_key)
            return (
              <button
                key={b.brand_key}
                onClick={() => {
                  if (active) {
                    setSelectedBrands(s => s.filter(k => k !== b.brand_key))
                  } else if (selectedBrands.length < 4) {
                    setSelectedBrands(s => [...s, b.brand_key])
                  }
                }}
                className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-all ${
                  active
                    ? 'text-white border-transparent'
                    : 'text-gray-500 border-gray-200 hover:border-gray-300'
                }`}
                style={active ? { background: BRAND_COLORS[i % BRAND_COLORS.length] } : {}}
              >
                {b.brand_name}
              </button>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar chart */}
        <div className="glass-card rounded-2xl p-6">
          <h2 className="font-semibold text-lg text-slate-800 mb-4 tracking-tight">Competitive radar</h2>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
              <PolarGrid stroke="#e5e7eb" />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12, fill: '#6b7280' }} />
              {visible.map((b, i) => (
                <Radar
                  key={b.brand_key}
                  name={b.brand_name}
                  dataKey={b.brand_name}
                  stroke={BRAND_COLORS[i % BRAND_COLORS.length]}
                  fill={BRAND_COLORS[i % BRAND_COLORS.length]}
                  fillOpacity={0.08}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              ))}
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Sentiment distribution */}
        <div className="glass-card rounded-2xl p-6">
          <h2 className="font-semibold text-lg text-slate-800 mb-4 tracking-tight">Sentiment distribution</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={distData} layout="vertical" margin={{ left: 100, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={v => `${v}%`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: '#6b7280' }} width={98} />
              <Tooltip formatter={(v) => `${v.toFixed(1)}%`} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="positive" name="Positive" stackId="s" fill="#10b981" />
              <Bar dataKey="neutral" name="Neutral" stackId="s" fill="#d1d5db" />
              <Bar dataKey="negative" name="Negative" stackId="s" fill="#ef4444" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Aspect-level heatmap */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200/50 bg-white/40">
          <h2 className="font-semibold text-lg text-slate-800 tracking-tight">Aspect sentiment heatmap</h2>
          <p className="text-xs font-medium text-slate-500 mt-1">VADER compound score per aspect — green positive, red negative, — insufficient data</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-5 py-3 text-left text-xs text-gray-400 uppercase w-36">Brand</th>
                {ASPECTS.map(a => (
                  <th key={a} className="px-3 py-3 text-center text-xs text-gray-400 uppercase capitalize">{a}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((b, i) => (
                <tr key={b.brand_key} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-5 py-2.5 font-medium text-gray-700 text-sm">{b.brand_name}</td>
                  {ASPECTS.map(a => (
                    <AspectCell key={a} score={b.aspects?.[a]?.score ?? null} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pros and cons cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {visible.map((b, i) => (
          <div key={b.brand_key} className="glass-card rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <span
                className="w-3.5 h-3.5 rounded-full shadow-sm"
                style={{ background: BRAND_COLORS[i % BRAND_COLORS.length] }}
              />
              <span className="font-bold text-slate-800 text-sm tracking-wide uppercase">{b.brand_name}</span>
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-emerald-600 font-medium mb-1">Top praise</p>
                <ul className="space-y-0.5">
                  {(b.themes?.positive || []).slice(0, 4).map((t, j) => (
                    <li key={j} className="text-xs text-gray-600 flex gap-1.5">
                      <span className="text-emerald-400 mt-0.5">+</span>{t}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs text-red-500 font-medium mt-2 mb-1">Top complaints</p>
                <ul className="space-y-0.5">
                  {(b.themes?.negative || []).slice(0, 4).map((t, j) => (
                    <li key={j} className="text-xs text-gray-600 flex gap-1.5">
                      <span className="text-red-400 mt-0.5">−</span>{t}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
