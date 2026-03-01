import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff, Mail, Lock, ArrowLeft } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './AuthPages.css'

const LoginPage: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  
  // Get success message from navigation state
  const successMessage = location.state?.message

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
    if (error) setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    console.log('Login form submitted with data:', { email: formData.email, password: '***' })
    
    if (!formData.email || !formData.password) {
      setError('Please fill in all fields')
      return
    }

    setLoading(true)
    setError('')

    try {
      console.log('Calling login function...')
      await login(formData.email, formData.password)
      console.log('Login successful, navigating to dashboard...')
      navigate('/dashboard')
    } catch (err: unknown) {
      console.error('Login error:', err)
      const asObj = err as Record<string, unknown>
      const response = asObj.response as { data?: any } | undefined
      const data = response?.data
      
      if (data && typeof data === 'object') {
        // Handle the custom_exception_handler format: { error: string, details: any }
        const details = data.details || data;
        
        if (typeof details === 'string') {
          setError(details);
        } else if (typeof details === 'object' && details !== null) {
          const detailObj = details as Record<string, any>;
          // Look for common DRF error keys inside details
          const firstError = 
            (Array.isArray(detailObj.non_field_errors) && detailObj.non_field_errors[0]) ||
            (Array.isArray(detailObj.email) && `Email: ${detailObj.email[0]}`) ||
            (Array.isArray(detailObj.password) && `Password: ${detailObj.password[0]}`) ||
            detailObj.detail ||
            data.error ||
            'Login failed. Please check your credentials.';
          setError(typeof firstError === 'string' ? firstError : 'Login failed. Please check your credentials.');
        } else {
          setError(data.error || 'Login failed. Please check your credentials.');
        }
      } else if (
        (asObj.code === 'ECONNABORTED') ||
        (typeof asObj.message === 'string' && (asObj.message as string).includes('timeout'))
      ) {
        setError('Request timed out. Please try again.')
      } else if (asObj.request) {
        setError('Unable to connect to server. Please check your connection and try again.')
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-overlay">
      <motion.div 
        className="auth-container"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="auth-header">
          <Link to="/" className="back-button">
            <ArrowLeft size={20} />
            Back to Home
          </Link>
          <div className="auth-logo">Forma</div>
          <h2>Welcome Back</h2>
          <p>Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {successMessage && (
            <motion.div 
              className="auth-success"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {successMessage}
            </motion.div>
          )}
          
          {error && (
            <motion.div 
              className="auth-error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {error}
            </motion.div>
          )}

          <div className="auth-field">
            <div className="input-wrapper">
              <Mail className="input-icon" size={20} />
              <input
                type="email"
                name="email"
                placeholder="Email address"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="auth-field">
            <div className="input-wrapper">
              <Lock className="input-icon" size={20} />
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                placeholder="Password"
                value={formData.password}
                onChange={handleChange}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="auth-submit"
            disabled={loading}
          >
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Don't have an account?{' '}
            <Link to="/signup" className="auth-link">
              Sign up here
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}

export default LoginPage