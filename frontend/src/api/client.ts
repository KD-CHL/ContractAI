import axios, { type AxiosRequestConfig, type AxiosResponse } from 'axios'
import type { ApiError } from '@/types/api'

const TOKEN_KEY = 'contractai_access_token'
const REFRESH_KEY = 'contractai_refresh_token'

// ─── Token helpers ───────────────────────────────────────────────────────────

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_KEY, refreshToken)
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

// ─── Axios instance ──────────────────────────────────────────────────────────

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ─── Request interceptor ─────────────────────────────────────────────────────

client.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ─── Response interceptor with token refresh ─────────────────────────────────

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function subscribeTokenRefresh(cb: (token: string) => void): void {
  refreshSubscribers.push(cb)
}

function onTokenRefreshed(newToken: string): void {
  refreshSubscribers.forEach((cb) => cb(newToken))
  refreshSubscribers = []
}

function onRefreshFailed(): void {
  refreshSubscribers = []
}

client.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config

    // Only attempt refresh on 401 and if we haven't already retried
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(normalizeError(error))
    }

    // Don't try to refresh on auth endpoints themselves
    const url = originalRequest.url || ''
    if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
      clearTokens()
      redirectToLogin()
      return Promise.reject(normalizeError(error))
    }

    originalRequest._retry = true

    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      clearTokens()
      redirectToLogin()
      return Promise.reject(normalizeError(error))
    }

    if (isRefreshing) {
      // Queue this request until the refresh completes
      return new Promise((resolve) => {
        subscribeTokenRefresh((newToken: string) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          resolve(client(originalRequest))
        })
      })
    }

    isRefreshing = true

    try {
      const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      })

      const newAccessToken: string = data.access_token
      const newRefreshToken: string = data.refresh_token

      setTokens(newAccessToken, newRefreshToken)
      onTokenRefreshed(newAccessToken)

      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
      return client(originalRequest)
    } catch {
      onRefreshFailed()
      clearTokens()
      redirectToLogin()
      return Promise.reject(normalizeError(error))
    } finally {
      isRefreshing = false
    }
  },
)

function redirectToLogin(): void {
  const currentPath = window.location.pathname
  if (currentPath !== '/login') {
    window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
  }
}

function normalizeError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const detail =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred'
    return {
      detail: typeof detail === 'string' ? detail : JSON.stringify(detail),
      status_code: error.response?.status,
    }
  }
  return { detail: 'An unexpected error occurred' }
}

// ─── Typed helper functions ──────────────────────────────────────────────────

export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await client.get<T>(url, config)
  return response.data
}

export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const response = await client.post<T>(url, data, config)
  return response.data
}

export async function patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const response = await client.patch<T>(url, data, config)
  return response.data
}

export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await client.delete<T>(url, config)
  return response.data
}

export default client
