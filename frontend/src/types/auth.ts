export interface User {
  email: string
  officer_id?: string
  full_name?: string
  department?: string
  role?: string
}

export type AuthMode = 'login' | 'register' | 'forgot'
