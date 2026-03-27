import React, { useState, useEffect } from 'react'
import axios from 'axios'
import Overview from './components/Overview'
import BrandComparison from './components/BrandComparison'
import ProductDrilldown from './components/ProductDrilldown'
import AgentInsights from './components/AgentInsights'
import Filters from './components/Filters'

const API = '/api'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'comparison', label: 'Brand Comparison' },
  { id: 'products', label: 'Products' },
  { id: 'insights', label: 'Agent Insights' },
]

export default function App() {
  const [tab, setTab] = useState('overview')
  const [brands, setBrands] = useState([])
  const [products, setProducts] = useState([])
  const [insights, setInsights] = useState([])
  const [overviewStats, setOverviewStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filters
  const [filters, setFilters] = useState({
    selectedBrands: [],
    minPrice: '',
    maxPrice: '',
    minRating: '',
    priceBand: '',
    minSentiment: '',
  })

  useEffect(() => {
    async function loadAll() {
      setLoading(true)
      try {
        const [bRes, pRes, iRes, oRes] = await Promise.all([
          axios.get(`${API}/brands`),
          axios.get(`${API}/products`),
          axios.get(`${API}/insights`),
          axios.get(`${API}/stats/overview`),
        ])
        setBrands(bRes.data)
        setProducts(pRes.data)
        setInsights(iRes.data)
        setOverviewStats(oRes.data)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    loadAll()
  }, [])

  // Apply filters client-side
  const filteredBrands = brands.filter(b => {
    if (filters.selectedBrands.length > 0 && !filters.selectedBrands.includes(b.brand_key)) return false
    if (filters.priceBand && b.pricing.price_band !== filters.priceBand) return false
    if (filters.minRating && (b.ratings.avg_rating || 0) < parseFloat(filters.minRating)) return false
    return true
  })

  const filteredProducts = products.filter(p => {
    if (filters.selectedBrands.length > 0 && !filters.selectedBrands.includes(p.brand)) return false
    if (filters.minPrice && (p.price || 0) < parseFloat(filters.minPrice)) return false
    if (filters.maxPrice && (p.price || 0) > parseFloat(filters.maxPrice)) return false
    if (filters.minRating && (p.rating || 0) < parseFloat(filters.minRating)) return false
    return true
  })

  if (loading) return (
    <div className="min-h-screen bg-hero-pattern bg-slate-50 flex items-center justify-center">
      <div className="text-center glass-card p-10 rounded-3xl">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-600 text-sm font-medium animate-pulse">Loading intelligence data…</p>
      </div>
    </div>
  )

  if (error) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="bg-red-50/80 backdrop-blur-md border border-red-200 rounded-2xl p-8 max-w-md text-center shadow-2xl">
        <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">!</div>
        <p className="text-red-800 font-bold mb-2">Could not load data</p>
        <p className="text-red-600 text-sm font-medium">{error}</p>
        <p className="text-slate-500 text-xs mt-4">Ensure the API is running on port 8000</p>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-hero-pattern bg-slate-50 text-slate-800">
      {/* Header */}
      <header className="glass sticky top-0 z-20 border-b border-white/50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gradient">Luggage Intelligence</h1>
            <p className="text-xs text-slate-500 font-medium">Amazon India · Competitive Dashboard</p>
          </div>
          <nav className="flex gap-2">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 ${
                  tab === t.id
                    ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-lg shadow-brand-500/30 -translate-y-0.5'
                    : 'text-slate-600 hover:bg-white/60 hover:text-brand-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 animate-fade-in">
        {/* Filters bar */}
        <Filters
          brands={brands}
          filters={filters}
          onFiltersChange={setFilters}
          className="mb-6"
        />

        {tab === 'overview' && (
          <Overview
            stats={overviewStats}
            brands={filteredBrands}
            products={filteredProducts}
          />
        )}
        {tab === 'comparison' && (
          <BrandComparison brands={filteredBrands} />
        )}
        {tab === 'products' && (
          <ProductDrilldown products={filteredProducts} brands={brands} />
        )}
        {tab === 'insights' && (
          <AgentInsights insights={insights} brands={brands} />
        )}
      </main>
    </div>
  )
}
