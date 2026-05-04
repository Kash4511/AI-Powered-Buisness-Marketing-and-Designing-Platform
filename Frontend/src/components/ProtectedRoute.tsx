import React, { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface ProtectedRouteProps {
  children: ReactNode
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="auth-overlay">
        <div className="auth-container" style={{ textAlign: 'center' }}>
          <div style={{ padding: '2rem' }}>
            <h3>Loading...</h3>
          </div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ message: 'Session expired. Please log in again.', isError: true }} />
  }

  return <>{children}</>
}

export default ProtectedRoute