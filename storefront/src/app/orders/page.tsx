'use client'

import { useState, useEffect } from 'react'
import { apiGet } from '@/lib/api'
import type { Order } from '@/lib/api'

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadOrders()
  }, [])

  async function loadOrders() {
    try {
      const res = await apiGet('/orders')
      if (!res.ok) throw new Error('Failed to load orders')
      const data = await res.json()
      setOrders(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load orders')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="p-8">Loading...</div>
  if (error) return <div className="p-8 text-red-600">{error}</div>

  if (orders.length === 0) {
    return (
      <div className="max-w-md mx-auto p-8 text-center">
        <h2 className="text-2xl font-bold">No orders yet</h2>
        <a href="/" className="mt-4 inline-block text-blue-600 hover:underline">Browse products</a>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">My Orders</h1>
      <table className="w-full border-collapse border border-slate-200">
        <thead>
          <tr className="bg-slate-100">
            <th className="p-3 text-left">Order ID</th>
            <th className="p-3 text-left">Status</th>
            <th className="p-3 text-right">Total</th>
            <th className="p-3 text-left">Date</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id} className="border-t">
              <td className="p-3 font-mono text-sm">{o.id}</td>
              <td className="p-3">
                <span
                  className={`px-2 py-1 rounded text-xs font-semibold ${
                    o.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                    o.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                    o.status === 'reserved' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-slate-100 text-slate-700'
                  }`}
                >
                  {o.status}
                </span>
              </td>
              <td className="p-3 text-right">${o.total.toFixed(2)}</td>
              <td className="p-3 text-sm text-slate-500">{new Date(o.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}