/* eslint-disable react/prop-types */
import React, { useState, useEffect, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  GitCompare,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  ChevronDown,
  Loader2,
  Building2,
  TrendingUp,
  TrendingDown,
  Target,
  Award,
  BarChart3,
  MinusCircle,
} from 'lucide-react'
import { listComplianceReports } from '../lib/api'

const FRAMEWORK_ORDER = ['BRSR', 'GRI', 'SASB', 'TCFD']

const FRAMEWORK_THEME = {
  BRSR: {
    badge: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    accent: '#4f46e5',
  },
  GRI: {
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    accent: '#059669',
  },
  SASB: {
    badge: 'bg-amber-100 text-amber-800 border-amber-200',
    accent: '#d97706',
  },
  TCFD: {
    badge: 'bg-sky-100 text-sky-800 border-sky-200',
    accent: '#0284c7',
  },
}

const STATUS_COLORS = {
  supported: '#2a6752',
  partial: '#c4a574',
  notSupported: '#c45c5c',
}

// Base select classes WITHOUT left padding — caller chooses pl-4 or pl-12
const selectFieldClass =
  'w-full appearance-none pr-11 py-3 bg-white border border-ink-200 rounded-xl text-sm text-ink-900 ' +
  'shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 ' +
  'transition-colors cursor-pointer font-medium'

function companyFromFilename(filename) {
  if (!filename) return 'Unknown'
  let base = filename.replace(/\.[^.]+$/i, '').trim()
  const suffix = /\s+(SASB|GRI|BRSR|TCFD|ESG)$/i
  while (suffix.test(base)) {
    base = base.replace(suffix, '').trim()
  }
  return base || 'Unknown'
}

function pickLatestPerCompanyFramework(reports) {
  const map = new Map()
  for (const r of reports) {
    const company = companyFromFilename(r.document_filename)
    const key = `${company}||${r.framework}`
    const prev = map.get(key)
    if (!prev || new Date(r.generated_at) > new Date(prev.generated_at)) {
      map.set(key, { ...r, _company: company })
    }
  }
  return Array.from(map.values())
}

const Compare = () => {
  const [searchParams] = useSearchParams()
  const preselect = searchParams.get('company') || ''
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCompany, setSelectedCompany] = useState(preselect)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const data = await listComplianceReports()
        if (!cancelled) setReports(data.reports || [])
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || e?.message || 'Failed to load reports')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const deduped = useMemo(() => pickLatestPerCompanyFramework(reports), [reports])

  const companies = useMemo(() => {
    const set = new Set(deduped.map((r) => r._company))
    return Array.from(set).sort((a, b) => a.localeCompare(b))
  }, [deduped])

  useEffect(() => {
    if (!companies.length) return
    if (!selectedCompany || !companies.includes(selectedCompany)) {
      setSelectedCompany(companies[0])
    }
  }, [companies, selectedCompany])

  // Build one slot per framework with its report (or null if missing)
  const slots = useMemo(() => {
    if (!selectedCompany) return FRAMEWORK_ORDER.map((fw) => ({ framework: fw, report: null }))
    return FRAMEWORK_ORDER.map((fw) => ({
      framework: fw,
      report:
        deduped.find((r) => r._company === selectedCompany && r.framework === fw) || null,
    }))
  }, [deduped, selectedCompany])

  const available = useMemo(() => slots.filter((s) => s.report), [slots])

  // Insights across all available frameworks
  const insights = useMemo(() => {
    if (available.length < 2) return null
    const rows = available.map((s) => {
      const sum = s.report.summary || {}
      return {
        framework: s.framework,
        rate: (sum.compliance_rate || 0) * 100,
        conf: (sum.average_confidence || 0) * 100,
        supported: sum.supported || 0,
        total: sum.total_clauses || 0,
      }
    })
    const sortedByRate = [...rows].sort((a, b) => b.rate - a.rate)
    const sortedByConf = [...rows].sort((a, b) => b.conf - a.conf)
    const sortedBySup = [...rows].sort((a, b) => b.supported - a.supported)
    const highest = sortedByRate[0]
    const lowest = sortedByRate[sortedByRate.length - 1]
    const range = highest.rate - lowest.rate
    return {
      rows,
      highest,
      lowest,
      range: Math.round(range * 10) / 10,
      bestConfidence: sortedByConf[0],
      mostSupported: sortedBySup[0],
    }
  }, [available])

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-80px)] flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-forest-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-80px)] py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          {/* Header */}
          <div className="mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-forest-50 border border-forest-200 mb-4">
              <GitCompare className="w-4 h-4 text-forest-600" />
              <span className="text-xs font-semibold uppercase tracking-wide text-forest-800">
                Live comparison mode
              </span>
            </div>
            <h1 className="font-display text-4xl font-bold text-ink-900 mb-3">
              Compare all four frameworks side-by-side
            </h1>
            <p className="text-lg text-ink-600 max-w-2xl">
              See how the same company&rsquo;s ESG report scores under BRSR, GRI, SASB, and TCFD at
              once. Pick an organization and watch the numbers update in real time.
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-xl border border-red-200 bg-red-50 text-red-800 text-sm">
              {error}
            </div>
          )}

          {!companies.length ? (
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-14 text-center">
              <BarChart3 className="w-16 h-16 text-ink-300 mx-auto mb-4" />
              <h2 className="font-display text-xl font-semibold text-ink-900 mb-2">
                No compliance data yet
              </h2>
              <p className="text-ink-600 mb-8 max-w-md mx-auto">
                Run evaluations on at least one company to use comparison mode.
              </p>
              <Link
                to="/documents"
                className="inline-flex items-center gap-2 px-6 py-3 gradient-forest text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all"
              >
                Go to documents
                <ExternalLink className="w-4 h-4" />
              </Link>
            </div>
          ) : (
            <>
              {/* Controls — just the organization selector */}
              <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6 mb-8">
                <div className="max-w-md">
                  <label
                    htmlFor="cmp-company"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Organization
                  </label>
                  <div className="relative">
                    <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400 pointer-events-none z-10" />
                    <select
                      id="cmp-company"
                      value={selectedCompany}
                      onChange={(e) => setSelectedCompany(e.target.value)}
                      className={`${selectFieldClass} pl-12`}
                    >
                      {companies.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400" />
                  </div>
                </div>
              </div>

              {available.length === 0 ? (
                <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 text-center">
                  <AlertTriangle className="w-14 h-14 text-amber-500 mx-auto mb-4" />
                  <h2 className="font-display text-xl font-semibold text-ink-900 mb-2">
                    No reports for this company
                  </h2>
                  <p className="text-ink-600 mb-6">
                    Run at least one compliance evaluation for{' '}
                    <span className="font-semibold text-ink-900">{selectedCompany}</span> to see it
                    here.
                  </p>
                  <Link
                    to="/documents"
                    className="inline-flex items-center gap-2 px-6 py-3 gradient-forest text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all"
                  >
                    Run an evaluation
                    <ExternalLink className="w-4 h-4" />
                  </Link>
                </div>
              ) : (
                <>
                  {/* Four-way comparison grid (2 per row) */}
                  <div className="grid sm:grid-cols-2 gap-5 mb-8">
                    {slots.map((slot) => (
                      <ComparisonCard
                        key={slot.framework}
                        slot={slot}
                        isWinner={
                          insights &&
                          slot.report &&
                          insights.highest.framework === slot.framework
                        }
                        isLaggard={
                          insights &&
                          slot.report &&
                          available.length > 1 &&
                          insights.lowest.framework === slot.framework
                        }
                      />
                    ))}
                  </div>

                  {/* Key insights — only when 2+ frameworks are evaluated */}
                  {insights ? (
                    <InsightsStrip insights={insights} company={selectedCompany} />
                  ) : (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                      <p className="text-sm text-amber-900">
                        <span className="font-semibold">Need at least two frameworks</span> to
                        compute insights. Run another evaluation to unlock the comparison summary.
                      </p>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </motion.div>
      </div>
    </div>
  )
}

// ─── Compact comparison card ───────────────────────────────────────

const ComparisonCard = ({ slot, isWinner, isLaggard }) => {
  const { framework, report } = slot
  const theme = FRAMEWORK_THEME[framework] || FRAMEWORK_THEME.BRSR

  if (!report) {
    return (
      <div className="relative bg-white/60 rounded-2xl border-2 border-dashed border-ink-200 overflow-hidden">
        <div className="h-1.5 w-full bg-ink-100" />
        <div className="p-5">
          <span
            className={`inline-flex items-center px-2.5 py-1 rounded-full border text-xs font-bold tracking-wide ${theme.badge} opacity-60`}
          >
            {framework}
          </span>
          <div className="mt-8 mb-2 flex flex-col items-center text-center text-ink-400">
            <MinusCircle className="w-9 h-9 mb-2" />
            <p className="font-display text-lg font-semibold text-ink-500">Not evaluated</p>
            <p className="text-xs text-ink-400 mt-1 px-2">
              No report yet for this framework.
            </p>
          </div>
          <Link
            to="/documents"
            className="mt-6 w-full inline-flex items-center justify-center gap-1.5 py-2 rounded-xl border border-ink-200 bg-white hover:bg-ink-50 text-ink-600 text-xs font-semibold transition-colors"
          >
            Run evaluation
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    )
  }

  const s = report.summary || {}
  const total = s.total_clauses || 0
  const rate = (s.compliance_rate || 0) * 100
  const avgConf = (s.average_confidence || 0) * 100
  const sup = s.supported || 0
  const par = s.partial || 0
  const nsp = s.not_supported || 0

  const borderClass = isWinner
    ? 'border-forest-400 shadow-forest-200/40'
    : isLaggard
      ? 'border-red-200'
      : 'border-ink-200'

  return (
    <motion.div
      key={report.report_id}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className={`relative bg-white rounded-2xl shadow-lg border-2 ${borderClass} overflow-hidden`}
    >
      {/* Framework accent strip */}
      <div className="h-1.5 w-full" style={{ backgroundColor: theme.accent }} />

      {isWinner && (
        <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-0.5 rounded-full bg-forest-100 border border-forest-200 text-forest-800 text-[10px] font-bold uppercase tracking-wide">
          <Award className="w-3 h-3" />
          Highest
        </div>
      )}

      <div className="p-5">
        {/* Framework badge + date */}
        <div className="flex items-center justify-between mb-3">
          <span
            className={`inline-flex items-center px-2.5 py-1 rounded-full border text-xs font-bold tracking-wide ${theme.badge}`}
          >
            {framework}
          </span>
          <span className="text-[10px] text-ink-400">
            {new Date(report.generated_at).toLocaleDateString()}
          </span>
        </div>

        {/* Compliance rate hero */}
        <div className="mb-4">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-500 mb-1">
            Compliance rate
          </p>
          <div className="flex items-baseline gap-1">
            <span className="font-display text-4xl font-bold text-forest-700 tabular-nums">
              {rate.toFixed(1)}
            </span>
            <span className="text-xl font-semibold text-forest-600">%</span>
          </div>
          <p className="text-[11px] text-ink-500 mt-0.5">
            {sup + par} of {total} clauses
          </p>
        </div>

        {/* Status bars */}
        <div className="space-y-2 mb-4">
          <StatusRow
            icon={<CheckCircle2 className="w-3.5 h-3.5" />}
            label="Supported"
            value={sup}
            total={total}
            color={STATUS_COLORS.supported}
          />
          <StatusRow
            icon={<AlertTriangle className="w-3.5 h-3.5" />}
            label="Partial"
            value={par}
            total={total}
            color={STATUS_COLORS.partial}
          />
          <StatusRow
            icon={<XCircle className="w-3.5 h-3.5" />}
            label="Not supported"
            value={nsp}
            total={total}
            color={STATUS_COLORS.notSupported}
          />
        </div>

        {/* Compact metrics row */}
        <div className="grid grid-cols-2 gap-2 pt-3 border-t border-ink-100 mb-3">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wide text-ink-500">Clauses</p>
            <p className="font-display text-sm font-bold text-ink-900 tabular-nums">{total}</p>
          </div>
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wide text-ink-500">Conf.</p>
            <p className="font-display text-sm font-bold text-ink-900 tabular-nums">
              {avgConf.toFixed(0)}%
            </p>
          </div>
        </div>

        <Link
          to={`/reports/${report.report_id}`}
          className="w-full inline-flex items-center justify-center gap-1.5 py-2 rounded-xl border border-forest-300 text-forest-800 bg-forest-50 hover:bg-forest-100 text-xs font-semibold transition-colors"
        >
          Open full report
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>
    </motion.div>
  )
}

const StatusRow = ({ icon, label, value, total, color }) => {
  const pct = total > 0 ? (value / total) * 100 : 0
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] mb-0.5">
        <div className="flex items-center gap-1 text-ink-700 font-medium truncate">
          <span style={{ color }}>{icon}</span>
          <span className="truncate">{label}</span>
        </div>
        <div className="tabular-nums text-ink-900 font-semibold shrink-0">
          {value}
          <span className="text-ink-400 font-normal"> ({pct.toFixed(0)}%)</span>
        </div>
      </div>
      <div className="h-1.5 bg-clay-100 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
    </div>
  )
}

// ─── Insights strip ────────────────────────────────────────────────

const InsightsStrip = ({ insights, company }) => {
  const { highest, lowest, range, bestConfidence, mostSupported } = insights

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-gradient-to-br from-forest-50 via-white to-clay-50 rounded-2xl shadow-lg border border-forest-200 p-6"
    >
      <div className="flex items-start gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-forest-100 border border-forest-200 flex items-center justify-center shrink-0">
          <Target className="w-5 h-5 text-forest-700" />
        </div>
        <div>
          <h3 className="font-display text-lg font-semibold text-ink-900">Key insights</h3>
          <p className="text-sm text-ink-600">
            <span className="font-semibold text-ink-900">{company}</span> scores best under{' '}
            <span className="font-semibold text-forest-700">{highest.framework}</span> (
            {highest.rate.toFixed(1)}%) and lowest under{' '}
            <span className="font-semibold text-red-700">{lowest.framework}</span> (
            {lowest.rate.toFixed(1)}%), a{' '}
            <span className="font-semibold text-ink-900">{range.toFixed(1)} pp</span> spread across
            standards.
          </p>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <InsightCard
          icon={TrendingUp}
          label="Highest compliance"
          value={highest.framework}
          hint={`${highest.rate.toFixed(1)}%`}
          accent="text-forest-700"
        />
        <InsightCard
          icon={TrendingDown}
          label="Lowest compliance"
          value={lowest.framework}
          hint={`${lowest.rate.toFixed(1)}%`}
          accent="text-red-700"
        />
        <InsightCard
          icon={CheckCircle2}
          label="Most clauses supported"
          value={mostSupported.framework}
          hint={`${mostSupported.supported} supported`}
          accent="text-forest-700"
        />
        <InsightCard
          icon={Award}
          label="Highest AI confidence"
          value={bestConfidence.framework}
          hint={`${bestConfidence.conf.toFixed(0)}% avg`}
          accent="text-forest-700"
        />
      </div>
    </motion.div>
  )
}

const InsightCard = ({ icon: Icon, label, value, hint, accent }) => (
  <div className="rounded-xl bg-white border border-ink-200 p-4 flex gap-3">
    <div className="w-10 h-10 rounded-xl bg-forest-50 border border-forest-100 flex items-center justify-center shrink-0">
      <Icon className={`w-5 h-5 ${accent}`} />
    </div>
    <div className="min-w-0">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-500 mb-0.5">{label}</p>
      <p className="font-display text-lg font-bold text-ink-900 leading-tight truncate">{value}</p>
      <p className="text-xs text-ink-500 mt-0.5 truncate">{hint}</p>
    </div>
  </div>
)

export default Compare
