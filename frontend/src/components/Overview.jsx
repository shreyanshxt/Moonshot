import React from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend,
} from 'recharts'

const BRAND_COLORS = {
  safari: '#4f6ef7',
  skybags: '#10b981',
  american_tourister: '#f59e0b',
  vip: '#ef4444',
  aristocrat: '#8b5cf6',
  nasher_miles: '#06b6d4',
}

function StatCard({ label, value, sub }) {
  return (
    <div className="glass-card rounded-2xl p-6">
      <p className="text-xs font-semibold text-brand-600 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-3xl font-bold text-slate-800">{value}</p>
      {sub && <p className="text-xs text-slate-500 font-medium mt-1">{sub}</p>}
    </div>
  )
}

function SentimentBadge({ score }) {
  const color = score >= 65 ? 'text-emerald-700 bg-emerald-50' :
                score >= 50 ? 'text-amber-700 bg-amber-50' : 'text-red-700 bg-red-50'
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${color}`}>
      {score?.toFixed(1)}
    </span>
  )
}

export default function Overview({ stats, brands, products }) {
  // Prepare price vs sentiment scatter data
  const scatterData = brands.map(b => ({
    x: b.pricing.avg_price || 0,
    y: b.sentiment.score || 0,
    z: b.ratings.total_reviews || 100,
    name: b.brand_name,
    key: b.brand_key,
  }))

  // Sentiment bar data
  const sentimentData = [...brands]
    .sort((a, b) => b.sentiment.score - a.sentiment.score)
    .map(b => ({
      name: b.brand_name,
      score: b.sentiment.score,
      positive: b.sentiment.positive_pct,
      negative: b.sentiment.negative_pct,
      neutral: b.sentiment.neutral_pct,
      fill: BRAND_COLORS[b.brand_key] || '#888',
    }))

  // Pricing bar data
  const pricingData = [...brands]
    .sort((a, b) => (b.pricing.avg_price || 0) - (a.pricing.avg_price || 0))
    .map(b => ({
      name: b.brand_name,
      avg_price: b.pricing.avg_price,
      avg_mrp: b.pricing.avg_mrp,
      discount: b.pricing.avg_discount_pct,
      fill: BRAND_COLORS[b.brand_key] || '#888',
    }))

  return (
    <div className="space-y-6">
      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-4">
        <StatCard label="Brands tracked" value={stats?.total_brands || brands.length} />
        <StatCard label="Products analysed" value={stats?.total_products || products.length} />
        <StatCard label="Reviews analysed" value={(stats?.total_reviews || 0).toLocaleString()} />
        <StatCard
          label="Avg sentiment"
          value={`${stats?.avg_sentiment_score || 0}/100`}
          sub="Across all brands"
        />
        <StatCard
          label="Avg selling price"
          value={stats?.avg_price_overall ? `₹${stats.avg_price_overall.toLocaleString()}` : '—'}
        />
        <StatCard label="Insights generated" value={stats?.insight_count || 0} />
      </div>

      {/* Brand snapshot table */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200/50 bg-white/40">
          <h2 className="font-semibold text-lg text-slate-800 tracking-tight">Brand snapshot</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-400 uppercase border-b border-gray-100">
                <th className="px-5 py-3 text-left">Brand</th>
                <th className="px-4 py-3 text-right">Avg price</th>
                <th className="px-4 py-3 text-right">MRP</th>
                <th className="px-4 py-3 text-right">Discount</th>
                <th className="px-4 py-3 text-right">Rating</th>
                <th className="px-4 py-3 text-right">Reviews</th>
                <th className="px-4 py-3 text-right">Sentiment</th>
                <th className="px-4 py-3 text-center">Band</th>
              </tr>
            </thead>
            <tbody>
              {brands.map((b, i) => (
                <tr key={b.brand_key} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-5 py-3 font-medium text-gray-800 flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full inline-block"
                      style={{ background: BRAND_COLORS[b.brand_key] || '#aaa' }}
                    />
                    {b.brand_name}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">
                    {b.pricing.avg_price ? `₹${b.pricing.avg_price.toLocaleString()}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-400">
                    {b.pricing.avg_mrp ? `₹${b.pricing.avg_mrp.toLocaleString()}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {b.pricing.avg_discount_pct != null ? (
                      <span className="text-orange-600 font-medium">{b.pricing.avg_discount_pct.toFixed(0)}%</span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-amber-600">★</span> {b.ratings.avg_rating?.toFixed(1) || '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">
                    {b.ratings.total_reviews?.toLocaleString() || '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <SentimentBadge score={b.sentiment.score} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full capitalize
                      ${b.pricing.price_band === 'premium' ? 'bg-purple-50 text-purple-700' :
                        b.pricing.price_band === 'mid-range' ? 'bg-blue-50 text-blue-700' :
                        'bg-gray-100 text-gray-600'}`}>
                      {b.pricing.price_band}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment scores */}
        <div className="glass-card rounded-2xl p-6">
          <h2 className="font-semibold text-lg text-slate-800 mb-4 tracking-tight">Sentiment score by brand</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={sentimentData} layout="vertical" margin={{ left: 90, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: '#9ca3af' }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: '#6b7280' }} width={88} />
              <Tooltip
                formatter={(v) => [`${v.toFixed(1)}/100`, 'Sentiment']}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {sentimentData.map((entry) => (
                  <rect key={entry.name} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Price vs Sentiment scatter */}
        <div className="glass-card rounded-2xl p-6">
          <h2 className="font-semibold text-lg text-slate-800 mb-1 tracking-tight">Price vs sentiment positioning</h2>
          <p className="text-xs font-medium text-slate-500 mb-4">Bubble size = total reviews</p>
          <ResponsiveContainer width="100%" height={220}>
            <ScatterChart margin={{ top: 10, right: 16, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="x"
                name="Avg price"
                tickFormatter={v => `₹${(v/1000).toFixed(0)}k`}
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                label={{ value: 'Avg price (₹)', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#9ca3af' }}
              />
              <YAxis
                dataKey="y"
                name="Sentiment"
                domain={[40, 100]}
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                label={{ value: 'Sentiment', angle: -90, position: 'insideLeft', offset: 10, fontSize: 11, fill: '#9ca3af' }}
              />
              <ZAxis dataKey="z" range={[60, 400]} />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ payload }) => {
                  if (!payload?.length) return null
                  const d = payload[0].payload
                  return (
                    <div className="bg-white border border-gray-200 rounded-lg p-2.5 shadow-sm text-xs">
                      <p className="font-medium">{d.name}</p>
                      <p className="text-gray-500">Avg price: ₹{d.x?.toLocaleString()}</p>
                      <p className="text-gray-500">Sentiment: {d.y?.toFixed(1)}/100</p>
                    </div>
                  )
                }}
              />
              <Scatter
                data={scatterData}
                fill="#4f6ef7"
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Pricing comparison */}
      <div className="glass-card rounded-2xl p-6">
        <h2 className="font-semibold text-lg text-slate-800 mb-4 tracking-tight">Price vs MRP — avg discount gap</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={pricingData} margin={{ left: 8, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6b7280' }} />
            <YAxis tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} tick={{ fontSize: 11, fill: '#9ca3af' }} />
            <Tooltip
              formatter={(v, n) => [`₹${v?.toLocaleString()}`, n === 'avg_price' ? 'Selling price' : 'MRP']}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="avg_mrp" name="MRP" fill="#e5e7eb" radius={[4, 4, 0, 0]} />
            <Bar dataKey="avg_price" name="Selling price" fill="#4f6ef7" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
