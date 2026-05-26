import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Plus, Settings, LogOut, Palette, Upload, X, ArrowRight, Sparkles, Check } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useBrand } from '../contexts/BrandContext'
import { dashboardApi } from '../lib/dashboardApi'
import type { FirmProfile } from '../lib/dashboardApi'

/* ── TOKENS ── */
const T = {
  bg:'#ffffff', bg2:'#f7f7f5', bg3:'#f0f0ec',
  dark:'#0a0a0a', bd:'rgba(0,0,0,0.08)', bd2:'rgba(0,0,0,0.15)',
  t1:'#111111', t2:'#666666', t3:'#aaaaaa',
} as const

const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
    *{box-sizing:border-box;margin:0;padding:0;}
    html,body{overflow-x:hidden;max-width:100vw;}
    body{font-family:'Instrument Sans',sans-serif;background:${T.bg2};color:${T.t1};}
    a{text-decoration:none;color:inherit;}
    .ba-nav-item{display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:8px;font-size:0.82rem;font-weight:500;color:${T.t2};text-decoration:none;cursor:pointer;transition:all 0.15s;font-family:'Instrument Sans',sans-serif;}
    .ba-nav-item:hover,.ba-nav-item.active{background:${T.bg2};color:${T.t1};}
    .ba-nav-item.active svg{color:${T.t1}!important;}
    .ba-logout-btn{display:flex;align-items:center;gap:6px;background:none;border:1px solid ${T.bd};border-radius:8px;padding:7px 14px;font-family:'Instrument Sans',sans-serif;font-size:0.78rem;font-weight:500;color:${T.t2};cursor:pointer;transition:all 0.2s;}
    .ba-logout-btn:hover{border-color:${T.bd2};color:${T.t1};background:${T.bg2};}
    .ba-sidebar-create{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:11px 14px;background:${T.dark};color:#fff;border:none;border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.82rem;font-weight:600;cursor:pointer;transition:all 0.2s;}
    .ba-sidebar-create:hover{background:#2a2a2a;transform:translateY(-1px);box-shadow:0 6px 20px rgba(0,0,0,0.15);}
    .ba-input{width:100%;padding:11px 14px;background:${T.bg2};border:1px solid ${T.bd};border-radius:9px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;color:${T.t1};outline:none;transition:all 0.2s;}
    .ba-input:focus{border-color:${T.bd2};background:#fff;box-shadow:0 0 0 3px rgba(0,0,0,0.04);}
    .ba-input::placeholder{color:${T.t3};}
    .ba-textarea{width:100%;padding:12px 14px;background:${T.bg2};border:1px solid ${T.bd};border-radius:9px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;color:${T.t1};outline:none;resize:vertical;transition:all 0.2s;line-height:1.6;}
    .ba-textarea:focus{border-color:${T.bd2};background:#fff;box-shadow:0 0 0 3px rgba(0,0,0,0.04);}
    .ba-textarea::placeholder{color:${T.t3};}
    .ba-select{width:100%;padding:11px 14px;background:${T.bg2};border:1px solid ${T.bd};border-radius:9px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;color:${T.t1};outline:none;cursor:pointer;appearance:none;transition:all 0.2s;}
    .ba-select:focus{border-color:${T.bd2};background:#fff;box-shadow:0 0 0 3px rgba(0,0,0,0.04);}
    .ba-btn-p{display:inline-flex;align-items:center;gap:7px;padding:11px 22px;background:${T.dark};color:#fff;border:none;border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;font-weight:600;cursor:pointer;transition:all 0.2s;}
    .ba-btn-p:hover:not(:disabled){background:#2a2a2a;transform:translateY(-1px);box-shadow:0 6px 20px rgba(0,0,0,0.15);}
    .ba-btn-p:disabled{opacity:0.45;cursor:not-allowed;transform:none;box-shadow:none;}
    .ba-btn-s{display:inline-flex;align-items:center;gap:7px;padding:11px 18px;background:none;border:1px solid ${T.bd2};border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;font-weight:500;color:${T.t2};cursor:pointer;transition:all 0.2s;}
    .ba-btn-s:hover:not(:disabled){border-color:rgba(0,0,0,0.25);color:${T.t1};background:${T.bg2};}
    .ba-btn-s:disabled{opacity:0.45;cursor:not-allowed;}
    .ba-chip{display:flex;align-items:center;gap:7px;padding:9px 14px;border:1px solid ${T.bd};border-radius:9px;cursor:pointer;transition:all 0.15s;background:${T.bg2};font-family:'Instrument Sans',sans-serif;font-size:0.82rem;font-weight:500;color:${T.t2};user-select:none;}
    .ba-chip:hover{border-color:${T.bd2};color:${T.t1};background:#fff;}
    .ba-chip.sel{background:${T.dark};border-color:${T.dark};color:#fff;}
    .ba-chip input{display:none;}
    @keyframes ba-spin{to{transform:rotate(360deg);}}
  `}</style>
)

const FONT_STYLES = [
  { value:'modern-sans',   label:'Modern Sans-Serif' },
  { value:'classic-serif', label:'Classic Serif' },
  { value:'creative',      label:'Creative / Display' },
  { value:'no-preference', label:'No Preference' },
]

const INDUSTRY_SPECIALTIES = [
  'Residential','Commercial','Mixed Practice','Sustainable/Green',
  'Educational/Civic','Hospitality','Healthcare','Interiors','Urban Design','Other',
]

const FIRM_SIZE_OPTIONS = [
  { value:'1-2', label:'1–2' },
  { value:'3-5', label:'3–5' },
  { value:'6-10', label:'6–10' },
  { value:'11+', label:'11+' },
]

type FormStep = 'firm-profile' | 'brand-assets'

const Label = ({ children, optional }: { children: React.ReactNode; optional?: boolean }) => (
  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:8 }}>
    <span style={{ fontSize:'0.78rem', fontWeight:600, color:T.t1 }}>{children}</span>
    {optional && <span style={{ fontSize:'0.68rem', color:T.t3, fontWeight:400 }}>optional</span>}
  </div>
)

const FieldDesc = ({ children }: { children: React.ReactNode }) => (
  <div style={{ fontSize:'0.72rem', color:T.t3, marginTop:6, lineHeight:1.5 }}>{children}</div>
)

const BrandAssets: React.FC = () => {
  const { logout }                    = useAuth()
  const { brandColors, updateBrandColors } = useBrand()
  const navigate                      = useNavigate()
  const [currentStep, setCurrentStep] = useState<FormStep>('firm-profile')
  const [formData, setFormData]       = useState<Partial<FirmProfile>>({
    primary_brand_color:   brandColors.primaryColor,
    secondary_brand_color: brandColors.secondaryColor,
    preferred_font_style:  brandColors.fontStyle,
    branding_guidelines:   '',
    firm_size:             '1-2',
    industry_specialties:  [],
  })
  const [loading, setLoading]                 = useState(false)
  const [saving, setSaving]                   = useState(false)
  const [hasExisting, setHasExisting]         = useState(false)
  const [saved, setSaved]                     = useState(false)
  const [formErrors, setFormErrors]           = useState<string[]>([])
  const [logoPreview, setLogoPreview]         = useState<string|null>(null)

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        const profile = await dashboardApi.getFirmProfile()
        if (profile) {
          setFormData({
            firm_name:             profile.firm_name || '',
            work_email:            profile.work_email || '',
            phone_number:          profile.phone_number || '',
            firm_website:          profile.firm_website || '',
            firm_size:             profile.firm_size || '1-2',
            industry_specialties:  profile.industry_specialties || [],
            location:              profile.location || '',
            primary_brand_color:   profile.primary_brand_color || '#0a0a0a',
            secondary_brand_color: profile.secondary_brand_color || '#f7f7f5',
            preferred_font_style:  profile.preferred_font_style || 'no-preference',
            branding_guidelines:   profile.branding_guidelines || '',
          })
          if (profile.logo) setLogoPreview(typeof profile.logo === 'string' ? profile.logo : null)
          if (profile.primary_brand_color || profile.branding_guidelines) setHasExisting(true)
        }
      } catch { /* no existing profile */ }
      finally { setLoading(false) }
    })()
  }, [])

  const set = (field: keyof FirmProfile, value: any) =>
    setFormData(prev => ({ ...prev, [field]: value }))

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!['image/jpeg','image/png','image/svg+xml'].includes(file.type)) {
      setFormErrors(['Invalid file type. Please upload JPG, PNG, or SVG.']); return
    }
    if (file.size > 2 * 1024 * 1024) {
      setFormErrors(['File too large. Maximum 2MB.']); return
    }
    set('logo', file); setFormErrors([])
    const r = new FileReader()
    r.onloadend = () => setLogoPreview(r.result as string)
    r.readAsDataURL(file)
  }

  const toggleSpecialty = (s: string) => {
    const cur = formData.industry_specialties || []
    set('industry_specialties', cur.includes(s) ? cur.filter(x => x !== s) : [...cur, s])
  }

  const validate = (data: Partial<FirmProfile> = formData): boolean => {
    const errors: string[] = []
    const hex   = /^#([A-Fa-f0-9]{6})$/
    const email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!data.firm_name) errors.push('Firm name is required')
    if (!data.work_email) errors.push('Work email is required')
    else if (!email.test(String(data.work_email).trim())) errors.push('Work email must be a valid email address')
    if (!data.primary_brand_color   || !hex.test(data.primary_brand_color))   errors.push('Primary color must be a valid hex e.g. #0a0a0a')
    if (!data.secondary_brand_color || !hex.test(data.secondary_brand_color)) errors.push('Secondary color must be a valid hex e.g. #f7f7f5')
    setFormErrors(errors)
    return errors.length === 0
  }

  const handleSave = async (andContinue = false) => {
    const data = { ...formData }
    if (data.firm_website && !String(data.firm_website).startsWith('http')) {
      data.firm_website = `https://${data.firm_website}`
    }
    if (!validate(data)) return
    setSaving(true)
    try {
      await dashboardApi.updateFirmProfile(data)
      setHasExisting(true)
      updateBrandColors({
        primaryColor:   data.primary_brand_color   || '#0a0a0a',
        secondaryColor: data.secondary_brand_color || '#f7f7f5',
        fontStyle:      data.preferred_font_style  || 'no-preference',
      })
      if (andContinue) { navigate('/create-lead-magnet') }
      else { setSaved(true); setTimeout(() => setSaved(false), 3000) }
    } catch (err) {
      setFormErrors(['Save failed. Please review your inputs and try again.'])
    } finally { setSaving(false) }
  }

  /* ── NAV ITEMS ── */
  const navItems = [
    { label:'My Lead Magnets', icon:<FileText size={16}/>,  href:'/dashboard' },
    { label:'Forma AI',        icon:<Sparkles size={16}/>,  href:'/forma-ai' },
    { label:'Brand Assets',    icon:<Palette size={16}/>,   href:'/brand-assets', active:true },
    { label:'Settings',        icon:<Settings size={16}/>,  href:'/settings' },
  ]

  const STEPS: { id: FormStep; label: string; num: number }[] = [
    { id:'firm-profile',  label:'Firm Information', num:1 },
    { id:'brand-assets',  label:'Brand & Style',    num:2 },
  ]

  if (loading) return (
    <>
      <GlobalStyles/>
      <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:12, height:'100vh', background:T.bg2 }}>
        <div style={{ fontFamily:"'Fraunces',serif", fontWeight:900, fontSize:'1.5rem', color:T.dark, letterSpacing:'-0.5px' }}>Forma.</div>
        <div style={{ width:20, height:20, border:`2px solid ${T.bd}`, borderTopColor:T.dark, borderRadius:'50%', animation:'ba-spin 0.8s linear infinite' }}/>
      </div>
    </>
  )

  return (
    <>
      <GlobalStyles/>

      {/* ── NAV ── */}
      <nav style={{ height:62, display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 24px', background:'#fff', borderBottom:`1px solid ${T.bd}`, position:'fixed', top:0, left:0, right:0, zIndex:200 }}>
        <div style={{ fontFamily:"'Fraunces',serif", fontWeight:900, fontSize:'1.35rem', color:T.dark, letterSpacing:'-0.5px' }}>Forma.</div>

        {/* Step indicator */}
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          {STEPS.map((s, i) => {
            const isActive = s.id === currentStep
            const isDone   = STEPS.findIndex(x => x.id === currentStep) > i
            return (
              <React.Fragment key={s.id}>
                <span style={{ display:'inline-flex', alignItems:'center', gap:7, padding:'6px 14px', borderRadius:20, fontSize:'0.78rem', fontWeight:500, transition:'all 0.2s', background: isActive ? T.dark : T.bg2, color: isActive ? '#fff' : isDone ? T.t2 : T.t3, border:`1px solid ${isActive ? T.dark : T.bd}` }}>
                  <span style={{ width:16, height:16, borderRadius:'50%', background: isActive ? 'rgba(255,255,255,0.2)' : isDone ? T.bg3 : T.bg3, display:'flex', alignItems:'center', justifyContent:'center', fontSize:9, fontWeight:700, flexShrink:0, color: isActive ? '#fff' : T.t3 }}>
                    {isDone ? '✓' : s.num}
                  </span>
                  {s.label}
                </span>
                {i < STEPS.length - 1 && <div style={{ width:18, height:1, background:T.bd }}/>}
              </React.Fragment>
            )
          })}
        </div>

        <button className="ba-logout-btn" onClick={() => { logout(); navigate('/') }}>
          <LogOut size={14}/> Log out
        </button>
      </nav>

      <div style={{ height:62 }}/>

      {/* ── BODY ── */}
      <div style={{ display:'flex', minHeight:'calc(100vh - 62px)' }}>

        {/* ── SIDEBAR ── */}
        <aside style={{ background:'#fff', borderRight:`1px solid ${T.bd}`, padding:'28px 16px', display:'flex', flexDirection:'column', gap:28, position:'fixed', top:62, left:0, width:228, height:'calc(100vh - 62px)', overflowY:'auto', overflowX:'hidden', zIndex:100 }}>
          <div style={{ display:'flex', alignItems:'center', gap:11, padding:'0 4px' }}>
            <div style={{ width:34, height:34, background:T.dark, borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
              <FileText size={15} color="#fff"/>
            </div>
            <div>
              <div style={{ fontFamily:"'Fraunces',serif", fontSize:'0.82rem', fontWeight:700, color:T.t1, letterSpacing:'-0.2px', lineHeight:1.2 }}>AI Lead Magnets</div>
              <div style={{ fontSize:'0.68rem', color:T.t3, lineHeight:1 }}>Your AI Workforce</div>
            </div>
          </div>

          <button className="ba-sidebar-create" onClick={() => navigate('/create-lead-magnet')}>
            <Plus size={16}/> Create Lead Magnet
          </button>

          <div>
            <div style={{ fontSize:'0.62rem', fontWeight:600, letterSpacing:'2.5px', textTransform:'uppercase', color:T.t3, padding:'0 8px', marginBottom:6 }}>Navigation</div>
            <nav style={{ display:'flex', flexDirection:'column', gap:2 }}>
              {navItems.map(item => (
                <a key={item.label} href={item.href} className={`ba-nav-item${item.active ? ' active' : ''}`} onClick={e => { e.preventDefault(); navigate(item.href) }}>
                  {item.icon} {item.label}
                </a>
              ))}
            </nav>
          </div>

          <div style={{ marginTop:'auto' }}>
            <div style={{ height:1, background:T.bd, marginBottom:16 }}/>
            <div style={{ background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:10, padding:14 }}>
              <div style={{ fontSize:'0.72rem', fontWeight:600, color:T.t1, marginBottom:4 }}>
                {currentStep === 'firm-profile' ? 'Step 1 of 2' : 'Step 2 of 2'}
              </div>
              <div style={{ fontSize:'0.7rem', color:T.t3, lineHeight:1.5 }}>
                {currentStep === 'firm-profile'
                  ? 'Enter your firm details — they appear on every lead magnet you generate.'
                  : 'Set your brand colors, fonts, and guidelines for consistent PDFs.'}
              </div>
            </div>
          </div>
        </aside>

        {/* ── SIDEBAR PLACEHOLDER ── */}
        <div style={{ width:228, flexShrink:0 }}/>

        {/* ── MAIN ── */}
        <main style={{ flex:1, padding:'40px 52px', background:T.bg2, minWidth:0 }}>

          {/* Page header */}
          <div style={{ marginBottom:32 }}>
            <div style={{ display:'inline-flex', alignItems:'center', gap:7, background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:20, padding:'4px 13px 4px 9px', fontSize:'0.7rem', fontWeight:600, color:T.t2, marginBottom:14 }}>
              <span style={{ width:6, height:6, borderRadius:'50%', background:T.dark }}/>
              {currentStep === 'firm-profile' ? 'Step 1 — Firm Information' : 'Step 2 — Brand & Style'}
            </div>
            <h1 style={{ fontFamily:"'Fraunces',serif", fontSize:'2rem', fontWeight:900, color:T.dark, letterSpacing:'-1px', lineHeight:1.05, marginBottom:6 }}>
              {currentStep === 'firm-profile'
                ? <>Your firm <em style={{ fontStyle:'italic', color:T.t3 }}>details.</em></>
                : <>Your brand <em style={{ fontStyle:'italic', color:T.t3 }}>identity.</em></>}
            </h1>
            <p style={{ fontSize:'0.88rem', color:T.t2 }}>
              {currentStep === 'firm-profile'
                ? 'These details appear on every lead magnet you generate — make them accurate.'
                : 'Brand colors and fonts are applied automatically to all your PDFs.'}
            </p>
          </div>

          {/* Error banner */}
          {formErrors.length > 0 && (
            <div style={{ marginBottom:20, background:'#fff2f2', border:'1px solid rgba(200,50,50,0.15)', borderRadius:10, padding:'12px 16px', display:'flex', flexDirection:'column', gap:4 }}>
              {formErrors.map((e, i) => (
                <div key={i} style={{ fontSize:'0.8rem', color:'#b00020', display:'flex', alignItems:'center', gap:7 }}>
                  <span>⚠</span> {e}
                </div>
              ))}
            </div>
          )}

          {/* Success toast */}
          {saved && (
            <motion.div initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }}
              style={{ marginBottom:20, background:'#f0faf4', border:'1px solid rgba(20,150,80,0.15)', borderRadius:10, padding:'12px 16px', display:'flex', alignItems:'center', gap:10, fontSize:'0.82rem', color:'#1a7a40' }}>
              <Check size={16}/> Brand assets saved successfully.
            </motion.div>
          )}

          {/* ── FORM PANEL ── */}
          <motion.div
            key={currentStep}
            initial={{ opacity:0, x:12 }}
            animate={{ opacity:1, x:0 }}
            style={{ background:'#fff', border:`1px solid ${T.bd}`, borderRadius:16, overflow:'hidden' }}
          >

            {/* ────── STEP 1: FIRM PROFILE ────── */}
            {currentStep === 'firm-profile' && (
              <>
                <div style={{ padding:'20px 28px', borderBottom:`1px solid ${T.bd}` }}>
                  <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1rem', fontWeight:700, color:T.dark, letterSpacing:'-0.2px' }}>Firm Information</div>
                </div>
                <div style={{ padding:28, display:'flex', flexDirection:'column', gap:20 }}>

                  {/* Logo upload */}
                  <div>
                    <Label>Firm Logo <span style={{ fontSize:'0.68rem', color:T.t3, fontWeight:400 }}>optional</span></Label>
                    {logoPreview ? (
                      <div style={{ display:'inline-flex', alignItems:'center', gap:12, padding:'12px 16px', background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:10 }}>
                        <img src={logoPreview} alt="Logo" style={{ height:40, maxWidth:120, objectFit:'contain', borderRadius:4 }}/>
                        <button onClick={() => { set('logo', null); setLogoPreview(null) }} style={{ display:'flex', alignItems:'center', gap:5, background:'none', border:`1px solid ${T.bd}`, borderRadius:7, padding:'5px 10px', fontSize:'0.72rem', color:T.t2, cursor:'pointer' }}>
                          <X size={12}/> Remove
                        </button>
                      </div>
                    ) : (
                      <label style={{ display:'inline-flex', alignItems:'center', gap:9, padding:'11px 18px', background:T.bg2, border:`1.5px dashed ${T.bd2}`, borderRadius:10, cursor:'pointer', fontSize:'0.82rem', color:T.t2, fontWeight:500, transition:'all 0.2s' }}>
                        <Upload size={15}/> Upload Logo
                        <input type="file" style={{ display:'none' }} onChange={handleLogoChange} accept=".jpg,.jpeg,.png,.svg"/>
                      </label>
                    )}
                    <FieldDesc>JPG, PNG, SVG · max 2MB · recommended 150×50px</FieldDesc>
                  </div>

                  {/* Two-col row */}
                  <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
                    <div>
                      <Label>Firm Name *</Label>
                      <input className="ba-input" type="text" value={formData.firm_name||''} onChange={e => set('firm_name', e.target.value)} placeholder="e.g. Kyro Studio"/>
                    </div>
                    <div>
                      <Label>Work Email *</Label>
                      <input className="ba-input" type="email" value={formData.work_email||''} onChange={e => set('work_email', e.target.value)} placeholder="you@yourfirm.com"/>
                    </div>
                    <div>
                      <Label optional>Phone Number</Label>
                      <input className="ba-input" type="tel" value={formData.phone_number||''} onChange={e => set('phone_number', e.target.value)} placeholder="+1 (555) 000-0000"/>
                    </div>
                    <div>
                      <Label optional>Firm Website</Label>
                      <input className="ba-input" type="url" value={formData.firm_website||''} onChange={e => set('firm_website', e.target.value)} placeholder="yourfirm.com"/>
                    </div>
                    <div>
                      <Label optional>Location</Label>
                      <input className="ba-input" type="text" value={formData.location||''} onChange={e => set('location', e.target.value)} placeholder="City, Country"/>
                    </div>
                  </div>

                  {/* Firm size */}
                  <div>
                    <Label>Firm Size</Label>
                    <div style={{ display:'flex', gap:8 }}>
                      {FIRM_SIZE_OPTIONS.map(o => (
                        <label key={o.value} className={`ba-chip${formData.firm_size===o.value?' sel':''}`} onClick={() => set('firm_size', o.value)}>
                          <input type="radio" readOnly checked={formData.firm_size===o.value}/>{o.label} people
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Industry specialties */}
                  <div>
                    <Label optional>Industry Specialties</Label>
                    <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:8 }}>
                      {INDUSTRY_SPECIALTIES.map(s => {
                        const sel = (formData.industry_specialties||[]).includes(s)
                        return (
                          <label key={s} className={`ba-chip${sel?' sel':''}`} onClick={() => toggleSpecialty(s)}>
                            <input type="checkbox" readOnly checked={sel}/>
                            {sel && <Check size={11}/>}
                            {s}
                          </label>
                        )
                      })}
                    </div>
                  </div>
                </div>

                <div style={{ padding:'18px 28px', borderTop:`1px solid ${T.bd}`, background:T.bg2, display:'flex', justifyContent:'flex-end' }}>
                  <button className="ba-btn-p" onClick={() => { setFormErrors([]); setCurrentStep('brand-assets') }}>
                    Continue to Brand <ArrowRight size={14}/>
                  </button>
                </div>
              </>
            )}

            {/* ────── STEP 2: BRAND & STYLE ────── */}
            {currentStep === 'brand-assets' && (
              <>
                <div style={{ padding:'20px 28px', borderBottom:`1px solid ${T.bd}` }}>
                  <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1rem', fontWeight:700, color:T.dark, letterSpacing:'-0.2px' }}>Brand & Style</div>
                </div>
                <div style={{ padding:28, display:'flex', flexDirection:'column', gap:24 }}>

                  {/* Colors */}
                  <div>
                    <div style={{ fontSize:'0.65rem', fontWeight:600, letterSpacing:'2px', textTransform:'uppercase', color:T.t3, marginBottom:14 }}>Brand Colors</div>
                    <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
                      {([
                        { field:'primary_brand_color',   label:'Primary Color',   desc:'Headings, buttons, accents', def:'#0a0a0a' },
                        { field:'secondary_brand_color',  label:'Secondary Color', desc:'Backgrounds, highlights',   def:'#f7f7f5' },
                      ] as const).map(c => (
                        <div key={c.field}>
                          <Label>{c.label} *</Label>
                          <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                            {/* Color swatch picker */}
                            <div style={{ position:'relative', flexShrink:0 }}>
                              <input type="color" value={(formData as any)[c.field]||c.def} onChange={e => set(c.field as any, e.target.value)}
                                style={{ width:42, height:42, borderRadius:9, border:`1px solid ${T.bd}`, cursor:'pointer', padding:3, background:'none' }}/>
                            </div>
                            <input className="ba-input" type="text" value={(formData as any)[c.field]||''} onChange={e => set(c.field as any, e.target.value)} placeholder={c.def} style={{ flex:1 }}/>
                            {/* Preview swatch */}
                            <div style={{ width:42, height:42, borderRadius:9, background:(formData as any)[c.field]||c.def, border:`1px solid ${T.bd}`, flexShrink:0 }}/>
                          </div>
                          <FieldDesc>{c.desc}</FieldDesc>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Font style */}
                  <div>
                    <div style={{ fontSize:'0.65rem', fontWeight:600, letterSpacing:'2px', textTransform:'uppercase', color:T.t3, marginBottom:14 }}>Typography</div>
                    <Label>Preferred Font Style</Label>
                    <div style={{ position:'relative' }}>
                      <select className="ba-select" value={formData.preferred_font_style||'no-preference'} onChange={e => set('preferred_font_style', e.target.value)}>
                        {FONT_STYLES.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                      </select>
                      <div style={{ position:'absolute', right:14, top:'50%', transform:'translateY(-50%)', pointerEvents:'none', color:T.t3, fontSize:12 }}>▾</div>
                    </div>
                    <FieldDesc>Applied to all generated PDF documents</FieldDesc>
                  </div>

                  {/* Brand guidelines */}
                  <div>
                    <div style={{ fontSize:'0.65rem', fontWeight:600, letterSpacing:'2px', textTransform:'uppercase', color:T.t3, marginBottom:14 }}>Brand Guidelines</div>
                    <Label optional>Additional Guidelines</Label>
                    <textarea className="ba-textarea" rows={5} value={formData.branding_guidelines||''} onChange={e => set('branding_guidelines', e.target.value)}
                      placeholder="Describe your brand tone, personality, design preferences, things to avoid…"/>
                    <FieldDesc>The AI reads these when generating your lead magnets</FieldDesc>
                  </div>

                  {/* Live preview strip */}
                  <div style={{ background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:12, padding:'16px 20px' }}>
                    <div style={{ fontSize:'0.65rem', fontWeight:600, letterSpacing:'2px', textTransform:'uppercase', color:T.t3, marginBottom:12 }}>Live Preview</div>
                    <div style={{ background:(formData.primary_brand_color||'#0a0a0a'), borderRadius:10, padding:'16px 20px', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                      <div>
                        <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1rem', fontWeight:900, color:(formData.secondary_brand_color||'#f7f7f5'), letterSpacing:'-0.3px', marginBottom:3 }}>
                          {formData.firm_name || 'Your Firm Name'}
                        </div>
                        <div style={{ fontSize:'0.72rem', color:'rgba(255,255,255,0.45)' }}>{formData.work_email||'email@yourfirm.com'}</div>
                      </div>
                      <div style={{ background:(formData.secondary_brand_color||'#f7f7f5'), borderRadius:7, padding:'7px 14px', fontSize:'0.72rem', fontWeight:600, color:(formData.primary_brand_color||'#0a0a0a') }}>
                        Download PDF
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{ padding:'18px 28px', borderTop:`1px solid ${T.bd}`, background:T.bg2, display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                  <button className="ba-btn-s" onClick={() => setCurrentStep('firm-profile')}>← Back</button>
                  <div style={{ display:'flex', gap:10 }}>
                    <button className="ba-btn-s" onClick={() => handleSave(false)} disabled={saving}>
                      {saving ? <><div style={{ width:13, height:13, border:`2px solid ${T.bd}`, borderTopColor:T.t2, borderRadius:'50%', animation:'ba-spin 0.8s linear infinite' }}/> Saving…</> : hasExisting ? 'Update' : 'Save'}
                    </button>
                    <button className="ba-btn-p" onClick={() => handleSave(true)} disabled={saving}>
                      {saving ? 'Saving…' : 'Save & Create Lead Magnet'} {!saving && <ArrowRight size={14}/>}
                    </button>
                  </div>
                </div>
              </>
            )}
          </motion.div>
        </main>
      </div>
    </>
  )
}

export default BrandAssets