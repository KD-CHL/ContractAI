import { get, post } from './client'
import type {
  AuthResponse,
  AuthStatus,
  ChangePasswordRequest,
  LoginRequest,
  RefreshRequest,
  RegisterRequest,
  User,
} from '@/types/api'

export function getAuthStatus(): Promise<AuthStatus> {
  return get<AuthStatus>('/auth/status')
}

export function getMe(): Promise<User> {
  return get<User>('/auth/me')
}

export function login(data: LoginRequest): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/login', data)
}

export function register(data: RegisterRequest): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/register', data)
}

export function refreshToken(data: RefreshRequest): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/refresh', data)
}

export function logout(): Promise<void> {
  return post<void>('/auth/logout')
}

export function changePassword(data: ChangePasswordRequest): Promise<void> {
  return post<void>('/auth/change-password', data)
}
