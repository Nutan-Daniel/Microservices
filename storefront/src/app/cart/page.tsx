'use client'

import { useState, useEffect } from 'react'
import { apiGet, apiPost, getToken } from '@/lib/api'
import type { Product, Order, CreateOrderBody, ChargeBody } from '@/lib/api'

export default function Cart() {
  const [cart, setCart] = useState<Record<string, number>>(() => {
    if (typeof window !== 'undefined') {
      return JSON.parse(localStorage.getItem('cart') || '{}')
    }
    return {}
  })
  const [products, setProducts] = useState<Record<string, Product>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [orderPlaced, setOrderPlaced] = useState(false)

  useEffect(() => {
    loadCart()
  }, [])

  async function loadCart() {
    const ids = Object.keys(cart)
    if (ids.length === 0) {
      setLoading(false)
      return
    }
    try {
      for (const id of ids) {
        const res = await apiGet(`/products/${id}`)
        if (res.ok) {
          const p = await res.json()
          setProducts((prev) => ({ ...prev, [id]: p }))
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load cart')
    } finally {
      setLoading(false)
    }
  }

  function removeItem(id: string) {
    setCart((prev) => {
      const next = { ...prev }
      delete next[id]
      localStorage.setItem('cart', JSON.stringify(next))
      return next
    })
    setProducts((prev) => {
      const next = { ...prev }
      delete next[id]
      return next
    })
  }

  function total() {
    return Object.entries(products).reduce(
      (sum, [id, p]) => sum + p.price * (cart[id] || 0),
      0
    )
  }

  async function checkout() {
    if (!getToken()) {
      setError('Please log in to checkout')
      return
    }
    const items = Object.entries(products).map(([id, p]) => ({
      product_id: id,
      quantity: cart[id] || 0,
      price: p.price,
    }))
    try {
      const res = await apiPost('/orders', { items })
      if (!res.ok) throw new Error('Failed to create order')
      const order = await res.json()

      // Charge payment
      const payRes = await apiPost('/payments/charge', {
        order_id: order.id,
        amount: order.total,
      })
      if (!payRes.ok) throw new Error('Payment failed')

      localStorage.removeItem('cart')
      setCart({})
      setOrderPlaced(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Checkout failed')
    }
  }

  if (loading) return <div className="p-8">Loading...</div>
  if (orderPlaced) {
    return (
      <div className="max-w-md mx-auto p-8 text-center">
        <h2 className="text-2xl font-bold text-green-600">Order Placed!</h2>
        <p>Your aquarium order has been created and payment processed.</p>
        <a href="/" className="mt-4 inline-block text-blue-600 hover:underline">Continue shopping</a>
      </div>
    )
  }

  const itemCount = Object.values(cart).reduce((a, b) => a + b, 0)

  if (itemCount === 0) {
    return (
      <div className="max-w-md mx-auto p-8 text-center">
        <h2 className="text-2xl font-bold">Your cart is empty</h2>
        <a href="/" className="mt-4 inline-block text-blue-600 hover:underline">Browse products</a>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Shopping Cart</h1>
      {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded">{error}</div>}
      <div className="space-y-4">
        {Object.entries(products).map(([id, p]) => (
          <div key={id} className="flex justify-between items-center border-b pb-4">
            <div>
              <h3 className="font-semibold">{p.name}</h3>
              <p className="text-sm text-slate-500">${p.price.toFixed(2)} × {cart[id]}</p>
            </div>
            <button
              onClick={() => removeItem(id)}
              className="text-red-600 hover:text-red-800 text-sm"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
      <div className="mt-6 border-t pt-4">
        <div className="flex justify-between mb-2">
          <span>Total</span>
          <span className="font-bold">${total().toFixed(2)}</span>
        </div>
        <button
          onClick={checkout}
          disabled={!getToken()}
          className="w-full bg-green-600 text-white py-3 rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed mt-4"
        >
          {getToken() ? 'Proceed to Payment' : 'Please log in to checkout'}
        </button>
      </div>
    </div>
  )
}