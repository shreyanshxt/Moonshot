import React, { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts'

const SORT_OPTIONS = [
  { value: 'rating', label: 'Rating' },
  { value: 'sentiment', label: 'Sentiment' },
  { value: 'price_asc', label: 'Price ↑' },
  { value: 'price_desc', label: 'Price ↓' },
  { value: 'discount', label: 'Discount' },
]

function StarBar({ distribution }) {
  if (!distribution) return null
  const total = Object.values(distribution).reduce((a, b) => a + b, 0) || 1
  return (
    <div className="space-y-1">
      {[5, 4, 3, 2, 1].map(star => {
        const count = distribution[star] || 0
        const pct = (count / total) * 100
        return (
          <div key={star} className="flex items-center gap-2 text-xs">
            <span className="text-amber-500 w-3">{star}</span>
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-400 rounded-full transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-gray-400 w-6 text-right">{count}</span>
          </div>
        )
      })}
    </div>
  )
}

function ProductModal({ product, onClose }) {
  if (!product) return null
  const aspects = product.aspects || {}

  const aspectData = Object.entries(aspects)
    .filter(([, v]) => v.score != null && v.mentions >= 3)
    .map(([key, v]) => ({
      aspect: key,
      score: v.score,
      mentions: v.mentions,
    }))
    .sort((a, b) => b.score - a.score)

  return (
    <div
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-start justify-center z-50 pt-12 px-4 pb-12 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="glass-card rounded-3xl max-w-2xl w-full shadow-2xl border-white/60"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-5 border-b border-gray-100 flex justify-between items-start">
          <div className="flex-1 pr-4">
            <p className="text-xs font-semibold text-brand-600 mb-1 uppercase tracking-widest">{product.brand?.replace('_', ' ')}</p>
            <h3 className="font-bold text-slate-900 text-lg leading-snug">{product.title}</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-2xl font-light transition-colors">×</button>
        </div>

        <div className="p-5 space-y-5">
          {/* Pricing + rating row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">Selling price</p>
              <p className="text-lg font-semibold text-gray-900">
                {product.price ? `₹${product.price.toLocaleString()}` : '—'}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-400">MRP</p>
              <p className="text-lg font-semibold text-gray-400 line-through">
                {product.mrp ? `₹${product.mrp.toLocaleString()}` : '—'}
              </p>
            </div>
            <div className="bg-orange-50 rounded-lg p-3">
              <p className="text-xs text-orange-400">Discount</p>
              <p className="text-lg font-semibold text-orange-600">
                {product.discount_pct != null ? `${product.discount_pct}%` : '—'}
              </p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3">
              <p className="text-xs text-amber-400">Rating</p>
              <p className="text-lg font-semibold text-amber-600">
                ★ {product.rating?.toFixed(1) || '—'}
              </p>
            </div>
          </div>

          {/* Sentiment + star distribution */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-50/50 rounded-xl p-4">
              <p className="text-xs font-medium text-slate-500 mb-2">Sentiment score</p>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-semibold text-gray-900">
                  {product.sentiment?.score?.toFixed(1) || '—'}
                </span>
                <span className="text-sm text-gray-400 mb-1">/100</span>
              </div>
              <div className="flex gap-3 mt-2 text-xs">
                <span className="text-emerald-600">{product.sentiment?.positive_pct?.toFixed(0)}% pos</span>
                <span className="text-gray-400">{product.sentiment?.neutral_pct?.toFixed(0)}% neu</span>
                <span className="text-red-500">{product.sentiment?.negative_pct?.toFixed(0)}% neg</span>
              </div>
            </div>
            <div className="bg-slate-50/50 rounded-xl p-4">
              <p className="text-xs font-medium text-slate-500 mb-2">Star distribution</p>
              <StarBar distribution={product.star_distribution} />
            </div>
          </div>

          {/* Aspect chart */}
          {aspectData.length > 0 && (
            <div>
              <p className="text-xs text-gray-400 mb-2">Aspect sentiment (VADER compound)</p>
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={aspectData} layout="vertical" margin={{ left: 60, right: 20 }}>
                  <XAxis type="number" domain={[-1, 1]} tick={{ fontSize: 10, fill: '#9ca3af' }} />
                  <YAxis type="category" dataKey="aspect" tick={{ fontSize: 11, fill: '#6b7280' }} width={58} />
                  <Tooltip formatter={(v) => v.toFixed(3)} contentStyle={{ fontSize: 11 }} />
                  <Bar dataKey="score" radius={[0, 3, 3, 0]}>
                    {aspectData.map((entry) => (
                      <Cell
                        key={entry.aspect}
                        fill={entry.score >= 0.05 ? '#10b981' : entry.score <= -0.05 ? '#ef4444' : '#d1d5db'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Top reviews */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-emerald-600 font-medium mb-2">What customers love</p>
              <div className="space-y-2">
                {(product.top_positive_reviews || []).map((r, i) => (
                  <div key={i} className="bg-emerald-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-emerald-800 mb-0.5">{r.title}</p>
                    <p className="text-xs text-emerald-700 line-clamp-3">{r.body}</p>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-red-500 font-medium mb-2">Common complaints</p>
              <div className="space-y-2">
                {(product.top_negative_reviews || []).map((r, i) => (
                  <div key={i} className="bg-red-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-red-800 mb-0.5">{r.title}</p>
                    <p className="text-xs text-red-700 line-clamp-3">{r.body}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <a
            href={product.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block text-center text-sm text-brand-500 hover:text-brand-600 underline"
          >
            View on Amazon India →
          </a>
        </div>
      </div>
    </div>
  )
}

export default function ProductDrilldown({ products, brands }) {
  const [selected, setSelected] = useState(null)
  const [sortBy, setSortBy] = useState('rating')
  const [search, setSearch] = useState('')

  const filtered = products
    .filter(p => !search || p.title?.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'rating') return (b.rating || 0) - (a.rating || 0)
      if (sortBy === 'sentiment') return ((b.sentiment?.score) || 0) - ((a.sentiment?.score) || 0)
      if (sortBy === 'price_asc') return (a.price || 0) - (b.price || 0)
      if (sortBy === 'price_desc') return (b.price || 0) - (a.price || 0)
      if (sortBy === 'discount') return (b.discount_pct || 0) - (a.discount_pct || 0)
      return 0
    })

  return (
    <>
      <div className="space-y-4">
        {/* Controls */}
        <div className="flex gap-3 items-center flex-wrap">
          <input
            type="text"
            placeholder="Search products…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm flex-1 min-w-48 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
          />
          <div className="flex gap-1">
            {SORT_OPTIONS.map(o => (
              <button
                key={o.value}
                onClick={() => setSortBy(o.value)}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-all duration-300 ${
                  sortBy === o.value ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/20' : 'glass text-slate-600 hover:bg-white/80'
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
          <span className="text-xs text-gray-400">{filtered.length} products</span>
        </div>

        {/* Product grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(p => (
            <button
              key={p.asin}
              onClick={() => setSelected(p)}
              className="glass-card rounded-2xl p-5 text-left group"
            >
              <div className="flex justify-between items-start mb-3">
                <span className="text-xs font-bold text-brand-600 uppercase tracking-widest">{p.brand?.replace('_', ' ')}</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  (p.sentiment?.score || 0) >= 65 ? 'text-emerald-700 bg-emerald-50' :
                  (p.sentiment?.score || 0) >= 50 ? 'text-amber-700 bg-amber-50' : 'text-red-600 bg-red-50'
                }`}>
                  {p.sentiment?.score?.toFixed(0) || '?'}/100
                </span>
              </div>
              <p className="text-sm font-medium text-gray-800 mb-3 line-clamp-2 group-hover:text-brand-600 transition-colors">
                {p.title}
              </p>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-base font-semibold text-gray-900">
                    {p.price ? `₹${p.price.toLocaleString()}` : '—'}
                  </span>
                  {p.discount_pct != null && (
                    <span className="ml-2 text-xs text-orange-500">{p.discount_pct}% off</span>
                  )}
                </div>
                <div className="text-sm text-amber-500">
                  ★ <span className="text-gray-700">{p.rating?.toFixed(1) || '—'}</span>
                  <span className="text-gray-400 text-xs ml-1">({(p.review_count || 0).toLocaleString()})</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {selected && <ProductModal product={selected} onClose={() => setSelected(null)} />}
    </>
  )
}
