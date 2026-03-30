import React, { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  Loader2,
  Building2,
  TrendingUp,
  Target,
  Layers,
  ChevronDown,
  ExternalLink,
  BarChart3,
} from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { listComplianceReports } from '../lib/api'

const FRAMEWORK_ORDER = ['BRSR', 'GRI', 'SASB', 'TCFD']

const CHART_COLORS = {
  compliance: '#3d8269',
  supported: '#2a6752',
  partial: '#c4a574',
  notSupported: '#c45c5c',
  grid: '#e0d5c5',
  axis: '#6f5540',
}

/** Derive a display company name from a report filename (strip extension & framework suffix). */
function companyFromReportFilename(filename) {
  if (!filename) return 'Unknown'
  let base = filename.replace(/\.[^.]+$/i, '').trim()
  const suffix = /\s+(SASB|GRI|BRSR|TCFD|ESG|BRSR\s+Report)$/i
  while (suffix.test(base)) {
    base = base.replace(suffix, '').trim()
  }
  return base || 'Unknown'
}

function pickLatestPerCompanyFramework(reports) {
  const map = new Map()
  for (const r of reports) {
    const company = companyFromReportFilename(r.document_filename)
    const fw = r.framework
    const key = `${company}||${fw}`
    const prev = map.get(key)
    if (!prev || new Date(r.generated_at) > new Date(prev.generated_at)) {
      map.set(key, { ...r, _company: company })
    }
  }
  return Array.from(map.values())
}

function buildCompanySnapshot(rows, company) {
  const mine = rows.filter((r) => r._company === company)
  const byFw = {}
  for (const r of mine) {
    byFw[r.framework] = r
  }
  const chart = FRAMEWORK_ORDER.map((fw) => {
    const rep = byFw[fw]
    if (!rep) {
      return {
        framework: fw,
        compliance_pct: null,
        supported: 0,
        partial: 0,
        not_supported: 0,
        total: 0,
        avg_confidence: null,
        report_id: null,
      }
    }
    const s = rep.summary || {}
    const total = s.total_clauses || 0
    const rate = typeof s.compliance_rate === 'number' ? s.compliance_rate * 100 : 0
    return {
      framework: fw,
      compliance_pct: Math.round(rate * 10) / 10,
      supported: s.supported ?? 0,
      partial: s.partial ?? 0,
      not_supported: s.not_supported ?? 0,
      total,
      avg_confidence:
        typeof s.average_confidence === 'number' ? Math.round(s.average_confidence * 1000) / 10 : null,
      report_id: rep.report_id,
    }
  })

  const covered = chart.filter((c) => c.total > 0)
  const avgCompliance =
    covered.length > 0
      ? covered.reduce((a, c) => a + (c.compliance_pct || 0), 0) / covered.length
      : 0
  const avgConf =
    covered.filter((c) => c.avg_confidence != null).length > 0
      ? covered
          .filter((c) => c.avg_confidence != null)
          .reduce((a, c) => a + c.avg_confidence, 0) /
        covered.filter((c) => c.avg_confidence != null).length
      : null

  const statusTotals = covered.reduce(
    (acc, c) => {
      acc.supported += c.supported
      acc.partial += c.partial
      acc.not_supported += c.not_supported
      return acc
    },
    { supported: 0, partial: 0, not_supported: 0 }
  )

  return {
    chart,
    frameworksWithData: covered.length,
    avgCompliance: Math.round(avgCompliance * 10) / 10,
    avgConfidence: avgConf != null ? Math.round(avgConf * 10) / 10 : null,
    statusTotals,
    totalClauses: covered.reduce((a, c) => a + c.total, 0),
  }
}

const Dashboard = () => {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCompany, setSelectedCompany] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await listComplianceReports()
        if (!cancelled) setReports(data.reports || [])
      } catch (e) {
        if (!cancelled) setError(e?.message || 'Failed to load reports')
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
    if (companies.length && !selectedCompany) {
      setSelectedCompany(companies[0])
    }
  }, [companies, selectedCompany])

  const snapshot = useMemo(() => {
    if (!selectedCompany) return null
    return buildCompanySnapshot(deduped, selectedCompany)
  }, [deduped, selectedCompany])

  const pieData = snapshot
    ? [
        { name: 'Supported', value: snapshot.statusTotals.supported, key: 'supported' },
        { name: 'Partial', value: snapshot.statusTotals.partial, key: 'partial' },
        { name: 'Not supported', value: snapshot.statusTotals.not_supported, key: 'not' },
      ].filter((d) => d.value > 0)
    : []

  const radarData = snapshot
    ? snapshot.chart
        .filter((c) => c.total > 0)
        .map((c) => ({
          subject: c.framework,
          score: c.compliance_pct ?? 0,
          full: 100,
        }))
    : []

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
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 mb-10">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-forest-50 border border-forest-200 mb-4">
                <LayoutDashboard className="w-4 h-4 text-forest-600" />
                <span className="text-xs font-semibold uppercase tracking-wide text-forest-800">
                  Compliance overview
                </span>
              </div>
              <h1 className="font-display text-4xl font-bold text-ink-900 mb-3">
                Organization dashboard
              </h1>
              <p className="text-lg text-ink-600 max-w-2xl">
                Compare ESG compliance across frameworks for each organization. Data comes from your
                saved compliance reports (latest run per company and standard).
              </p>
            </div>

            {companies.length > 0 && (
              <div className="w-full lg:w-80">
                <label
                  htmlFor="dashboard-company"
                  className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                >
                  Organization
                </label>
                <div className="relative">
                  <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400 pointer-events-none" />
                  <select
                    id="dashboard-company"
                    value={selectedCompany}
                    onChange={(e) => setSelectedCompany(e.target.value)}
                    className="w-full appearance-none pl-12 pr-11 py-3.5 bg-white border border-ink-200 rounded-xl text-sm font-medium text-ink-900 shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 transition-colors cursor-pointer"
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
            )}
          </div>

          {error && (
            <div className="mb-8 p-4 rounded-xl border border-red-200 bg-red-50 text-red-800 text-sm">
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
                Run evaluations from Documents, then open this dashboard to see cross-standard
                compliance visualizations.
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
            snapshot && (
              <>
                {/* KPI cards */}
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                  {[
                    {
                      label: 'Avg. compliance rate',
                      value: `${snapshot.avgCompliance}%`,
                      sub: 'Across frameworks with data',
                      icon: TrendingUp,
                      accent: 'text-forest-700',
                    },
                    {
                      label: 'Frameworks covered',
                      value: `${snapshot.frameworksWithData} / 4`,
                      sub: 'BRSR · GRI · SASB · TCFD',
                      icon: Layers,
                      accent: 'text-forest-600',
                    },
                    {
                      label: 'Clauses evaluated',
                      value: snapshot.totalClauses,
                      sub: 'Total across selected org',
                      icon: Target,
                      accent: 'text-ink-800',
                    },
                    {
                      label: 'Avg. confidence',
                      value:
                        snapshot.avgConfidence != null ? `${snapshot.avgConfidence}%` : '—',
                      sub: 'Model confidence (when available)',
                      icon: BarChart3,
                      accent: 'text-ink-700',
                    },
                  ].map((k, i) => (
                    <motion.div
                      key={k.label}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="bg-white rounded-2xl border border-ink-200 shadow-md p-5 flex gap-4"
                    >
                      <div className="w-11 h-11 rounded-xl bg-forest-50 border border-forest-100 flex items-center justify-center shrink-0">
                        <k.icon className={`w-5 h-5 ${k.accent}`} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-medium uppercase tracking-wide text-ink-500 mb-1">
                          {k.label}
                        </p>
                        <p className="font-display text-2xl font-bold text-ink-900 tabular-nums">
                          {k.value}
                        </p>
                        <p className="text-xs text-ink-500 mt-0.5 leading-snug">{k.sub}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>

                <div className="grid lg:grid-cols-2 gap-6 mb-8">
                  {/* Compliance by framework */}
                  <div className="bg-white rounded-2xl border border-ink-200 shadow-lg p-6">
                    <h3 className="font-display text-lg font-semibold text-ink-900 mb-1">
                      Compliance rate by standard
                    </h3>
                    <p className="text-sm text-ink-500 mb-6">
                      Share of clauses marked supported or partial (same as report summary).
                    </p>
                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={snapshot.chart.map((c) => ({
                            name: c.framework,
                            Compliance: c.total > 0 ? c.compliance_pct ?? 0 : 0,
                            hasData: c.total > 0,
                          }))}
                          margin={{ top: 8, right: 8, left: -8, bottom: 0 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                          <XAxis
                            dataKey="name"
                            tick={{ fill: '#5f646f', fontSize: 12 }}
                            axisLine={{ stroke: CHART_COLORS.grid }}
                          />
                          <YAxis
                            domain={[0, 100]}
                            tickFormatter={(v) => `${v}%`}
                            tick={{ fill: '#5f646f', fontSize: 11 }}
                            axisLine={{ stroke: CHART_COLORS.grid }}
                          />
                          <Tooltip
                            content={({ active, payload, label }) => {
                              if (!active || !payload?.length) return null
                              const row = snapshot.chart.find((x) => x.framework === label)
                              if (row && !row.total) {
                                return (
                                  <div className="rounded-lg border border-ink-200 bg-white px-3 py-2 text-xs shadow-lg">
                                    <span className="text-ink-600">No report for {label}</span>
                                  </div>
                                )
                              }
                              return (
                                <div className="rounded-lg border border-ink-200 bg-white px-3 py-2 text-xs shadow-lg">
                                  <p className="font-semibold text-ink-900">{label}</p>
                                  <p className="text-forest-700">
                                    Compliance: {payload[0]?.value}%
                                  </p>
                                </div>
                              )
                            }}
                          />
                          <Bar dataKey="Compliance" radius={[8, 8, 0, 0]} maxBarSize={56}>
                            {snapshot.chart.map((c) => (
                              <Cell
                                key={c.framework}
                                fill={c.total > 0 ? CHART_COLORS.compliance : '#e1e3e5'}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Radar — coverage shape */}
                  <div className="bg-white rounded-2xl border border-ink-200 shadow-lg p-6">
                    <h3 className="font-display text-lg font-semibold text-ink-900 mb-1">
                      Balance across standards
                    </h3>
                    <p className="text-sm text-ink-500 mb-4">
                      Normalized compliance score by framework (radar).
                    </p>
                    <div className="h-72 w-full">
                      {radarData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
                            <PolarGrid stroke={CHART_COLORS.grid} />
                            <PolarAngleAxis
                              dataKey="subject"
                              tick={{ fill: '#5f646f', fontSize: 11 }}
                            />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                            <Radar
                              name="Compliance %"
                              dataKey="score"
                              stroke={CHART_COLORS.compliance}
                              fill={CHART_COLORS.compliance}
                              fillOpacity={0.35}
                              strokeWidth={2}
                            />
                            <Tooltip
                              formatter={(value) => [`${value}%`, 'Compliance']}
                              contentStyle={{
                                borderRadius: '0.5rem',
                                border: '1px solid #e0d5c5',
                                fontSize: '12px',
                              }}
                            />
                          </RadarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-ink-500 text-sm">
                          No framework-level data for this organization.
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="grid lg:grid-cols-3 gap-6 mb-8">
                  {/* Stacked status by framework */}
                  <div className="lg:col-span-2 bg-white rounded-2xl border border-ink-200 shadow-lg p-6">
                    <h3 className="font-display text-lg font-semibold text-ink-900 mb-1">
                      Clause outcomes by standard
                    </h3>
                    <p className="text-sm text-ink-500 mb-6">
                      Stacked counts: supported, partial, and not supported.
                    </p>
                    <div className="h-80 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={snapshot.chart.filter((c) => c.total > 0)}
                          margin={{ top: 8, right: 8, left: -8, bottom: 0 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                          <XAxis dataKey="framework" tick={{ fill: '#5f646f', fontSize: 12 }} />
                          <YAxis tick={{ fill: '#5f646f', fontSize: 11 }} allowDecimals={false} />
                          <Tooltip
                            contentStyle={{
                              borderRadius: '0.5rem',
                              border: '1px solid #e0d5c5',
                              fontSize: '12px',
                            }}
                          />
                          <Legend
                            wrapperStyle={{ fontSize: '12px', paddingTop: 8 }}
                            formatter={(value) => <span className="text-ink-700">{value}</span>}
                          />
                          <Bar dataKey="supported" stackId="a" fill={CHART_COLORS.supported} name="Supported" radius={[0, 0, 0, 0]} />
                          <Bar dataKey="partial" stackId="a" fill={CHART_COLORS.partial} name="Partial" />
                          <Bar
                            dataKey="not_supported"
                            stackId="a"
                            fill={CHART_COLORS.notSupported}
                            name="Not supported"
                            radius={[6, 6, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Donut overall */}
                  <div className="bg-white rounded-2xl border border-ink-200 shadow-lg p-6 flex flex-col">
                    <h3 className="font-display text-lg font-semibold text-ink-900 mb-1">
                      Overall mix
                    </h3>
                    <p className="text-sm text-ink-500 mb-4">All frameworks combined for this org.</p>
                    <div className="flex-1 min-h-[220px] relative">
                      {pieData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={pieData}
                              cx="50%"
                              cy="50%"
                              innerRadius={52}
                              outerRadius={80}
                              paddingAngle={2}
                              dataKey="value"
                              nameKey="name"
                            >
                              {pieData.map((entry) => (
                                <Cell
                                  key={entry.key}
                                  fill={
                                    entry.key === 'supported'
                                      ? CHART_COLORS.supported
                                      : entry.key === 'partial'
                                        ? CHART_COLORS.partial
                                        : CHART_COLORS.notSupported
                                  }
                                />
                              ))}
                            </Pie>
                            <Tooltip
                              formatter={(value, name) => [value, name]}
                              contentStyle={{
                                borderRadius: '0.5rem',
                                border: '1px solid #e0d5c5',
                                fontSize: '12px',
                              }}
                            />
                            <Legend
                              wrapperStyle={{ fontSize: '12px' }}
                              verticalAlign="bottom"
                              height={36}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="absolute inset-0 flex items-center justify-center text-ink-500 text-sm">
                          No clause data
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Report links */}
                <div className="bg-clay-50/80 rounded-2xl border border-ink-200 p-6">
                  <h3 className="font-display text-lg font-semibold text-ink-900 mb-4">
                    Open reports
                  </h3>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {snapshot.chart.map((c) => (
                      <div
                        key={c.framework}
                        className="flex items-center justify-between gap-2 rounded-xl border border-ink-200 bg-white px-4 py-3"
                      >
                        <span className="text-sm font-medium text-ink-800">{c.framework}</span>
                        {c.report_id ? (
                          <Link
                            to={`/reports/${c.report_id}`}
                            className="text-xs font-semibold text-forest-700 hover:text-forest-900 inline-flex items-center gap-1"
                          >
                            View
                            <ExternalLink className="w-3.5 h-3.5" />
                          </Link>
                        ) : (
                          <span className="text-xs text-ink-400">No report</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )
          )}
        </motion.div>
      </div>
    </div>
  )
}

export default Dashboard
