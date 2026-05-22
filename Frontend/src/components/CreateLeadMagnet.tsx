import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, Plus, Settings, LogOut, Palette, Download, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { dashboardApi } from '../lib/dashboardApi'
import type { TemplateSelectionRequest, LeadMagnetGeneration } from '../lib/dashboardApi'
import LeadMagnetGenerationForm from './forms/LeadMagnetGenerationForm'
import TemplateSelectionForm from './forms/TemplateSelectionForm'
import Modal from './Modal'

/* ─────────────────────────────────────────────
   DESIGN TOKENS — mirrors the Forma landing page
───────────────────────────────────────────── */
const T = {
  bg:   '#ffffff',
  bg2:  '#f7f7f5',
  bg3:  '#f0f0ec',
  dark: '#0a0a0a',
  bd:   'rgba(0,0,0,0.08)',
  bd2:  'rgba(0,0,0,0.15)',
  t1:   '#111111',
  t2:   '#666666',
  t3:   '#aaaaaa',
} as const

/* ─────────────────────────────────────────────
   FONT + GLOBAL STYLES
───────────────────────────────────────────── */
const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
    @keyframes spin { to { transform:rotate(360deg); } }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
    .clm-nav-item { display:flex; align-items:center; gap:9px; padding:9px 10px; border-radius:8px; font-size:0.82rem; font-weight:500; color:${T.t2}; text-decoration:none; cursor:pointer; transition:all 0.15s; font-family:'Instrument Sans',sans-serif; }
    .clm-nav-item:hover { background:${T.bg2}; color:${T.t1}; }
    .clm-nav-item:hover svg { color:${T.t1} !important; }
    .clm-nav-item.active-link { background:${T.bg2}; color:${T.t1}; font-weight:600; }
    .clm-step-pill { display:inline-flex; align-items:center; gap:7px; padding:7px 14px; border-radius:20px; font-family:'Instrument Sans',sans-serif; font-size:0.78rem; font-weight:500; transition:all 0.2s; cursor:default; }
    .clm-step-pill.idle { background:${T.bg2}; color:${T.t3}; border:1px solid ${T.bd}; }
    .clm-step-pill.active { background:${T.dark}; color:#fff; border:1px solid ${T.dark}; }
    .clm-step-pill.done { background:${T.bg2}; color:${T.t2}; border:1px solid ${T.bd}; }
    .clm-back-btn { display:inline-flex; align-items:center; gap:6px; background:none; border:1px solid ${T.bd}; border-radius:8px; padding:7px 14px; font-family:'Instrument Sans',sans-serif; font-size:0.78rem; font-weight:500; color:${T.t2}; cursor:pointer; transition:all 0.2s; }
    .clm-back-btn:hover { border-color:${T.bd2}; color:${T.t1}; background:${T.bg2}; }
    .clm-logout-btn { display:flex; align-items:center; gap:6px; background:none; border:1px solid ${T.bd}; border-radius:8px; padding:7px 14px; font-family:'Instrument Sans',sans-serif; font-size:0.78rem; font-weight:500; color:${T.t2}; cursor:pointer; transition:all 0.2s; }
    .clm-logout-btn:hover { border-color:${T.bd2}; color:${T.t1}; background:${T.bg2}; }
    .clm-sidebar-create { display:flex; align-items:center; justify-content:center; gap:8px; width:100%; padding:11px 14px; background:${T.dark}; color:#fff; border:none; border-radius:10px; font-family:'Instrument Sans',sans-serif; font-size:0.82rem; font-weight:600; cursor:pointer; transition:all 0.2s; }
    .clm-sidebar-create:hover { background:#2a2a2a; transform:translateY(-1px); box-shadow:0 6px 20px rgba(0,0,0,0.15); }
    .clm-sidebar-create.active-create { background:${T.bg2}; color:${T.t1}; border:1px solid ${T.bd2}; }
    .clm-pdf-dl-btn { display:inline-flex; align-items:center; gap:7px; padding:9px 18px; background:${T.dark}; color:#fff; border:none; border-radius:9px; font-family:'Instrument Sans',sans-serif; font-size:0.82rem; font-weight:600; cursor:pointer; transition:all 0.2s; }
    .clm-pdf-dl-btn:hover { background:#2a2a2a; }
    .clm-pdf-close-btn { display:inline-flex; align-items:center; gap:7px; padding:9px 16px; background:none; border:1px solid ${T.bd2}; border-radius:9px; font-family:'Instrument Sans',sans-serif; font-size:0.82rem; font-weight:500; color:${T.t2}; cursor:pointer; transition:all 0.2s; }
    .clm-pdf-close-btn:hover { border-color:rgba(0,0,0,0.25); color:${T.t1}; background:${T.bg2}; }
  `}</style>
)

type FormStep = 'lead-magnet-generation' | 'template-selection'

const CreateLeadMagnet: React.FC = () => {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [currentStep, setCurrentStep]         = useState<FormStep>('lead-magnet-generation')
  const [capturedAnswers, setCapturedAnswers] = useState<LeadMagnetGeneration & { title?: string }>({} as LeadMagnetGeneration & { title?: string })
  const [loading, setLoading]                 = useState(false)
  const [errorMessage, setErrorMessage]       = useState<string | null>(null)
  const [successMessage, setSuccessMessage]   = useState<string | null>(null)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [previewUrl, setPreviewUrl]           = useState<string | null>(null)
  const [isGenerating, setIsGenerating]       = useState(false)
  const [activeNav, setActiveNav]             = useState('create')

  const handleLogout = () => { logout(); navigate('/') }

  const handleBack = () => {
    setErrorMessage(null); setSuccessMessage(null)
    if (currentStep === 'template-selection') setCurrentStep('lead-magnet-generation')
    else navigate('/dashboard')
  }

  const humanizeTitle = (topic: string, type: string) => {
    const topicMap: Record<string, string> = {
      'sustainable-architecture':'Sustainable Architecture','smart-homes':'Smart Homes',
      'adaptive-reuse':'Adaptive Reuse','wellness-biophilic':'Wellness & Biophilic Design',
      'modular-prefab':'Modular & Prefab','urban-placemaking':'Urban Placemaking',
      'passive-house':'Passive House & Net-Zero','climate-resilient':'Climate-Resilient Design',
      'project-roi':'Project ROI','branding-differentiation':'Branding & Differentiation','custom':'Custom Topic',
    }
    const typeMap: Record<string, string> = {
      'guide':'Guide','case-study':'Case Study','checklist':'Checklist',
      'roi-calculator':'ROI Calculator','trends-report':'Trends Report',
      'onboarding-flow':'Client Onboarding Flow','design-portfolio':'Design Portfolio',
    }
    return `${topicMap[topic] || topic} ${typeMap[type] || type}`
  }

  const toTitleCase = (s?: string) =>
    (s || '').replace(/\w\S*/g, w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())

  const fileToDataUrl = (file: File): Promise<string> =>
    new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result as string); r.onerror = rej; r.readAsDataURL(file) })

  const handleGenerationSubmit = async (data: LeadMagnetGeneration) => {
    setCapturedAnswers({ ...data, title: humanizeTitle(data.main_topic, data.lead_magnet_type) })
    setCurrentStep('template-selection')
  }

  const handleTemplateSubmit = async (templateId: string, templateName: string, architecturalImages?: File[]) => {
    if (loading || isGenerating) return
    setLoading(true); setErrorMessage(null); setSuccessMessage(null)
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
      const professionalTitle = (capturedAnswers.title?.trim()) ||
        `The ${toTitleCase(String(capturedAnswers.main_topic || 'Architectural'))} ${toTitleCase(String(capturedAnswers.lead_magnet_type || 'Guide'))}`

      const leadMagnet = await dashboardApi.createLeadMagnetWithData({ title: professionalTitle, generation_data: generationData })
      setSuccessMessage('Lead magnet created. Saving template selection…')

      const selectionRequest: TemplateSelectionRequest = {
        lead_magnet_id: leadMagnet.id, template_id: templateId, template_name: templateName,
        template_thumbnail: architecturalImages?.[0]?.name,
        captured_answers: capturedAnswers as unknown as Record<string, unknown>,
        source: 'create-lead-magnet',
      }
      await dashboardApi.selectTemplate(selectionRequest)
      setSuccessMessage('Template selected. Generating PDF with AI…')

      try {
        const imgs = architecturalImages?.length
          ? await Promise.all(architecturalImages.slice(0, 6).map(fileToDataUrl)) : []
        setIsGenerating(true)
        await dashboardApi.generatePDFWithAI({ template_id: templateId, lead_magnet_id: leadMagnet.id, use_ai_content: true, user_answers: capturedAnswers as unknown as Record<string, unknown>, architectural_images: imgs })
        setSuccessMessage('PDF generated and downloaded')
      } catch (pdfError) {
        const e = pdfError as { message?: string }
        setErrorMessage(typeof e.message === 'string' ? e.message : 'PDF generation failed')
      }
    } catch (err: unknown) {
      const msg = typeof (err as { message?: unknown }).message === 'string'
        ? (err as { message: string }).message
        : 'Failed to create lead magnet. Please review inputs and try again.'
      setErrorMessage(msg)
    } finally { setIsGenerating(false); setLoading(false) }
  }

  /* ── SIDEBAR NAV ── */
  const navItems = [
    { id:'magnets',  label:'My Lead Magnets', icon:<FileText size={16} />,  href:'/dashboard' },
    { id:'ai',       label:'Forma AI',        icon:<Settings size={16} />,  href:'/forma-ai' },
    { id:'brand',    label:'Brand Assets',    icon:<Palette size={16} />,   href:'/brand-assets' },
    { id:'settings', label:'Settings',        icon:<Settings size={16} />,  href:'/settings' },
  ]

  /* ── STEP CONFIG ── */
  const steps: { id: FormStep; label: string; num: number }[] = [
    { id:'lead-magnet-generation', label:'Lead Magnet Details', num:1 },
    { id:'template-selection',     label:'Choose Template',     num:2 },
  ]

  const stepStatus = (id: FormStep) => {
    if (id === currentStep) return 'active'
    const currentIdx = steps.findIndex(s => s.id === currentStep)
    const thisIdx    = steps.findIndex(s => s.id === id)
    return thisIdx < currentIdx ? 'done' : 'idle'
  }

  return (
    <>
      <GlobalStyles />

      {/* ════════ NAV ════════ */}
      <nav style={{
        height:62, display:'flex', alignItems:'center', justifyContent:'space-between',
        padding:'0 36px', background:'#fff', borderBottom:`1px solid ${T.bd}`,
        position:'sticky', top:0, zIndex:100,
      }}>
        <div style={{ fontFamily:"'Fraunces',serif", fontWeight:900, fontSize:'1.35rem', color:T.dark, letterSpacing:'-0.5px' }}>
          Forma.
        </div>

        {/* Step progress in nav center */}
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          {steps.map((s, i) => {
            const status = stepStatus(s.id)
            return (
              <React.Fragment key={s.id}>
                <span className={`clm-step-pill ${status}`}>
                  {status === 'done'
                    ? <span style={{ width:16, height:16, borderRadius:'50%', background:T.t2, color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontSize:9, fontWeight:700, flexShrink:0 }}>✓</span>
                    : <span style={{ width:16, height:16, borderRadius:'50%', background: status === 'active' ? 'rgba(255,255,255,0.2)' : T.bg3, display:'flex', alignItems:'center', justifyContent:'center', fontSize:9, fontWeight:700, flexShrink:0, color: status === 'active' ? '#fff' : T.t3 }}>{s.num}</span>
                  }
                  {s.label}
                </span>
                {i < steps.length - 1 && (
                  <div style={{ width:20, height:1, background: stepStatus(steps[i+1].id) !== 'idle' ? T.bd2 : T.bd }} />
                )}
              </React.Fragment>
            )
          })}
        </div>

        <button className="clm-logout-btn" onClick={handleLogout}>
          <LogOut size={14} />
          Log out
        </button>
      </nav>

      {/* ════════ BODY ════════ */}
      <div style={{ display:'grid', gridTemplateColumns:'228px 1fr', minHeight:'calc(100vh - 62px)', fontFamily:"'Instrument Sans',sans-serif" }}>

        {/* ── SIDEBAR ── */}
        <aside style={{
          background:'#fff', borderRight:`1px solid ${T.bd}`,
          padding:'28px 16px', display:'flex', flexDirection:'column', gap:28,
          position:'sticky', top:62, height:'calc(100vh - 62px)', overflowY:'auto',
        }}>
          {/* Brand block */}
          <div style={{ display:'flex', alignItems:'center', gap:11, padding:'0 4px' }}>
            <div style={{ width:34, height:34, background:T.dark, borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
              <FileText size={15} color="#fff" />
            </div>
            <div>
              <div style={{ fontFamily:"'Fraunces',serif", fontSize:'0.82rem', fontWeight:700, color:T.t1, letterSpacing:'-0.2px', lineHeight:1.2 }}>AI Lead Magnets</div>
              <div style={{ fontSize:'0.68rem', color:T.t3, lineHeight:1 }}>Your AI Workforce</div>
            </div>
          </div>

          {/* Create (active state) */}
          <button className="clm-sidebar-create active-create">
            <Plus size={16} />
            Create Lead Magnet
          </button>

          {/* Nav */}
          <div>
            <div style={{ fontSize:'0.62rem', fontWeight:600, letterSpacing:'2.5px', textTransform:'uppercase', color:T.t3, padding:'0 8px', marginBottom:6 }}>
              Navigation
            </div>
            <nav style={{ display:'flex', flexDirection:'column', gap:2 }}>
              {navItems.map(item => (
                <a
                  key={item.id}
                  href={item.href}
                  className="clm-nav-item"
                  onClick={e => { e.preventDefault(); navigate(item.href) }}
                >
                  {item.icon}
                  {item.label}
                </a>
              ))}
            </nav>
          </div>

          {/* Bottom hint */}
          <div style={{ marginTop:'auto' }}>
            <div style={{ height:1, background:T.bd, marginBottom:16 }} />
            <div style={{ background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:10, padding:'14px' }}>
              <div style={{ fontSize:'0.72rem', fontWeight:600, color:T.t1, marginBottom:4 }}>
                {currentStep === 'lead-magnet-generation' ? 'Step 1 of 2' : 'Step 2 of 2'}
              </div>
              <div style={{ fontSize:'0.7rem', color:T.t3, lineHeight:1.5 }}>
                {currentStep === 'lead-magnet-generation'
                  ? 'Tell us about your audience and goals to generate the right content.'
                  : 'Pick a format that best fits your lead generation strategy.'}
              </div>
            </div>
          </div>
        </aside>

        {/* ── MAIN ── */}
        <main style={{ padding:'40px 52px', background:T.bg2, minHeight:'calc(100vh - 62px)' }}>

          {/* Page header */}
          <div style={{ marginBottom:32 }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:20 }}>
              <button className="clm-back-btn" onClick={handleBack}>
                <ArrowLeft size={14} />
                {currentStep === 'template-selection' ? 'Back to Details' : 'Back to Dashboard'}
              </button>

              {/* Inline step indicator */}
              <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                {steps.map((s, i) => {
                  const status = stepStatus(s.id)
                  return (
                    <React.Fragment key={s.id}>
                      <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                        <div style={{
                          width:22, height:22, borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center',
                          fontSize:'0.65rem', fontWeight:700, flexShrink:0,
                          background: status === 'active' ? T.dark : status === 'done' ? T.bg3 : T.bg3,
                          color:       status === 'active' ? '#fff'  : status === 'done' ? T.t2  : T.t3,
                          border:      status === 'active' ? 'none' : `1px solid ${T.bd}`,
                        }}>
                          {status === 'done' ? '✓' : s.num}
                        </div>
                        <span style={{ fontSize:'0.75rem', fontWeight: status === 'active' ? 600 : 400, color: status === 'active' ? T.t1 : T.t3 }}>
                          {s.label}
                        </span>
                      </div>
                      {i < steps.length - 1 && (
                        <div style={{ width:24, height:1, background:T.bd, margin:'0 2px' }} />
                      )}
                    </React.Fragment>
                  )
                })}
              </div>
            </div>

            <div>
              <div style={{ display:'inline-flex', alignItems:'center', gap:7, background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:20, padding:'4px 13px 4px 9px', fontSize:'0.7rem', fontWeight:600, color:T.t2, letterSpacing:'0.5px', marginBottom:14 }}>
                <span style={{ width:6, height:6, borderRadius:'50%', background:T.dark }} />
                {currentStep === 'lead-magnet-generation' ? 'Step 1 — Lead Magnet Details' : 'Step 2 — Choose Template'}
              </div>
              <h1 style={{ fontFamily:"'Fraunces',serif", fontSize:'2rem', fontWeight:900, color:T.dark, letterSpacing:'-1px', lineHeight:1.05, marginBottom:6 }}>
                {currentStep === 'lead-magnet-generation'
                  ? <>Describe your <em style={{ fontStyle:'italic', color:T.t3 }}>audience.</em></>
                  : <>Choose your <em style={{ fontStyle:'italic', color:T.t3 }}>format.</em></>}
              </h1>
              <p style={{ fontSize:'0.88rem', color:T.t2 }}>
                {currentStep === 'lead-magnet-generation'
                  ? 'Tell us your topic, audience, pain points and goals. Takes less than 2 minutes.'
                  : 'Pick the format that best suits your lead generation strategy.'}
              </p>
            </div>

            {/* Status messages */}
            {(errorMessage || successMessage) && (
              <div style={{ marginTop:16, display:'flex', flexDirection:'column', gap:8 }}>
                {errorMessage && (
                  <div style={{ display:'flex', alignItems:'flex-start', gap:10, background:'#fff2f2', border:'1px solid rgba(200,50,50,0.15)', borderRadius:10, padding:'12px 16px', fontSize:'0.82rem', color:'#b00020' }}>
                    <span style={{ fontSize:16, flexShrink:0 }}>⚠</span>
                    {errorMessage}
                  </div>
                )}
                {successMessage && (
                  <div style={{ display:'flex', alignItems:'center', gap:10, background:'#f0faf4', border:'1px solid rgba(20,150,80,0.15)', borderRadius:10, padding:'12px 16px', fontSize:'0.82rem', color:'#1a7a40' }}>
                    <div style={{ width:16, height:16, border:`2px solid #1a7a40`, borderTopColor:'transparent', borderRadius:'50%', animation:'spin 0.8s linear infinite', flexShrink:0 }} />
                    {successMessage}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Generating overlay card */}
          {isGenerating && (
            <div style={{
              background:'#fff', border:`1px solid ${T.bd}`, borderRadius:16,
              padding:'32px 28px', marginBottom:24,
              display:'flex', alignItems:'center', gap:20,
            }}>
              <div style={{
                width:44, height:44, background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:12,
                display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
              }}>
                <div style={{ width:20, height:20, border:`2px solid ${T.bd}`, borderTopColor:T.dark, borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
              </div>
              <div>
                <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1rem', fontWeight:700, color:T.dark, letterSpacing:'-0.2px', marginBottom:3 }}>
                  Generating your PDF…
                </div>
                <div style={{ fontSize:'0.8rem', color:T.t2 }}>
                  AI is writing content and assembling your branded lead magnet. This usually takes 15–30 seconds.
                </div>
              </div>
            </div>
          )}

          {/* Form wrapper */}
          <div style={{
            background:'#fff', border:`1px solid ${T.bd}`, borderRadius:16,
            overflow:'hidden',
            opacity: isGenerating ? 0.5 : 1,
            pointerEvents: isGenerating ? 'none' : 'auto',
            transition:'opacity 0.3s',
          }}>
            {currentStep === 'lead-magnet-generation' && (
              <LeadMagnetGenerationForm onSubmit={handleGenerationSubmit} loading={loading} />
            )}
            {currentStep === 'template-selection' && (
              <TemplateSelectionForm onSubmit={handleTemplateSubmit} onClose={handleBack} loading={loading || isGenerating} />
            )}
          </div>

        </main>
      </div>

      {/* ════════ PDF PREVIEW MODAL ════════ */}
      <Modal
        isOpen={showPreviewModal}
        onClose={() => { setShowPreviewModal(false); if (previewUrl) { window.URL.revokeObjectURL(previewUrl); setPreviewUrl(null) } }}
        title="PDF Preview"
        maxWidth={1200}
      >
        {previewUrl ? (
          <div style={{ display:'flex', flexDirection:'column', height:'80vh' }}>
            {/* Modal header */}
            <div style={{
              display:'flex', alignItems:'center', justifyContent:'space-between',
              padding:'16px 24px', borderBottom:`1px solid ${T.bd}`, background:'#fff',
            }}>
              <div style={{ display:'flex', alignItems:'center', gap:9 }}>
                <div style={{ width:32, height:32, background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center' }}>
                  <FileText size={15} color={T.t2} />
                </div>
                <div>
                  <div style={{ fontFamily:"'Fraunces',serif", fontSize:'0.95rem', fontWeight:700, color:T.dark, letterSpacing:'-0.2px' }}>Lead Magnet Preview</div>
                  <div style={{ fontSize:'0.72rem', color:T.t3 }}>Review before downloading</div>
                </div>
              </div>
              <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                <button className="clm-pdf-dl-btn" onClick={() => { if (previewUrl) { const a = document.createElement('a'); a.href = previewUrl; a.setAttribute('download','lead-magnet.pdf'); document.body.appendChild(a); a.click(); a.remove() } }}>
                  <Download size={14} />
                  Download PDF
                </button>
                <button className="clm-pdf-close-btn" onClick={() => { setShowPreviewModal(false); if (previewUrl) { window.URL.revokeObjectURL(previewUrl); setPreviewUrl(null) } }}>
                  <X size={14} />
                  Close
                </button>
              </div>
            </div>

            {/* iframe */}
            <div style={{ flex:1, background:T.bg2, padding:20, overflow:'hidden' }}>
              <iframe
                title="Lead Magnet Preview"
                src={previewUrl}
                style={{ width:'100%', height:'100%', border:'none', borderRadius:10, background:'#fff' }}
              />
            </div>
          </div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'60px 40px', gap:14 }}>
            <div style={{ width:48, height:48, background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:12, display:'flex', alignItems:'center', justifyContent:'center' }}>
              <div style={{ width:20, height:20, border:`2px solid ${T.bd}`, borderTopColor:T.dark, borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
            </div>
            <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1rem', fontWeight:700, color:T.dark, letterSpacing:'-0.2px' }}>Generating preview…</div>
            <div style={{ fontSize:'0.8rem', color:T.t3 }}>Your PDF is being assembled</div>
          </div>
        )}
      </Modal>
    </>
  )
}

export default CreateLeadMagnet