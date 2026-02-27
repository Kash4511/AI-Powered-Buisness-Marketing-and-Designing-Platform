import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, Download, Plus, Settings, LogOut, Palette, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { dashboardApi } from '../lib/dashboardApi'
import type { TemplateSelectionRequest } from '../lib/dashboardApi'
import LeadMagnetGenerationForm from './forms/LeadMagnetGenerationForm'
import TemplateSelectionForm from './forms/TemplateSelectionForm'
import './CreateLeadMagnet.css'
import type { LeadMagnetGeneration } from '../lib/dashboardApi';
import Modal from './Modal'

type FormStep = 'lead-magnet-generation' | 'template-selection'

const CreateLeadMagnet: React.FC = () => {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState<FormStep>('lead-magnet-generation')
  const [capturedAnswers, setCapturedAnswers] = useState<LeadMagnetGeneration & { title?: string }>(
    {} as LeadMagnetGeneration & { title?: string }
  );
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  // Removed Review & Confirm modal staging state
  const [isGenerating, setIsGenerating] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const handleBack = () => {
    setErrorMessage(null)
    setSuccessMessage(null)
    if (currentStep === 'template-selection') {
      setCurrentStep('lead-magnet-generation')
    } else {
      navigate('/dashboard')
    }
  }

  // Removed firm profile step entirely

  const humanizeTitle = (topic: string, type: string) => {
    const topicMap: Record<string, string> = {
      'sustainable-architecture': 'Sustainable Architecture',
      'smart-homes': 'Smart Homes',
      'adaptive-reuse': 'Adaptive Reuse',
      'wellness-biophilic': 'Wellness & Biophilic Design',
      'modular-prefab': 'Modular & Prefab',
      'urban-placemaking': 'Urban Placemaking',
      'passive-house': 'Passive House & Net-Zero',
      'climate-resilient': 'Climate-Resilient Design',
      'project-roi': 'Project ROI',
      'branding-differentiation': 'Branding & Differentiation',
      'custom': 'Custom Topic'
    }
    
    const typeMap: Record<string, string> = {
      'guide': 'Guide',
      'case-study': 'Case Study',
      'checklist': 'Checklist',
      'roi-calculator': 'ROI Calculator',
      'trends-report': 'Trends Report',
      'onboarding-flow': 'Client Onboarding Flow',
      'design-portfolio': 'Design Portfolio'
    }
    
    return `${topicMap[topic] || topic} ${typeMap[type] || type}`
  }

  const handleGenerationSubmit = async (data: LeadMagnetGeneration) => {
    // Just capture the data and move to template selection
    // Don't create the lead magnet yet
    setCapturedAnswers({
      ...data,
      title: humanizeTitle(data.main_topic, data.lead_magnet_type)
    })
    setCurrentStep('template-selection')
  }

  const fileToDataUrl = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const toTitleCase = (s?: string) => (s || '').replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());

  // Removed preflight analyzeQuality in favor of streamlined flow

  const handleTemplateSubmit = async (templateId: string, templateName: string, architecturalImages?: File[]) => {
    // Directly create the lead magnet and generate the PDF, no review modal
    if (loading || isGenerating) return
    setLoading(true)
    setErrorMessage(null)
    setSuccessMessage(null)
    try {
      const generationData: LeadMagnetGeneration = {
        main_topic: capturedAnswers.main_topic,
        lead_magnet_type: capturedAnswers.lead_magnet_type,
        target_audience: capturedAnswers.target_audience,
        audience_pain_points: capturedAnswers.audience_pain_points,
        desired_outcome: capturedAnswers.desired_outcome,
        call_to_action: capturedAnswers.call_to_action,
        special_requests: capturedAnswers.special_requests,
      }

      const professionalTitle = (capturedAnswers.title && capturedAnswers.title.trim()) 
        || `The ${toTitleCase(String(capturedAnswers.main_topic || 'Architectural'))} ${toTitleCase(String(capturedAnswers.lead_magnet_type || 'Guide'))}`;

      const leadMagnet = await dashboardApi.createLeadMagnetWithData({
        title: professionalTitle,
        generation_data: generationData,
      })

      setSuccessMessage('Lead magnet created. Saving template selection...')

      const selectionRequest: TemplateSelectionRequest = {
        lead_magnet_id: leadMagnet.id,
        template_id: templateId,
        template_name: templateName,
        template_thumbnail: architecturalImages && architecturalImages.length > 0 ? architecturalImages[0].name : undefined,
        captured_answers: capturedAnswers as unknown as Record<string, unknown>,
        source: 'create-lead-magnet'
      }

      await dashboardApi.selectTemplate(selectionRequest)
      setSuccessMessage('Template selected. Generating PDF with AI...')

      try {
        const architecturalImageDataUrls = architecturalImages && architecturalImages.length > 0 
          ? await Promise.all(architecturalImages.slice(0,6).map(fileToDataUrl))
          : [];
        setIsGenerating(true)
        await dashboardApi.generatePDFWithAI({
          template_id: templateId,
          lead_magnet_id: leadMagnet.id,
          use_ai_content: true,
          user_answers: capturedAnswers as unknown as Record<string, unknown>,
          architectural_images: architecturalImageDataUrls
        })
        setSuccessMessage('PDF generated and downloaded')
      } catch (pdfError) {
        const e = pdfError as { message?: string }
        setErrorMessage(typeof e.message === 'string' ? e.message : 'PDF generation failed')
      }

    } catch (err: unknown) {
      console.error('Failed to create lead magnet with template:', err)
      const msg = (typeof (err as { message?: unknown }).message === 'string')
        ? ((err as { message?: string }).message as string)
        : 'Failed to create lead magnet. Please review inputs and try again.'
      setErrorMessage(msg)
    } finally {
      setIsGenerating(false)
      setLoading(false)
    }
  }

  // Removed legacy proceedAfterConfirm flow in favor of direct submission

  return (
    <div className="create-lead-magnet">
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
          
          <button className="sidebar-create-btn active">
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
              <a href="/brand-assets" className="nav-item">
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

        <main className="create-content">
          <div className="create-header">
            <button className="back-button" onClick={handleBack}>
              <ArrowLeft size={20} />
              Back
            </button>
            
            <div className="step-indicator">
              <div className={`step ${currentStep === 'lead-magnet-generation' ? 'active' : currentStep === 'template-selection' ? 'completed' : ''}`}>
                1. Lead Magnet Details
              </div>
              <div className={`step ${currentStep === 'template-selection' ? 'active' : ''}`}>
                2. Choose Template
              </div>
            </div>

            {errorMessage && (
              <div className="status-message error" style={{ marginTop: '8px', color: '#b00020' }}>{errorMessage}</div>
            )}
            {successMessage && (
              <div className="status-message success" style={{ marginTop: '8px', color: '#0b7a0b' }}>{successMessage}</div>
            )}
          </div>

          <div className="form-container">
            {currentStep === 'lead-magnet-generation' && (
              <LeadMagnetGenerationForm
                onSubmit={handleGenerationSubmit}
                loading={loading}
              />
            )}

            {currentStep === 'template-selection' && (
  <TemplateSelectionForm
    onSubmit={handleTemplateSubmit}
    onClose={handleBack}
    loading={loading || isGenerating}
  />
)}

          </div>
        </main>
      </div>
      <Modal 
        isOpen={showPreviewModal}
        onClose={() => {
          setShowPreviewModal(false)
          if (previewUrl) { window.URL.revokeObjectURL(previewUrl); setPreviewUrl(null) }
        }}
        title="PDF Preview"
        maxWidth={1200}
      >
        {previewUrl ? (
          <div className="pdf-preview-container">
            <div className="pdf-preview-header">
              <div className="pdf-preview-title">
                <FileText size={20} />
                <span>Lead Magnet Preview</span>
              </div>
              <div className="pdf-preview-actions">
                <button
                  className="pdf-preview-btn pdf-download-btn"
                  onClick={() => {
                    if (previewUrl) {
                      const link = document.createElement('a')
                      link.href = previewUrl
                      link.setAttribute('download', 'lead-magnet.pdf')
                      document.body.appendChild(link)
                      link.click()
                      link.remove()
                    }
                  }}
                >
                  <Download size={16} />
                  Download PDF
                </button>
                <button
                  className="pdf-preview-btn pdf-close-btn"
                  onClick={() => {
                    setShowPreviewModal(false)
                    if (previewUrl) { window.URL.revokeObjectURL(previewUrl); setPreviewUrl(null) }
                  }}
                >
                  <X size={16} />
                  Close
                </button>
              </div>
            </div>
            <div className="pdf-preview-content">
              <iframe 
                title="Lead Magnet Preview" 
                src={previewUrl} 
                className="pdf-preview-iframe"
              />
            </div>
          </div>
        ) : (
          <div className="pdf-preview-loading">
            <div className="loading-spinner"></div>
            <p>Generating PDF preview...</p>
          </div>
        )}
      </Modal>

      {/* Review & Confirm modal removed as requested */}
    </div>
  )
}

export default CreateLeadMagnet
