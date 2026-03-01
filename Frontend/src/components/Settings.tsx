import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, Plus, Settings as SettingsIcon, LogOut, Palette, ChevronDown } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { dashboardApi } from '../lib/dashboardApi'
import type { FirmProfile } from '../lib/dashboardApi'
import './Settings.css'

const Settings: React.FC = () => {
  const { logout, user } = useAuth()
  const navigate = useNavigate()
  const [firmProfile, setFirmProfile] = useState<FirmProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState({
    fullName: user?.name || '',
    firmName: '',
    firmSize: '1-2',
    workEmail: '',
    phoneNumber: '',
    website: '',
    guidelines: '',
    usingFormaFor: 'Personal Use',
    email: user?.email || ''
  })

  useEffect(() => {
    const loadProfile = async () => {
      try {
        // Get company information from the same API that Brand Assets uses
        const profile = await dashboardApi.getFirmProfile()
        setFirmProfile(profile)
        
        // Populate form with company information from Brand Assets/Firm Profile
        setFormData({
          fullName: user?.name || '',
          firmName: profile?.firm_name || '',
          firmSize: profile?.firm_size || '1-2',
          workEmail: profile?.work_email || '',
          phoneNumber: profile?.phone_number || '',
          website: profile?.firm_website || '',
          guidelines: profile?.branding_guidelines || '',
          usingFormaFor: 'Personal Use', // This field doesn't exist in the model yet
          email: user?.email || ''
        })
      } catch (error) {
        console.error('Failed to load firm profile from Brand Assets:', error)
        // If profile doesn't exist, initialize with empty values
        setFormData(prev => ({
          ...prev,
          firmName: '',
          firmSize: '1-2',
          workEmail: '',
          phoneNumber: '',
          website: '',
          guidelines: ''
        }))
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      loadProfile()
    }
  }, [user])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const handleBack = () => {
    navigate('/dashboard')
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // Update company information - this will sync with Brand Assets since they use the same API
      const updatedProfile = await dashboardApi.updateFirmProfile({
        firm_name: formData.firmName,
        firm_size: formData.firmSize,
        work_email: formData.workEmail,
        phone_number: formData.phoneNumber,
        firm_website: formData.website,
        branding_guidelines: formData.guidelines
      })
      setFirmProfile(updatedProfile)
      alert('Company information updated successfully! Changes will be reflected in Brand Assets.')
    } catch (error) {
      console.error('Failed to update company information:', error)
      alert('Failed to update company information. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleChangeEmail = () => {
    // TODO: Implement email change functionality
    alert('Email change functionality coming soon!')
  }

  if (loading) {
    return (
      <div className="settings">
        <div className="settings-loading">Loading...</div>
      </div>
    )
  }

  return (
    <div className="settings">
      <nav className="dashboard-nav">
        <div className="nav-brand">Forma</div>
        <div className="nav-actions">
          <div className="user-menu">
            <span className="user-name">{user?.name || 'User'}</span>
            <ChevronDown size={16} className="user-arrow" />
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={18} />
          </button>
        </div>
      </nav>

      <div className="dashboard-layout">
        <aside className="dashboard-sidebar">
          <div className="sidebar-brand">
            <div className="brand-icon">📄</div>
            <div className="brand-info">
              <h3>AI Lead Magnets</h3>
              <p>Your AI Workforce</p>
            </div>
          </div>
          
          <button className="sidebar-create-btn" onClick={() => navigate('/create-lead-magnet')}>
            <Plus size={20} />
            Create Lead Magnet
          </button>

          <div className="sidebar-section">
            <h4>Navigation</h4>
            <nav className="sidebar-nav">
              <a href="/dashboard" className="nav-item">
                <FileText size={18} />
                My Lead Magnets
              </a>
              <a href="/forma-ai" className="nav-item">
                <SettingsIcon size={18} />
                Forma AI
              </a>
              <a href="/brand-assets" className="nav-item">
                <Palette size={18} />
                Brand Assets
              </a>
              <a href="/settings" className="nav-item active">
                <SettingsIcon size={18} />
                Settings
              </a>
            </nav>
          </div>
        </aside>

        <main className="settings-content">
          <button className="back-button" onClick={handleBack}>
            <ArrowLeft size={20} />
            Back to Dashboard
          </button>

          <div className="settings-header">
            <h1 className="settings-title">Personal profile</h1>
            <p className="settings-subtitle">Manage your account and company information.</p>
          </div>

          <div className="settings-form">
            <div className="settings-section">
              <label className="settings-label">Full Name</label>
              <input
                type="text"
                className="settings-input"
                value={formData.fullName}
                onChange={(e) => handleInputChange('fullName', e.target.value)}
                placeholder="Enter your full name"
              />
            </div>

            <div className="settings-section">
              <label className="settings-label">Company Information</label>
              <div className="company-info-list">
                <div className="company-info-row">
                  <span className="company-info-label">Firm:</span>
                  <input
                    type="text"
                    className="company-info-value"
                    value={formData.firmName || ''}
                    onChange={(e) => handleInputChange('firmName', e.target.value)}
                    placeholder="Firm name"
                  />
                </div>
                <div className="company-info-row">
                  <span className="company-info-label">Size:</span>
                  <select
                    className="company-info-value company-info-select"
                    value={formData.firmSize}
                    onChange={(e) => handleInputChange('firmSize', e.target.value)}
                  >
                    <option value="1-2">1-2</option>
                    <option value="3-5">3-5</option>
                    <option value="6-10">6-10</option>
                    <option value="11+">11+</option>
                  </select>
                </div>
                <div className="company-info-row">
                  <span className="company-info-label">Email:</span>
                  <input
                    type="email"
                    className="company-info-value"
                    value={formData.workEmail || ''}
                    onChange={(e) => handleInputChange('workEmail', e.target.value)}
                    placeholder="Work email"
                  />
                </div>
                <div className="company-info-row">
                  <span className="company-info-label">Phone:</span>
                  <input
                    type="tel"
                    className="company-info-value"
                    value={formData.phoneNumber || ''}
                    onChange={(e) => handleInputChange('phoneNumber', e.target.value)}
                    placeholder="Phone number"
                  />
                </div>
                <div className="company-info-row">
                  <span className="company-info-label">Website:</span>
                  <input
                    type="url"
                    className="company-info-value"
                    value={formData.website || ''}
                    onChange={(e) => handleInputChange('website', e.target.value)}
                    placeholder="Website URL"
                  />
                </div>
                <div className="company-info-row guidelines-row">
                  <span className="company-info-label">Guidelines:</span>
                  <textarea
                    className="company-info-textarea"
                    value={formData.guidelines || ''}
                    onChange={(e) => handleInputChange('guidelines', e.target.value)}
                    placeholder="Enter branding guidelines"
                    rows={4}
                  />
                </div>
              </div>
            </div>

            <div className="settings-section">
              <label className="settings-label">Using Forma for</label>
              <select
                className="settings-select"
                value={formData.usingFormaFor}
                onChange={(e) => handleInputChange('usingFormaFor', e.target.value)}
              >
                <option value="Personal Use">Personal Use</option>
                <option value="Business Use">Business Use</option>
                <option value="Team Use">Team Use</option>
              </select>
            </div>

            <div className="settings-section">
              <label className="settings-label">Email address</label>
              <div className="email-field-group">
                <input
                  type="email"
                  className="settings-input email-input"
                  value={formData.email}
                  readOnly
                />
                <button className="change-email-btn" onClick={handleChangeEmail}>
                  Change
                </button>
              </div>
            </div>

            <div className="settings-actions">
              <button className="save-btn" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default Settings

