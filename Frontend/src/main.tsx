import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App'

window.addEventListener('unhandledrejection', (event) => {
  const msg = String(event.reason && (event.reason.message || event.reason))
  if (msg.includes('ERR_NETWORK_IO_SUSPENDED')) {
    event.preventDefault()
  }
})

window.addEventListener('error', (event) => {
  const msg = String(event.message || '')
  if (msg.includes('ERR_NETWORK_IO_SUSPENDED')) {
    event.preventDefault()
  }
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
