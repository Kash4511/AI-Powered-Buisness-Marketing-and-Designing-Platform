import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, FileText, Download, Plus, Settings, LogOut, Palette, Upload, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useBrand } from '../contexts/BrandContext'
import { dashboardApi } from '../lib/dashboardApi'
import type { FirmProfile } from '../lib/dashboardApi'
import './BrandAssets.css'

const FONT_STYLES = [
  { value: 'modern-sans', label: 'Modern Sans-Serif' },
  { value: 'classic-serif', label: 'Classic Serif' },
  { value: 'creative', label: 'Creative/Display' },
  { value: 'no-preference', label: 'No Preference' }
]

const INDUSTRY_SPECIALTIES = [
  'Residential',
  'Commercial', 
  'Mixed Practice',
  'Sustainable/Green',
  'Educational/Civic',
  'Hospitality',
  'Healthcare',
  'Interiors',
  'Urban Design',
  'Other'
];

const FIRM_SIZE_OPTIONS = [
  { value: '1-2', label: '1–2' },
  { value: '3-5', label: '3–5' },
  { value: '6-10', label: '6–10' },
  { value: '11+', label: '11+' }
];


type FormStep = 'firm-profile' | 'brand-assets';

const BrandAssets: React.FC = () => {
  const { logout } = useAuth()
  const { brandColors, updateBrandColors } = useBrand()
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState<FormStep>('firm-profile');
  const [formData, setFormData] = useState<Partial<FirmProfile>>({
    primary_brand_color: brandColors.primaryColor,
    secondary_brand_color: brandColors.secondaryColor,
    preferred_font_style: brandColors.fontStyle,
    branding_guidelines: ''
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [hasExistingAssets, setHasExistingAssets] = useState(false)
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const handleBack = () => {
    if (currentStep === 'brand-assets') {
      setCurrentStep('firm-profile');
    } else {
      navigate('/dashboard');
    }
  };

  // Load existing brand assets
  useEffect(() => {
    const loadBrandAssets = async () => {
      try {
        setLoading(true)
        const profile = await dashboardApi.getFirmProfile()
        if (profile) {
          setFormData({
            firm_name: profile.firm_name || '',
            work_email: profile.work_email || '',
            phone_number: profile.phone_number || '',
            firm_website: profile.firm_website || '',
            firm_size: profile.firm_size || '1-2',
            industry_specialties: profile.industry_specialties || [],
            location: profile.location || '',
            primary_brand_color: profile.primary_brand_color || '#2a5766',
            secondary_brand_color: profile.secondary_brand_color || '#ffffff', 
            preferred_font_style: profile.preferred_font_style || 'no-preference',
            branding_guidelines: profile.branding_guidelines || ''
          });
          if (profile.logo) {
            setLogoPreview(typeof profile.logo === 'string' ? profile.logo : null);
          }
          if (profile.primary_brand_color || profile.branding_guidelines) {
            setHasExistingAssets(true)
          }
        }
      } catch {
        console.log('No existing brand assets found')
      } finally {
        setLoading(false)
      }
    }

    loadBrandAssets()
  }, [])

  const handleInputChange = (field: keyof FirmProfile, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validation
    const validTypes = ['image/jpeg', 'image/png', 'image/svg+xml'];
    if (!validTypes.includes(file.type)) {
      setFormErrors(['Invalid file type. Please upload JPG, PNG, or SVG.']);
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      setFormErrors(['File too large. Maximum size is 2MB.']);
      return;
    }

    handleInputChange('logo', file);
    setFormErrors([]);

    // Preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setLogoPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const removeLogo = () => {
    handleInputChange('logo', null);
    setLogoPreview(null);
  };

  const handleSpecialtyToggle = (specialty: string) => {
    const current = formData.industry_specialties || []
    const updated = current.includes(specialty)
      ? current.filter(s => s !== specialty)
      : [...current, specialty]
    handleInputChange('industry_specialties', updated)
  }

  const handleNextStep = () => {
    if (currentStep === 'firm-profile') {
      setCurrentStep('brand-assets');
    }
  };

  const handleSave = async () => {
    const validatedData = { ...formData };
    
    // Ensure firm_website has protocol if provided
    if (validatedData.firm_website && typeof validatedData.firm_website === 'string') {
      const url = validatedData.firm_website.trim();
      if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
        validatedData.firm_website = `https://${url}`;
      }
    }

    if (!validateForm(validatedData)) {
      return;
    }
    setSaving(true)
    try {
      await dashboardApi.updateFirmProfile(validatedData)
      setHasExistingAssets(true)
      updateBrandColors({
        primaryColor: validatedData.primary_brand_color || '#2a5766',
        secondaryColor: validatedData.secondary_brand_color || '#ffffff', 
        fontStyle: validatedData.preferred_font_style || 'no-preference'
      })
      setShowConfirmation(true);
    } catch (err) {
      console.error('Failed to save brand assets:', err)
    } finally {
      setSaving(false)
    }
  }

  const validateForm = (data: Partial<FirmProfile> = formData): boolean => {
    const errors: string[] = [];
    const hex = /^#([A-Fa-f0-9]{6})$/;
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    // URL regex that expects a protocol
    const urlRe = /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([/\w .-]*)*\/?$/;

    if (!data.firm_name) errors.push('Firm name is required');
    if (!data.work_email) {
      errors.push('Work email is required');
    } else if (!emailRe.test(String(data.work_email).trim())) {
      errors.push('Work email must be a valid email address');
    }
    
    if (data.firm_website && !urlRe.test(String(data.firm_website).trim())) {
      errors.push('Firm website must be a valid URL');
    }

    // phone_number is optional in the model, so we'll make it optional here too
    if (data.phone_number && data.phone_number.length > 20) {
      errors.push('Phone number is too long');
    }
    
    if (!data.primary_brand_color || !hex.test(data.primary_brand_color)) errors.push('Primary color must be a valid hex like #2a5766');
    if (!data.secondary_brand_color || !hex.test(data.secondary_brand_color)) errors.push('Secondary color must be a valid hex like #ffffff');
    setFormErrors(errors);
    return errors.length === 0;
  };

  const handleSaveAndContinue = async () => {
    const validatedData = { ...formData };
    
    // Ensure firm_website has protocol if provided
    if (validatedData.firm_website && typeof validatedData.firm_website === 'string') {
      const url = validatedData.firm_website.trim();
      if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
        validatedData.firm_website = `https://${url}`;
      }
    }

    if (!validateForm(validatedData)) {
      return;
    }
    try {
      // Save profile first
      await dashboardApi.updateFirmProfile(validatedData);
      updateBrandColors({
        primaryColor: validatedData.primary_brand_color || '#2a5766',
        secondaryColor: validatedData.secondary_brand_color || '#ffffff',
        fontStyle: validatedData.preferred_font_style || 'no-preference'
      });
      // Continue to Create Lead Magnet without showing preview here
      navigate('/create-lead-magnet');
    } catch (err) {
      console.error('Failed during Save & Continue:', err);
      setFormErrors(['Save failed. Please review your inputs and try again.']);
    }
  };

  if (loading) {
    return (
      <div className="brand-assets">
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#ffffff' }}>
          Loading brand assets...
        </div>
      </div>
    )
  }

  return (
    <div className="brand-assets">
      <nav className="dashboard-nav">
        <div className="nav-brand">Forma</div>
        <div className="nav-actions">
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
                <Settings size={18} />
                Forma AI
              </a>
              <a href="#" className="nav-item active">
                <Palette size={18} />
                Brand Assets
              </a>
              <a href="/settings" className="nav-item">
                <Settings size={18} />
                Settings
              </a>
            </nav>
          </div>

        </aside>

        <main className="brand-content">
          <div className="brand-header">
            <button className="back-button" onClick={handleBack}>
              <ArrowLeft size={20} />
              Back to Dashboard
            </button>
            
            <div className="brand-title-section">
              <h1 className="brand-main-title">Brand Assets</h1>
              <p className="brand-subtitle">
                Set up your brand colors, fonts, and guidelines. These will be applied to all your lead magnets.
              </p>
            </div>
          </div>

          <div className="brand-form-container">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="brand-form"
            >
              {currentStep === 'firm-profile' && (
                <div className="form-section">
                  <h2 className="section-title">Firm Information</h2>
                  
                  <div className="form-group">
                    <label className="form-label">Firm Logo</label>
                    <div className="logo-upload-container">
                      {logoPreview ? (
                        <div className="logo-preview-wrapper">
                          <img src={logoPreview} alt="Logo Preview" className="logo-preview-img" />
                          <button className="remove-logo-btn" onClick={removeLogo}>
                            <X size={14} />
                          </button>
                        </div>
                      ) : (
                        <label className="logo-upload-placeholder">
                          <Upload size={24} />
                          <span>Upload Logo</span>
                          <input
                            type="file"
                            className="hidden-file-input"
                            onChange={handleLogoChange}
                            accept=".jpg,.jpeg,.png,.svg"
                          />
                        </label>
                      )}
                    </div>
                    <p className="field-description">Supported: JPG, PNG, SVG (Max 2MB). Recommended: 150x50px</p>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Firm Name *</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.firm_name || ''}
                      onChange={(e) => handleInputChange('firm_name', e.target.value)}
                      placeholder="Enter your firm name"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Work Email *</label>
                    <input
                      type="email"
                      className="form-input"
                      value={formData.work_email || ''}
                      onChange={(e) => handleInputChange('work_email', e.target.value)}
                      placeholder="your@company.com"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Phone Number</label>
                    <input
                      type="tel"
                      className="form-input"
                      value={formData.phone_number || ''}
                      onChange={(e) => handleInputChange('phone_number', e.target.value)}
                      placeholder="+1 (555) 123-4567"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Firm Website</label>
                    <input
                      type="url"
                      className="form-input"
                      value={formData.firm_website || ''}
                      onChange={(e) => handleInputChange('firm_website', e.target.value)}
                      placeholder="https://www.yourfirm.com"
                    />
                  </div>
                  <div className="form-actions">
                    <button 
                      type="button" 
                      className="btn btn-primary"
                      onClick={handleNextStep}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}

              {currentStep === 'brand-assets' && (
                <>
                  <div className="form-section">
                    <h2 className="section-title">Brand Colors</h2>
                    
                    <div className="form-group">
                      <label className="form-label">Primary Brand Color</label>
                      <div className="color-input-group">
                        <input
                          type="color"
                          className="color-input"
                          value={formData.primary_brand_color || '#2a5766'}
                          onChange={(e) => handleInputChange('primary_brand_color', e.target.value)}
                        />
                        <input
                          type="text"
                          className="form-input color-text"
                          value={formData.primary_brand_color || ''}
                          onChange={(e) => handleInputChange('primary_brand_color', e.target.value)}
                          placeholder="#2a5766"
                        />
                      </div>
                      <p className="field-description">Used for headings, accents, and call-to-action elements</p>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Secondary Brand Color</label>
                      <div className="color-input-group">
                        <input
                          type="color"
                          className="color-input"
                          value={formData.secondary_brand_color || '#ffffff'}
                          onChange={(e) => handleInputChange('secondary_brand_color', e.target.value)}
                        />
                        <input
                          type="text"
                          className="form-input color-text"
                          value={formData.secondary_brand_color || ''}
                          onChange={(e) => handleInputChange('secondary_brand_color', e.target.value)}
                          placeholder="#ffffff"
                        />
                      </div>
                      <p className="field-description">Used for backgrounds and complementary elements</p>
                    </div>
                  </div>

                  <div className="form-section">
                    <h2 className="section-title">Typography</h2>
                    
                    <div className="form-group">
                      <label className="form-label">Preferred Font Style</label>
                      <select
                        className="form-select"
                        value={formData.preferred_font_style || 'no-preference'}
                        onChange={(e) => handleInputChange('preferred_font_style', e.target.value)}
                      >
                        {FONT_STYLES.map((font) => (
                          <option key={font.value} value={font.value}>
                            {font.label}
                          </option>
                        ))}
                      </select>
                      <p className="field-description">The font style that best represents your brand</p>
                    </div>
                  </div>

                  <div className="form-section">
                    <h2 className="section-title">Brand Guidelines</h2>
                    
                    <div className="form-group">
                      <label className="form-label">Additional Branding Guidelines</label>
                      <textarea
                        className="form-textarea"
                        value={formData.branding_guidelines || ''}
                        onChange={(e) => handleInputChange('branding_guidelines', e.target.value)}
                        placeholder="Any specific branding requirements, style guides, tone of voice, or design preferences..."
                        rows={6}
                      />
                      <p className="field-description">Describe your brand personality, tone, and any specific design requirements</p>
                    </div>
                  </div>

                  <div className="form-actions">
                    <button 
                      type="button" 
                      className="btn btn-primary"
                      onClick={handleSave}
                      disabled={saving}
                    >
                      {saving ? 'Saving...' : (hasExistingAssets ? 'Update Brand Assets' : 'Save Brand Assets')}
                    </button>
                    <button 
                      type="button" 
                      className="btn btn-secondary"
                      onClick={handleSaveAndContinue}
                      disabled={saving}
                      style={{ marginLeft: '12px' }}
                    >
                      Save and Continue
                    </button>
                  </div>
                </>
              )}
            </motion.div>
          </div>
        </main>
      </div>
      {formErrors.length > 0 && (
        <div className="error-banner">
          {formErrors.map((e, i) => (<div key={i}>{e}</div>))}
        </div>
      )}
      {showConfirmation && (
        <div className="confirmation-modal">
          <div className="confirmation-content">
            <h2>Success!</h2>
            <p>Your brand assets have been saved.</p>
            <button onClick={() => setShowConfirmation(false)}>Close</button>
          </div>
        </div>
      )}
      
    </div>
  )
}

export default BrandAssets