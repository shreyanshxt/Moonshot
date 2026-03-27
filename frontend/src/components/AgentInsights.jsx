import React from 'react'

const TYPE_CONFIG = {
  value_for_money: { icon: '◈', color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-100', label: 'Value for money' },
  discount_dependency: { icon: '⬇', color: 'text-orange-600', bg: 'bg-orange-50 border-orange-100', label: 'Discount dependency' },
  hidden_dissatisfaction: { icon: '◎', color: 'text-purple-600', bg: 'bg-purple-50 border-purple-100', label: 'Hidden dissatisfaction' },
  anomaly: { icon: '⚡', color: 'text-red-600', bg: 'bg-red-50 border-red-100', label: 'Aspect anomaly' },
  price_parity: { icon: '⇔', color: 'text-blue-600', bg: 'bg-blue-50 border-blue-100', label: 'Price parity' },
  market_presence: { icon: '◉', color: 'text-gray-700', bg: 'bg-gray-50 border-gray-200', label: 'Market presence' },
}

export default function AgentInsights({ insights, brands }) {
  const brandNameMap = Object.fromEntries(brands.map(b => [b.brand_key, b.brand_name]))

  return (
    <div className="space-y-6">
      <div className="glass-card bg-amber-50/40 border-amber-200/50 rounded-2xl p-5">
        <p className="text-sm font-bold text-amber-800 tracking-wide">AGENT INSIGHTS</p>
        <p className="text-xs font-medium text-amber-700/80 mt-1">
          These insights are automatically generated from cross-brand analysis — they highlight non-obvious patterns
          that a human analyst might miss in the raw data.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {insights.map((insight, i) => {
          const cfg = TYPE_CONFIG[insight.type] || TYPE_CONFIG.market_presence
          return (
            <div
              key={i}
              className={`glass-card rounded-2xl p-6 ${cfg.bg}`}
            >
              <div className="flex items-start gap-4">
                <span className={`text-2xl ${cfg.color} mt-0.5 leading-none`}>{cfg.icon}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full bg-white/80 backdrop-blur-sm border shadow-sm ${cfg.color}`}>
                      {cfg.label}
                    </span>
                    {insight.brand && (
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">
                        {brandNameMap[insight.brand] || insight.brand}
                      </span>
                    )}
                  </div>
                  <h3 className="font-bold text-slate-900 mb-1.5 text-lg">{insight.headline}</h3>
                  <p className="text-sm text-slate-600 leading-relaxed font-medium">{insight.detail}</p>
                </div>
              </div>
            </div>
          )
        })}

        {insights.length === 0 && (
          <div className="text-center py-12 text-gray-400 text-sm">
            No insights generated yet. Run the analysis pipeline to generate insights.
          </div>
        )}
      </div>
    </div>
  )
}
