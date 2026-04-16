/* eslint-disable react/prop-types */
import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Loader2,
  Sparkles,
  Leaf,
  Users,
  Building2,
  ChevronDown,
  ChevronRight,
  Zap,
  Clock,
  Wrench,
  Download,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react'
import { generateActionPlan, getActionPlan, downloadActionPlanPdf } from '../lib/api'

const EFFORT_CONFIG = {
  quick_win: { label: 'Quick win', icon: Zap, color: 'bg-forest-100 text-forest-800 border-forest-200' },
  moderate: { label: 'Moderate', icon: Clock, color: 'bg-amber-100 text-amber-800 border-amber-200' },
  structural: { label: 'Structural', icon: Wrench, color: 'bg-red-100 text-red-800 border-red-200' },
}

const PILLAR_CONFIG = {
  Environment: { icon: Leaf, gradient: 'from-emerald-600 to-green-700', badge: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  Social: { icon: Users, gradient: 'from-blue-600 to-indigo-700', badge: 'bg-blue-100 text-blue-800 border-blue-200' },
  Governance: { icon: Building2, gradient: 'from-purple-600 to-violet-700', badge: 'bg-purple-100 text-purple-800 border-purple-200' },
}

const LOADING_STEPS = [
  'Collecting compliance gaps...',
  'Grouping by ESG pillar...',
  'Analyzing improvement impact...',
  'Ranking by effort level...',
  'Building executive roadmap...',
]

const ActionPlan = ({ reportId, onClose, reportMeta }) => {
  const [phase, setPhase] = useState('loading') // loading | idle | generating | done | error
  const [plan, setPlan] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const [expandedPillar, setExpandedPillar] = useState(null)
  const [loadingStep, setLoadingStep] = useState(0)
  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const bodyRef = useRef(null)

  // On mount, try to load a cached plan from the server
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const cached = await getActionPlan(reportId)
        if (!cancelled) {
          setPlan(cached)
          setPhase('done')
          const pillars = cached.pillars || {}
          const biggest = Object.entries(pillars).sort((a, b) => b[1].length - a[1].length)[0]
          if (biggest) setExpandedPillar(biggest[0])
        }
      } catch {
        if (!cancelled) setPhase('idle')
      }
    })()
    return () => { cancelled = true }
  }, [reportId])

  // Cycle through loading step labels while generating
  useEffect(() => {
    if (phase !== 'generating') return
    setLoadingStep(0)
    const interval = setInterval(() => {
      setLoadingStep((s) => (s + 1) % LOADING_STEPS.length)
    }, 3500)
    return () => clearInterval(interval)
  }, [phase])

  const generate = async () => {
    setPhase('generating')
    setErrorMsg(null)
    try {
      const data = await generateActionPlan(reportId)
      setPlan(data)
      setPhase('done')
      const pillars = data.pillars || {}
      const biggest = Object.entries(pillars).sort((a, b) => b[1].length - a[1].length)[0]
      if (biggest) setExpandedPillar(biggest[0])
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Something went wrong'
      setErrorMsg(detail)
      setPhase('error')
    }
  }

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true)
    try {
      const blob = await downloadActionPlanPdf(reportId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const safeName = (reportMeta?.document_filename || 'report').replace(/\.pdf$/i, '')
      a.download = `${safeName}_${reportMeta?.framework || 'ESG'}_Action_Plan.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Action plan PDF download failed:', err)
    } finally {
      setDownloadingPdf(false)
    }
  }

  // Block background page scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const compliancePct = plan?.report_meta?.compliance_rate != null
    ? (plan.report_meta.compliance_rate * 100).toFixed(1)
    : reportMeta?.compliance_rate != null
      ? (reportMeta.compliance_rate * 100).toFixed(1)
      : '?'

  return (
    <AnimatePresence>
      <motion.div
        key="action-plan-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[60] bg-ink-950/60 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: 'spring', stiffness: 280, damping: 26 }}
          className="bg-white rounded-2xl shadow-2xl border border-ink-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="px-6 py-5 gradient-forest text-white flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-white/15 border border-white/20 flex items-center justify-center shrink-0">
                <Sparkles className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h2 className="font-display font-bold text-lg leading-tight">
                  Executive Action Plan
                </h2>
                <p className="text-[11px] text-white/80 truncate">
                  {reportMeta?.document_filename || 'Compliance report'} &middot; {reportMeta?.framework || ''}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {phase === 'done' && (
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  disabled={downloadingPdf}
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-white/15 hover:bg-white/25 border border-white/20 transition-colors text-sm font-semibold disabled:opacity-50"
                  aria-label="Download action plan as PDF"
                >
                  {downloadingPdf ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  <span>{downloadingPdf ? 'Generating...' : 'Download PDF'}</span>
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Body */}
          <div
            ref={bodyRef}
            className="flex-1 overflow-y-auto overscroll-contain"
          >
            {/* Initial loading check for cached plan */}
            {phase === 'loading' && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <Loader2 className="w-8 h-8 text-forest-600 animate-spin mb-3" />
                <p className="text-sm text-ink-500">Loading...</p>
              </div>
            )}

            {phase === 'idle' && (
              <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
                <div className="w-16 h-16 rounded-2xl bg-forest-100 border border-forest-200 flex items-center justify-center mb-5">
                  <TrendingUp className="w-8 h-8 text-forest-700" />
                </div>
                <h3 className="font-display font-bold text-xl text-ink-900 mb-2">
                  Gap Analysis &amp; Improvement Roadmap
                </h3>
                <p className="text-sm text-ink-600 max-w-md mb-8 leading-relaxed">
                  Our AI consultant will analyze all non-compliant and partially-compliant clauses,
                  group them by ESG pillar, and produce a prioritized action plan with specific
                  wording suggestions, sorted by effort level.
                </p>
                <button
                  type="button"
                  onClick={generate}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl gradient-forest text-white font-semibold text-sm shadow-lg hover:shadow-xl transition-all"
                >
                  <Sparkles className="w-4 h-4" />
                  Generate Action Plan
                </button>
              </div>
            )}

            {phase === 'generating' && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="relative mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-forest-100 border border-forest-200 flex items-center justify-center">
                    <Sparkles className="w-8 h-8 text-forest-700" />
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white border border-ink-200 flex items-center justify-center">
                    <Loader2 className="w-3.5 h-3.5 text-forest-600 animate-spin" />
                  </div>
                </div>
                <p className="text-sm text-ink-800 font-semibold mb-1">Generating Action Plan</p>
                <AnimatePresence mode="wait">
                  <motion.p
                    key={loadingStep}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.25 }}
                    className="text-xs text-ink-500"
                  >
                    {LOADING_STEPS[loadingStep]}
                  </motion.p>
                </AnimatePresence>
                <p className="text-[10px] text-ink-400 mt-3">This may take 15-30 seconds</p>
              </div>
            )}

            {phase === 'error' && (
              <div className="flex flex-col items-center justify-center py-20 text-center px-6">
                <AlertTriangle className="w-12 h-12 text-red-500 mb-3" />
                <p className="text-sm text-red-800 font-medium max-w-md mb-4">{errorMsg}</p>
                <button
                  type="button"
                  onClick={generate}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl gradient-forest text-white font-semibold text-sm shadow-lg"
                >
                  Retry
                </button>
              </div>
            )}

            {phase === 'done' && plan && (
              <div className="px-6 py-6 space-y-6">
                {/* Executive summary */}
                {plan.summary && (
                  <div className="bg-forest-50 border border-forest-200 rounded-xl p-5">
                    <div className="flex items-start gap-3">
                      <Sparkles className="w-5 h-5 text-forest-700 shrink-0 mt-0.5" />
                      <div>
                        <h3 className="font-display font-bold text-sm text-forest-900 mb-1">
                          Executive Summary
                        </h3>
                        <p className="text-sm text-forest-800 leading-relaxed">{plan.summary}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* KPI strip */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-clay-50 rounded-xl border border-ink-200 p-4 text-center">
                    <div className="text-2xl font-display font-bold text-ink-900">{compliancePct}%</div>
                    <div className="text-[10px] uppercase tracking-wide font-semibold text-ink-500 mt-1">Current compliance</div>
                  </div>
                  <div className="bg-clay-50 rounded-xl border border-ink-200 p-4 text-center">
                    <div className="text-2xl font-display font-bold text-ink-900">{plan.report_meta?.gaps_analyzed || 0}</div>
                    <div className="text-[10px] uppercase tracking-wide font-semibold text-ink-500 mt-1">Gaps analyzed</div>
                  </div>
                  <div className="bg-clay-50 rounded-xl border border-ink-200 p-4 text-center">
                    <div className="text-2xl font-display font-bold text-ink-900">
                      {plan.top_5?.length || 0}
                    </div>
                    <div className="text-[10px] uppercase tracking-wide font-semibold text-ink-500 mt-1">Priority actions</div>
                  </div>
                </div>

                {/* Top 5 priority actions */}
                {plan.top_5?.length > 0 && (
                  <div>
                    <h3 className="font-display font-bold text-base text-ink-900 mb-3 flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-forest-600" />
                      Top {plan.top_5.length} Priority Actions
                    </h3>
                    <div className="space-y-3">
                      {plan.top_5.map((item, i) => (
                        <Top5Card key={i} item={item} rank={i + 1} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Pillar breakdown */}
                {plan.pillars && Object.entries(plan.pillars).map(([pillar, actions]) => {
                  if (!actions || actions.length === 0) return null
                  const cfg = PILLAR_CONFIG[pillar] || PILLAR_CONFIG.Governance
                  const PillarIcon = cfg.icon
                  const isOpen = expandedPillar === pillar
                  return (
                    <div key={pillar} className="border border-ink-200 rounded-xl overflow-hidden">
                      <button
                        type="button"
                        onClick={() => setExpandedPillar(isOpen ? null : pillar)}
                        className="w-full flex items-center gap-3 px-5 py-4 bg-clay-50/60 hover:bg-clay-100/60 transition-colors text-left"
                      >
                        {isOpen ? <ChevronDown className="w-4 h-4 text-ink-500" /> : <ChevronRight className="w-4 h-4 text-ink-500" />}
                        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${cfg.gradient} flex items-center justify-center`}>
                          <PillarIcon className="w-4 h-4 text-white" />
                        </div>
                        <span className="font-display font-bold text-sm text-ink-900 flex-1">{pillar}</span>
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full border text-xs font-semibold ${cfg.badge}`}>
                          {actions.length} action{actions.length !== 1 ? 's' : ''}
                        </span>
                      </button>
                      <AnimatePresence initial={false}>
                        {isOpen && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="px-5 py-4 space-y-3 border-t border-ink-200">
                              {actions.map((item, i) => (
                                <ActionCard key={i} item={item} />
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────

const EffortBadge = ({ effort }) => {
  const cfg = EFFORT_CONFIG[effort] || EFFORT_CONFIG.moderate
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-semibold ${cfg.color}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

const Top5Card = ({ item, rank }) => (
  <div className="flex gap-4 bg-white rounded-xl border border-ink-200 p-4 shadow-sm">
    <div className="w-9 h-9 rounded-full bg-forest-600 text-white flex items-center justify-center font-display font-bold text-sm shrink-0">
      {rank}
    </div>
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 flex-wrap mb-1">
        <span className="font-semibold text-sm text-ink-900">{item.action}</span>
        <EffortBadge effort={item.effort} />
        {item.pillar && (
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold ${(PILLAR_CONFIG[item.pillar] || PILLAR_CONFIG.Governance).badge}`}>
            {item.pillar}
          </span>
        )}
      </div>
      <p className="text-xs text-ink-700 leading-relaxed">{item.detail}</p>
      {item.impact && (
        <p className="text-[11px] text-forest-700 mt-1.5 font-medium italic">{item.impact}</p>
      )}
      {item.clauses?.length > 0 && (
        <p className="text-[10px] text-ink-400 mt-1">
          Clauses: {item.clauses.join(', ')}
        </p>
      )}
    </div>
  </div>
)

const ActionCard = ({ item }) => (
  <div className="bg-white rounded-lg border border-ink-200 p-4">
    <div className="flex items-center gap-2 flex-wrap mb-1.5">
      <span className="font-semibold text-sm text-ink-900">{item.action}</span>
      <EffortBadge effort={item.effort} />
    </div>
    <p className="text-xs text-ink-700 leading-relaxed">{item.detail}</p>
    {item.impact && (
      <p className="text-[11px] text-forest-700 mt-1.5 font-medium italic">{item.impact}</p>
    )}
    {item.clauses?.length > 0 && (
      <p className="text-[10px] text-ink-400 mt-1">
        Clauses: {item.clauses.join(', ')}
      </p>
    )}
  </div>
)

export default ActionPlan
