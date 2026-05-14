import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const LandingPage: React.FC = () => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  React.useEffect(() => {
    if (isAuthenticated) navigate('/dashboard')
  }, [isAuthenticated, navigate])

  const goLogin  = () => navigate('/login')
  const goSignup = () => navigate('/signup')

  return (
    <div style={{ background: '#fff', color: '#111', fontFamily: "'Instrument Sans', sans-serif", fontSize: 15, lineHeight: 1.7 }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,700&family=Instrument+Sans:wght@400;500;600&display=swap');
        @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css');
        *{margin:0;padding:0;box-sizing:border-box;}
        html{scroll-behavior:smooth;}
        a{text-decoration:none;color:inherit;}
        :root{
          --bg:#ffffff;--bg2:#f7f7f5;--bg3:#f0f0ec;
          --dark:#0a0a0a;--bd:rgba(0,0,0,0.08);--bd2:rgba(0,0,0,0.15);
          --t1:#111111;--t2:#666666;--t3:#aaaaaa;
        }
        .fraunces{font-family:'Fraunces',serif;}
        .nav-link-hover:hover{color:#111 !important;}
        .btn-dark{background:#0a0a0a;color:#fff;border:none;border-radius:10px;padding:11px 22px;font-family:'Instrument Sans',sans-serif;font-size:0.85rem;font-weight:600;cursor:pointer;transition:all .2s;display:inline-flex;align-items:center;gap:8px;}
        .btn-dark:hover{background:#2a2a2a;transform:translateY(-1px);box-shadow:0 6px 20px rgba(0,0,0,0.15);}
        .btn-outline{background:transparent;color:#666;border:1px solid rgba(0,0,0,0.15);border-radius:10px;padding:11px 22px;font-family:'Instrument Sans',sans-serif;font-size:0.85rem;font-weight:500;cursor:pointer;transition:all .2s;display:inline-flex;align-items:center;gap:8px;}
        .btn-outline:hover{border-color:rgba(0,0,0,0.3);color:#111;}
        .tpl-card{background:#fff;border:1px solid rgba(0,0,0,0.08);border-radius:14px;overflow:hidden;cursor:pointer;transition:all .2s;}
        .tpl-card:hover{border-color:rgba(0,0,0,0.15);transform:translateY(-2px);box-shadow:0 12px 32px rgba(0,0,0,0.08);}
        .feat-item{padding:24px 0;border-bottom:1px solid rgba(0,0,0,0.08);display:flex;gap:18px;align-items:flex-start;cursor:pointer;transition:all .2s;}
        .feat-item:first-child{border-top:1px solid rgba(0,0,0,0.08);}
        .feat-item:hover .feat-icon-box{background:#0a0a0a !important;color:#fff !important;border-color:#0a0a0a !important;}
        .feat-icon-box{width:40px;height:40px;flex-shrink:0;background:#f7f7f5;border:1px solid rgba(0,0,0,0.08);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;color:#666;transition:all .2s;}
        .step-card{background:#fff;padding:36px 32px;}
        .footer-link-item{font-size:0.78rem;color:#aaa;cursor:pointer;transition:color .2s;}
        .footer-link-item:hover{color:#666;}
        @media(max-width:900px){
          .hero-grid{grid-template-columns:1fr !important;}
          .hero-right-col{display:none !important;}
          .nav-links-row{display:none !important;}
          .steps-grid{grid-template-columns:1fr !important;}
          .tpl-grid{grid-template-columns:1fr 1fr !important;}
          .features-layout{grid-template-columns:1fr !important;}
          .section-pad{padding:60px 24px !important;}
          .hero-pad{padding:0 24px !important;}
          .nav-pad{padding:0 24px !important;}
          .logos-pad{padding:18px 24px !important;}
          .format-pad{padding:22px 24px !important;}
          .cta-pad{padding:72px 24px !important;}
          .footer-pad{padding:24px !important;}
        }
      `}</style>

      {/* NAV */}
      <nav style={{ height: 62, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 52px', borderBottom: '1px solid rgba(0,0,0,0.08)', background: '#fff', position: 'sticky', top: 0, zIndex: 100 }} className="nav-pad">
        <div className="fraunces" style={{ fontWeight: 900, fontSize: '1.4rem', color: '#0a0a0a', letterSpacing: '-0.5px' }}>Forma.</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 32 }} className="nav-links-row">
          <a href="#how"       style={{ fontSize: '0.85rem', color: '#666', cursor: 'pointer' }} className="nav-link-hover">How it works</a>
          <a href="#features"  style={{ fontSize: '0.85rem', color: '#666', cursor: 'pointer' }} className="nav-link-hover">Features</a>
          <a href="#templates" style={{ fontSize: '0.85rem', color: '#666', cursor: 'pointer' }} className="nav-link-hover">Templates</a>
          <a href="#pricing"   style={{ fontSize: '0.85rem', color: '#666', cursor: 'pointer' }} className="nav-link-hover">Pricing</a>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span onClick={goLogin}  style={{ fontSize: '0.85rem', color: '#666', cursor: 'pointer', padding: '8px 16px' }} className="nav-link-hover">Log in</span>
          <button onClick={goSignup} className="btn-dark"><i className="ti ti-bolt" /> Get started free</button>
        </div>
      </nav>

      {/* HERO */}
      <section style={{ minHeight: '90vh', display: 'grid', gridTemplateColumns: '1fr 1fr', alignItems: 'center', padding: '0 52px', gap: 60, background: '#fff', position: 'relative', overflow: 'hidden' }} className="hero-grid hero-pad">
        <div style={{ padding: '60px 0' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#f7f7f5', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 20, padding: '5px 14px 5px 10px', fontSize: '0.72rem', fontWeight: 600, color: '#666', letterSpacing: '0.5px', marginBottom: 24 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#0a0a0a' }} />
            AI Lead Magnet Generator for Architects
          </div>
          <h1 className="fraunces" style={{ fontSize: '4rem', fontWeight: 900, lineHeight: 1.05, letterSpacing: '-2px', color: '#0a0a0a', marginBottom: 22 }}>
            The Most Efficient<br/>
            <em style={{ fontStyle: 'italic', color: '#aaa' }}>Beautiful</em><br/>
            <span style={{ position: 'relative' }}>
              Lead Magnet
              <span style={{ position: 'absolute', bottom: 4, left: 0, right: 0, height: 3, background: '#0a0a0a', borderRadius: 2 }} />
            </span>{' '}Generator
          </h1>
          <p style={{ fontSize: '1.05rem', color: '#666', lineHeight: 1.65, maxWidth: 440, marginBottom: 36 }}>
            We turn your <strong style={{ color: '#111', fontWeight: 600 }}>topic, audience &amp; goals</strong> into polished, branded PDF lead magnets — in seconds. No design skills. No copywriters.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 44 }}>
            <button onClick={goSignup} className="btn-dark" style={{ padding: '13px 26px', fontSize: '0.9rem' }}><i className="ti ti-bolt" /> Generate for free</button>
            <button className="btn-outline" style={{ padding: '13px 22px', fontSize: '0.9rem' }}>See examples →</button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: '0.78rem', color: '#aaa' }}>
            <div style={{ display: 'flex' }}>
              {['KR','MA','JS','PL'].map((a, i) => (
                <div key={i} style={{ width: 28, height: 28, borderRadius: '50%', border: '2px solid #fff', background: '#f0f0ec', marginLeft: i === 0 ? 0 : -8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 600, color: '#666' }}>{a}</div>
              ))}
            </div>
            <span>Trusted by 200+ architecture firms</span>
          </div>
        </div>

        {/* PDF MOCKUP */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 0' }} className="hero-right-col">
          <div style={{ position: 'relative', width: '100%', maxWidth: 420 }}>
            {/* Back card */}
            <div style={{ position: 'absolute', top: -14, left: 20, right: -14, zIndex: 0, transform: 'rotate(2.5deg)', background: '#fff', borderRadius: 16, border: '1px solid rgba(0,0,0,0.15)', boxShadow: '0 8px 24px rgba(0,0,0,0.06)', opacity: 0.65, overflow: 'hidden' }}>
              <div style={{ background: '#f7f7f5', borderBottom: '1px solid rgba(0,0,0,0.08)', padding: '10px 16px', display: 'flex', gap: 5 }}>
                {['#e0e0e0','#e0e0e0','#e0e0e0'].map((c,i) => <div key={i} style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />)}
              </div>
              <div style={{ padding: '16px 18px' }}>
                <div style={{ height: 8, background: '#f0f0ec', borderRadius: 3, width: '70%', marginBottom: 8 }} />
                <div style={{ height: 6, background: '#f0f0ec', borderRadius: 3, width: '50%' }} />
              </div>
            </div>

            {/* Front card */}
            <div style={{ position: 'relative', zIndex: 1, background: '#fff', borderRadius: 16, border: '1px solid rgba(0,0,0,0.15)', boxShadow: '0 24px 60px rgba(0,0,0,0.10),0 8px 20px rgba(0,0,0,0.06)', overflow: 'hidden' }}>
              <div style={{ background: '#f7f7f5', borderBottom: '1px solid rgba(0,0,0,0.08)', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ display: 'flex', gap: 5 }}>
                  {['#ff5f56','#ffbd2e','#27c93f'].map((c,i) => <div key={i} style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />)}
                </div>
                <span style={{ fontSize: 11, color: '#aaa', marginLeft: 4 }}>Sustainable Architecture Trends 2026.pdf</span>
              </div>
              <div style={{ padding: '22px 22px 20px' }}>
                {/* Cover sim */}
                <div style={{ background: '#0a0a0a', borderRadius: 10, padding: 18, marginBottom: 14, position: 'relative', overflow: 'hidden' }}>
                  <div style={{ fontSize: 8, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 8, fontWeight: 600 }}>Industry Trends Report · 2025–2026</div>
                  <div className="fraunces" style={{ fontSize: 18, fontWeight: 900, color: '#fff', lineHeight: 1.15, letterSpacing: '-0.3px', marginBottom: 10 }}>Sustainable Architecture Revolution</div>
                  <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.45)', lineHeight: 1.5, marginBottom: 14 }}>Mastering sustainable trends to overcome ROI uncertainty and accelerate project timelines.</div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {['kyro@gmail.com','kyro.com','3423131'].map((t,i) => (
                      <span key={i} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 20, padding: '3px 9px', fontSize: 8, color: 'rgba(255,255,255,0.55)' }}>{t}</span>
                    ))}
                  </div>
                </div>
                {/* Content sim */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <div style={{ height: 9, borderRadius: 3, background: 'rgba(0,0,0,0.12)', width: '45%', marginBottom: 8 }} />
                  {['95%','88%','76%'].map((w,i) => <div key={i} style={{ height: 6, borderRadius: 3, background: '#f0f0ec', width: w }} />)}
                  <div style={{ height: 52, background: '#f7f7f5', borderRadius: 7, border: '1px solid rgba(0,0,0,0.08)', margin: '10px 0', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
                    <i className="ti ti-photo" style={{ fontSize: 14, color: '#ccc' }} />
                    <span style={{ fontSize: 10, color: '#ccc' }}>Architectural image</span>
                  </div>
                  <div style={{ height: 9, borderRadius: 3, background: 'rgba(0,0,0,0.12)', width: '45%', marginBottom: 8 }} />
                  {['90%','72%'].map((w,i) => <div key={i} style={{ height: 6, borderRadius: 3, background: '#f0f0ec', width: w }} />)}
                </div>
              </div>
            </div>

            {/* Badge 1 */}
            <div style={{ position: 'absolute', top: 20, right: -30, background: '#fff', border: '1px solid rgba(0,0,0,0.15)', borderRadius: 10, padding: '10px 14px', boxShadow: '0 8px 24px rgba(0,0,0,0.10)', display: 'flex', alignItems: 'center', gap: 9, whiteSpace: 'nowrap', zIndex: 2 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: '#f7f7f5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}><i className="ti ti-sparkles" /></div>
              <div style={{ fontSize: 11 }}><strong style={{ display: 'block', fontWeight: 600, fontSize: 12 }}>AI-generated</strong><span style={{ color: '#aaa', fontSize: 10 }}>Content + design</span></div>
            </div>

            {/* Badge 2 */}
            <div style={{ position: 'absolute', bottom: 40, left: -30, background: '#fff', border: '1px solid rgba(0,0,0,0.15)', borderRadius: 10, padding: '10px 14px', boxShadow: '0 8px 24px rgba(0,0,0,0.10)', display: 'flex', alignItems: 'center', gap: 9, whiteSpace: 'nowrap', zIndex: 2 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: '#f7f7f5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}><i className="ti ti-file-download" /></div>
              <div style={{ fontSize: 11 }}><strong style={{ display: 'block', fontWeight: 600, fontSize: 12 }}>Ready in seconds</strong><span style={{ color: '#aaa', fontSize: 10 }}>Download instantly</span></div>
            </div>
          </div>
        </div>
      </section>

      {/* FORMAT STRIP */}
      <div style={{ padding: '28px 52px', background: '#0a0a0a', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }} className="format-pad">
        <span style={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.3)', marginRight: 8 }}>Output formats:</span>
        {['PDF','Trends Report','Ultimate Guide','Checklist','Case Study','ROI Calculator','Onboarding Flow'].map((f,i) => (
          <span key={i} style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, padding: '7px 16px', fontSize: '0.82rem', fontWeight: 600, color: 'rgba(255,255,255,0.6)', letterSpacing: '0.5px' }}>{f}</span>
        ))}
      </div>

      {/* LOGOS */}
      <div style={{ background: '#f7f7f5', borderTop: '1px solid rgba(0,0,0,0.08)', borderBottom: '1px solid rgba(0,0,0,0.08)', padding: '20px 52px', display: 'flex', alignItems: 'center', gap: 20 }} className="logos-pad">
        <span style={{ fontSize: '0.72rem', color: '#aaa', letterSpacing: '1px', textTransform: 'uppercase', whiteSpace: 'nowrap', flexShrink: 0 }}>Used by firms including</span>
        <div style={{ width: 1, height: 18, background: 'rgba(0,0,0,0.15)', flexShrink: 0 }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
          {['Kyro Studio','Arcform','BuildVision','NexSpace','Velta Co.','Drafta'].map((n,i) => (
            <span key={i} style={{ fontSize: '0.82rem', fontWeight: 600, color: '#aaa', letterSpacing: '0.3px' }}>{n}</span>
          ))}
        </div>
      </div>

      {/* HOW IT WORKS */}
      <section style={{ padding: '88px 52px', borderBottom: '1px solid rgba(0,0,0,0.08)' }} id="how" className="section-pad">
        <div style={{ fontSize: '0.7rem', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#aaa', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 20, height: 1.5, background: '#aaa', display: 'inline-block' }} />
          How it works
        </div>
        <h2 className="fraunces" style={{ fontSize: '2.6rem', fontWeight: 900, letterSpacing: '-1.2px', color: '#0a0a0a', marginBottom: 12, lineHeight: 1.1 }}>
          Three steps to a<br/><em style={{ fontStyle: 'italic', color: '#aaa' }}>professional</em> lead magnet.
        </h2>
        <p style={{ fontSize: '0.95rem', color: '#666', lineHeight: 1.65, maxWidth: 480, marginBottom: 52 }}>No design software. No copywriters. Just your expertise and Forma's AI engine.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 1, background: 'rgba(0,0,0,0.08)', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 14, overflow: 'hidden' }} className="steps-grid">
          {[
            { n:'01', icon:'ti-forms',        title:'Describe your audience', desc:'Tell us your topic, target audience, their pain points, and the outcome you want. Takes less than 2 minutes.' },
            { n:'02', icon:'ti-layout-grid',  title:'Choose a template',      desc:'Pick from 6 formats — Trends Report, Ultimate Guide, Checklist, Case Study, ROI Calculator, or Onboarding Flow.' },
            { n:'03', icon:'ti-file-download', title:'Download your PDF',     desc:'AI generates your fully branded, professionally designed PDF — ready to publish and start collecting leads.' },
          ].map((s,i) => (
            <div key={i} className="step-card">
              <div className="fraunces" style={{ fontSize: '3rem', fontWeight: 900, color: '#f0f0ec', lineHeight: 1, marginBottom: 20 }}>{s.n}</div>
              <div style={{ width: 42, height: 42, background: '#f7f7f5', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 18, fontSize: 19, color: '#666' }}><i className={`ti ${s.icon}`} /></div>
              <div className="fraunces" style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0a0a0a', marginBottom: 8, letterSpacing: '-0.2px' }}>{s.title}</div>
              <p style={{ fontSize: '0.82rem', color: '#666', lineHeight: 1.65 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES */}
      <section style={{ padding: '88px 52px', borderBottom: '1px solid rgba(0,0,0,0.08)', background: '#f7f7f5' }} id="features" className="section-pad">
        <div style={{ fontSize: '0.7rem', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#aaa', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 20, height: 1.5, background: '#aaa', display: 'inline-block' }} />
          Features
        </div>
        <h2 className="fraunces" style={{ fontSize: '2.6rem', fontWeight: 900, letterSpacing: '-1.2px', color: '#0a0a0a', marginBottom: 12, lineHeight: 1.1 }}>
          Everything you need.<br/><em style={{ fontStyle: 'italic', color: '#aaa' }}>Nothing you don't.</em>
        </h2>
        <p style={{ fontSize: '0.95rem', color: '#666', lineHeight: 1.65, maxWidth: 480, marginBottom: 52 }}>Forma is purpose-built for architecture firms — not a generic marketing tool bolted together.</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 60, alignItems: 'start' }} className="features-layout">
          <div>
            {[
              { icon:'ti-sparkles', title:'AI-powered content',          desc:'Claude generates specific, useful, industry-relevant content — not generic filler. Every section is tailored to your exact audience and topic.' },
              { icon:'ti-palette',  title:'Your brand, automatically',   desc:'Upload your logo and set your brand colors. Every PDF is rendered with your firm\'s identity baked in from cover to back cover.' },
              { icon:'ti-photo',    title:'Architectural image support', desc:'Add up to 6 of your own project photos. Forma intelligently places them throughout the document for maximum visual impact.' },
              { icon:'ti-download', title:'Instant PDF download',        desc:'No exports, no rendering queues. Your lead magnet is generated and downloaded in seconds — print-ready and web-ready.' },
            ].map((f,i) => (
              <div key={i} className="feat-item">
                <div className="feat-icon-box"><i className={`ti ${f.icon}`} /></div>
                <div>
                  <div className="fraunces" style={{ fontSize: '1rem', fontWeight: 700, color: '#0a0a0a', marginBottom: 4, letterSpacing: '-0.2px' }}>{f.title}</div>
                  <p style={{ fontSize: '0.8rem', color: '#666', lineHeight: 1.6 }}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <div style={{ background: '#0a0a0a', borderRadius: 16, padding: 28, position: 'sticky', top: 80, minHeight: 340, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', overflow: 'hidden', backgroundImage: 'linear-gradient(rgba(255,255,255,0.02) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.02) 1px,transparent 1px)', backgroundSize: '32px 32px' }}>
            <div style={{ fontSize: 9, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', marginBottom: 20 }}>Live preview — Sustainable Architecture Guide</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[['70%',true],['90%',true],['55%',false],['80%',false],['65%',false],['75%',false]].map(([w,a],i) => (
                <div key={i} style={{ height: 7, borderRadius: 3, background: a ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.08)', width: w as string }} />
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
              {['ti-trending-up','ti-chart-bar','ti-users'].map((ic,i) => (
                <div key={i} style={{ flex: 1, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: 14 }}>
                  <div style={{ fontSize: 18, color: 'rgba(255,255,255,0.4)', marginBottom: 8 }}><i className={`ti ${ic}`} /></div>
                  <div style={{ height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.1)', marginBottom: 5 }} />
                  <div style={{ height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.1)', width: '60%' }} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* TEMPLATES */}
      <section style={{ padding: '88px 52px', borderBottom: '1px solid rgba(0,0,0,0.08)' }} id="templates" className="section-pad">
        <div style={{ fontSize: '0.7rem', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', color: '#aaa', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 20, height: 1.5, background: '#aaa', display: 'inline-block' }} />
          Templates
        </div>
        <h2 className="fraunces" style={{ fontSize: '2.6rem', fontWeight: 900, letterSpacing: '-1.2px', color: '#0a0a0a', marginBottom: 12, lineHeight: 1.1 }}>
          Six formats.<br/><em style={{ fontStyle: 'italic', color: '#aaa' }}>Infinite</em> topics.
        </h2>
        <p style={{ fontSize: '0.95rem', color: '#666', lineHeight: 1.65, maxWidth: 480, marginBottom: 52 }}>Every template is designed for architecture professionals — not generic business content.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16 }} className="tpl-grid">
          {[
            { bg:'#0a0a0a', tag:'Popular',     name:'Trends Report',   desc:'Industry insights and forward-looking analysis for your niche. Positions you as a market leader.' },
            { bg:'#1a1428', tag:'Authority',   name:'Ultimate Guide',   desc:'Deep-dive educational content that positions you as the go-to expert in your field.' },
            { bg:'#0f1e18', tag:'Quick Win',   name:'Checklist',        desc:'Quick-reference action items your audience can implement today. High perceived value, low friction.' },
            { bg:'#1e1610', tag:'Trust',       name:'Case Study',       desc:'Real-world proof that builds trust and drives conversions. Show, don\'t tell.' },
            { bg:'#1e1018', tag:'Interactive', name:'ROI Calculator',   desc:'Help prospects quantify their potential gains. The highest-converting lead magnet format.' },
            { bg:'#101828', tag:'Engagement',  name:'Onboarding Flow',  desc:'Turn new leads into engaged clients with a step-by-step welcome journey.' },
          ].map((t,i) => (
            <div key={i} className="tpl-card">
              <div style={{ height: 130, background: t.bg, padding: 18, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', position: 'relative', overflow: 'hidden', backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.03) 1px,transparent 1px)', backgroundSize: '28px 28px' }}>
                <span style={{ display: 'inline-block', fontSize: '0.58rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1.5px', color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 20, padding: '3px 9px', marginBottom: 6, position: 'relative', zIndex: 1 }}>{t.tag}</span>
                <div className="fraunces" style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff', letterSpacing: '-0.2px', position: 'relative', zIndex: 1 }}>{t.name}</div>
              </div>
              <div style={{ padding: '16px 18px' }}><p style={{ fontSize: '0.78rem', color: '#666', lineHeight: 1.55 }}>{t.desc}</p></div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '100px 52px', background: '#fff', textAlign: 'center', position: 'relative', overflow: 'hidden' }} className="cta-pad">
        <h2 className="fraunces" style={{ fontSize: '3.2rem', fontWeight: 900, letterSpacing: '-1.5px', color: '#0a0a0a', marginBottom: 16, position: 'relative', zIndex: 1 }}>
          Ready to generate your<br/><em style={{ fontStyle: 'italic', color: '#aaa' }}>first</em> lead magnet?
        </h2>
        <p style={{ fontSize: '1rem', color: '#666', maxWidth: 400, margin: '0 auto 36px', lineHeight: 1.65, position: 'relative', zIndex: 1 }}>
          Join 200+ architecture firms already using Forma to attract better clients with less effort.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, position: 'relative', zIndex: 1 }}>
          <button onClick={goSignup} className="btn-dark" style={{ padding: '14px 28px', fontSize: '0.95rem' }}><i className="ti ti-bolt" /> Start for free</button>
          <button className="btn-outline" style={{ padding: '14px 22px', fontSize: '0.95rem' }}>View pricing</button>
        </div>
        <p style={{ marginTop: 16, fontSize: '0.75rem', color: '#aaa', position: 'relative', zIndex: 1 }}>No credit card required · First lead magnet free</p>
      </section>

      {/* FOOTER */}
      <footer style={{ padding: '28px 52px', borderTop: '1px solid rgba(0,0,0,0.08)', background: '#f7f7f5', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }} className="footer-pad">
        <div className="fraunces" style={{ fontWeight: 900, fontSize: '1.1rem', color: '#0a0a0a', letterSpacing: '-0.3px' }}>Forma.</div>
        <div style={{ display: 'flex', gap: 24 }}>
          {['Features','Templates','Pricing','Documentation','Privacy'].map((l,i) => (
            <span key={i} className="footer-link-item">{l}</span>
          ))}
        </div>
        <span style={{ fontSize: '0.72rem', color: '#aaa' }}>© 2026 Forma. All rights reserved.</span>
      </footer>
    </div>
  )
}

export default LandingPage