'use client'

import { useState, useEffect } from 'react'
import { apiGet } from '@/lib/api'
import type { Product } from '@/lib/api'

export default function ProductPage({ params }: { params: { id: string } }) {
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadProduct()
  }, [params.id])

  async function loadProduct() {
    try {
      const res = await apiGet(`/api/products/${params.id}`)
      if (!res.ok) throw new Error('Product not found')
      const data = await res.json()
      setProduct(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="p-8">Loading...</div>
  if (error) return <div className="p-8 text-red-600">{error}</div>
  if (!product) return null

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h1 className="text-3xl font-bold">{product.name}</h1>
          {product.species && (
            <p className="text-lg text-slate-600">{product.species}</p>
          )}
          {product.scientific_name && (
            <p className="text-sm italic text-slate-500">{product.scientific_name}</p>
          )}
          <p className="text-2xl font-bold mt-4">${product.price.toFixed(2)}</p>
          <p className="text-sm text-slate-500 mt-2">
            {product.water_type} • {product.care_level} • {product.product_type}
          </p>
          {product.is_wysiwyg && (
            <span className="text-xs font-bold text-blue-600 mt-1 inline-block">WYSIWYG</span>
          )}
          {product.is_livestock && (
            <span className="text-xs font-bold text-green-600 mt-1 inline-block">Livestock</span>
          )}
          <p className="mt-4 text-slate-700">{product.description}</p>
          <div className="mt-6 space-y-2 text-sm text-slate-600">
            {product.temperament && <p><strong>Temperament:</strong> {product.temperament}</p>}
            {product.max_size_cm && <p><strong>Max size:</strong> {product.max_size_cm} cm</p>}
            {product.temp_min_c && product.temp_max_c && (
              <p><strong>Temperature:</strong> {product.temp_min_c}°C – {product.temp_max_c}°C</p>
            )}
            {product.ph_min && product.ph_max && (
              <p><strong>pH:</strong> {product.ph_min} – {product.ph_max}</p>
            )}
            {product.diet && <p><strong>Diet:</strong> {product.diet}</p>}
            {product.origin && <p><strong>Origin:</strong> {product.origin}</p>}
            {product.compatibility_notes && (
              <p><strong>Compatibility:</strong> {product.compatibility_notes}</p>
            )}
          </div>
        </div>
        <div className="bg-slate-100 rounded-lg p-6 border">
          <h2 className="font-bold mb-4">Add to Cart</h2>
          <div className="flex items-center gap-4">
            <span className="text-lg font-bold">${product.price.toFixed(2)}</span>
            <button
              className="w-full bg-blue-600 text-white py-3 rounded hover:bg-blue-700 disabled:opacity-50"
              disabled={product.is_livestock}
            >
              Add to cart
            </button>
          </div>
          {product.is_livestock && (
            <p className="mt-3 text-xs text-red-600">
              Livestock is limited to 1 per order due to shipping constraints.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}