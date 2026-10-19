const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8000'

async function request(path: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${GATEWAY_URL}${path}`, { ...options, headers })
  return res
}

export async function apiGet(path: string): Promise<Response> {
  return request(path, { method: 'GET' })
}

export async function apiPost(path: string, body: unknown): Promise<Response> {
  return request(path, { method: 'POST', body: JSON.stringify(body) })
}

export function setToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('token', token)
  }
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

export function clearToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token')
  }
}

export interface Product {
  id: string
  name: string
  description: string | null
  price: number
  category_id: string | null
  product_type: string
  water_type: string | null
  is_wysiwyg: boolean
  is_livestock: boolean
  species: string | null
  scientific_name: string | null
  care_level: string | null
  max_size_cm: number | null
  temperament: string | null
  temp_min_c: number | null
  temp_max_c: number | null
  ph_min: number | null
  ph_max: number | null
  diet: string | null
  origin: string | null
  compatibility_notes: string | null
  brand: string | null
  tank_size_min_litres: number | null
  power_watts: number | null
  created_at: string
}

export interface Order {
  id: string
  user_id: string
  status: string
  total: number
  created_at: string
}

export interface RegisterBody {
  email: string
  password: string
}

export interface LoginBody {
  email: string
  password: string
}

export interface OrderItem {
  product_id: string
  quantity: number
  price: number
}

export interface CreateOrderBody {
  items: OrderItem[]
}

export interface ChargeBody {
  order_id: string
  amount: number
}