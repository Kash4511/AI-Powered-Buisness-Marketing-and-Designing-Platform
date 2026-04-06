import React, { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Download, Plus, Settings, LogOut, User, Palette, Trash2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { dashboardApi } from '../lib/dashboardApi'
import type { DashboardStats, LeadMagnet } from '../lib/dashboardApi'
import './Dashboard.css'

const Dashboard: React.FC = () => {
  const { logout, user } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [projects, setProjects] = useState<LeadMagnet[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const handleCreateLeadMagnet = () => {
    navigate('/create-lead-magnet')
  }

  const handleDeleteLeadMagnet = async (id: number, title: string) => {
    if (!confirm(`Are you sure you want to delete "${title}"? This action cannot be undone.`)) {
      return
    }

    try {
      setDeletingId(id)
      await dashboardApi.deleteLeadMagnet(id)
      
      setProjects(projects.filter(p => p.id !== id))
      
      const [statsData] = await Promise.all([
        dashboardApi.getStats()
      ])
      setStats(statsData)
    } catch (err) {
      console.error('Failed to delete lead magnet:', err)
      alert('Failed to delete lead magnet. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }
  
  // Fetch dashboard data on component mount
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        const [statsData, projectsData] = await Promise.all([
          dashboardApi.getStats(),
          dashboardApi.getLeadMagnets()
        ])
        setStats(statsData)
        setProjects(projectsData)
        setError(null)
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
        setError('Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) return projects
    const query = searchQuery.toLowerCase()
    return projects.filter(project => 
      project.title.toLowerCase().includes(query) ||
      project.status.toLowerCase().includes(query)
    )
  }, [projects, searchQuery])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    
    if (diffInDays === 0) return 'Today'
    if (diffInDays === 1) return '1 day ago'
    if (diffInDays < 7) return `${diffInDays} days ago`
    return date.toLocaleDateString()
  }

  if (loading) {
    return (
      <div className="dashboard">
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#ffffff' }}>
          Loading dashboard...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dashboard">
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#ff6b6b' }}>
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <nav className="dashboard-nav">
        <div className="nav-brand">Forma</div>
        <div className="nav-center-info" style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          {stats && (
            <div className="token-display" style={{ 
              background: 'rgba(197, 160, 89, 0.1)', 
              padding: '0.4rem 0.8rem', 
              borderRadius: '20px',
              border: '1px solid rgba(197, 160, 89, 0.3)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
              color: '#c5a059'
            }}>
              <span style={{ fontWeight: 600 }}>Groq Tokens:</span>
              <span>{stats.ai_credits_remaining.toLocaleString()} left</span>
            </div>
          )}
          <div className="user-profile" style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', color: '#ffffff' }}>
            <div className="user-avatar" style={{ 
              width: '32px', 
              height: '32px', 
              borderRadius: '50%', 
              background: '#c5a059',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              fontSize: '0.9rem'
            }}>
              {user?.name?.charAt(0) || 'U'}
            </div>
            <span className="user-name" style={{ fontWeight: 500 }}>{user?.name || 'User'}</span>
          </div>
        </div>
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
          
          <button className="sidebar-create-btn" onClick={handleCreateLeadMagnet}>
            <Plus size={20} />
            Create Lead Magnet
          </button>

          <div className="sidebar-section">
            <h4>Navigation</h4>
            <nav className="sidebar-nav">
              <a href="#" className="nav-item active">
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

        <main className="dashboard-main-content">
          <div className="main-header">
            <div className="header-top">
              <motion.h1
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                className="main-title"
              >
                My Lead Magnets
              </motion.h1>
              <motion.button
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="create-btn-header"
                onClick={handleCreateLeadMagnet}
              >
                <Plus size={20} />
                Create Lead Magnet
              </motion.button>
            </div>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="main-subtitle"
            >
              Manage and interact with your AI-powered lead magnets
            </motion.p>
          </div>

          <div className="stats-grid">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="stat-card"
            >
              <div className="stat-header">
                <span className="stat-label">Total Lead Magnets</span>
                <FileText className="stat-icon" />
              </div>
              <div className="stat-value">{stats?.total_lead_magnets || 0}</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="stat-card"
            >
              <div className="stat-header">
                <span className="stat-label">Active Lead Magnets</span>
                <Download className="stat-icon" />
              </div>
              <div className="stat-value">{stats?.active_lead_magnets || 0}</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="stat-card"
            >
              <div className="stat-header">
                <span className="stat-label">Total Downloads</span>
                <Settings className="stat-icon" />
              </div>
              <div className="stat-value">{stats?.total_downloads || 0}</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="stat-card"
            >
              <div className="stat-header">
                <span className="stat-label">Leads Generated</span>
                <User className="stat-icon" />
              </div>
              <div className="stat-value">{stats?.leads_generated || 0}</div>
            </motion.div>
          </div>

          <div className="content-section">
            <div className="search-section">
              <div className="search-wrapper">
                <input
                  type="text"
                  placeholder="Search lead magnets..."
                  className="search-input"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className="projects-grid">
              {filteredProjects.length === 0 ? (
                <div className="no-results">
                  {searchQuery.trim() ? (
                    <p>No lead magnets found matching "{searchQuery}"</p>
                  ) : (
                    <div>
                      <p>No lead magnets created yet</p>
                      <p style={{ fontSize: '0.9rem', color: '#888', marginTop: '0.5rem' }}>Click "Create Lead Magnet" to get started</p>
                    </div>
                  )}
                </div>
              ) : (
                filteredProjects.map((project, index) => (
                  <motion.div
                    key={project.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className={`project-card ${project.status}`}
                  >
                    <div className="project-header">
                      <div className="project-avatar">
                        <FileText className="project-icon" />
                      </div>
                      <div className="project-info">
                        <h3 className="project-title">{project.title}</h3>
                        <span className={`status-badge ${project.status}`}>
                          {project.status === 'in-progress' ? 'In Progress' : 
                           project.status === 'completed' ? 'Completed' : 'Draft'}
                        </span>
                      </div>
                      <button 
                        className="delete-btn"
                        onClick={() => handleDeleteLeadMagnet(project.id, project.title)}
                        disabled={deletingId === project.id}
                        title="Delete lead magnet"
                      >
                        {deletingId === project.id ? '...' : <Trash2 size={18} />}
                      </button>
                    </div>
                    
                    <p className="project-description">
                      {project.description || 
                       (project.status === 'completed' ? 'Generates high-quality leads for architectural services' :
                        project.status === 'in-progress' ? 'Converting prospects into qualified leads' : 
                        'Draft lead magnet ready for review')}
                    </p>
                    
                    <div className="project-metrics">
                      <div className="metric">
                        <span className="metric-value">{project.downloads_count}</span>
                        <span className="metric-label">Downloads</span>
                      </div>
                      <div className="metric">
                        <span className="metric-value">{project.leads_count}</span>
                        <span className="metric-label">Leads Generated</span>
                      </div>
                    </div>
                    
                    <div className="project-footer">
                      <span className="project-last-activity">Created: {formatDate(project.created_at)}</span>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default Dashboard