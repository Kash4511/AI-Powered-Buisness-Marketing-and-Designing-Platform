import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { apiClient } from '../lib/apiClient'

interface User {
  id: number
  email: string
  name: string
  phone_number?: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, name: string, phone_number: string) => Promise<void>
  register: (email: string, password: string, name: string, phone_number: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)


interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const isAuthenticated = !!user

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token')
      if (token) {
        try {
          console.log('AuthContext: Initial auth check...');
          const response = await apiClient.get('/api/auth/profile/')
          setUser(response.data)
          console.log('AuthContext: Profile loaded successfully');
        } catch (error: any) {
          console.error('Auth check failed:', error)
          // Only clear if it's NOT a retry-able error (like a 401 that might be refreshed)
          // apiClient already handles 401 refresh. If it reaches here, refresh also failed.
          if (error.response?.status === 401 || !localStorage.getItem('refresh_token')) {
            console.log('AuthContext: Session invalid, clearing tokens');
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            setUser(null)
          }
        }
      }
      setLoading(false)
    }

    checkAuth()
    
    const handleAuthExpired = () => {
      console.log('AuthContext: Token expired, logging out');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    };

    window.addEventListener('auth:expired', handleAuthExpired);
    return () => {
      window.removeEventListener('auth:expired', handleAuthExpired);
    };
  }, [])

  const login = async (email: string, password: string) => {
    try {
      console.log('AuthContext: Attempting login...');
      const response = await apiClient.post('/api/auth/login/', {
        email,
        password,
      })

      if (!response.data || !response.data.access) {
        throw new Error('Invalid login response from server');
      }

      const { access, refresh } = response.data
      localStorage.setItem('access_token', access)
      localStorage.setItem('refresh_token', refresh)

      // Fetch user profile - if this fails, we want to clear tokens and throw
      try {
        console.log('AuthContext: Fetching user profile...');
        const profileResponse = await apiClient.get('/api/auth/profile/')
        setUser(profileResponse.data)
        console.log('AuthContext: Login successful');
      } catch (profileError) {
        console.error('AuthContext: Profile fetch failed after login:', profileError)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        throw profileError
      }
    } catch (error: unknown) {
      console.error('AuthContext: Login failed:', error)
      throw error
    }
  }

  const signup = async (email: string, password: string, name: string, phone_number: string) => {
    try {
      const response = await apiClient.post('/api/auth/register/', {
        email,
        password,
        password_confirm: password,
        name,
        phone_number,
      })

      const { access, refresh } = response.data
      localStorage.setItem('access_token', access)
      localStorage.setItem('refresh_token', refresh)

      // Fetch user profile
      const profileResponse = await apiClient.get('/api/auth/profile/')
      setUser(profileResponse.data)
    } catch (error: unknown) {
      console.error('Signup failed:', error)
      throw error
    }
  }

  const register = async (email: string, password: string, name: string, phone_number: string) => {
    try {
      const response = await apiClient.post('/api/auth/register/', {
        email,
        password,
        password_confirm: password,
        name,
        phone_number,
      })
      // Don't automatically log in - just register
      console.log('Registration successful:', response.data)
    } catch (error: unknown) {
      console.error('Registration failed:', error)
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }

  const value: AuthContextType = {
    user,
    loading,
    login,
    signup,
    register,
    logout,
    isAuthenticated,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}