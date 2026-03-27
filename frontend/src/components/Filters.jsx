import React from 'react'

const PRICE_BANDS = ['', 'budget', 'mid-range', 'premium']
const RATINGS = ['', '3', '3.5', '4', '4.5']

export default function Filters({ brands, filters, onFiltersChange, className = '' }) {
  function update(key, val) {
    onFiltersChange(f => ({ ...f, [key]: val }))
  }

  const activeCount = [
    filters.selectedBrands.length > 0,
    filters.minPrice,
    filters.maxPrice,
    filters.minRating,
    filters.priceBand,
  ].filter(Boolean).length

  function reset() {
    onFiltersChange({
      selectedBrands: [],
      minPrice: '',
      maxPrice: '',
      minRating: '',
      priceBand: '',
      minSentiment: '',
    })
  }

  return (
    <div className={`glass-card rounded-2xl p-5 ${className}`}>
      <div className="flex flex-wrap gap-4 items-end">
        {/* Brand multi-select */}
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase tracking-widest">Brands</label>
          <div className="flex flex-wrap gap-2">
            {brands.map(b => {
              const active = filters.selectedBrands.includes(b.brand_key)
              return (
                <button
                  key={b.brand_key}
                  onClick={() => {
                    if (active) {
                      update('selectedBrands', filters.selectedBrands.filter(k => k !== b.brand_key))
                    } else {
                      update('selectedBrands', [...filters.selectedBrands, b.brand_key])
                    }
                  }}
                  className={`text-xs font-bold px-3 py-1.5 rounded-xl transition-all duration-300 ${
                    active
                      ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-md shadow-brand-500/30'
                      : 'bg-white/50 text-slate-600 border border-slate-200 hover:bg-white hover:shadow-sm'
                  }`}
                >
                  {b.brand_name}
                </button>
              )
            })}
          </div>
        </div>

        {/* Price band */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase tracking-widest">Price band</label>
          <select
            value={filters.priceBand}
            onChange={e => update('priceBand', e.target.value)}
            className="bg-white/60 border border-slate-200 rounded-xl px-3 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500/40 transition-shadow"
          >
            <option value="">All bands</option>
            <option value="budget">Budget</option>
            <option value="mid-range">Mid-range</option>
            <option value="premium">Premium</option>
          </select>
        </div>

        {/* Price range */}
        <div className="flex items-end gap-2">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase tracking-widest">Min price (₹)</label>
            <input
              type="number"
              placeholder="0"
              value={filters.minPrice}
              onChange={e => update('minPrice', e.target.value)}
              className="bg-white/60 border border-slate-200 rounded-xl px-3 py-2 text-sm font-medium w-28 focus:outline-none focus:ring-2 focus:ring-brand-500/40 transition-shadow"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase tracking-widest">Max price (₹)</label>
            <input
              type="number"
              placeholder="∞"
              value={filters.maxPrice}
              onChange={e => update('maxPrice', e.target.value)}
              className="bg-white/60 border border-slate-200 rounded-xl px-3 py-2 text-sm font-medium w-28 focus:outline-none focus:ring-2 focus:ring-brand-500/40 transition-shadow"
            />
          </div>
        </div>

        {/* Min rating */}
        <div>
          <label className="block text-xs font-semibold text-slate-500 mb-2 uppercase tracking-widest">Min rating</label>
          <select
            value={filters.minRating}
            onChange={e => update('minRating', e.target.value)}
            className="bg-white/60 border border-slate-200 rounded-xl px-3 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500/40 transition-shadow"
          >
            <option value="">Any</option>
            <option value="3">3★ +</option>
            <option value="3.5">3.5★ +</option>
            <option value="4">4★ +</option>
            <option value="4.5">4.5★ +</option>
          </select>
        </div>

        {/* Reset */}
        {activeCount > 0 && (
          <button
            onClick={reset}
            className="text-xs font-bold text-slate-500 hover:text-slate-700 px-4 py-2 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors bg-white/50"
          >
            Reset ({activeCount})
          </button>
        )}
      </div>
    </div>
  )
}
