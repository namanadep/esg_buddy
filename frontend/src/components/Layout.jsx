import React, { useState, useEffect } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Leaf, 
  Upload, 
  FileText, 
  CheckSquare, 
  BarChart3,
  Activity,
  Menu,
  X
} from 'lucide-react'
import { getHealthCheck } from '../lib/api'

const Layout = () => {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [healthStatus, setHealthStatus] = useState(null)
  
  useEffect(() => {
    // Check health status
    getHealthCheck()
      .then(data => setHealthStatus(data))
      .catch(() => setHealthStatus({ status: 'error' }))
  }, [])
  
  const navigation = [
    { name: 'Home', href: '/', icon: Leaf },
    { name: 'Upload', href: '/upload', icon: Upload },
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'Clauses', href: '/clauses', icon: CheckSquare },
    { name: 'Reports', href: '/reports', icon: BarChart3 },
  ]
  
  const isActive = (href) => {
    if (href === '/') return location.pathname === '/'
    return location.pathname.startsWith(href)
  }
  
  return (
    <div className="min-h-screen bg-clay-50">
      {/* Background gradient */}
      <div className="fixed inset-0 gradient-radial pointer-events-none" />
      
      {/* Navigation */}
      <nav className="relative border-b border-ink-200/30 glass">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-3 group">
              <div className="w-12 h-12 gradient-forest rounded-2xl flex items-center justify-center transform group-hover:scale-105 transition-transform duration-300">
                <Leaf className="w-7 h-7 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <h1 className="font-display text-2xl font-semibold text-ink-900 tracking-tight">
                  ESGBuddy
                </h1>
                <p className="text-xs text-ink-500 font-medium tracking-wide">
                  COMPLIANCE COPILOT
                </p>
              </div>
            </Link>
            
            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-1">
              {navigation.map((item, index) => {
                const Icon = item.icon
                const active = isActive(item.href)
                
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className="relative px-4 py-2 group"
                  >
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="flex items-center space-x-2"
                    >
                      <Icon 
                        className={`w-4 h-4 transition-colors ${
                          active ? 'text-forest-600' : 'text-ink-500 group-hover:text-forest-600'
                        }`}
                        strokeWidth={2}
                      />
                      <span className={`text-sm font-medium transition-colors ${
                        active ? 'text-forest-700' : 'text-ink-700 group-hover:text-forest-700'
                      }`}>
                        {item.name}
                      </span>
                    </motion.div>
                    
                    {active && (
                      <motion.div
                        layoutId="activeTab"
                        className="absolute bottom-0 left-0 right-0 h-0.5 bg-forest-600"
                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                      />
                    )}
                  </Link>
                )
              })}
            </div>
            
            {/* Health Status */}
            <div className="hidden md:flex items-center space-x-3">
              {healthStatus && (
                <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-white/50 border border-ink-200/50">
                  <Activity 
                    className={`w-3.5 h-3.5 ${
                      healthStatus.status === 'healthy' 
                        ? 'text-green-600 animate-pulse' 
                        : 'text-red-600'
                    }`}
                  />
                  <span className="text-xs font-medium text-ink-700">
                    {healthStatus.status === 'healthy' ? 'Operational' : 'Error'}
                  </span>
                </div>
              )}
            </div>
            
            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-ink-700 hover:bg-white/50 transition-colors"
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
        
        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-ink-200/30 bg-white/90"
          >
            <div className="px-4 py-4 space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon
                const active = isActive(item.href)
                
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                      active
                        ? 'bg-forest-50 text-forest-700'
                        : 'text-ink-700 hover:bg-clay-100'
                    }`}
                  >
                    <Icon className="w-5 h-5" strokeWidth={2} />
                    <span className="font-medium">{item.name}</span>
                  </Link>
                )
              })}
            </div>
          </motion.div>
        )}
      </nav>
      
      {/* Main Content */}
      <main className="relative">
        <Outlet />
      </main>
      
      {/* Footer */}
      <footer className="relative mt-20 border-t border-ink-200/30 bg-white/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <p className="text-sm text-ink-600">
              © 2026 ESGBuddy. All rights reserved.
            </p>
            <div className="flex items-center space-x-6 text-sm text-ink-600">
              <span>Powered by AI & ESG Standards</span>
              {healthStatus && healthStatus.vector_store && (
                <span className="px-3 py-1 rounded-full bg-forest-50 text-forest-700 text-xs font-medium">
                  {healthStatus.vector_store.esg_clauses} Clauses Indexed
                </span>
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default Layout
