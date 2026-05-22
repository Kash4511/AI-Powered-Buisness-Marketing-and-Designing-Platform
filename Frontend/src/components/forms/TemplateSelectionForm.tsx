import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FileText, AlertCircle, ChevronLeft, CheckCircle, ArrowRight } from 'lucide-react'
import { dashboardApi } from '../../lib/dashboardApi'
import { apiClient } from '../../lib/apiClient'
import type { PDFTemplate } from '../../lib/dashboardApi'
import ImageUpload from './ImageUpload'
import modernFront from '../../images/tmp1-front.png'
import modernBack from '../../images/temp1-back.png'

const T = {
  bg:'#ffffff', bg2:'#f7f7f5', bg3:'#f0f0ec',
  dark:'#0a0a0a', bd:'rgba(0,0,0,0.08)', bd2:'rgba(0,0,0,0.15)',
  t1:'#111111', t2:'#666666', t3:'#aaaaaa',
} as const

const Styles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
    .tsf-card{position:relative;border:1.5px solid ${T.bd};border-radius:12px;overflow:hidden;cursor:pointer;transition:all 0.2s;background:#fff;}
    .tsf-card:hover{border-color:${T.bd2};transform:translateY(-2px);box-shadow:0 12px 32px rgba(0,0,0,0.08);}
    .tsf-card.sel{border-color:${T.dark};border-width:2px;box-shadow:0 0 0 3px rgba(0,0,0,0.06);}
    .tsf-thumb{position:relative;aspect-ratio:3/4;overflow:hidden;background:${T.bg2};}
    .tsf-thumb .img-primary{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:opacity 0.3s;}
    .tsf-thumb .img-hover{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity 0.3s;}
    .tsf-card:hover .img-hover{opacity:1;}
    .tsf-card:hover .img-primary{opacity:0;}
    .tsf-sel-badge{position:absolute;top:10px;right:10px;z-index:2;width:26px;height:26px;border-radius:50%;background:${T.dark};color:#fff;display:flex;align-items:center;justify-content:center;}
    .tsf-btn-p{display:inline-flex;align-items:center;gap:7px;padding:12px 24px;background:${T.dark};color:#fff;border:none;border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.85rem;font-weight:600;cursor:pointer;transition:all 0.2s;}
    .tsf-btn-p:hover:not(:disabled){background:#2a2a2a;transform:translateY(-1px);box-shadow:0 6px 20px rgba(0,0,0,0.15);}
    .tsf-btn-p:disabled{opacity:0.45;cursor:not-allowed;transform:none;box-shadow:none;}
    .tsf-btn-s{display:inline-flex;align-items:center;gap:6px;padding:11px 18px;background:none;border:1px solid ${T.bd2};border-radius:10px;font-family:'Instrument Sans',sans-serif;font-size:0.83rem;font-weight:500;color:${T.t2};cursor:pointer;transition:all 0.2s;}
    .tsf-btn-s:hover{border-color:rgba(0,0,0,0.25);color:${T.t1};background:${T.bg2};}
    @keyframes tsf-spin{to{transform:rotate(360deg);}}
    .tsf-spinner{animation:tsf-spin 0.8s linear infinite;}
  `}</style>
)

interface Props {
  onClose: ()=>void
  onSubmit: (templateId:string, templateName:string, architecturalImages?:File[])=>void
  loading?: boolean
}

const TemplateSelectionForm: React.FC<Props> = ({ onClose, onSubmit, loading=false }) => {
  const [templates, setTemplates]           = useState<PDFTemplate[]>([])
  const [selected, setSelected]             = useState<PDFTemplate|null>(null)
  const [fetching, setFetching]             = useState(true)
  const [error, setError]                   = useState<string|null>(null)
  const [showImageUpload, setShowImageUpload] = useState(false)
  const [elapsed, setElapsed]               = useState(0)
  const [imgErrors, setImgErrors]           = useState<Record<string,boolean>>({})

  useEffect(()=>{
    ;(async()=>{
      try {
        setFetching(true); setError(null)
        const data = await dashboardApi.getTemplates()
        const base = String(apiClient.defaults.baseURL||'').replace(/\/$/,'')
        const mapped:PDFTemplate[] = (data||[]).map((t:any)=>{
          const isModern=(t.name||'').toLowerCase().includes('modern')||(t.id||'').toLowerCase().startsWith('template')
          return {
            ...t,
            preview_url: isModern?`${base}/media/photo.png`:(t.preview_url||t.preview||t.thumbnail||t.image||null),
            hover_preview_url: isModern?`${base}/media/tempphoto1.png`:(t.hover_preview_url||null),
          }
        })
        setTemplates(mapped)
      } catch { setError('Failed to load templates. Please check your connection.') }
      finally { setFetching(false) }
    })()
  },[])

  useEffect(()=>{
    let t:ReturnType<typeof setInterval>|null=null
    if(loading){ setElapsed(0); t=setInterval(()=>setElapsed(s=>s+1),1000) }
    return ()=>{ if(t) clearInterval(t) }
  },[loading])

  const handleSubmit = () => {
    if(!selected){setError('Please select a template before continuing');return}
    setShowImageUpload(true)
  }

  const handleImagesSelected = (images:File[]) => {
    setShowImageUpload(false)
    if(selected) onSubmit(selected.id, selected.name, images)
  }

  const renderThumb = (template:PDFTemplate, index:number) => {
    const isModern=(template.name||'').toLowerCase().includes('modern')||(template.id||'').toLowerCase().startsWith('template')
    const hasErr=imgErrors[template.id]
    const eager=index<4

    if(isModern) return (
      <div className="tsf-thumb">
        <img src={modernFront} alt={`${template.name} front`} className="img-primary" loading={eager?"eager":"lazy"} onError={()=>setImgErrors(p=>({...p,[template.id]:true}))}/>
        <img src={modernBack}  alt={`${template.name} back`}  className="img-hover"   loading="lazy"                onError={()=>setImgErrors(p=>({...p,[template.id]:true}))}/>
      </div>
    )

    if(hasErr||!template.preview_url) return (
      <div className="tsf-thumb" style={{display:'flex',alignItems:'center',justifyContent:'center',background:T.bg3}}>
        <FileText size={40} color={T.t3}/>
      </div>
    )

    return (
      <div className="tsf-thumb">
        <img src={template.preview_url} alt={template.name} className="img-primary" loading={eager?"eager":"lazy"} onError={()=>setImgErrors(p=>({...p,[template.id]:true}))}/>
        {template.hover_preview_url&&(
          <img src={template.hover_preview_url} alt={`${template.name} hover`} className="img-hover" loading="lazy" onError={()=>setImgErrors(p=>({...p,[template.id]:true}))}/>
        )}
      </div>
    )
  }

  /* ── IMAGE UPLOAD SCREEN ── */
  if(showImageUpload) return (
    <div style={{background:'#fff'}}>
      <ImageUpload onImagesSelected={handleImagesSelected} onClose={()=>setShowImageUpload(false)}/>
    </div>
  )

  /* ── LOADING ── */
  if(fetching) return (
    <>
      <Styles/>
      <div style={{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:'80px 40px',gap:14,background:'#fff'}}>
        <div style={{width:36,height:36,border:`3px solid ${T.bg3}`,borderTopColor:T.dark,borderRadius:'50%',animation:'tsf-spin 0.8s linear infinite'}}/>
        <div style={{fontFamily:"'Fraunces',serif",fontSize:'1rem',fontWeight:700,color:T.dark}}>Loading templates…</div>
        <div style={{fontSize:'0.8rem',color:T.t3}}>Fetching your available formats</div>
      </div>
    </>
  )

  /* ── ERROR ── */
  if(error&&templates.length===0) return (
    <>
      <Styles/>
      <div style={{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:'80px 40px',gap:16,background:'#fff',textAlign:'center'}}>
        <div style={{width:48,height:48,background:'#fff2f2',border:'1px solid rgba(200,50,50,0.15)',borderRadius:13,display:'flex',alignItems:'center',justifyContent:'center'}}>
          <AlertCircle size={22} color="#c03030"/>
        </div>
        <div style={{fontFamily:"'Fraunces',serif",fontSize:'1.05rem',fontWeight:700,color:T.dark}}>Couldn't load templates</div>
        <div style={{fontSize:'0.82rem',color:T.t2,maxWidth:320}}>{error}</div>
        <button className="tsf-btn-p" onClick={()=>window.location.reload()}>Try again</button>
      </div>
    </>
  )

  return (
    <>
      <Styles/>

      {/* HEADER */}
      <div style={{padding:'20px 28px',borderBottom:`1px solid ${T.bd}`,background:'#fff',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
        <div>
          <div style={{fontFamily:"'Fraunces',serif",fontSize:'1rem',fontWeight:700,color:T.dark,letterSpacing:'-0.2px',marginBottom:2}}>
            Choose a Template
          </div>
          <div style={{fontSize:'0.75rem',color:T.t3}}>
            {selected?`Selected: ${selected.name}`:'Click a template to select it'}
          </div>
        </div>
        {error&&(
          <div style={{fontSize:'0.78rem',color:'#b00020',background:'#fff2f2',border:'1px solid rgba(200,50,50,0.15)',borderRadius:8,padding:'7px 12px'}}>
            {error}
          </div>
        )}
      </div>

      {/* TEMPLATE GRID */}
      <div style={{padding:'24px 28px',background:'#fff'}}>
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(200px,1fr))',gap:16}}>
          {templates.map((t,i)=>(
            <motion.div
              key={t.id}
              className={`tsf-card${selected?.id===t.id?' sel':''}`}
              onClick={()=>setSelected(t)}
              whileHover={{scale:1.01}}
              whileTap={{scale:0.99}}
            >
              {selected?.id===t.id&&(
                <div className="tsf-sel-badge"><CheckCircle size={14}/></div>
              )}
              {renderThumb(t,i)}
              <div style={{padding:'12px 14px',borderTop:`1px solid ${T.bd}`}}>
                <div style={{fontFamily:"'Fraunces',serif",fontSize:'0.88rem',fontWeight:700,color:T.dark,letterSpacing:'-0.2px',marginBottom:2}}>{t.name}</div>
                {t.description&&<div style={{fontSize:'0.72rem',color:T.t2,lineHeight:1.5}}>{t.description}</div>}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* FOOTER */}
      <div style={{padding:'18px 28px',borderTop:`1px solid ${T.bd}`,display:'flex',alignItems:'center',justifyContent:'space-between',background:T.bg2}}>
        <div style={{fontSize:'0.72rem',color:T.t3}}>
          {selected?'Ready to continue with your selected template':'Select a template to proceed'}
        </div>
        <div style={{display:'flex',gap:10}}>
          <button className="tsf-btn-s" onClick={onClose}><ChevronLeft size={15}/> Back</button>
          <button className="tsf-btn-p" onClick={handleSubmit} disabled={!selected||loading}>
            {loading
              ? <><div style={{width:14,height:14,border:'2px solid rgba(255,255,255,0.3)',borderTopColor:'#fff',borderRadius:'50%'}} className="tsf-spinner"/> Processing… ({elapsed}s)</>
              : <>Continue <ArrowRight size={14}/></>}
          </button>
        </div>
      </div>

      {/* LOADING OVERLAY */}
      {loading&&(
        <div style={{position:'fixed',inset:0,background:'rgba(255,255,255,0.85)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:200,backdropFilter:'blur(4px)'}}>
          <div style={{background:'#fff',border:`1px solid ${T.bd}`,borderRadius:16,padding:'36px 48px',textAlign:'center',display:'flex',flexDirection:'column',alignItems:'center',gap:14}}>
            <div style={{width:40,height:40,border:`3px solid ${T.bg3}`,borderTopColor:T.dark,borderRadius:'50%'}} className="tsf-spinner"/>
            <div style={{fontFamily:"'Fraunces',serif",fontSize:'1.05rem',fontWeight:700,color:T.dark,letterSpacing:'-0.2px'}}>
              Creating your lead magnet…
            </div>
            <div style={{fontSize:'0.82rem',color:T.t2}}>AI is generating your PDF. This can take up to 30 seconds.</div>
            <div style={{display:'inline-flex',alignItems:'center',gap:6,background:T.bg2,border:`1px solid ${T.bd}`,borderRadius:20,padding:'4px 14px',fontSize:'0.75rem',color:T.t2}}>
              <span style={{width:5,height:5,borderRadius:'50%',background:T.dark,flexShrink:0}}/>
              {elapsed}s elapsed
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default TemplateSelectionForm