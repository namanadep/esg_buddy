import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Upload, 
  FileSearch, 
  CheckCircle2, 
  TrendingUp, 
  Sparkles,
  ArrowRight,
  Shield,
  Zap,
  Target
} from 'lucide-react'
import { getSystemStats } from '../lib/api'

const Home = () => {
  const [stats, setStats] = useState(null)
  
  useEffect(() => {
    getSystemStats()
      .then(setStats)
      .catch(console.error)
  }, [])
  
  const features = [
    {
      icon: FileSearch,
      title: 'Semantic Retrieval',
      description: 'Advanced AI finds relevant ESG evidence in your documents using vector embeddings'
    },
    {
      icon: Sparkles,
      title: 'GPT-4 Analysis',
      description: 'State-of-the-art language models evaluate compliance with expert-level reasoning'
    },
    {
      icon: Shield,
      title: 'Rule Validation',
      description: 'Deterministic rule engine validates numeric, temporal, and structural requirements'
    },
    {
      icon: Target,
      title: 'Accuracy Tracking',
      description: 'Comprehensive metrics measure retrieval accuracy, LLM precision, and confidence calibration'
    }
  ]
  
  const frameworks = [
    { name: 'BRSR', count: stats?.clauses_parsed || 0, color: 'forest' },
    { name: 'GRI', count: stats?.clauses_parsed || 0, color: 'clay' },
    { name: 'SASB', count: stats?.clauses_parsed || 0, color: 'forest' },
    { name: 'TCFD', count: stats?.clauses_parsed || 0, color: 'clay' }
  ]
  
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-forest-50 border border-forest-200 mb-6">
                <Zap className="w-4 h-4 text-forest-600" />
                <span className="text-sm font-medium text-forest-700">
                  AI-Powered Compliance Engine
                </span>
              </div>
              
              <h1 className="font-display text-5xl lg:text-6xl font-bold text-ink-900 mb-6 leading-tight">
                Your Intelligent
                <span className="block text-forest-600 italic">
                  ESG Copilot
                </span>
              </h1>
              
              <p className="text-xl text-ink-600 mb-8 leading-relaxed max-w-xl">
                Automated clause-level ESG compliance verification using semantic retrieval, 
                GPT-4 reasoning, and deterministic rule validation.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  to="/upload"
                  className="group inline-flex items-center justify-center px-8 py-4 gradient-forest text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
                >
                  <Upload className="w-5 h-5 mr-2 group-hover:rotate-12 transition-transform" />
                  Upload Document
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </Link>
                
                <Link
                  to="/clauses"
                  className="inline-flex items-center justify-center px-8 py-4 bg-white border-2 border-ink-200 text-ink-700 rounded-xl font-semibold hover:border-forest-300 hover:bg-forest-50 transition-all duration-300"
                >
                  Explore Clauses
                </Link>
              </div>
              
              {stats && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="mt-12 flex items-center space-x-8"
                >
                  <div>
                    <div className="text-3xl font-display font-bold text-ink-900">
                      {stats.clauses_parsed}
                    </div>
                    <div className="text-sm text-ink-600 font-medium">
                      ESG Clauses
                    </div>
                  </div>
                  <div className="h-12 w-px bg-ink-200" />
                  <div>
                    <div className="text-3xl font-display font-bold text-ink-900">
                      {stats.documents || 0}
                    </div>
                    <div className="text-sm text-ink-600 font-medium">
                      Documents Analyzed
                    </div>
                  </div>
                  <div className="h-12 w-px bg-ink-200" />
                  <div>
                    <div className="text-3xl font-display font-bold text-ink-900">
                      {stats.reports || 0}
                    </div>
                    <div className="text-sm text-ink-600 font-medium">
                      Reports Generated
                    </div>
                  </div>
                </motion.div>
              )}
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative"
            >
              <div className="relative bg-white rounded-3xl shadow-2xl overflow-hidden border border-ink-200/50">
                <div className="p-8">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="font-display text-xl font-semibold text-ink-900">
                      Compliance Overview
                    </h3>
                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                  </div>
                  
                  <div className="space-y-4">
                    {[
                      { label: 'GRI 305: Emissions', status: 'Supported', value: 95 },
                      { label: 'BRSR Principle 6', status: 'Partial', value: 68 },
                      { label: 'TCFD Strategy (a)', status: 'Supported', value: 88 },
                      { label: 'SASB TR-AU-410a', status: 'Inferred', value: 72 }
                    ].map((item, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.4 + idx * 0.1 }}
                        className="relative"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-ink-700">
                            {item.label}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded-full font-semibold ${
                            item.status === 'Supported' 
                              ? 'bg-green-100 text-green-700'
                              : item.status === 'Partial'
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-blue-100 text-blue-700'
                          }`}>
                            {item.status}
                          </span>
                        </div>
                        <div className="h-2 bg-clay-100 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${item.value}%` }}
                            transition={{ duration: 1, delay: 0.6 + idx * 0.1 }}
                            className="h-full gradient-forest"
                          />
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
                
                <div className="bg-gradient-to-br from-forest-600 to-forest-700 px-8 py-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-forest-100 text-sm font-medium mb-1">
                        Overall Compliance Rate
                      </div>
                      <div className="text-white text-3xl font-display font-bold">
                        81%
                      </div>
                    </div>
                    <TrendingUp className="w-12 h-12 text-forest-200" strokeWidth={1.5} />
                  </div>
                </div>
              </div>
              
              {/* Decorative elements */}
              <div className="absolute -top-4 -right-4 w-24 h-24 bg-forest-200 rounded-full opacity-20 blur-2xl" />
              <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-clay-300 rounded-full opacity-20 blur-3xl" />
            </motion.div>
          </div>
        </div>
      </section>
      
      {/* Features Section */}
      <section className="relative py-20 bg-white/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-display text-4xl font-bold text-ink-900 mb-4">
              How ESGBuddy Works
            </h2>
            <p className="text-lg text-ink-600 max-w-2xl mx-auto">
              A hybrid AI pipeline that combines the best of semantic search, 
              language models, and rule-based validation
            </p>
          </motion.div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  className="group"
                >
                  <div className="relative p-8 bg-white rounded-2xl border border-ink-200 hover:border-forest-300 transition-all duration-300 hover:shadow-lg">
                    <div className="w-14 h-14 gradient-forest rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                      <Icon className="w-7 h-7 text-white" strokeWidth={2} />
                    </div>
                    
                    <h3 className="font-display text-xl font-semibold text-ink-900 mb-3">
                      {feature.title}
                    </h3>
                    
                    <p className="text-ink-600 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>
      
      {/* Frameworks Section */}
      <section className="relative py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-display text-4xl font-bold text-ink-900 mb-4">
              Supported ESG Frameworks
            </h2>
            <p className="text-lg text-ink-600 max-w-2xl mx-auto">
              Comprehensive coverage of major ESG reporting standards
            </p>
          </motion.div>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {frameworks.map((framework, index) => (
              <motion.div
                key={framework.name}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
                className="relative p-8 bg-white rounded-2xl border-2 border-ink-200 hover:border-forest-400 transition-all duration-300 hover:shadow-xl group cursor-pointer"
              >
                <div className="text-center">
                  <div className="font-display text-3xl font-bold text-ink-900 mb-2">
                    {framework.name}
                  </div>
                  <div className="text-sm text-ink-500 font-medium">
                    ESG Framework
                  </div>
                  <div className="mt-4 pt-4 border-t border-ink-100">
                    <div className="text-2xl font-bold text-forest-600 group-hover:scale-110 transition-transform">
                      {Math.floor(framework.count / 4)}+
                    </div>
                    <div className="text-xs text-ink-500 font-medium mt-1">
                      Clauses
                    </div>
                  </div>
                </div>
                
                <div className="absolute inset-0 bg-gradient-to-br from-forest-50 to-transparent opacity-0 group-hover:opacity-100 rounded-2xl transition-opacity duration-300 -z-10" />
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

export default Home
