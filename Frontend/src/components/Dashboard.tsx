import React, { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Download, Plus, Settings, LogOut, User, Palette, Trash2, Search, LayoutDashboard, Sparkles } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { dashboardApi } from '../lib/dashboardApi'
import type { DashboardStats, LeadMagnet } from '../lib/dashboardApi'

/* ─────────────────────────────────────────────
   DESIGN TOKENS — mirrors the Forma landing page
───────────────────────────────────────────── */
const T = {
  bg:    '#ffffff',
  bg2:   '#f7f7f5',
  bg3:   '#f0f0ec',
  dark:  '#0a0a0a',
  bd:    'rgba(0,0,0,0.08)',
  bd2:   'rgba(0,0,0,0.15)',
  t1:    '#111111',
  t2:    '#666666',
  t3:    '#aaaaaa',
} as const

/* ─────────────────────────────────────────────
   FONT INJECTION (Fraunces + Instrument Sans)
───────────────────────────────────────────── */
const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Instrument Sans',sans-serif; background:${T.bg2}; color:${T.t1}; }
    a { text-decoration:none; color:inherit; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .forma-nav-item { display:flex; align-items:center; gap:9px; padding:9px 10px; border-radius:8px; font-size:0.82rem; font-weight:500; color:${T.t2}; text-decoration:none; cursor:pointer; transition:all 0.15s; }
    .forma-nav-item:hover { background:${T.bg2}; color:${T.t1}; }
    .forma-nav-item:hover svg { color:${T.t1}; }
    .forma-nav-item.active { background:${T.bg2}; color:${T.t1}; font-weight:600; }
    .forma-nav-item.active svg { color:${T.t1}; }
    .forma-project-card { background:#fff; padding:24px; transition:background 0.15s; position:relative; }
    .forma-project-card:hover { background:#fafaf9; }
    .forma-delete-btn { background:none; border:none; cursor:pointer; color:${T.t3}; display:flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:7px; transition:all 0.15s; flex-shrink:0; }
    .forma-delete-btn:hover { background:#fff2f2; color:#c03030; }
    .forma-delete-btn:disabled { opacity:0.4; cursor:not-allowed; }
    .forma-stat-card { background:#fff; border:1px solid ${T.bd}; border-radius:14px; padding:22px; transition:border-color 0.2s; }
    .forma-stat-card:hover { border-color:${T.bd2}; }
    .forma-tpl-card { background:${T.bg}; border:1px solid ${T.bd}; border-radius:14px; overflow:hidden; cursor:pointer; transition:all 0.2s; }
    .forma-tpl-card:hover { border-color:${T.bd2}; transform:translateY(-2px); box-shadow:0 12px 32px rgba(0,0,0,0.08); }
    .forma-feat-item { padding:20px 0; border-bottom:1px solid ${T.bd}; display:flex; gap:16px; align-items:flex-start; }
    .forma-feat-item:first-child { border-top:1px solid ${T.bd}; }
    .forma-feat-icon { width:38px; height:38px; flex-shrink:0; background:${T.bg2}; border:1px solid ${T.bd}; border-radius:9px; display:flex; align-items:center; justify-content:center; color:${T.t2}; transition:all 0.2s; }
    .forma-feat-item:hover .forma-feat-icon { background:${T.dark}; color:#fff; border-color:${T.dark}; }
    .forma-search-input { width:100%; padding:10px 14px 10px 40px; background:${T.bg2}; border:1px solid ${T.bd}; border-radius:9px; font-family:'Instrument Sans',sans-serif; font-size:0.83rem; color:${T.t1}; outline:none; transition:all 0.2s; }
    .forma-search-input:focus { border-color:${T.bd2}; background:#fff; box-shadow:0 0 0 3px rgba(0,0,0,0.04); }
    .forma-search-input::placeholder { color:${T.t3}; }
    .forma-logout-btn { display:flex; align-items:center; gap:6px; background:none; border:1px solid ${T.bd}; border-radius:8px; padding:7px 14px; font-family:'Instrument Sans',sans-serif; font-size:0.78rem; font-weight:500; color:${T.t2}; cursor:pointer; transition:all 0.2s; }
    .forma-logout-btn:hover { border-color:${T.bd2}; color:${T.t1}; background:${T.bg2}; }
    .forma-create-btn { display:inline-flex; align-items:center; gap:8px; padding:10px 18px; background:${T.dark}; color:#fff; border:none; border-radius:10px; font-family:'Instrument Sans',sans-serif; font-size:0.82rem; font-weight:600; cursor:pointer; transition:all 0.2s; white-space:nowrap; }
    .forma-create-btn:hover { background:#2a2a2a; transform:translateY(-1px); box-shadow:0 6px 20px rgba(0,0,0,0.15); }
    .forma-sidebar-create { display:flex; align-items:center; justify-content:center; gap:8px; width:100%; padding:11px 14px; background:${T.dark}; color:#fff; border:none; border-radius:10px; font-family:'Instrument Sans',sans-serif; font-size:0.82rem; font-weight:600; cursor:pointer; transition:all 0.2s; }
    .forma-sidebar-create:hover { background:#2a2a2a; transform:translateY(-1px); box-shadow:0 6px 20px rgba(0,0,0,0.15); }
  `}</style>
)

/* ─────────────────────────────────────────────
   STATUS BADGE
───────────────────────────────────────────── */
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles: Record<string, React.CSSProperties> = {
    completed:   { background:'#f0faf4', color:'#1a7a40', border:'1px solid rgba(20,150,80,0.15)' },
    'in-progress':{ background:'#fff8ed', color:'#96600a', border:'1px solid rgba(180,120,20,0.15)' },
    draft:       { background:T.bg2,     color:T.t2,      border:`1px solid ${T.bd}` },
  }
  const dots: Record<string, string> = {
    completed:    '#1a7a40',
    'in-progress':'#d4860e',
    draft:         T.t3,
  }
  const label = status === 'in-progress' ? 'In Progress' : status.charAt(0).toUpperCase() + status.slice(1)
  return (
    <span style={{
      display:'inline-flex', alignItems:'center', gap:5,
      fontSize:'0.68rem', fontWeight:600,
      borderRadius:20, padding:'3px 10px',
      letterSpacing:'0.3px',
      ...styles[status] ?? styles.draft,
    }}>
      <span style={{ width:5, height:5, borderRadius:'50%', background: dots[status] ?? T.t3, flexShrink:0 }} />
      {label}
    </span>
  )
}

/* ─────────────────────────────────────────────
   MAIN DASHBOARD
───────────────────────────────────────────── */
const Dashboard: React.FC = () => {
  const { logout, user } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery]   = useState('')
  const [stats, setStats]               = useState<DashboardStats | null>(null)
  const [projects, setProjects]         = useState<LeadMagnet[]>([])
  const [loading, setLoading]           = useState(true)
  const [error, setError]               = useState<string | null>(null)
  const [deletingId, setDeletingId]     = useState<number | null>(null)
  const [activeNav, setActiveNav]       = useState('magnets')

  const handleLogout          = () => { logout(); navigate('/') }
  const handleCreateLeadMagnet = () => navigate('/create-lead-magnet')

  const handleDelete = async (id: number, title: string) => {
    if (!confirm(`Delete "${title}"? This cannot be undone.`)) return
    try {
      setDeletingId(id)
      await dashboardApi.deleteLeadMagnet(id)
      setProjects(prev => prev.filter(p => p.id !== id))
      const s = await dashboardApi.getStats()
      setStats(s)
    } catch { alert('Failed to delete. Please try again.') }
    finally { setDeletingId(null) }
  }

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        const [s, p] = await Promise.all([dashboardApi.getStats(), dashboardApi.getLeadMagnets()])
        setStats(s); setProjects(p); setError(null)
      } catch { setError('Failed to load dashboard data') }
      finally { setLoading(false) }
    })()
  }, [])

  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) return projects
    const q = searchQuery.toLowerCase()
    return projects.filter(p => p.title.toLowerCase().includes(q) || p.status.toLowerCase().includes(q))
  }, [projects, searchQuery])

  const formatDate = (d: string) => {
    const days = Math.floor((Date.now() - new Date(d).getTime()) / 86400000)
    if (days === 0) return 'Today'
    if (days === 1) return '1 day ago'
    if (days < 7)  return `${days} days ago`
    return new Date(d).toLocaleDateString()
  }

  /* ── LOADING ── */
  if (loading) return (
    <>
      <GlobalStyles />
      <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:12, height:'100vh', background:T.bg2 }}>
        <div style={{ fontFamily:"'Fraunces',serif", fontWeight:900, fontSize:'1.5rem', color:T.dark, letterSpacing:'-0.5px' }}>Forma.</div>
        <div style={{ fontSize:'0.82rem', color:T.t3 }}>Loading your dashboard…</div>
        <div style={{ width:20, height:20, border:`2px solid ${T.bd}`, borderTopColor:T.dark, borderRadius:'50%', animation:'spin 0.8s linear infinite', marginTop:4 }} />
      </div>
    </>
  )

  /* ── ERROR ── */
  if (error) return (
    <>
      <GlobalStyles />
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100vh', background:T.bg2 }}>
        <div style={{ background:'#fff', border:`1px solid ${T.bd}`, borderRadius:16, padding:'40px 48px', textAlign:'center' }}>
          <div style={{ fontFamily:"'Fraunces',serif", fontWeight:700, fontSize:'1.1rem', color:T.t1, marginBottom:6 }}>Something went wrong</div>
          <div style={{ fontSize:'0.83rem', color:'#c03030' }}>{error}</div>
        </div>
      </div>
    </>
  )

  /* ── STAT CARDS DATA ── */
  const statCards = [
    { label:'Total Lead Magnets', value: stats?.total_lead_magnets  ?? 0, icon: <FileText size={15} /> },
    { label:'Active',             value: stats?.active_lead_magnets ?? 0, icon: <Sparkles  size={15} /> },
    { label:'Total Downloads',    value: stats?.total_downloads     ?? 0, icon: <Download  size={15} /> },
    { label:'Leads Generated',    value: stats?.leads_generated     ?? 0, icon: <User      size={15} /> },
  ]

  /* ── SIDEBAR NAV ── */
  const navItems = [
    { id:'magnets',  label:'My Lead Magnets', icon:<FileText size={16} />,      href:'#' },
    { id:'ai',       label:'Forma AI',        icon:<Sparkles size={16} />,      href:'/forma-ai' },
    { id:'brand',    label:'Brand Assets',    icon:<Palette size={16} />,       href:'/brand-assets' },
    { id:'settings', label:'Settings',        icon:<Settings size={16} />,      href:'/settings' },
  ]

  return (
    <>
      <GlobalStyles />

      {/* ════════════════════ NAV ════════════════════ */}
      <nav style={{
        height:62, display:'flex', alignItems:'center', justifyContent:'space-between',
        padding:'0 36px', background:'#fff', borderBottom:`1px solid ${T.bd}`,
        position:'sticky', top:0, zIndex:100,
      }}>
        {/* Brand */}
        <div style={{ fontFamily:"'Fraunces',serif", fontWeight:900, fontSize:'1.35rem', color:T.dark, letterSpacing:'-0.5px' }}>
          Forma.
        </div>

        {/* Center */}
        <div style={{ display:'flex', alignItems:'center', gap:16 }}>
          {stats && (
            <div style={{
              display:'inline-flex', alignItems:'center', gap:6,
              background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:20,
              padding:'5px 14px', fontSize:'0.78rem', color:T.t2,
            }}>
              <span style={{ width:6, height:6, borderRadius:'50%', background:T.dark }} />
              <span style={{ fontWeight:600, color:T.t1 }}>Tokens</span>
              <span>{stats.ai_credits_remaining.toLocaleString()} left</span>
            </div>
          )}
          <div style={{ display:'flex', alignItems:'center', gap:9 }}>
            <div style={{
              width:30, height:30, borderRadius:'50%', background:T.dark,
              color:'#fff', display:'flex', alignItems:'center', justifyContent:'center',
              fontSize:'0.75rem', fontWeight:700, flexShrink:0,
            }}>
              {user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
            </div>
            <span style={{ fontSize:'0.85rem', fontWeight:500, color:T.t1 }}>{user?.name ?? 'User'}</span>
          </div>
        </div>

        {/* Logout */}
        <button className="forma-logout-btn" onClick={handleLogout}>
          <LogOut size={14} />
          Log out
        </button>
      </nav>

      {/* ════════════════════ BODY ════════════════════ */}
      <div style={{ display:'grid', gridTemplateColumns:'228px 1fr', minHeight:'calc(100vh - 62px)' }}>

        {/* ── SIDEBAR ── */}
        <aside style={{
          background:'#fff', borderRight:`1px solid ${T.bd}`,
          padding:'28px 16px', display:'flex', flexDirection:'column', gap:28,
          position:'sticky', top:62, height:'calc(100vh - 62px)', overflowY:'auto',
        }}>
          {/* Brand block */}
          <div style={{ display:'flex', alignItems:'center', gap:11, padding:'0 4px' }}>
            <div style={{
              width:34, height:34, background:T.dark, borderRadius:9,
              display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
            }}>
              <FileText size={15} color="#fff" />
            </div>
            <div>
              <div style={{ fontFamily:"'Fraunces',serif", fontSize:'0.82rem', fontWeight:700, color:T.t1, letterSpacing:'-0.2px', lineHeight:1.2 }}>AI Lead Magnets</div>
              <div style={{ fontSize:'0.68rem', color:T.t3, lineHeight:1 }}>Your AI Workforce</div>
            </div>
          </div>

          {/* Create button */}
          <button className="forma-sidebar-create" onClick={handleCreateLeadMagnet}>
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
                  className={`forma-nav-item${activeNav === item.id ? ' active' : ''}`}
                  onClick={e => { e.preventDefault(); setActiveNav(item.id); if (item.href !== '#') navigate(item.href) }}
                >
                  {item.icon}
                  {item.label}
                </a>
              ))}
            </nav>
          </div>

          {/* Divider + hint */}
          <div style={{ marginTop:'auto', padding:'0 4px' }}>
            <div style={{ height:1, background:T.bd, marginBottom:16 }} />
            <div style={{
              background:T.bg2, border:`1px solid ${T.bd}`, borderRadius:10, padding:'14px 14px',
            }}>
              <div style={{ fontSize:'0.72rem', fontWeight:600, color:T.t1, marginBottom:4 }}>First magnet free</div>
              <div style={{ fontSize:'0.7rem', color:T.t3, lineHeight:1.5 }}>No credit card required. Generate your first PDF now.</div>
            </div>
          </div>
        </aside>

        {/* ── MAIN ── */}
        <main style={{ padding:'40px 44px', background:T.bg2 }}>

          {/* Header */}
          <div style={{ marginBottom:32 }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:6 }}>
              <motion.h1
                initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }}
                style={{ fontFamily:"'Fraunces',serif", fontSize:'2rem', fontWeight:900, color:T.dark, letterSpacing:'-1px', lineHeight:1.05 }}
              >
                My Lead Magnets
              </motion.h1>
              <motion.button
                initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.08 }}
                className="forma-create-btn"
                onClick={handleCreateLeadMagnet}
              >
                <Plus size={16} />
                Create Lead Magnet
              </motion.button>
            </div>
            <motion.p
              initial={{ opacity:0, y:14 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.14 }}
              style={{ fontSize:'0.87rem', color:T.t2 }}
            >
              Manage and interact with your AI-powered lead magnets
            </motion.p>
          </div>

          {/* Stat cards */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14, marginBottom:28 }}>
            {statCards.map((s, i) => (
              <motion.div
                key={s.label}
                className="forma-stat-card"
                initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.18 + i * 0.06 }}
              >
                <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14 }}>
                  <span style={{ fontSize:'0.65rem', fontWeight:600, letterSpacing:'0.8px', textTransform:'uppercase', color:T.t3 }}>{s.label}</span>
                  <span style={{ color:T.t3 }}>{s.icon}</span>
                </div>
                <div style={{ fontFamily:"'Fraunces',serif", fontSize:'2rem', fontWeight:900, color:T.dark, letterSpacing:'-1px', lineHeight:1 }}>
                  {s.value}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Content panel */}
          <motion.div
            initial={{ opacity:0, y:14 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.44 }}
            style={{ background:'#fff', border:`1px solid ${T.bd}`, borderRadius:16, overflow:'hidden' }}
          >
            {/* Search bar */}
            <div style={{
              padding:'18px 24px', borderBottom:`1px solid ${T.bd}`,
              display:'flex', alignItems:'center', justifyContent:'space-between', gap:16,
            }}>
              <div style={{ position:'relative', flex:1, maxWidth:340 }}>
                <Search size={15} style={{ position:'absolute', left:13, top:'50%', transform:'translateY(-50%)', color:T.t3, pointerEvents:'none' }} />
                <input
                  className="forma-search-input"
                  type="text"
                  placeholder="Search lead magnets…"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
              </div>
              <div style={{ fontSize:'0.65rem', fontWeight:600, letterSpacing:'2px', textTransform:'uppercase', color:T.t3 }}>
                {filteredProjects.length} {filteredProjects.length === 1 ? 'item' : 'items'}
              </div>
            </div>

            {/* Grid */}
            {filteredProjects.length === 0 ? (
              /* Empty state */
              <div style={{ padding:'72px 40px', textAlign:'center' }}>
                <div style={{
                  width:50, height:50, background:T.bg2, border:`1px solid ${T.bd}`,
                  borderRadius:13, display:'flex', alignItems:'center', justifyContent:'center',
                  margin:'0 auto 16px', color:T.t3,
                }}>
                  <FileText size={20} />
                </div>
                <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1.05rem', fontWeight:700, color:T.t1, marginBottom:6, letterSpacing:'-0.2px' }}>
                  {searchQuery.trim() ? `No results for "${searchQuery}"` : 'No lead magnets yet'}
                </div>
                <div style={{ fontSize:'0.82rem', color:T.t3, marginBottom:22 }}>
                  {searchQuery.trim() ? 'Try a different search term.' : 'Generate your first AI-powered PDF lead magnet now.'}
                </div>
                {!searchQuery.trim() && (
                  <button className="forma-create-btn" onClick={handleCreateLeadMagnet} style={{ margin:'0 auto' }}>
                    <Plus size={15} />
                    Create Lead Magnet
                  </button>
                )}
              </div>
            ) : (
              <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:1, background:T.bd }}>
                {filteredProjects.map((project, index) => (
                  <motion.div
                    key={project.id}
                    className="forma-project-card"
                    initial={{ opacity:0, y:16 }}
                    animate={{ opacity:1, y:0 }}
                    transition={{ delay:0.5 + index * 0.06 }}
                  >
                    {/* Card header */}
                    <div style={{ display:'flex', alignItems:'flex-start', gap:11, marginBottom:14 }}>
                      <div style={{
                        width:38, height:38, background:T.bg2, border:`1px solid ${T.bd}`,
                        borderRadius:9, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
                      }}>
                        <FileText size={16} color={T.t2} />
                      </div>
                      <div style={{ flex:1, minWidth:0 }}>
                        <div style={{
                          fontFamily:"'Fraunces',serif", fontSize:'0.93rem', fontWeight:700,
                          color:T.dark, letterSpacing:'-0.2px', lineHeight:1.25, marginBottom:6,
                          overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap',
                        }}>
                          {project.title}
                        </div>
                        <StatusBadge status={project.status} />
                      </div>
                      <button
                        className="forma-delete-btn"
                        onClick={() => handleDelete(project.id, project.title)}
                        disabled={deletingId === project.id}
                        title="Delete"
                      >
                        {deletingId === project.id
                          ? <div style={{ width:14, height:14, border:`2px solid ${T.bd}`, borderTopColor:T.t2, borderRadius:'50%', animation:'spin 0.8s linear infinite' }} />
                          : <Trash2 size={15} />}
                      </button>
                    </div>

                    {/* Description */}
                    <p style={{
                      fontSize:'0.78rem', color:T.t2, lineHeight:1.55, marginBottom:16,
                      display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden',
                    }}>
                      {project.description ||
                        (project.status === 'completed'   ? 'Generates high-quality leads for architectural services.' :
                         project.status === 'in-progress' ? 'Converting prospects into qualified leads.' :
                                                             'Draft lead magnet ready for review.')}
                    </p>

                    {/* Metrics */}
                    <div style={{
                      display:'flex', gap:20, padding:'14px 0',
                      borderTop:`1px solid ${T.bd}`, borderBottom:`1px solid ${T.bd}`, marginBottom:14,
                    }}>
                      {[
                        { value: project.downloads_count, label:'Downloads' },
                        { value: project.leads_count,     label:'Leads' },
                      ].map(m => (
                        <div key={m.label}>
                          <div style={{ fontFamily:"'Fraunces',serif", fontSize:'1.4rem', fontWeight:900, color:T.dark, letterSpacing:'-0.5px', lineHeight:1 }}>{m.value}</div>
                          <div style={{ fontSize:'0.65rem', color:T.t3, fontWeight:500, textTransform:'uppercase', letterSpacing:'0.5px', marginTop:2 }}>{m.label}</div>
                        </div>
                      ))}
                    </div>

                    {/* Footer */}
                    <div style={{ fontSize:'0.7rem', color:T.t3 }}>
                      Created {formatDate(project.created_at)}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>

        </main>
      </div>
    </>
  )
}

export default Dashboard