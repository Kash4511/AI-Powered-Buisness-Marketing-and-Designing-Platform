import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Mail, Lock, User, Phone, Terminal } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const showcaseCards = [
  { bg: '#0a0a0a', tag: 'Developer Mode',  title: 'Internal Testing Instance',   lines: ['100%','100%'] },
  { bg: '#1a1428', tag: 'API Access',      title: 'Token Monitoring Dashboard',      lines: ['70%','50%'] },
]

const DeveloperSignupPage: React.FC = () => {
  const [formData, setFormData]               = useState({ name: '', email: '', phone_number: '', password: '', password_confirm: '', dev_key: '' })
  const [showPassword, setShowPassword]       = useState(false)
  const [showConfirm, setShowConfirm]         = useState(false)
  const [showDevKey, setShowDevKey]           = useState(false)
  const [error, setError]                     = useState('')
  const [loading, setLoading]                 = useState(false)
  const { registerDeveloper }                 = useAuth()
  const navigate                              = useNavigate()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
    if (error) setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || !formData.email || !formData.password || !formData.password_confirm || !formData.dev_key) { setError('Please fill in all required fields'); return }
    if (formData.password !== formData.password_confirm) { setError('Passwords do not match'); return }
    setLoading(true); setError('')
    try {
      await registerDeveloper(formData.email, formData.password, formData.name, formData.phone_number, formData.dev_key)
      navigate('/login', { state: { message: 'Developer account created! Please sign in.' } })
    } catch (err: any) {
      const msg = err.response?.data?.details?.dev_key?.[0] || 'Registration failed. Ensure email is unique and developer key is correct.'
      setError(msg)
    } finally { setLoading(false) }
  }

  const Label = ({ children }: { children: string }) => (
    <label style={{ fontSize: '0.68rem', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: '0.1em', color: '#aaa', display: 'block', marginBottom: 6 }}>{children}</label>
  )

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '1fr 1fr', fontFamily: "'Instrument Sans',sans-serif", background: '#fff' }}>
      <style>{`
        @keyframes sp-spin{to{transform:rotate(360deg)}}
        .sp-in{background:#fafafa;border:1px solid rgba(0,0,0,0.08);border-radius:10px;padding:11px 11px 11px 38px;width:100%;font-family:'Instrument Sans',sans-serif;font-size:0.88rem;color:#111;outline:none;transition:border-color .2s,box-shadow .2s;}
        .sp-in:focus{border-color:#3b82f6!important;box-shadow:0 0 0 3px rgba(59,130,246,0.1)!important;}
        .sp-btn:hover:not(:disabled){background:#2563eb!important;transform:translateY(-1px);}
        @media(max-width:768px){.sp-right{display:none!important;}}
      `}</style>

      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 56px', position: 'relative', minHeight: '100vh' }}>
        <div style={{ position: 'fixed', top: 0, left: 0, width: '50%', height: 60, display: 'flex', alignItems: 'center', padding: '0 56px', borderBottom: '1px solid rgba(0,0,0,0.06)', background: '#fff', zIndex: 10 }}>
          <Link to="/" style={{ fontFamily: "'Fraunces',serif", fontWeight: 900, fontSize: '1.25rem', color: '#0a0a0a', letterSpacing: '-0.5px', textDecoration: 'none' }}>Forma.</Link>
        </div>

        <div style={{ maxWidth: 360, width: '100%' }}>
          <div style={{ fontSize: '0.68rem', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase' as const, color: '#3b82f6', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Terminal size={14} /> Developer Access
          </div>
          <h1 style={{ fontFamily: "'Fraunces',serif", fontSize: '2.2rem', fontWeight: 900, letterSpacing: '-1.2px', color: '#0a0a0a', marginBottom: 6, lineHeight: 1.1 }}>
            Developer<br/><em style={{ fontStyle: 'italic', color: '#3b82f6' }}>Registration.</em>
          </h1>
          <p style={{ fontSize: '0.85rem', color: '#999', marginBottom: 22, lineHeight: 1.6 }}>Provision an isolated testing account with unlimited token resources.</p>

          {error && <div style={{ background: 'rgba(220,60,60,0.05)', border: '1px solid rgba(220,60,60,0.18)', borderRadius: 9, padding: '10px 14px', fontSize: '0.78rem', color: 'rgba(200,50,50,0.9)', marginBottom: 14 }}>{error}</div>}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <Label>Full Name</Label>
              <div style={{ position: 'relative' }}>
                <User size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#ccc', pointerEvents: 'none' }} />
                <input className="sp-in" type="text" name="name" value={formData.name} onChange={handleChange} placeholder="Dev name" required />
              </div>
            </div>
            <div>
              <Label>Email</Label>
              <div style={{ position: 'relative' }}>
                <Mail size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#ccc', pointerEvents: 'none' }} />
                <input className="sp-in" type="email" name="email" value={formData.email} onChange={handleChange} placeholder="dev@forma.ai" required />
              </div>
            </div>
            <div>
              <Label>Phone (optional)</Label>
              <div style={{ position: 'relative' }}>
                <Phone size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#ccc', pointerEvents: 'none' }} />
                <input className="sp-in" type="tel" name="phone_number" value={formData.phone_number} onChange={handleChange} placeholder="Internal extension" />
              </div>
            </div>
            <div>
              <Label>Password</Label>
              <div style={{ position: 'relative' }}>
                <Lock size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#ccc', pointerEvents: 'none' }} />
                <input className="sp-in" type={showPassword ? 'text' : 'password'} name="password" value={formData.password} onChange={handleChange} placeholder="Secret key" required />
                <button type="button" onClick={() => setShowPassword(!showPassword)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#bbb', display: 'flex', alignItems: 'center' }}>
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
            <div>
              <Label>Confirm Password</Label>
              <div style={{ position: 'relative' }}>
                <Lock size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#ccc', pointerEvents: 'none' }} />
                <input className="sp-in" type={showConfirm ? 'text' : 'password'} name="password_confirm" value={formData.password_confirm} onChange={handleChange} placeholder="Repeat secret key" required />
              </div>
            </div>

            <div>
              <Label>Developer Secret Key</Label>
              <div style={{ position: 'relative' }}>
                <Terminal size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#ccc', pointerEvents: 'none' }} />
                <input className="sp-in" type={showDevKey ? 'text' : 'password'} name="dev_key" value={formData.dev_key} onChange={handleChange} placeholder="Only devs know this (4 digits)" required />
                <button type="button" onClick={() => setShowDevKey(!showDevKey)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#bbb', display: 'flex', alignItems: 'center' }}>
                  {showDevKey ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="sp-btn"
              style={{ width: '100%', padding: '12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 10, fontFamily: "'Instrument Sans',sans-serif", fontSize: '0.88rem', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', transition: 'all .2s', marginTop: 4 }}>
              {loading ? 'Provisioning...' : 'Provision Developer Account'}
            </button>
          </form>
        </div>
      </div>

      <div className="sp-right" style={{ background: '#f0f7ff', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 52px', position: 'sticky' as const, top: 0, height: '100vh' }}>
        <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(rgba(59,130,246,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,0.03) 1px,transparent 1px)', backgroundSize: '40px 40px' }} />
        <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: 420 }}>
          <h2 style={{ fontFamily: "'Fraunces',serif", fontSize: '2rem', fontWeight: 900, color: '#0a0a0a', marginBottom: 6 }}>Dev Environment</h2>
          <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 28 }}>Complete isolation from production workflows and unlimited credit allocation.</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {showcaseCards.map((card, i) => (
              <div key={i} style={{ background: '#fff', border: '1px solid rgba(59,130,246,0.1)', borderRadius: 12, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 42, height: 42, borderRadius: 9, background: card.bg }} />
                <div>
                  <span style={{ fontSize: '0.58rem', fontWeight: 700, color: '#3b82f6', background: '#eff6ff', borderRadius: 20, padding: '2px 7px' }}>{card.tag}</span>
                  <div style={{ fontFamily: "'Fraunces',serif", fontSize: '0.85rem', fontWeight: 700 }}>{card.title}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DeveloperSignupPage
