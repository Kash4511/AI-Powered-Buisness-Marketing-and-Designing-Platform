import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff, User, Mail, Phone, Lock, ArrowLeft } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './AuthPages.css'

const SignupPage: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone_number: '',
    password: '',
    password_confirm: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
    if (error) setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    console.log('Signup form submitted with data:', formData)
    
    if (!formData.name || !formData.email || !formData.password || !formData.password_confirm) {
      setError('Please fill in all required fields')
      return
    }

    if (formData.password !== formData.password_confirm) {
      setError('Passwords do not match')
      return
    }

    if (formData.password.length < 4) {
      setError('Password must be at least 4 characters long')
      return
    }

    setLoading(true)
    setError('')

    try {
      console.log('Calling register function...')
      await register(formData.email, formData.password, formData.name, formData.phone_number)
      console.log('Registration successful, navigating to login...')
      navigate('/login', { state: { message: 'Account created successfully! Please sign in with your credentials.' } })
    } catch (err: unknown) {
      console.error('Signup error:', err)
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
            (Array.isArray(detailObj.email) && `Email: ${detailObj.email[0]}`) ||
            (Array.isArray(detailObj.password) && `Password: ${detailObj.password[0]}`) ||
            (Array.isArray(detailObj.non_field_errors) && detailObj.non_field_errors[0]) ||
            detailObj.detail ||
            data.error ||
            'Registration failed. Please check your information.';
          setError(typeof firstError === 'string' ? firstError : 'Registration failed. Please check your information.');
        } else {
          setError(data.error || 'Registration failed. Please check your information.');
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
          <h2>Create Account</h2>
          <p>Join us to get started</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
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
              <User className="input-icon" size={20} />
              <input
                type="text"
                name="name"
                placeholder="Full name"
                value={formData.name}
                onChange={handleChange}
                required
              />
            </div>
          </div>

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
              <Phone className="input-icon" size={20} />
              <input
                type="tel"
                name="phone_number"
                placeholder="Phone number (optional)"
                value={formData.phone_number}
                onChange={handleChange}
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

          <div className="auth-field">
            <div className="input-wrapper">
              <Lock className="input-icon" size={20} />
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                name="password_confirm"
                placeholder="Confirm password"
                value={formData.password_confirm}
                onChange={handleChange}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              >
                {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="auth-submit"
            disabled={loading}
            onClick={() => console.log('Signup button clicked!')}
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <Link to="/login" className="auth-link">
              Sign in here
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}

export default SignupPage