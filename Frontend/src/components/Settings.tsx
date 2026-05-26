import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText, Plus, Settings as SettingsIcon,
  LogOut, Palette, Sparkles, Check, User,
  Building2, Mail, Phone, Globe, AlignLeft,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { dashboardApi } from '../lib/dashboardApi'
import type { FirmProfile } from '../lib/dashboardApi'

const Settings: React.FC = () => {
  const { logout, user } = useAuth()
  const navigate         = useNavigate()

  const [firmProfile, setFirmProfile]   = useState<FirmProfile | null>(null)
  const [loading, setLoading]           = useState(true)
  const [saving, setSaving]             = useState(false)
  const [saved, setSaved]               = useState(false)
  const [saveError, setSaveError]       = useState<string | null>(null)
  const [hoveredNav, setHoveredNav]     = useState<string | null>(null)

  const [formData, setFormData] = useState({
    fullName:     user?.name  || '',
    firmName:     '',
    firmSize:     '1-2',
    workEmail:    '',
    phoneNumber:  '',
    website:      '',
    guidelines:   '',
    usingFormaFor:'Personal Use',
    email:        user?.email || '',
  })

  useEffect(() => {
    const load = async () => {
      try {
        const profile = await dashboardApi.getFirmProfile()
        setFirmProfile(profile)
        setFormData({
          fullName:     user?.name || '',
          firmName:     profile?.firm_name          || '',
          firmSize:     profile?.firm_size          || '1-2',
          workEmail:    profile?.work_email         || '',
          phoneNumber:  profile?.phone_number       || '',
          website:      profile?.firm_website       || '',
          guidelines:   profile?.branding_guidelines|| '',
          usingFormaFor:'Personal Use',
          email:        user?.email                 || '',
        })
      } catch {
        setFormData(prev => ({ ...prev, firmName:'', firmSize:'1-2', workEmail:'', phoneNumber:'', website:'', guidelines:'' }))
      } finally { setLoading(false) }
    }
    if (user) load()
  }, [user])

  const change = (field: string, value: string) =>
    setFormData(prev => ({ ...prev, [field]: value }))

  const handleSave = async () => {
    setSaving(true); setSaveError(null); setSaved(false)
    try {
      const updated = await dashboardApi.updateFirmProfile({
        firm_name:           formData.firmName,
        firm_size:           formData.firmSize,
        work_email:          formData.workEmail,
        phone_number:        formData.phoneNumber,
        firm_website:        formData.website,
        branding_guidelines: formData.guidelines,
      })
      setFirmProfile(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setSaveError('Failed to save. Please try again.')
    } finally { setSaving(false) }
  }

  const navItems = [
    { label:'My Lead Magnets', icon:<FileText size={15}/>,    href:'/dashboard'     },
    { label:'Forma AI',        icon:<Sparkles size={15}/>,    href:'/forma-ai'      },
    { label:'Brand Assets',    icon:<Palette size={15}/>,     href:'/brand-assets'  },
    { label:'Settings',        icon:<SettingsIcon size={15}/>,href:'/settings', active:true },
  ]

  /* ── FIELD HELPER ── */
  const Field = ({
    label, field, type = 'text', placeholder, icon: Icon, textarea = false,
  }: {
    label: string; field: string; type?: string; placeholder: string
    icon: React.FC<any>; textarea?: boolean
  }) => (
    <div>
      <label style={{ fontSize:'0.68rem', fontWeight:600, textTransform:'uppercase' as const, letterSpacing:'0.1em', color:'#aaa', display:'block', marginBottom:6 }}>{label}</label>
      <div style={{ position:'relative' }}>
        <Icon size={14} style={{ position:'absolute', left:13, top: textarea ? 13 : '50%', transform: textarea ? 'none' : 'translateY(-50%)', color:'#ccc', pointerEvents:'none', flexShrink:0 }} />
        {textarea ? (
          <textarea
            value={(formData as any)[field]}
            onChange={e => change(field, e.target.value)}
            placeholder={placeholder}
            rows={4}
            style={{ width:'100%', paddingLeft:38, paddingRight:14, paddingTop:11, paddingBottom:11, background:'#fafafa', border:'1px solid rgba(0,0,0,0.08)', borderRadius:10, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.85rem', color:'#111', outline:'none', resize:'vertical', lineHeight:1.6 }}
            onFocus={e => { e.target.style.borderColor='rgba(0,0,0,0.28)'; e.target.style.boxShadow='0 0 0 3px rgba(0,0,0,0.04)' }}
            onBlur={e  => { e.target.style.borderColor='rgba(0,0,0,0.08)'; e.target.style.boxShadow='none' }}
          />
        ) : (
          <input
            type={type}
            value={(formData as any)[field]}
            onChange={e => change(field, e.target.value)}
            placeholder={placeholder}
            style={{ width:'100%', paddingLeft:38, paddingRight:14, paddingTop:11, paddingBottom:11, background:'#fafafa', border:'1px solid rgba(0,0,0,0.08)', borderRadius:10, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.85rem', color:'#111', outline:'none' }}
            onFocus={e => { e.target.style.borderColor='rgba(0,0,0,0.28)'; e.target.style.boxShadow='0 0 0 3px rgba(0,0,0,0.04)' }}
            onBlur={e  => { e.target.style.borderColor='rgba(0,0,0,0.08)'; e.target.style.boxShadow='none' }}
          />
        )}
      </div>
    </div>
  )

  if (loading) return (
    <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:"'Instrument Sans',sans-serif", background:'#f7f7f5' }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');@keyframes st-spin{to{transform:rotate(360deg)}}`}</style>
      <div style={{ textAlign:'center' }}>
        <div style={{ width:36, height:36, border:'3px solid rgba(0,0,0,0.08)', borderTopColor:'#0a0a0a', borderRadius:'50%', animation:'st-spin .8s linear infinite', margin:'0 auto 12px' }} />
        <p style={{ color:'#aaa', fontSize:'0.85rem' }}>Loading settings…</p>
      </div>
    </div>
  )

  return (
    <div style={{ minHeight:'100vh', background:'#f7f7f5', fontFamily:"'Instrument Sans',sans-serif", color:'#111' }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
        @keyframes st-spin{to{transform:rotate(360deg)}}
        input::placeholder,textarea::placeholder{color:#ccc;}
        select:focus{outline:none;border-color:rgba(0,0,0,0.28)!important;box-shadow:0 0 0 3px rgba(0,0,0,0.04)!important;}
        ::-webkit-scrollbar{width:4px;} ::-webkit-scrollbar-track{background:transparent;} ::-webkit-scrollbar-thumb{background:rgba(0,0,0,0.12);border-radius:4px;}
      `}</style>

      {/* ── NAV ── */}
      <nav style={{ height:60, background:'#fff', borderBottom:'1px solid rgba(0,0,0,0.07)', display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 28px', position:'sticky', top:0, zIndex:100 }}>
        <div style={{ fontFamily:"'Fraunces',serif", fontWeight:900, fontSize:'1.25rem', color:'#0a0a0a', letterSpacing:'-0.5px' }}>Forma.</div>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <div style={{ width:30, height:30, borderRadius:'50%', background:'#0a0a0a', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:"'Fraunces',serif", fontWeight:700, fontSize:'0.85rem', color:'#fff' }}>
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <span style={{ fontSize:'0.85rem', fontWeight:500, color:'#555' }}>{user?.name || 'User'}</span>
          </div>
          <button onClick={() => { logout(); navigate('/') }}
            style={{ width:34, height:34, borderRadius:8, border:'1px solid rgba(0,0,0,0.08)', background:'transparent', cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', color:'#aaa', transition:'all .2s' }}
            onMouseEnter={e => { (e.currentTarget).style.background='#f7f7f5'; (e.currentTarget).style.color='#555' }}
            onMouseLeave={e => { (e.currentTarget).style.background='transparent'; (e.currentTarget).style.color='#aaa' }}>
            <LogOut size={15} />
          </button>
        </div>
      </nav>

      <div style={{ display:'flex', minHeight:'calc(100vh - 60px)' }}>

        {/* ── SIDEBAR ── */}
        <aside style={{ width:228, background:'#fff', borderRight:'1px solid rgba(0,0,0,0.07)', display:'flex', flexDirection:'column', padding:'24px 16px', gap:4, flexShrink:0, position:'sticky', top:60, height:'calc(100vh - 60px)', overflowY:'auto' }}>
          <button onClick={() => navigate('/create-lead-magnet')}
            style={{ display:'flex', alignItems:'center', gap:9, padding:'11px 14px', background:'#0a0a0a', color:'#fff', border:'none', borderRadius:10, fontFamily:"'Instrument Sans',sans-serif", fontWeight:600, fontSize:'0.82rem', cursor:'pointer', marginBottom:10, transition:'all .2s' }}
            onMouseEnter={e => { (e.currentTarget).style.background='#2a2a2a'; (e.currentTarget).style.transform='translateY(-1px)' }}
            onMouseLeave={e => { (e.currentTarget).style.background='#0a0a0a'; (e.currentTarget).style.transform='none' }}>
            <Plus size={15} />Create Lead Magnet
          </button>
          <span style={{ fontSize:'0.62rem', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.12em', color:'#bbb', padding:'10px 4px 5px' }}>Navigation</span>
          {navItems.map(({ label, icon, href, active }) => (
            <a key={label} href={href}
              onClick={e => { e.preventDefault(); navigate(href) }}
              onMouseEnter={() => setHoveredNav(label)}
              onMouseLeave={() => setHoveredNav(null)}
              style={{ display:'flex', alignItems:'center', gap:9, padding:'9px 11px', borderRadius:8, fontSize:'0.82rem', color: active ? '#0a0a0a' : hoveredNav === label ? '#0a0a0a' : '#888', textDecoration:'none', background: active ? '#f7f7f5' : hoveredNav === label ? '#f7f7f5' : 'transparent', fontWeight: active ? 600 : 400, transition:'all .15s', borderLeft: active ? '2px solid #0a0a0a' : '2px solid transparent' }}>
              {icon}{label}
            </a>
          ))}
        </aside>

        {/* ── MAIN ── */}
        <main style={{ flex:1, padding:'40px 48px', overflowY:'auto', maxWidth:760 }}>

          {/* Header */}
          <div style={{ marginBottom:36 }}>
            <div style={{ fontSize:'0.68rem', fontWeight:600, letterSpacing:'3px', textTransform:'uppercase' as const, color:'#bbb', marginBottom:10, display:'flex', alignItems:'center', gap:8 }}>
              <span style={{ width:14, height:1.5, background:'#bbb', display:'inline-block' }} />Settings
            </div>
            <h1 style={{ fontFamily:"'Fraunces',serif", fontSize:'2rem', fontWeight:900, letterSpacing:'-0.8px', color:'#0a0a0a', lineHeight:1.1, marginBottom:6 }}>
              Personal profile.
            </h1>
            <p style={{ fontSize:'0.88rem', color:'#999', lineHeight:1.6 }}>Manage your account and company information. Changes sync with Brand Assets.</p>
          </div>

          {/* ── SECTION: Account ── */}
          <div style={{ background:'#fff', border:'1px solid rgba(0,0,0,0.07)', borderRadius:14, padding:'28px 28px', marginBottom:18 }}>
            <div style={{ marginBottom:22 }}>
              <div style={{ fontSize:'0.68rem', fontWeight:600, textTransform:'uppercase' as const, letterSpacing:'2px', color:'#bbb', marginBottom:4, display:'flex', alignItems:'center', gap:7 }}>
                <span style={{ width:14, height:1.5, background:'#bbb', display:'inline-block' }} />Account
              </div>
              <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1.1rem', fontWeight:700, color:'#0a0a0a', letterSpacing:'-0.2px' }}>Personal details</div>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
              <Field label="Full Name"     field="fullName"  placeholder="Your full name"    icon={User}  />
              <div>
                <label style={{ fontSize:'0.68rem', fontWeight:600, textTransform:'uppercase' as const, letterSpacing:'0.1em', color:'#aaa', display:'block', marginBottom:6 }}>Email Address</label>
                <div style={{ position:'relative' }}>
                  <Mail size={14} style={{ position:'absolute', left:13, top:'50%', transform:'translateY(-50%)', color:'#ccc', pointerEvents:'none' }} />
                  <input type="email" value={formData.email} readOnly
                    style={{ width:'100%', paddingLeft:38, paddingRight:80, paddingTop:11, paddingBottom:11, background:'#fafafa', border:'1px solid rgba(0,0,0,0.08)', borderRadius:10, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.85rem', color:'#aaa', outline:'none', cursor:'not-allowed' }} />
                  <button
                    style={{ position:'absolute', right:8, top:'50%', transform:'translateY(-50%)', padding:'4px 10px', background:'#f0f0ec', border:'1px solid rgba(0,0,0,0.08)', borderRadius:6, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.7rem', fontWeight:600, color:'#888', cursor:'pointer' }}
                    onClick={() => alert('Email change coming soon!')}>
                    Change
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ── SECTION: Company ── */}
          <div style={{ background:'#fff', border:'1px solid rgba(0,0,0,0.07)', borderRadius:14, padding:'28px 28px', marginBottom:18 }}>
            <div style={{ marginBottom:22 }}>
              <div style={{ fontSize:'0.68rem', fontWeight:600, textTransform:'uppercase' as const, letterSpacing:'2px', color:'#bbb', marginBottom:4, display:'flex', alignItems:'center', gap:7 }}>
                <span style={{ width:14, height:1.5, background:'#bbb', display:'inline-block' }} />Company
              </div>
              <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1.1rem', fontWeight:700, color:'#0a0a0a', letterSpacing:'-0.2px' }}>Firm information</div>
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
                <Field label="Firm Name" field="firmName" placeholder="Your firm name" icon={Building2} />
                <div>
                  <label style={{ fontSize:'0.68rem', fontWeight:600, textTransform:'uppercase' as const, letterSpacing:'0.1em', color:'#aaa', display:'block', marginBottom:6 }}>Firm Size</label>
                  <select value={formData.firmSize} onChange={e => change('firmSize', e.target.value)}
                    style={{ width:'100%', padding:'11px 14px', background:'#fafafa', border:'1px solid rgba(0,0,0,0.08)', borderRadius:10, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.85rem', color:'#111', outline:'none', appearance:'none' as const, cursor:'pointer' }}>
                    {['1-2','3-5','6-10','11+'].map(v => <option key={v} value={v}>{v} people</option>)}
                  </select>
                </div>
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
                <Field label="Work Email"    field="workEmail"   type="email" placeholder="work@firm.com"    icon={Mail}  />
                <Field label="Phone Number"  field="phoneNumber" type="tel"   placeholder="+1 234 567 8900"   icon={Phone} />
              </div>
              <Field label="Website" field="website" type="url" placeholder="https://yourfirm.com" icon={Globe} />
              <Field label="Branding Guidelines" field="guidelines" placeholder="Describe your tone, brand colors, key messages…" icon={AlignLeft} textarea />
            </div>
          </div>

          {/* ── SECTION: Preferences ── */}
          <div style={{ background:'#fff', border:'1px solid rgba(0,0,0,0.07)', borderRadius:14, padding:'28px 28px', marginBottom:28 }}>
            <div style={{ marginBottom:22 }}>
              <div style={{ fontSize:'0.68rem', fontWeight:600, textTransform:'uppercase' as const, letterSpacing:'2px', color:'#bbb', marginBottom:4, display:'flex', alignItems:'center', gap:7 }}>
                <span style={{ width:14, height:1.5, background:'#bbb', display:'inline-block' }} />Preferences
              </div>
              <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1.1rem', fontWeight:700, color:'#0a0a0a', letterSpacing:'-0.2px' }}>Usage</div>
            </div>
            <div>
              <label style={{ fontSize:'0.68rem', fontWeight:600, textTransform:'uppercase' as const, letterSpacing:'0.1em', color:'#aaa', display:'block', marginBottom:6 }}>Using Forma for</label>
              <select value={formData.usingFormaFor} onChange={e => change('usingFormaFor', e.target.value)}
                style={{ width:'100%', maxWidth:280, padding:'11px 14px', background:'#fafafa', border:'1px solid rgba(0,0,0,0.08)', borderRadius:10, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.85rem', color:'#111', outline:'none', appearance:'none' as const, cursor:'pointer' }}>
                <option>Personal Use</option>
                <option>Business Use</option>
                <option>Team Use</option>
              </select>
            </div>
          </div>

          {/* ── SAVE BAR ── */}
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', flexWrap:'wrap', gap:12 }}>
            <div style={{ fontSize:'0.8rem', color: saveError ? 'rgba(200,50,50,0.9)' : saved ? 'rgba(40,150,80,0.9)' : '#bbb' }}>
              {saveError ? `⚠ ${saveError}` : saved ? '✓ Changes saved successfully' : 'Changes will sync with Brand Assets'}
            </div>
            <div style={{ display:'flex', gap:10 }}>
              <button onClick={() => navigate('/dashboard')}
                style={{ padding:'11px 20px', background:'transparent', border:'1px solid rgba(0,0,0,0.1)', borderRadius:10, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.85rem', fontWeight:500, color:'#888', cursor:'pointer', transition:'all .2s' }}
                onMouseEnter={e => { (e.currentTarget).style.borderColor='rgba(0,0,0,0.2)'; (e.currentTarget).style.color='#111' }}
                onMouseLeave={e => { (e.currentTarget).style.borderColor='rgba(0,0,0,0.1)'; (e.currentTarget).style.color='#888' }}>
                Cancel
              </button>
              <button onClick={handleSave} disabled={saving}
                style={{ display:'flex', alignItems:'center', gap:8, padding:'11px 24px', background:'#0a0a0a', color:'#fff', border:'none', borderRadius:10, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.85rem', fontWeight:600, cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.7 : 1, transition:'all .2s' }}
                onMouseEnter={e => { if (!saving) { (e.currentTarget).style.background='#2a2a2a'; (e.currentTarget).style.transform='translateY(-1px)' }}}
                onMouseLeave={e => { (e.currentTarget).style.background='#0a0a0a'; (e.currentTarget).style.transform='none' }}>
                {saving
                  ? <><span style={{ width:13, height:13, border:'2px solid rgba(255,255,255,0.25)', borderTopColor:'#fff', borderRadius:'50%', display:'inline-block', animation:'st-spin .65s linear infinite' }} />Saving…</>
                  : saved
                  ? <><Check size={14} />Saved</>
                  : 'Save Changes'}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default Settings
