import { Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import { apiClient } from './lib/apiClient'
import { AuthProvider } from './contexts/AuthContext'
import { BrandProvider } from './contexts/BrandContext'
import { BrandThemeProvider } from './contexts/BrandThemeProvider'
import { ImageLibraryProvider } from './components/ImageLibrary'
import LandingPage from './components/LandingPage'
import LoginPage from './components/LoginPage'
import SignupPage from './components/SignupPage'
import Dashboard from './components/Dashboard'
import CreateLeadMagnet from './components/CreateLeadMagnet'
import BrandAssets from './components/BrandAssets'
import FormaAI from './components/FormaAI'
import Settings from './components/Settings'
import ProtectedRoute from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'
import './App.css'

function App() {
  useEffect(() => {
    apiClient.options('/api/health/').catch(() => {});
    apiClient.get('/api/health/').catch(() => {});
  }, []);
  return (
    <ErrorBoundary>
      <div className="App">
        <AuthProvider>
          <BrandProvider>
            <BrandThemeProvider>
              <ImageLibraryProvider>
                <Routes>
                  <Route path="/" element={<LandingPage />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/signup" element={<SignupPage />} />
                  <Route 
                    path="/dashboard" 
                    element={
                      <ProtectedRoute>
                        <Dashboard />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/create-lead-magnet" 
                    element={
                      <ProtectedRoute>
                        <CreateLeadMagnet />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/brand-assets" 
                    element={
                      <ProtectedRoute>
                        <BrandAssets />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/forma-ai" 
                    element={
                      <ProtectedRoute>
                        <FormaAI />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/settings" 
                    element={
                      <ProtectedRoute>
                        <Settings />
                      </ProtectedRoute>
                    } 
                  />
                </Routes>
              </ImageLibraryProvider>
              </BrandThemeProvider>
            </BrandProvider>
          </AuthProvider>
      </div>
    </ErrorBoundary>
  )
}

export default App
