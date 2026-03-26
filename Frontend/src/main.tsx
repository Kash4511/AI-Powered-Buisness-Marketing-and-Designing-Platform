import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App'

window.addEventListener('unhandledrejection', (event) => {
  const msg = String(event.reason && (event.reason.message || event.reason))
  if (msg.includes('ERR_NETWORK_IO_SUSPENDED')) {
    event.preventDefault()
    return
  }
  console.error('[Global Promise Rejection]', event.reason);
})

window.addEventListener('error', (event) => {
  const msg = String(event.message || '')
  if (msg.includes('ERR_NETWORK_IO_SUSPENDED')) {
    event.preventDefault()
    return
  }
  console.error('[Global Error]', event.error || msg);
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
