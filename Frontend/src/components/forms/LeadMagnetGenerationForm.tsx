import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, ArrowLeft, Sparkles } from 'lucide-react'
import type { LeadMagnetGeneration } from '../../lib/dashboardApi'
import { dashboardApi } from '../../lib/dashboardApi'

const T = {
  bg:'#ffffff', bg2:'#f7f7f5', bg3:'#f0f0ec',
  dark:'#0a0a0a', bd:'rgba(0,0,0,0.08)', bd2:'rgba(0,0,0,0.15)',
  t1:'#111111', t2:'#666666', t3:'#aaaaaa',
} as const

const Styles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
    .lmf-chip{position:relative;display:flex;align-items:center;justify-content:center;padding:11px 14px;border:1px solid ${T.bd};border-radius:9px;cursor:pointer;transition:all 0.15s;background:${T.bg2};font-family:'Instrument Sans',sans-serif;font-size:0.82rem;font-weight:500;color:${T.t2};text-align:center;user-select:none;}
    .lmf-chip:hover{border-color:${T.bd2};color:${T.t1};background:#fff;}
    .lmf-chip.sel{background:${T.dark};border-color:${T.dark};color:#fff;font-weight:600;}
    .lmf-chip input{position:absolute;opacity:0;pointer-events:none;}
    .lmf-chk{display:flex;align-items:center;gap:9px;padding:10px 14px;border:1px solid ${T.bd};border-radius:9px;cursor:pointer;transition:all 0.15s;background:${T.bg2};font-family:'Instrument Sans',sans-serif;font-size:0.82rem;font-weight:500;color:${T.t2};user-select:none;}
    .lmf-chk:hover{border-color:${T.bd2};color:${T.t1};background:#fff;}
    .lmf-chk.sel{background:${T.dark};border-color:${T.dark};color:#fff;}
    .lmf-chk input{position:absolute;opacity:0;pointer-events:none;}
    .lmf-chkbox{width:16px;height:16px;border-radius:4px;border:1.5px solid currentColor;display:flex;align-items:center;justify-content:center;flex-shrink:0;opacity:0.5;}
    .lmf-chk.sel .lmf-chkbox{opacity:1;background:rgba(255,255,255,0.2);border-color:rgba(255,255,255,0.5);}
    .lmf-ta{width:100%;padding:12px 14px;background:${T.bg2};border:1px solid ${T.bd};border-radius:9px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;color:${T.t1};outline:none;resize:vertical;transition:all 0.2s;line-height:1.6;}
    .lmf-ta:focus{border-color:${T.bd2};background:#fff;box-shadow:0 0 0 3px rgba(0,0,0,0.04);}
    .lmf-ta::placeholder{color:${T.t3};}
    .lmf-in{width:100%;padding:11px 14px;background:${T.bg2};border:1px solid ${T.bd};border-radius:9px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;color:${T.t1};outline:none;transition:all 0.2s;}
    .lmf-in:focus{border-color:${T.bd2};background:#fff;box-shadow:0 0 0 3px rgba(0,0,0,0.04);}
    .lmf-in::placeholder{color:${T.t3};}
    .lmf-btn-p{display:inline-flex;align-items:center;gap:7px;padding:11px 22px;background:${T.dark};color:#fff;border:none;border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;font-weight:600;cursor:pointer;transition:all 0.2s;}
    .lmf-btn-p:hover:not(:disabled){background:#2a2a2a;transform:translateY(-1px);box-shadow:0 6px 20px rgba(0,0,0,0.15);}
    .lmf-btn-p:disabled{opacity:0.45;cursor:not-allowed;transform:none;box-shadow:none;}
    .lmf-btn-s{display:inline-flex;align-items:center;gap:7px;padding:11px 18px;background:none;border:1px solid ${T.bd2};border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;font-weight:500;color:${T.t2};cursor:pointer;transition:all 0.2s;}
    .lmf-btn-s:hover:not(:disabled){border-color:rgba(0,0,0,0.25);color:${T.t1};background:${T.bg2};}
    .lmf-btn-s:disabled{opacity:0.45;cursor:not-allowed;}
    .lmf-btn-g{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;background:${T.bg2};border:1px solid ${T.bd};border-radius:8px;font-family:'Instrument Sans',sans-serif;font-size:0.78rem;font-weight:500;color:${T.t2};cursor:pointer;transition:all 0.2s;}
    .lmf-btn-g:hover:not(:disabled){border-color:${T.bd2};color:${T.t1};}
    .lmf-btn-g:disabled{opacity:0.45;cursor:not-allowed;}
    @keyframes lmf-spin{to{transform:rotate(360deg);}}
  `}</style>
)

const LEAD_MAGNET_TYPES = [
  {value:'guide',label:'Guide'},{value:'case-study',label:'Case Study'},
  {value:'checklist',label:'Checklist'},{value:'roi-calculator',label:'ROI Calculator'},
  {value:'trends-report',label:'Trends Report'},{value:'onboarding-flow',label:'Client Onboarding Flow'},
  {value:'design-portfolio',label:'Design Portfolio'},{value:'custom',label:'Custom'},
]
const MAIN_TOPICS = [
  {value:'sustainable-architecture',label:'Sustainable Architecture'},{value:'smart-homes',label:'Smart Homes'},
  {value:'adaptive-reuse',label:'Adaptive Reuse'},{value:'wellness-biophilic',label:'Wellness / Biophilic'},
  {value:'modular-prefab',label:'Modular / Prefab'},{value:'urban-placemaking',label:'Urban Placemaking'},
  {value:'passive-house',label:'Passive House / Net-Zero'},{value:'climate-resilient',label:'Climate-Resilient'},
  {value:'project-roi',label:'Project ROI'},{value:'branding-differentiation',label:'Branding & Differentiation'},
  {value:'custom',label:'Custom'},
]
const TARGET_AUDIENCES = ['Homeowners','Developers','Commercial Clients','Government','Architects/Peers','Contractors','Real Estate Agents','Nonprofits','Facility Managers','Other']
const PAIN_POINTS = ['High costs','ROI uncertainty','Compliance issues','Sustainability demands','Risk management','Long timelines','Tech complexity','Poor communication','Competition','Approvals','Energy efficiency','Health/Wellness','Vendor reliability','Other']

const STEPS = ['Type & Topic','Target Audience','Pain Points','Outcome & CTA']

interface Props { onSubmit:(data:LeadMagnetGeneration)=>void; loading?:boolean }

const LeadMagnetGenerationForm: React.FC<Props> = ({ onSubmit, loading=false }) => {
  const [fd, setFd] = useState<Partial<LeadMagnetGeneration>>({
    lead_magnet_type:'guide', main_topic:'sustainable-architecture',
    target_audience:[], audience_pain_points:[],
    desired_outcome:'', call_to_action:'', special_requests:'',
  })
  const [step, setStep]           = useState(0)
  const [sloganLoading, setSL]    = useState(false)
  const [sloganError, setSE]      = useState('')

  const set = (f:keyof LeadMagnetGeneration, v:string|string[]) => {
    if (f==='desired_outcome'||f==='call_to_action') setSE('')
    setFd(p=>({...p,[f]:v}))
  }
  const toggle = (f:'target_audience'|'audience_pain_points', item:string) => {
    const cur = (fd[f] as string[])||[]
    set(f, cur.includes(item)?cur.filter(i=>i!==item):[...cur,item])
  }

  const isValid = () => {
    switch(step){
      case 0: return !!(fd.lead_magnet_type&&fd.main_topic)
      case 1: return (fd.target_audience?.length??0)>0
      case 2: return (fd.audience_pain_points?.length??0)>0
      case 3: return !!(fd.desired_outcome&&fd.call_to_action)
      default:return false
    }
  }

  const next = () => {
    if(step<STEPS.length-1){setStep(s=>s+1);return}
    const out=(fd.desired_outcome||'').trim(), cta=(fd.call_to_action||'').trim()
    if(out.length<15){setSE('Please describe your desired outcome in at least 15 characters');return}
    if(cta.length<15){setSE('Please describe your call to action in at least 15 characters');return}
    setSE(''); onSubmit(fd as LeadMagnetGeneration)
  }

  const generateSlogan = async () => {
    setSL(true); setSE('')
    try {
      const fp = await dashboardApi.getFirmProfile()
      const r  = await dashboardApi.generateSlogan({user_answers:fd as unknown as Record<string,unknown>, firm_profile:fp as unknown as Record<string,unknown>})
      set('special_requests', r.slogan)
    } catch { setSE('Failed to generate slogan. Please try again.') }
    finally { setSL(false) }
  }

  const Label = ({children,optional}:{children:React.ReactNode;optional?:boolean}) => (
    <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
      <span style={{fontSize:'0.78rem',fontWeight:600,color:T.t1}}>{children}</span>
      {optional&&<span style={{fontSize:'0.68rem',color:T.t3,fontWeight:400}}>optional</span>}
    </div>
  )

  const Tick = () => (
    <svg width="9" height="7" viewBox="0 0 9 7" fill="none">
      <path d="M1 3.5L3.5 6L8 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )

  const renderStep = () => {
    const variants = {initial:{opacity:0,x:12},animate:{opacity:1,x:0},exit:{opacity:0,x:-12}}
    switch(step){
      case 0: return (
        <motion.div key="s0" {...variants}>
          <div style={{marginBottom:28}}>
            <Label>Lead Magnet Type *</Label>
            <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
              {LEAD_MAGNET_TYPES.map(t=>(
                <label key={t.value} className={`lmf-chip${fd.lead_magnet_type===t.value?' sel':''}`}>
                  <input type="radio" name="lmt" value={t.value} checked={fd.lead_magnet_type===t.value} onChange={e=>set('lead_magnet_type',e.target.value)}/>
                  {t.label}
                </label>
              ))}
            </div>
          </div>
          <div>
            <Label>Main Topic *</Label>
            <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
              {MAIN_TOPICS.map(t=>(
                <label key={t.value} className={`lmf-chip${fd.main_topic===t.value?' sel':''}`}>
                  <input type="radio" name="mt" value={t.value} checked={fd.main_topic===t.value} onChange={e=>set('main_topic',e.target.value)}/>
                  {t.label}
                </label>
              ))}
            </div>
          </div>
        </motion.div>
      )
      case 1: return (
        <motion.div key="s1" {...variants}>
          <Label>Target Audience — select all that apply *</Label>
          <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:8}}>
            {TARGET_AUDIENCES.map(a=>{
              const chk=(fd.target_audience||[]).includes(a)
              return(
                <label key={a} className={`lmf-chk${chk?' sel':''}`}>
                  <input type="checkbox" checked={chk} onChange={()=>toggle('target_audience',a)}/>
                  <div className="lmf-chkbox">{chk&&<Tick/>}</div>
                  {a}
                </label>
              )
            })}
          </div>
        </motion.div>
      )
      case 2: return (
        <motion.div key="s2" {...variants}>
          <Label>Audience Pain Points — select all that apply *</Label>
          <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:8}}>
            {PAIN_POINTS.map(p=>{
              const chk=(fd.audience_pain_points||[]).includes(p)
              return(
                <label key={p} className={`lmf-chk${chk?' sel':''}`}>
                  <input type="checkbox" checked={chk} onChange={()=>toggle('audience_pain_points',p)}/>
                  <div className="lmf-chkbox">{chk&&<Tick/>}</div>
                  {p}
                </label>
              )
            })}
          </div>
        </motion.div>
      )
      case 3: return (
        <motion.div key="s3" {...variants} style={{display:'flex',flexDirection:'column',gap:20}}>
          <div>
            <Label>Desired Outcome / Solution *</Label>
            <textarea className="lmf-ta" rows={4} value={fd.desired_outcome||''} onChange={e=>set('desired_outcome',e.target.value)} placeholder="Describe the main outcome or solution your lead magnet will provide…"/>
          </div>
          <div>
            <Label>Call-to-Action *</Label>
            <input className="lmf-in" type="text" value={fd.call_to_action||''} onChange={e=>set('call_to_action',e.target.value)} placeholder="e.g., Schedule Consultation, Download Portfolio, Get Quote"/>
          </div>
          <div>
            <Label optional>Special Requests or Additional Sections</Label>
            <textarea className="lmf-ta" rows={3} value={fd.special_requests||''} onChange={e=>set('special_requests',e.target.value)} placeholder="Any specific requirements, additional sections, or customizations…"/>
            <div style={{marginTop:10}}>
              <button type="button" className="lmf-btn-g" onClick={generateSlogan} disabled={sloganLoading}>
                {sloganLoading
                  ? <><div style={{width:12,height:12,border:`2px solid ${T.bd}`,borderTopColor:T.t2,borderRadius:'50%',animation:'lmf-spin 0.8s linear infinite'}}/> Generating…</>
                  : <><Sparkles size={12}/> Generate Slogan</>}
              </button>
            </div>
            {sloganError && (
              <div style={{marginTop:10,fontSize:'0.78rem',color:'#b00020',background:'#fff2f2',border:'1px solid rgba(200,50,50,0.15)',borderRadius:8,padding:'9px 13px'}}>
                {sloganError}
              </div>
            )}
          </div>
        </motion.div>
      )
      default: return null
    }
  }

  return (
    <>
      <Styles/>

      {/* HEADER */}
      <div style={{padding:'20px 28px',borderBottom:`1px solid ${T.bd}`,background:'#fff'}}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:12}}>
          <span style={{fontFamily:"'Fraunces',serif",fontSize:'1rem',fontWeight:700,color:T.dark,letterSpacing:'-0.2px'}}>
            {STEPS[step]}
          </span>
          <span style={{fontSize:'0.72rem',color:T.t3}}>Step {step+1} of {STEPS.length}</span>
        </div>
        {/* Segmented progress */}
        <div style={{display:'flex',gap:6,marginBottom:8}}>
          {STEPS.map((_,i)=>(
            <div key={i} style={{flex:1,height:3,borderRadius:2,background:i<=step?T.dark:T.bg3,transition:'background 0.3s'}}/>
          ))}
        </div>
        <div style={{display:'flex',justifyContent:'space-between'}}>
          {STEPS.map((s,i)=>(
            <span key={s} style={{fontSize:'0.62rem',color:i===step?T.t1:i<step?T.t2:T.t3,fontWeight:i===step?600:400,transition:'color 0.2s'}}>
              {s}
            </span>
          ))}
        </div>
      </div>

      {/* BODY */}
      <div style={{padding:'28px',background:'#fff',minHeight:300}}>
        <AnimatePresence mode="wait">{renderStep()}</AnimatePresence>
      </div>

      {/* FOOTER */}
      <div style={{padding:'18px 28px',borderTop:`1px solid ${T.bd}`,display:'flex',alignItems:'center',justifyContent:'space-between',background:T.bg2}}>
        <span style={{fontSize:'0.72rem',color:T.t3}}>
          {step===STEPS.length-1?'Required fields must be at least 15 characters':'Select options to continue'}
        </span>
        <div style={{display:'flex',gap:10}}>
          {step>0&&(
            <button className="lmf-btn-s" onClick={()=>setStep(s=>s-1)} disabled={loading}>
              <ArrowLeft size={14}/> Previous
            </button>
          )}
          <button className="lmf-btn-p" onClick={next} disabled={!isValid()||loading}>
            {loading
              ? <><div style={{width:14,height:14,border:'2px solid rgba(255,255,255,0.3)',borderTopColor:'#fff',borderRadius:'50%',animation:'lmf-spin 0.8s linear infinite'}}/> Creating…</>
              : step===STEPS.length-1
                ? <>Create Lead Magnet <ArrowRight size={14}/></>
                : <>Continue <ArrowRight size={14}/></>}
          </button>
        </div>
      </div>
    </>
  )
}

export default LeadMagnetGenerationForm