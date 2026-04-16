/* eslint-disable react/prop-types */
import React, { useEffect, useRef, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  ExternalLink,
  Sparkles,
  Zap,
} from 'lucide-react'
import { streamEvaluation } from '../lib/api'

const STATUS_CONFIG = {
  supported: {
    icon: CheckCircle2,
    bg: 'bg-forest-500',
    ring: 'ring-forest-300',
    label: 'Supported',
  },
  partial: {
    icon: AlertTriangle,
    bg: 'bg-amber-500',
    ring: 'ring-amber-300',
    label: 'Partial',
  },
  not_supported: {
    icon: XCircle,
    bg: 'bg-red-500',
    ring: 'ring-red-300',
    label: 'Not supported',
  },
}

/**
 * Full-screen modal that streams clause-by-clause evaluation in real time.
 *
 * Props:
 *   documentId, framework, documentFilename – evaluation params
 *   onClose – called when the user closes the overlay
 */
const LiveEvaluation = ({ documentId, framework, documentFilename, onClose }) => {
  const [phase, setPhase] = useState('connecting') // connecting | streaming | done | error
  const [total, setTotal] = useState(0)
  const [clauses, setClauses] = useState([]) // { clause_id, title, section, status }
  const [counts, setCounts] = useState({ supported: 0, partial: 0, not_supported: 0 })
  const [reportId, setReportId] = useState(null)
  const [summary, setSummary] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const gridRef = useRef(null)

  const handleEvent = useCallback((eventName, data) => {
    if (eventName === 'init') {
      setTotal(data.total)
      setPhase('streaming')
    } else if (eventName === 'clause') {
      setClauses((prev) => [
        ...prev,
        {
          clause_id: data.clause_id,
          title: data.title,
          section: data.section,
          status: data.status,
        },
      ])
      setCounts({
        supported: data.supported,
        partial: data.partial,
        not_supported: data.not_supported,
      })
    } else if (eventName === 'done') {
      setReportId(data.report_id)
      setSummary(data.summary)
      setPhase('done')
    } else if (eventName === 'error') {
      setErrorMsg(data.message || 'Evaluation failed')
      setPhase('error')
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    ;(async () => {
      try {
        await streamEvaluation(documentId, framework, documentFilename, (ev, data) => {
          if (!controller.signal.aborted) handleEvent(ev, data)
        }, { signal: controller.signal })
      } catch (err) {
        if (!controller.signal.aborted) {
          setErrorMsg(err?.message || 'Stream connection failed')
          setPhase('error')
        }
      }
    })()
    return () => {
      controller.abort()
    }
  }, [documentId, framework, documentFilename, handleEvent])

  // Auto-scroll the grid to keep latest results visible
  useEffect(() => {
    const el = gridRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [clauses])

  const completed = clauses.length
  const pct = total > 0 ? (completed / total) * 100 : 0
  const rate =
    total > 0
      ? (((counts.supported + counts.partial) / total) * 100).toFixed(1)
      : '0.0'

  return (
    <AnimatePresence>
      <motion.div
        key="live-eval-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[60] bg-ink-950/60 backdrop-blur-sm flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: 'spring', stiffness: 280, damping: 26 }}
          className="bg-white rounded-2xl shadow-2xl border border-ink-200 w-full max-w-3xl max-h-[88vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="px-6 py-5 gradient-forest text-white flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-white/15 border border-white/20 flex items-center justify-center shrink-0">
                <Zap className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h2 className="font-display font-bold text-lg leading-tight">
                  Live evaluation
                </h2>
                <p className="text-[11px] text-white/80 truncate">
                  {documentFilename} &middot; {framework}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/10 transition-colors shrink-0"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Progress bar */}
          <div className="px-6 pt-5 pb-3 shrink-0">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-ink-600 font-medium">
                {phase === 'connecting' && 'Connecting...'}
                {phase === 'streaming' && `Evaluating ${completed} of ${total} clauses`}
                {phase === 'done' && `All ${total} clauses evaluated`}
                {phase === 'error' && 'Evaluation failed'}
              </span>
              <span className="font-display text-sm font-bold text-forest-700 tabular-nums">
                {rate}% compliance
              </span>
            </div>
            <div className="h-2.5 bg-clay-100 rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full gradient-forest"
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ ease: 'easeOut', duration: 0.35 }}
              />
            </div>
          </div>

          {/* KPI strip */}
          <div className="px-6 pb-4 flex items-center gap-3 shrink-0">
            <KpiBadge
              label="Supported"
              count={counts.supported}
              color="bg-forest-100 text-forest-800 border-forest-200"
            />
            <KpiBadge
              label="Partial"
              count={counts.partial}
              color="bg-amber-100 text-amber-800 border-amber-200"
            />
            <KpiBadge
              label="Not supported"
              count={counts.not_supported}
              color="bg-red-100 text-red-800 border-red-200"
            />
            {total > 0 && completed < total && phase === 'streaming' && (
              <KpiBadge
                label="Pending"
                count={total - completed}
                color="bg-clay-100 text-ink-600 border-clay-200"
              />
            )}
          </div>

          {/* Clause grid */}
          <div
            ref={gridRef}
            className="flex-1 overflow-y-auto px-6 pb-4"
          >
            {phase === 'connecting' && (
              <div className="flex flex-col items-center justify-center py-16 text-ink-500">
                <Loader2 className="w-8 h-8 animate-spin text-forest-600 mb-3" />
                <p className="text-sm">Starting evaluation&hellip;</p>
              </div>
            )}

            {(phase === 'streaming' || phase === 'done') && (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                {/* Completed clauses */}
                {clauses.map((c, i) => (
                  <ClauseChip key={c.clause_id + '-' + i} clause={c} index={i} />
                ))}
                {/* Pending placeholders */}
                {phase === 'streaming' &&
                  Array.from({ length: Math.min(total - completed, 12) }).map((_, i) => (
                    <PendingChip key={`pending-${i}`} />
                  ))}
              </div>
            )}

            {phase === 'error' && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <XCircle className="w-12 h-12 text-red-500 mb-3" />
                <p className="text-sm text-red-800 font-medium max-w-md">{errorMsg}</p>
              </div>
            )}
          </div>

          {/* Footer — done state */}
          {phase === 'done' && reportId && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="px-6 py-4 bg-forest-50 border-t border-forest-200 flex items-center justify-between shrink-0"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-forest-700" />
                <p className="text-sm font-semibold text-forest-900">
                  Evaluation complete &mdash; {summary?.compliance_rate != null
                    ? `${(summary.compliance_rate * 100).toFixed(1)}% compliance`
                    : `${rate}% compliance`}
                </p>
              </div>
              <Link
                to={`/reports/${reportId}`}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl gradient-forest text-white font-semibold text-sm shadow-lg hover:shadow-xl transition-all"
              >
                View full report
                <ExternalLink className="w-4 h-4" />
              </Link>
            </motion.div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────

const KpiBadge = ({ label, count, color }) => (
  <div
    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold tabular-nums ${color}`}
  >
    <span>{label}</span>
    <span>{count}</span>
  </div>
)

const ClauseChip = ({ clause, index }) => {
  const cfg = STATUS_CONFIG[clause.status] || STATUS_CONFIG.not_supported
  const Icon = cfg.icon
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25, delay: Math.min(index * 0.008, 0.15) }}
      className={`rounded-xl border border-ink-200 bg-white p-2.5 flex items-start gap-2 ring-1 ${cfg.ring}`}
    >
      <div
        className={`w-5 h-5 rounded-full ${cfg.bg} flex items-center justify-center shrink-0 mt-0.5`}
      >
        <Icon className="w-3 h-3 text-white" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold text-ink-900 leading-tight truncate" title={clause.title}>
          {clause.title}
        </p>
        <p className="text-[10px] text-ink-500 truncate">{clause.section || clause.clause_id}</p>
      </div>
    </motion.div>
  )
}

const PendingChip = () => (
  <div className="rounded-xl border border-dashed border-ink-200 bg-clay-50/50 p-2.5 flex items-start gap-2 animate-pulse">
    <div className="w-5 h-5 rounded-full bg-ink-100 flex items-center justify-center shrink-0 mt-0.5">
      <Loader2 className="w-3 h-3 text-ink-400 animate-spin" />
    </div>
    <div className="min-w-0 flex-1 space-y-1">
      <div className="h-3 w-3/4 bg-ink-100 rounded" />
      <div className="h-2.5 w-1/2 bg-ink-100/60 rounded" />
    </div>
  </div>
)

export default LiveEvaluation
