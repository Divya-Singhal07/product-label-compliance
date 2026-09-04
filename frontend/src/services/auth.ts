import type { User } from '../types/auth'

const API = '/api'

/** Check if there's an active session. Returns null if not authenticated. */
export async function getMe(): Promise<User | null> {
  try {
    const res = await fetch(`${API}/me`, { credentials: 'include' })
    if (!res.ok) return null
    return (await res.json()) as User
  } catch {
    return null
  }
}

export interface LoginInput {
  officer_id: string
  password: string
}

export interface RegisterInput {
  full_name: string
  officer_id: string
  email: string
  password: string
  confirm_password: string
  department: string
  role: string
}

export interface AuthSuccess {
  success: true
  email: string
}

export interface AuthNotice {
  notice: string
}

export interface AuthError {
  error: string
}

export type LoginResult = AuthSuccess | AuthError
export type RegisterResult = AuthSuccess | AuthNotice | AuthError

/** Login with officer ID + password. */
export async function login(input: LoginInput): Promise<LoginResult> {
  const res = await fetch(`${API}/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return res.json() as Promise<LoginResult>
}

/** Register a new account. */
export async function register(input: RegisterInput): Promise<RegisterResult> {
  const res = await fetch(`${API}/register`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return res.json() as Promise<RegisterResult>
}

/** Log out. Clears session cookies. */
export async function logout(): Promise<void> {
  await fetch(`${API}/logout`, {
    method: 'POST',
    credentials: 'include',
  })
}

export interface ForgotPasswordResult {
  success?: boolean
  message?: string
  error?: string
}

/** Request password reset link for an Officer ID. */
export async function forgotPassword(officer_id: string): Promise<ForgotPasswordResult> {
  const res = await fetch(`${API}/forgot-password`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ officer_id }),
  })
  return res.json() as Promise<ForgotPasswordResult>
}
