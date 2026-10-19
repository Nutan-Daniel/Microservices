'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { apiGet, getToken } from '@/lib/api'
import type { Product } from '@/lib/api'

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [cart, setCart] = useState<Record<string, number>>(() => {
    if (typeof window !== 'undefined') {
      return JSON.parse(localStorage.getItem('cart') || '{}')
    }
    return {}
  })

  useEffect(() => {
    loadProducts()
  }, [])

  async function loadProducts() {
    try {
      const res = await apiGet('/products')
      if (!res.ok) throw new Error('Failed to load products')
      const data = await res.json()
      setProducts(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  function addToCart(productId: string) {
    setCart((prev) => {
      const next = { ...prev, [productId]: (prev[productId] || 0) + 1 }
      localStorage.setItem('cart', JSON.stringify(next))
      return next
    })
  }

  if (loading) return <div className="p-8">Loading...</div>
  if (error) return <div className="p-8 text-red-600">{error}</div>

  const cartCount = Object.values(cart).reduce((a, b) => a + b, 0)

  return (
    <div className="max-w-7xl mx-auto p-4">
      <nav className="flex justify-between items-center mb-8 border-b pb-4">
        <Link href="/" className="text-xl font-bold text-blue-700">
          AquaShop
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/cart" className="relative">
            Cart ({cartCount})
          </Link>
          {getToken() ? (
            <>
              <Link href="/orders" className="text-sm hover:underline">My Orders</Link>
              <button
                onClick={() => {
                  localStorage.removeItem('token')
                  window.location.reload()
                }}
                className="text-sm hover:underline text-red-600"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-sm hover:underline">Login</Link>
              <Link href="/register" className="text-sm hover:underline">Register</Link>
            </>
          )}
        </div>
      </nav>

      <h1 className="text-2xl font-bold mb-6">Aquarium Shop</h1>
      <p className="mb-6">
        Freshwater & saltwater fish, corals, invertebrates, aquatic plants, and equipment.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((p) => (
          <div key={p.id} className="border rounded-lg p-4 bg-white shadow-sm">
            <Link href={`/products/${p.id}`} className="block">
              <h2 className="font-semibold">{p.name}</h2>
              {p.species && <p className="text-sm text-slate-500">{p.species}</p>}
              <p className="text-lg font-bold mt-2">${p.price.toFixed(2)}</p>
              <p className="text-xs text-slate-500 mt-2">
                {p.water_type} • {p.care_level} • {p.product_type}
              </p>
              {p.is_wysiwyg && (
                <span className="text-xs text-blue-600 font-bold mt-1">WYSIWYG</span>
              )}
              {p.is_livestock && (
                <span className="text-xs text-green-600 font-bold mt-1">Livestock</span>
              )}
            </Link>
            <button
              onClick={() => addToCart(p.id)}
              className="mt-4 w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              disabled={p.is_livestock && cart[p.id] > 0}
            >
              {p.is_livestock && cart[p.id] > 0 ? 'Already in cart' : 'Add to cart'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}