/**
 * Application entry point.
 *
 * Mounts React app to DOM with StrictMode enabled.
 *
 * Related: App.tsx (root component), index.css (global styles)
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
