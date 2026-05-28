import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, Plus, Settings, LogOut, Palette, Send, File as PdfIcon, X, Sparkles, ArrowRight, Download } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import Modal from './Modal'
import TemplateSelectionForm from './forms/TemplateSelectionForm'
import { apiClient } from '../lib/apiClient'

/* ── TOKENS ── */
const T = {
  bg:'#ffffff', bg2:'#f7f7f5', bg3:'#f0f0ec',
  dark:'#0a0a0a', bd:'rgba(0,0,0,0.08)', bd2:'rgba(0,0,0,0.15)',
  t1:'#111111', t2:'#666666', t3:'#aaaaaa',
} as const

const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
    * { box-sizing:border-box; margin:0; padding:0; }
    body { font-family:'Instrument Sans',sans-serif; }
    a { text-decoration:none; color:inherit; }
    .fai-nav-item { display:flex; align-items:center; gap:9px; padding:9px 10px; border-radius:8px; font-size:0.82rem; font-weight:500; color:${T.t2}; text-decoration:none; cursor:pointer; transition:all 0.15s; font-family:'Instrument Sans',sans-serif; }
    .fai-nav-item:hover, .fai-nav-item.active { background:${T.bg2}; color:${T.t1}; }
    .fai-nav-item.active svg { color:${T.t1} !important; }
    .fai-logout-btn { display:flex; align-items:center; gap:6px; background:none; border:1px solid ${T.bd}; border-radius:8px; padding:7px 14px; font-family:'Instrument Sans',sans-serif; font-size:0.78rem; font-weight:500; color:${T.t2}; cursor:pointer; transition:all 0.2s; }
    .fai-logout-btn:hover { border-color:${T.bd2}; color:${T.t1}; background:${T.bg2}; }
    .fai-sidebar-create { display:flex; align-items:center; justify-content:center; gap:8px; width:100%; padding:11px 14px; background:${T.dark}; color:#fff; border:none; border-radius:10px; font-family:'Instrument Sans',sans-serif; font-size:0.82rem; font-weight:600; cursor:pointer; transition:all 0.2s; }
    .fai-sidebar-create:hover { background:#2a2a2a; transform:translateY(-1px); box-shadow:0 6px 20px rgba(0,0,0,0.15); }
    .fai-send-btn { display:inline-flex; align-items:center; gap:7px; padding:10px 18px; background:${T.dark}; color:#fff; border:none; border-radius:9px; font-family:'Instrument Sans',sans-serif; font-size:0.82rem; font-weight:600; cursor:pointer; transition:all 0.2s; flex-shrink:0; }
    .fai-send-btn:hover:not(:disabled) { background:#2a2a2a; }
    .fai-send-btn:disabled { opacity:0.4; cursor:not-allowed; }
    .fai-attach-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 12px; background:${T.bg2}; border:1px solid ${T.bd}; border-radius:8px; font-family:'Instrument Sans',sans-serif; font-size:0.78rem; font-weight:500; color:${T.t2}; cursor:pointer; transition:all 0.2s; }
    .fai-attach-btn:hover { border-color:${T.bd2}; color:${T.t1}; }
    .fai-attach-btn.has-template { background:${T.dark}; border-color:${T.dark}; color:#fff; }
    .fai-chat-ta { width:100%; resize:none; border:none; outline:none; font-family:'Instrument Sans',sans-serif; font-size:0.88rem; color:${T.t1}; background:transparent; line-height:1.6; min-height:24px; max-height:200px; overflow-y:auto; }
    .fai-chat-ta::placeholder { color:${T.t3}; }
    @keyframes fai-spin { to { transform:rotate(360deg); } }
    @keyframes fai-pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
  `}</style>
)

/* ── MESSAGE TYPE ── */
interface Message {
  id: number
  role: 'user' | 'assistant' | 'error' | 'system' | 'pdf'
  text: string
  pdfUrl?: string
  pdfTitle?: string
}

const FormaAI: React.FC = () => {
  const { logout } = useAuth()
  const navigate   = useNavigate()

  const [message, setMessage]                   = useState('')
  const [messages, setMessages]                 = useState<Message[]>([])
  const [showTemplateModal, setShowTemplateModal] = useState(false)
  const [selectedTemplateId, setSelectedTemplateId]     = useState('')
  const [selectedTemplateName, setSelectedTemplateName] = useState('')
  const [architecturalImages, setArchitecturalImages]   = useState<File[]>([])
  const [isGenerating, setIsGenerating]         = useState(false)
  const [progress, setProgress]                 = useState(0)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [previewUrl, setPreviewUrl]             = useState<string|null>(null)
  const [templateError, setTemplateError]       = useState<string|null>(null)
  const [detectedType, setDetectedType]         = useState<string|null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef    = useRef<HTMLTextAreaElement>(null)
  const timers         = useRef<number[]>([])
  const msgId          = useRef(0)

  const addMsg = (role: Message['role'], text: string) => {
    msgId.current += 1
    setMessages(prev => [...prev, { id: msgId.current, role, text }])
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior:'smooth' })
  }, [messages])

  const handleTemplateSelect = (tId: string, tName: string, images?: File[]) => {
    setSelectedTemplateId(tId)
    setSelectedTemplateName(tName)
    setTemplateError(null)
    if (images?.length) setArchitecturalImages(images)
    setShowTemplateModal(false)
  }

  /* ─────────────────────────────────────────────
     SEND — fixes the 500:
     • Sends JSON (not FormData) when no binary files
     • Architectural images are sent as base64 strings
     • Proper error decoding from ArrayBuffer
  ───────────────────────────────────────────── */
  const handleSend = async () => {
    const text = message.trim()
    if (!text) return

    if (!selectedTemplateId) {
      setTemplateError('Please choose a template before sending.')
      return
    }

    addMsg('user', text)
    setMessage('')
    if (textareaRef.current) { textareaRef.current.style.height = 'auto' }
    setTemplateError(null)
    setIsGenerating(true)
    setProgress(0)

    timers.current.forEach(t => window.clearTimeout(t))
    timers.current = []
    timers.current.push(window.setTimeout(() => setProgress(30), 800))
    timers.current.push(window.setTimeout(() => setProgress(65), 2500))

    try {
      // Convert architectural images to base64 so we can send JSON (avoids FormData parsing issues on Django)
      const imageDataUrls: string[] = await Promise.all(
        architecturalImages.slice(0, 6).map(file =>
          new Promise<string>((res, rej) => {
            const reader = new FileReader()
            reader.onload  = () => res(reader.result as string)
            reader.onerror = rej
            reader.readAsDataURL(file)
          })
        )
      )

      const payload = {
        message:               text,
        generate_pdf:          true,
        template_id:           selectedTemplateId,
        architectural_images:  imageDataUrls,   // base64 array — Django can decode these
      }

      // POST to new clean endpoint — returns 202 JSON with job_id
      const res = await apiClient.post('/api/ai-chat/', payload, {
        headers: { 'Content-Type': 'application/json' },
      })

      const data = res.data
      if (data?.job_id) {
        const typeLabel = data?.lm_label ?? 'lead magnet'
        const lmTitle   = `${typeLabel}: ${text.slice(0, 60)}${text.length > 60 ? '…' : ''}`
        addMsg('system', `✦ Generating your ${typeLabel}… this takes 2–5 minutes.`)

        // Poll for completion
        await pollForPDF(data.job_id, lmTitle)
      } else if (data?.message) {
        addMsg('assistant', data.message)
      }
    } catch (err: any) {
      const errData = err?.response?.data
      let errMsg = 'Something went wrong. Please try again.'
      if (typeof errData === 'object' && errData !== null) {
        errMsg = errData.error ?? errData.details ?? errData.message ?? errMsg
      } else if (err?.message) {
        errMsg = err.message
      }
      // 400 means missing type — show as assistant guidance, not red error
      if (err?.response?.status === 400) {
        addMsg('assistant', errMsg)
      } else {
        addMsg('error', errMsg)
      }
    } finally {
      setProgress(100)
      setIsGenerating(false)
      timers.current.forEach(t => window.clearTimeout(t))
      timers.current = []
    }
  }

  /* ── Poll job until complete, then show PDF inline ── */
  const pollForPDF = async (jobId: string, title: string) => {
    const MAX_POLLS  = 90   // 90 × 4s = 6 minutes max
    const INTERVAL   = 4000 // 4 seconds

    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise(r => setTimeout(r, INTERVAL))
      try {
        const status = await apiClient.get(`/api/pdf-generation/status/${jobId}/`)
        const job    = status.data

        if (job.status === 'complete' || job.status === 'completed') {
          // Job done — use the PDF URL directly for the iframe preview.
          // Cloudinary URLs do not set X-Frame-Options, avoiding "sameorigin" blocks.
          let pdfUrl = job.pdf_url || ''
          
          if (pdfUrl) {
            // Add PDF preview message using the direct URL
            msgId.current += 1
            setMessages(prev => [...prev, {
              id:       msgId.current,
              role:     'pdf',
              text:     title,
              pdfUrl:   pdfUrl,
              pdfTitle: title,
            }])
          } else {
            // Fallback: If pdf_url is missing from status, try to get it from the download endpoint
            try {
              const res = await apiClient.get(`/api/lead-magnets/${job.lead_magnet_id}/download/`)
              if (res.data?.pdf_url) {
                msgId.current += 1
                setMessages(prev => [...prev, {
                  id:       msgId.current,
                  role:     'pdf',
                  text:     title,
                  pdfUrl:   res.data.pdf_url,
                  pdfTitle: title,
                }])
                return
              }
            } catch (err) {
              console.error('Fallback download URL fetch error:', err)
            }
            addMsg('assistant', `✅ Your ${title} is ready! Check your dashboard to download it.`)
          }
          return
        }

        if (job.status === 'failed' || job.status === 'error') {
          addMsg('error', `Generation failed: ${job.error || 'Unknown error'}`)
          return
        }

        // Still processing — update the last system message with progress
        const pct = job.progress ?? 0
        const msg = job.message  ?? 'Processing…'
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.role === 'system' && last.text.startsWith('✦')) {
            return [...prev.slice(0, -1), { ...last, text: `✦ ${msg} (${pct}%)` }]
          }
          return prev
        })
      } catch {
        // polling error — keep trying silently
      }
    }
    // Timed out
    addMsg('error', 'Generation is taking longer than expected. Check your dashboard — it may still complete.')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  /* ── SIDEBAR NAV ── */
  const navItems = [
    { id:'magnets',  label:'My Lead Magnets', icon:<FileText size={16}/>,  href:'/dashboard' },
    { id:'ai',       label:'Forma AI',        icon:<Sparkles size={16}/>,  href:'/forma-ai'  },
    { id:'brand',    label:'Brand Assets',    icon:<Palette size={16}/>,   href:'/brand-assets' },
    { id:'settings', label:'Settings',        icon:<Settings size={16}/>,  href:'/settings' },
  ]

  /* ── MESSAGE BUBBLE ── */
  const Bubble = ({ msg }: { msg: Message }) => {
    const isUser   = msg.role === 'user'
    const isError  = msg.role === 'error'
    const isSystem = msg.role === 'system'
    const isPDF    = msg.role === 'pdf'

    if (isSystem) return (
      <div style={{ display:'flex', justifyContent:'center', margin:'8px 0' }}>
        <span style={{ display:'inline-flex', alignItems:'center', gap:6, background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:20, padding:'4px 14px', fontSize:'0.75rem', color:T.t2 }}>
          {msg.text}
        </span>
      </div>
    )

    if (isPDF) return (
      <motion.div
        initial={{ opacity:0, y:10 }}
        animate={{ opacity:1, y:0 }}
        style={{ marginBottom:16 }}
      >
        {/* PDF preview card */}
        <div style={{ background:'#fff', border:`1px solid ${T.bd}`, borderRadius:14, overflow:'hidden', maxWidth:540 }}>
          {/* Card header */}
          <div style={{ padding:'14px 18px', borderBottom:`1px solid ${T.bd}`, display:'flex', alignItems:'center', gap:10 }}>
            <div style={{ width:32, height:32, background:T.dark, borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
              <FileText size={15} color="#fff"/>
            </div>
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ fontFamily:"'Fraunces',serif", fontSize:'0.88rem', fontWeight:700, color:T.dark, letterSpacing:'-0.2px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {msg.pdfTitle}
              </div>
              <div style={{ fontSize:'0.68rem', color:T.t3, marginTop:1 }}>PDF ready — preview below</div>
            </div>
            {/* Download button */}
            <a
              href={msg.pdfUrl}
              download={`${msg.pdfTitle ?? 'lead-magnet'}.pdf`}
              style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'8px 14px', background:T.dark, color:'#fff', borderRadius:8, fontSize:'0.75rem', fontWeight:600, textDecoration:'none', flexShrink:0, fontFamily:"'Instrument Sans',sans-serif" }}
            >
              <Download size={13}/> Download PDF
            </a>
          </div>
          {/* Iframe preview */}
          <div style={{ height:480, background:T.bg2, position:'relative' }}>
            <iframe
              src={msg.pdfUrl}
              title={msg.pdfTitle}
              style={{ width:'100%', height:'100%', border:'none' }}
            />
          </div>
        </div>
      </motion.div>
    )

    return (
      <motion.div
        initial={{ opacity:0, y:8 }}
        animate={{ opacity:1, y:0 }}
        style={{
          display:'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: 12,
        }}
      >
        {/* Assistant avatar */}
        {!isUser && (
          <div style={{ width:28, height:28, borderRadius:'50%', background: isError ? '#fff2f2' : T.dark, border: isError ? '1px solid rgba(200,50,50,0.2)' : 'none', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, marginRight:10, marginTop:2 }}>
            {isError
              ? <span style={{ fontSize:13 }}>⚠</span>
              : <Sparkles size={13} color="#fff"/>}
          </div>
        )}

        <div style={{
          maxWidth:'72%',
          padding:'11px 15px',
          borderRadius: isUser ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
          background: isUser ? T.dark : isError ? '#fff2f2' : '#fff',
          border: isUser ? 'none' : isError ? '1px solid rgba(200,50,50,0.15)' : `1px solid ${T.bd}`,
          color: isUser ? '#fff' : isError ? '#b00020' : T.t1,
          fontSize: '0.85rem',
          lineHeight: 1.6,
          fontFamily:"'Instrument Sans',sans-serif",
          whiteSpace:'pre-wrap',
          wordBreak:'break-word',
        }}>
          {msg.text}
        </div>
      </motion.div>
    )
  }

  return (
    <>
      <GlobalStyles/>

      {/* ════════ NAV ════════ */}
      <nav style={{ height:62, display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 36px', background:'#fff', borderBottom:`1px solid ${T.bd}`, position:'sticky', top:0, zIndex:100 }}>
        <div style={{ fontFamily:"'Fraunces',serif", fontWeight:900, fontSize:'1.35rem', color:T.dark, letterSpacing:'-0.5px' }}>Forma.</div>
        <div style={{ display:'inline-flex', alignItems:'center', gap:7, background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:20, padding:'4px 14px 4px 10px', fontSize:'0.72rem', fontWeight:600, color:T.t2 }}>
          <span style={{ width:6, height:6, borderRadius:'50%', background:T.dark }}/>
          Forma AI — Architecture Assistant
        </div>
        <button className="fai-logout-btn" onClick={()=>{ logout(); navigate('/') }}>
          <LogOut size={14}/> Log out
        </button>
      </nav>

      {/* ════════ BODY ════════ */}
      <div style={{ display:'grid', gridTemplateColumns:'228px 1fr', minHeight:'calc(100vh - 62px)', fontFamily:"'Instrument Sans',sans-serif" }}>

        {/* ── SIDEBAR ── */}
        <aside style={{ background:'#fff', borderRight:`1px solid ${T.bd}`, padding:'28px 16px', display:'flex', flexDirection:'column', gap:28, position:'sticky', top:62, height:'calc(100vh - 62px)', overflowY:'auto' }}>
          <div style={{ display:'flex', alignItems:'center', gap:11, padding:'0 4px' }}>
            <div style={{ width:34, height:34, background:T.dark, borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
              <FileText size={15} color="#fff"/>
            </div>
            <div>
              <div style={{ fontFamily:"'Fraunces',serif", fontSize:'0.82rem', fontWeight:700, color:T.t1, letterSpacing:'-0.2px', lineHeight:1.2 }}>AI Lead Magnets</div>
              <div style={{ fontSize:'0.68rem', color:T.t3, lineHeight:1 }}>Your AI Workforce</div>
            </div>
          </div>

          <button className="fai-sidebar-create" onClick={()=>navigate('/create-lead-magnet')}>
            <Plus size={16}/> Create Lead Magnet
          </button>

          <div>
            <div style={{ fontSize:'0.62rem', fontWeight:600, letterSpacing:'2.5px', textTransform:'uppercase', color:T.t3, padding:'0 8px', marginBottom:6 }}>Navigation</div>
            <nav style={{ display:'flex', flexDirection:'column', gap:2 }}>
              {navItems.map(item => (
                <a key={item.id} href={item.href} className={`fai-nav-item${item.href==='/forma-ai'?' active':''}`} onClick={e=>{ e.preventDefault(); navigate(item.href) }}>
                  {item.icon} {item.label}
                </a>
              ))}
            </nav>
          </div>

          {/* Template status */}
          <div style={{ marginTop:'auto' }}>
            <div style={{ height:1, background:T.bd, marginBottom:16 }}/>
            <div style={{ background: selectedTemplateId ? T.dark : T.bg2, border:`1px solid ${selectedTemplateId ? T.dark : T.bd}`, borderRadius:10, padding:'14px', cursor: selectedTemplateId ? 'default' : 'pointer', transition:'all 0.2s' }}
              onClick={()=>!selectedTemplateId&&setShowTemplateModal(true)}>
              <div style={{ fontSize:'0.72rem', fontWeight:600, color: selectedTemplateId ? '#fff' : T.t1, marginBottom:4 }}>
                {selectedTemplateId ? '✓ Template selected' : 'No template selected'}
              </div>
              <div style={{ fontSize:'0.7rem', color: selectedTemplateId ? 'rgba(255,255,255,0.55)' : T.t3, lineHeight:1.5 }}>
                {selectedTemplateId ? selectedTemplateName : 'Click to choose a template before chatting.'}
              </div>
              {selectedTemplateId && (
                <button onClick={e=>{ e.stopPropagation(); setSelectedTemplateId(''); setSelectedTemplateName(''); setArchitecturalImages([]) }}
                  style={{ marginTop:8, display:'inline-flex', alignItems:'center', gap:4, background:'rgba(255,255,255,0.12)', border:'1px solid rgba(255,255,255,0.2)', borderRadius:6, padding:'3px 9px', fontSize:'0.65rem', color:'rgba(255,255,255,0.7)', cursor:'pointer' }}>
                  <X size={10}/> Change
                </button>
              )}
            </div>
          </div>
        </aside>

        {/* ── MAIN CHAT ── */}
        <main style={{ display:'flex', flexDirection:'column', background:T.bg2, height:'calc(100vh - 62px)' }}>

          {/* Page title bar */}
          <div style={{ padding:'24px 36px 0', background:T.bg2 }}>
            <div style={{ display:'inline-flex', alignItems:'center', gap:7, background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:20, padding:'4px 13px 4px 9px', fontSize:'0.7rem', fontWeight:600, color:T.t2, letterSpacing:'0.5px', marginBottom:12 }}>
              <span style={{ width:6, height:6, borderRadius:'50%', background:T.dark }}/>
              AI Architecture Assistant
            </div>
            <h1 style={{ fontFamily:"'Fraunces',serif", fontSize:'1.8rem', fontWeight:900, color:T.dark, letterSpacing:'-0.8px', lineHeight:1.05, marginBottom:4 }}>
              Forma <em style={{ fontStyle:'italic', color:T.t3 }}>AI.</em>
            </h1>
            <p style={{ fontSize:'0.85rem', color:T.t2, marginBottom:20 }}>
              Describe your business and the type of lead magnet you want. AI generates a full branded PDF in minutes.
            </p>
          </div>

          {/* Messages area */}
          <div style={{ flex:1, overflowY:'auto', padding:'0 36px 12px' }}>
            {messages.length === 0 ? (
              /* Empty state */
              <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100%', gap:16, paddingBottom:40 }}>
                <div style={{ width:52, height:52, background:'#fff', border:`1px solid ${T.bd}`, borderRadius:14, display:'flex', alignItems:'center', justifyContent:'center' }}>
                  <Sparkles size={22} color={T.t3}/>
                </div>
                <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1.1rem', fontWeight:700, color:T.dark, letterSpacing:'-0.3px', textAlign:'center' }}>
                  Describe your business
                </div>
                <div style={{ fontSize:'0.82rem', color:T.t3, textAlign:'center', maxWidth:320, lineHeight:1.6 }}>
                  Describe your business — what you do, who you serve, and what type of lead magnet you want (Guide, Checklist, Trends Report, etc).
                </div>
                {/* Quick prompts */}
                <div style={{ display:'flex', flexWrap:'wrap', gap:8, justifyContent:'center', marginTop:8 }}>
                  {[
                    'I run a perfume business selling 3,5,10 and 35ml bottles — create a Trends Report',
                    'I have an architecture firm specialising in sustainable homes — make a Checklist',
                    'I own a real estate agency in Dubai — create a Guide for first-time buyers',
                    'I run a SaaS company for HR teams — build an ROI Calculator',
                  ].map(p => (
                    <button key={p} onClick={()=>setMessage(p)} style={{ padding:'7px 14px', background:'#fff', border:`1px solid ${T.bd}`, borderRadius:20, fontSize:'0.75rem', color:T.t2, cursor:'pointer', fontFamily:"'Instrument Sans',sans-serif", transition:'all 0.15s' }}
                      onMouseOver={e=>(e.currentTarget.style.borderColor=T.bd2)}
                      onMouseOut={e=>(e.currentTarget.style.borderColor=T.bd)}>
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ paddingTop:16 }}>
                <AnimatePresence initial={false}>
                  {messages.map(m => <Bubble key={m.id} msg={m}/>)}
                </AnimatePresence>

                {/* Typing indicator */}
                {isGenerating && (
                  <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:12 }}>
                    <div style={{ width:28, height:28, borderRadius:'50%', background:T.dark, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                      <Sparkles size={13} color="#fff"/>
                    </div>
                    <div style={{ background:'#fff', border:`1px solid ${T.bd}`, borderRadius:'14px 14px 14px 4px', padding:'11px 15px', display:'flex', alignItems:'center', gap:5 }}>
                      {[0,1,2].map(i => (
                        <div key={i} style={{ width:6, height:6, borderRadius:'50%', background:T.t3, animation:`fai-pulse 1.2s ease-in-out ${i*0.2}s infinite` }}/>
                      ))}
                    </div>
                    {progress > 0 && progress < 100 && (
                      <span style={{ fontSize:'0.72rem', color:T.t3 }}>{progress}%</span>
                    )}
                  </div>
                )}
                <div ref={messagesEndRef}/>
              </div>
            )}
          </div>

          {/* ── INPUT BAR ── */}
          <div style={{ padding:'12px 36px 24px', background:T.bg2 }}>
            {/* Template error */}
            {templateError && (
              <div style={{ marginBottom:10, fontSize:'0.78rem', color:'#b00020', background:'#fff2f2', border:'1px solid rgba(200,50,50,0.15)', borderRadius:9, padding:'9px 14px', display:'flex', alignItems:'center', gap:8 }}>
                <span>⚠</span> {templateError}
              </div>
            )}

            <motion.div
              initial={{ opacity:0, y:12 }} animate={{ opacity:1, y:0 }}
              style={{ background:'#fff', border:`1px solid ${T.bd}`, borderRadius:14, overflow:'hidden', boxShadow:'0 2px 12px rgba(0,0,0,0.06)' }}
            >
              {/* Textarea */}
              <div style={{ padding:'14px 16px' }}>
                <textarea
                  ref={textareaRef}
                  className="fai-chat-ta"
                  value={message}
                  onChange={e => {
                    setMessage(e.target.value)
                    e.currentTarget.style.height = 'auto'
                    e.currentTarget.style.height = `${e.currentTarget.scrollHeight}px`
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Describe your business and mention the type of lead magnet you want (e.g. Guide, Checklist, Trends Report)…"
                  rows={1}
                  disabled={isGenerating}
                />
              </div>

              {/* Controls row */}
              <div style={{ padding:'10px 14px', borderTop:`1px solid ${T.bd}`, display:'flex', alignItems:'center', justifyContent:'space-between', background:T.bg2 }}>
                <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                  {/* Template picker button */}
                  <button
                    className={`fai-attach-btn${selectedTemplateId?' has-template':''}`}
                    onClick={()=>setShowTemplateModal(true)}
                  >
                    <PdfIcon size={14}/>
                    {selectedTemplateId ? selectedTemplateName : 'Choose template'}
                    {architecturalImages.length > 0 && (
                      <span style={{ display:'inline-flex', alignItems:'center', justifyContent:'center', width:16, height:16, borderRadius:'50%', background:'rgba(255,255,255,0.25)', fontSize:'0.6rem', fontWeight:700 }}>
                        {architecturalImages.length}
                      </span>
                    )}
                  </button>

                  <span style={{ fontSize:'0.7rem', color:T.t3 }}>Press ↵ to send</span>
                </div>

                <button className="fai-send-btn" onClick={handleSend} disabled={!message.trim()||isGenerating}>
                  {isGenerating
                    ? <><div style={{ width:13, height:13, border:'2px solid rgba(255,255,255,0.3)', borderTopColor:'#fff', borderRadius:'50%', animation:'fai-spin 0.8s linear infinite' }}/> Generating…</>
                    : <><Send size={13}/> Send <ArrowRight size={13}/></>}
                </button>
              </div>
            </motion.div>
          </div>
        </main>
      </div>

      {/* ════════ TEMPLATE MODAL ════════ */}
      <Modal isOpen={showTemplateModal} onClose={()=>setShowTemplateModal(false)} title="Choose Your Template">
        <TemplateSelectionForm
          onSubmit={handleTemplateSelect}
          onClose={()=>setShowTemplateModal(false)}
        />
      </Modal>

      {/* ════════ PDF PREVIEW MODAL ════════ */}
      <Modal isOpen={showPreviewModal} onClose={()=>{ setShowPreviewModal(false); if(previewUrl){URL.revokeObjectURL(previewUrl);setPreviewUrl(null)} }} title="PDF Preview" maxWidth={1000}>
        {previewUrl ? (
          <div style={{ display:'flex', flexDirection:'column', height:'75vh' }}>
            <div style={{ flex:1, background:T.bg2, padding:16, borderRadius:10, overflow:'hidden' }}>
              <iframe title="PDF Preview" src={previewUrl} style={{ width:'100%', height:'100%', border:'none', borderRadius:8 }}/>
            </div>
            <div style={{ display:'flex', justifyContent:'flex-end', gap:10, marginTop:14 }}>
              <button
                style={{ display:'inline-flex', alignItems:'center', gap:7, padding:'10px 20px', background:T.dark, color:'#fff', border:'none', borderRadius:9, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.82rem', fontWeight:600, cursor:'pointer' }}
                onClick={()=>{ if(previewUrl){ const a=document.createElement('a'); a.href=previewUrl; a.download=`forma-ai-${selectedTemplateId}.pdf`; document.body.appendChild(a); a.click(); a.remove() } }}
              >
                Download PDF
              </button>
              <button
                style={{ display:'inline-flex', alignItems:'center', gap:7, padding:'10px 16px', background:'none', border:`1px solid ${T.bd2}`, borderRadius:9, fontFamily:"'Instrument Sans',sans-serif", fontSize:'0.82rem', color:T.t2, cursor:'pointer' }}
                onClick={()=>{ setShowPreviewModal(false); if(previewUrl){URL.revokeObjectURL(previewUrl);setPreviewUrl(null)} }}
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'60px', gap:14 }}>
            <div style={{ width:36, height:36, border:`3px solid ${T.bg3}`, borderTopColor:T.dark, borderRadius:'50%', animation:'fai-spin 0.8s linear infinite' }}/>
            <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1rem', fontWeight:700, color:T.dark }}>Preparing preview…</div>
          </div>
        )}
      </Modal>
    </>
  )
}

export default FormaAI