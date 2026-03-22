import React, { useState } from 'react'
import { motion } from 'framer-motion'
import type { LeadMagnetGeneration } from '../../lib/dashboardApi'
import { dashboardApi } from '../../lib/dashboardApi'
import './LeadMagnetGenerationForm.css'

interface LeadMagnetGenerationFormProps {
  onSubmit: (data: LeadMagnetGeneration) => void
  loading?: boolean
}

const LEAD_MAGNET_TYPES = [
  { value: 'guide', label: 'Guide' },
  { value: 'case-study', label: 'Case Study' },
  { value: 'checklist', label: 'Checklist' },
  { value: 'roi-calculator', label: 'ROI Calculator' },
  { value: 'trends-report', label: 'Trends Report' },
  { value: 'onboarding-flow', label: 'Client Onboarding Flow' },
  { value: 'design-portfolio', label: 'Design Portfolio' },
  { value: 'custom', label: 'Custom' }
]

const MAIN_TOPICS = [
  { value: 'sustainable-architecture', label: 'Sustainable Architecture' },
  { value: 'smart-homes', label: 'Smart Homes' },
  { value: 'adaptive-reuse', label: 'Adaptive Reuse' },
  { value: 'wellness-biophilic', label: 'Wellness/Biophilic' },
  { value: 'modular-prefab', label: 'Modular/Prefab' },
  { value: 'urban-placemaking', label: 'Urban Placemaking' },
  { value: 'passive-house', label: 'Passive House/Net-Zero' },
  { value: 'climate-resilient', label: 'Climate-Resilient' },
  { value: 'project-roi', label: 'Project ROI' },
  { value: 'branding-differentiation', label: 'Branding & Differentiation' },
  { value: 'custom', label: 'Custom' }
]

const TARGET_AUDIENCES = [
  'Homeowners',
  'Developers', 
  'Commercial Clients',
  'Government',
  'Architects/Peers',
  'Contractors',
  'Real Estate Agents',
  'Nonprofits',
  'Facility Managers',
  'Other'
]

const PAIN_POINTS = [
  'High costs',
  'ROI uncertainty',
  'Compliance issues', 
  'Sustainability demands',
  'Risk management',
  'Long timelines',
  'Tech complexity',
  'Poor communication',
  'Competition',
  'Approvals',
  'Energy efficiency',
  'Health/Wellness',
  'Vendor reliability',
  'Other'
]

const LeadMagnetGenerationForm: React.FC<LeadMagnetGenerationFormProps> = ({ 
  onSubmit, 
  loading = false 
}) => {
  const [formData, setFormData] = useState<Partial<LeadMagnetGeneration>>({
    lead_magnet_type: 'guide',
    main_topic: 'sustainable-architecture',
    target_audience: [],
    audience_pain_points: [],
    desired_outcome: '',
    call_to_action: '',
    special_requests: ''
  })

  const [currentStep, setCurrentStep] = useState(0)
  const [slogan, setSlogan] = useState('');
  const [sloganLoading, setSloganLoading] = useState(false);
  const [sloganError, setSloganError] = useState('');

  const steps = [
    'Type & Topic',
    'Target Audience',
    'Pain Points',
    'Outcome & CTA'
  ]

  const handleInputChange = (field: keyof LeadMagnetGeneration, value: string | string[]) => {
    if (field === 'desired_outcome' || field === 'call_to_action') {
      setSloganError('')
    }
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleArrayToggle = (field: 'target_audience' | 'audience_pain_points', item: string) => {
    const current = formData[field] || []
    const updated = current.includes(item)
      ? current.filter(i => i !== item)
      : [...current, item]
    handleInputChange(field, updated)
  }

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleSubmit()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSubmit = () => {
    const desiredOutcome = formData.desired_outcome || ''
    const callToAction = formData.call_to_action || ''
    if (!desiredOutcome || desiredOutcome.trim().length < 15) {
      setSloganError('Please describe your desired outcome in at least 15 characters')
      return
    }
    if (!callToAction || callToAction.trim().length < 15) {
      setSloganError('Please describe your call to action in at least 15 characters')
      return
    }
    if (isFormValid()) {
      setSloganError('')
      onSubmit(formData as LeadMagnetGeneration)
    }
  }

  const handleGenerateSlogan = async () => {
    setSloganLoading(true);
    setSloganError('');
    try {
      const firmProfile = await dashboardApi.getFirmProfile();
      const response = await dashboardApi.generateSlogan({
        user_answers: formData as unknown as Record<string, unknown>,
        firm_profile: firmProfile as unknown as Record<string, unknown>,
      });
      setSlogan(response.slogan);
      handleInputChange('special_requests', response.slogan);
    } catch (error) {
      setSloganError('Failed to generate slogan. Please try again.');
    } finally {
      setSloganLoading(false);
    }
  };

  const isStepValid = () => {
    switch (currentStep) {
      case 0:
        return formData.lead_magnet_type && formData.main_topic
      case 1:
        return (formData.target_audience?.length || 0) > 0
      case 2:
        return (formData.audience_pain_points?.length || 0) > 0
      case 3:
        return formData.desired_outcome && formData.call_to_action
      default:
        return false
    }
  }

  const isFormValid = () => {
    return formData.lead_magnet_type &&
           formData.main_topic &&
           (formData.target_audience?.length || 0) > 0 &&
           (formData.audience_pain_points?.length || 0) > 0 &&
           formData.desired_outcome &&
           formData.call_to_action
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="form-step">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="form-group"
            >
              <label className="form-label">Lead Magnet Type *</label>
              <div className="option-grid">
                {LEAD_MAGNET_TYPES.map((type) => (
                  <label key={type.value} className={`option-card ${formData.lead_magnet_type === type.value ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="lead_magnet_type"
                      value={type.value}
                      checked={formData.lead_magnet_type === type.value}
                      onChange={(e) => handleInputChange('lead_magnet_type', e.target.value)}
                    />
                    <span className="option-label">{type.label}</span>
                  </label>
                ))}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="form-group"
            >
              <label className="form-label">Main Topic *</label>
              <div className="option-grid">
                {MAIN_TOPICS.map((topic) => (
                  <label key={topic.value} className={`option-card ${formData.main_topic === topic.value ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="main_topic"
                      value={topic.value}
                      checked={formData.main_topic === topic.value}
                      onChange={(e) => handleInputChange('main_topic', e.target.value)}
                    />
                    <span className="option-label">{topic.label}</span>
                  </label>
                ))}
              </div>
            </motion.div>
          </div>
        )

      case 1:
        return (
          <div className="form-step">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="form-group"
            >
              <label className="form-label">Target Audience (select all that apply) *</label>
              <div className="checkbox-grid">
                {TARGET_AUDIENCES.map((audience) => (
                  <label key={audience} className="checkbox-option">
                    <input
                      type="checkbox"
                      checked={(formData.target_audience || []).includes(audience)}
                      onChange={() => handleArrayToggle('target_audience', audience)}
                    />
                    <span className="checkbox-label">{audience}</span>
                  </label>
                ))}
              </div>
            </motion.div>
          </div>
        )

      case 2:
        return (
          <div className="form-step">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="form-group"
            >
              <label className="form-label">Audience Pain Points / Challenges (select all that apply) *</label>
              <div className="checkbox-grid">
                {PAIN_POINTS.map((pain) => (
                  <label key={pain} className="checkbox-option">
                    <input
                      type="checkbox"
                      checked={(formData.audience_pain_points || []).includes(pain)}
                      onChange={() => handleArrayToggle('audience_pain_points', pain)}
                    />
                    <span className="checkbox-label">{pain}</span>
                  </label>
                ))}
              </div>
            </motion.div>
          </div>
        )

      case 3:
        return (
          <div className="form-step">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="form-group"
            >
              <label className="form-label">Desired Outcome / Solution *</label>
              <textarea
                className="form-textarea"
                value={formData.desired_outcome || ''}
                onChange={(e) => handleInputChange('desired_outcome', e.target.value)}
                placeholder="Describe the main outcome or solution your lead magnet will provide..."
                rows={4}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="form-group"
            >
              <label className="form-label">Call-to-Action *</label>
              <input
                type="text"
                className="form-input"
                value={formData.call_to_action || ''}
                onChange={(e) => handleInputChange('call_to_action', e.target.value)}
                placeholder="e.g., Schedule Consultation, Download Portfolio, Get Quote"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="form-group"
            >
              <label className="form-label">Special Requests or Additional Sections</label>
              <textarea
                className="form-textarea"
                value={formData.special_requests || ''}
                onChange={(e) => handleInputChange('special_requests', e.target.value)}
                placeholder="Any specific requirements, additional sections, or customizations..."
                rows={3}
              />
              <button
                type="button"
                className="btn btn-secondary mt-2"
                onClick={handleGenerateSlogan}
                disabled={sloganLoading}
              >
                {sloganLoading ? 'Generating...' : 'Generate Slogan'}
              </button>
              {sloganError && <p className="text-red-500 text-sm mt-2">{sloganError}</p>}
            </motion.div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="lead-magnet-form">
      <div className="form-header">
        <h1 className="form-title">Create Lead Magnet</h1>
        <div className="form-progress">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
          <span className="progress-text">
            Step {currentStep + 1} of {steps.length}: {steps[currentStep]}
          </span>
        </div>
      </div>

      <div className="form-content">
        {renderStepContent()}
      </div>

      <div className="form-actions">
        {currentStep > 0 && (
          <button 
            type="button" 
            className="btn btn-secondary"
            onClick={handlePrevious}
            disabled={loading}
          >
            Previous
          </button>
        )}
        
        <button 
          type="button" 
          className="btn btn-primary"
          onClick={handleNext}
          disabled={!isStepValid() || loading}
        >
          {loading ? 'Creating...' : (currentStep === steps.length - 1 ? 'Create Lead Magnet' : 'Next')}
        </button>
      </div>
    </div>
  )
}

export default LeadMagnetGenerationForm