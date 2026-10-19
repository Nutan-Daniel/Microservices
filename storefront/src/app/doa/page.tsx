'use client'

import { useState } from 'react'
import { apiPost } from '@/lib/api'

export default function DOA() {
  const [reservationId, setReservationId] = useState('')
  const [evidenceUrl, setEvidenceUrl] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess(false)
    try {
      const res = await apiPost(`/inventory/reservations/${reservationId}/doa`, {
        evidence_url: evidenceUrl || undefined,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'DOA claim failed')
      }
      setSuccess(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'DOA claim failed')
    }
  }

  return (
    <div className="max-w-md mx-auto p-8">
      {success ? (
        <div className="text-center">
          <h2 className="text-2xl font-bold text-green-600">DOA Claim Submitted</h2>
          <p>Your claim has been received with photo evidence.</p>
          <p className="mt-4">We will review your claim and process a refund or replacement.</p>
        </div>
      ) : (
        <>
          <h1 className="text-2xl font-bold mb-6">Report Dead on Arrival (DOA)</h1>
          <p className="mb-6 text-slate-600">
            If your livestock arrived deceased, please submit a claim with photo evidence. Claims must be filed within the guarantee window.
          </p>
          {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded">{error}</div>}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Reservation ID</label>
              <input
                type="text"
                required
                className="w-full border rounded px-3 py-2"
                value={reservationId}
                onChange={(e) => setReservationId(e.target.value)}
                placeholder="e.g. res_abc123"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Photo Evidence URL</label>
              <input
                type="url"
                className="w-full border rounded px-3 py-2"
                value={evidenceUrl}
                onChange={(e) => setEvidenceUrl(e.target.value)}
                placeholder="https://example.com/photo.jpg"
              />
            </div>
            <button type="submit" className="w-full bg-red-600 text-white py-3 rounded hover:bg-red-700">
              Submit DOA Claim
            </button>
          </form>
          <p className="mt-4 text-sm text-center text-slate-500">
            Need help? Contact customer support.
          </p>
        </>
      )}
    </div>
  )
}