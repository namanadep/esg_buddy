/* eslint-disable react/prop-types */
import React, { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Building2,
  ChevronDown,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  Trophy,
  Equal,
  ArrowRightLeft,
  Layers as LayersIcon,
  Users,
  MinusCircle,
} from 'lucide-react'
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { getComplianceReport } from '../lib/api'

const FRAMEWORKS = ['BRSR', 'GRI', 'SASB', 'TCFD']

const COMPANY_A_COLOR = '#2a6752' // forest-600
const COMPANY_B_COLOR = '#c45c5c' // muted red

const selectFieldClass =
  'w-full appearance-none pr-11 py-3 bg-white border border-ink-200 rounded-xl text-sm text-ink-900 ' +
  'shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 ' +
  'transition-colors cursor-pointer font-medium'

function sectionFromEvaluation(ev) {
  const fromClause = ev?.clause?.section
  if (fromClause && typeof fromClause === 'string' && fromClause.trim()) {
    return fromClause.trim()
  }
  // Fallback: derive from clause_id prefix (e.g. "BRSR_governance_01" -> "governance")
  const parts = (ev?.clause_id || '').split('_')
  if (parts.length >= 2) {
    return parts[1].charAt(0).toUpperCase() + parts[1].slice(1)
  }
  return 'General'
}

function buildSectionStats(evaluations) {
  const sections = new Map()
  for (const ev of evaluations || []) {
    const section = sectionFromEvaluation(ev)
    if (!sections.has(section)) {
      sections.set(section, { total: 0, supported: 0, partial: 0, notSupported: 0 })
    }
    const bucket = sections.get(section)
    bucket.total += 1
    if (ev.final_status === 'supported') bucket.supported += 1
    else if (ev.final_status === 'partial') bucket.partial += 1
    else if (ev.final_status === 'not_supported') bucket.notSupported += 1
  }
  return sections
}

function statusToScore(status) {
  if (status === 'supported') return 1
  if (status === 'partial') return 0.5
  return 0
}

const CompaniesCompare = ({ deduped, companies }) => {
  const [framework, setFramework] = useState('BRSR')
  const [companyA, setCompanyA] = useState('')
  const [companyB, setCompanyB] = useState('')

  const [reportA, setReportA] = useState(null)
  const [reportB, setReportB] = useState(null)
  const [loadingReports, setLoadingReports] = useState(false)
  const [fetchError, setFetchError] = useState(null)

  // Auto-pick two distinct companies on first mount
  useEffect(() => {
    if (!companies.length) return
    if (!companyA) setCompanyA(companies[0])
    if (!companyB && companies.length > 1) setCompanyB(companies[1])
  }, [companies, companyA, companyB])

  // Pick the report objects (from list endpoint) for the two selected companies on the chosen framework
  const slotA = useMemo(
    () => deduped.find((r) => r._company === companyA && r.framework === framework) || null,
    [deduped, companyA, framework],
  )
  const slotB = useMemo(
    () => deduped.find((r) => r._company === companyB && r.framework === framework) || null,
    [deduped, companyB, framework],
  )

  // Fetch full reports (with evaluations) when both slots are present
  useEffect(() => {
    let cancelled = false
    if (!slotA || !slotB) {
      setReportA(null)
      setReportB(null)
      setFetchError(null)
      return () => {
        cancelled = true
      }
    }
    ;(async () => {
      setLoadingReports(true)
      setFetchError(null)
      try {
        const [a, b] = await Promise.all([
          getComplianceReport(slotA.report_id),
          getComplianceReport(slotB.report_id),
        ])
        if (cancelled) return
        setReportA(a)
        setReportB(b)
      } catch (err) {
        if (cancelled) return
        setFetchError(err?.response?.data?.detail || err?.message || 'Failed to load reports')
        setReportA(null)
        setReportB(null)
      } finally {
        if (!cancelled) setLoadingReports(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [slotA, slotB])

  // ─── Build the comparison data ────────────────────────────────────────
  const radarData = useMemo(() => {
    if (!reportA || !reportB) return []
    const statsA = buildSectionStats(reportA.evaluations)
    const statsB = buildSectionStats(reportB.evaluations)
    const allSections = new Set([...statsA.keys(), ...statsB.keys()])
    return Array.from(allSections)
      .sort((a, b) => a.localeCompare(b))
      .map((section) => {
        const a = statsA.get(section)
        const b = statsB.get(section)
        const rateA = a ? ((a.supported + a.partial) / a.total) * 100 : 0
        const rateB = b ? ((b.supported + b.partial) / b.total) * 100 : 0
        return {
          section,
          [companyA]: Math.round(rateA),
          [companyB]: Math.round(rateB),
        }
      })
  }, [reportA, reportB, companyA, companyB])

  const diffRows = useMemo(() => {
    if (!reportA || !reportB) return []
    const map = new Map()
    for (const ev of reportA.evaluations || []) {
      map.set(ev.clause_id, {
        clause_id: ev.clause_id,
        title: ev.clause?.title || ev.clause_id,
        section: sectionFromEvaluation(ev),
        statusA: ev.final_status,
        statusB: null,
      })
    }
    for (const ev of reportB.evaluations || []) {
      const existing = map.get(ev.clause_id)
      if (existing) {
        existing.statusB = ev.final_status
      } else {
        map.set(ev.clause_id, {
          clause_id: ev.clause_id,
          title: ev.clause?.title || ev.clause_id,
          section: sectionFromEvaluation(ev),
          statusA: null,
          statusB: ev.final_status,
        })
      }
    }
    const rows = Array.from(map.values()).map((row) => {
      const isMissingEither = row.statusA === null || row.statusB === null
      const agreement = !isMissingEither && row.statusA === row.statusB
      const scoreA = row.statusA ? statusToScore(row.statusA) : null
      const scoreB = row.statusB ? statusToScore(row.statusB) : null
      const delta =
        scoreA !== null && scoreB !== null ? scoreA - scoreB : 0
      return {
        ...row,
        isMissingEither,
        agreement,
        delta,
      }
    })
    // Disagreements first, then by section
    rows.sort((x, y) => {
      if (x.agreement !== y.agreement) return x.agreement ? 1 : -1
      if (x.section !== y.section) return x.section.localeCompare(y.section)
      return x.clause_id.localeCompare(y.clause_id)
    })
    return rows
  }, [reportA, reportB])

  const summaryStats = useMemo(() => {
    if (!reportA || !reportB) return null
    const sumA = reportA.summary || {}
    const sumB = reportB.summary || {}
    const rateA = (sumA.compliance_rate || 0) * 100
    const rateB = (sumB.compliance_rate || 0) * 100
    let agreements = 0
    let disagreements = 0
    let onlyA = 0
    let onlyB = 0
    for (const row of diffRows) {
      if (row.statusA === null) onlyB += 1
      else if (row.statusB === null) onlyA += 1
      else if (row.agreement) agreements += 1
      else disagreements += 1
    }
    return {
      rateA,
      rateB,
      supportedA: sumA.supported || 0,
      supportedB: sumB.supported || 0,
      partialA: sumA.partial || 0,
      partialB: sumB.partial || 0,
      totalA: sumA.total_clauses || 0,
      totalB: sumB.total_clauses || 0,
      agreements,
      disagreements,
      onlyA,
      onlyB,
      winner:
        Math.abs(rateA - rateB) < 0.05
          ? 'tie'
          : rateA > rateB
            ? 'A'
            : 'B',
      gap: Math.abs(rateA - rateB),
    }
  }, [reportA, reportB, diffRows])

  const [diffFilter, setDiffFilter] = useState('disagreements') // 'all' | 'disagreements' | 'agreements'

  const filteredRows = useMemo(() => {
    if (diffFilter === 'all') return diffRows
    if (diffFilter === 'disagreements')
      return diffRows.filter((r) => !r.agreement || r.isMissingEither)
    return diffRows.filter((r) => r.agreement && !r.isMissingEither)
  }, [diffRows, diffFilter])

  if (!companies.length) {
    return null
  }

  const sameCompany = companyA && companyB && companyA === companyB

  return (
    <div className="space-y-6">
      {/* Selectors */}
      <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6">
        <div className="grid md:grid-cols-3 gap-4">
          <SelectorField
            id="cmp-framework"
            label="Framework"
            value={framework}
            onChange={setFramework}
            options={FRAMEWORKS.map((f) => ({ value: f, label: f }))}
            icon={<LayersIcon className="w-5 h-5 text-ink-400" />}
          />
          <SelectorField
            id="cmp-cA"
            label="Company A"
            value={companyA}
            onChange={setCompanyA}
            options={companies.map((c) => ({ value: c, label: c }))}
            icon={<Building2 className="w-5 h-5" style={{ color: COMPANY_A_COLOR }} />}
          />
          <SelectorField
            id="cmp-cB"
            label="Company B"
            value={companyB}
            onChange={setCompanyB}
            options={companies.map((c) => ({ value: c, label: c }))}
            icon={<Building2 className="w-5 h-5" style={{ color: COMPANY_B_COLOR }} />}
          />
        </div>
      </div>

      {/* Headline */}
      {companyA && companyB && !sameCompany && (
        <motion.div
          key={`${companyA}-${companyB}-${framework}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="bg-gradient-to-br from-forest-50 via-white to-clay-50 rounded-2xl border border-forest-100 p-6"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-forest-100 border border-forest-200 flex items-center justify-center shrink-0">
              <ArrowRightLeft className="w-5 h-5 text-forest-700" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-forest-700 mb-1">
                Head-to-head
              </p>
              <h2 className="font-display text-2xl font-bold text-ink-900">
                How does <span className="text-forest-700">{companyA}</span> compare to{' '}
                <span style={{ color: COMPANY_B_COLOR }}>{companyB}</span> on{' '}
                <span className="text-ink-900">{framework}</span>?
              </h2>
            </div>
          </div>
        </motion.div>
      )}

      {/* Empty / error states */}
      {sameCompany && (
        <EmptyHint
          title="Pick two different companies"
          message="Select two distinct organizations to see a side-by-side comparison."
        />
      )}

      {!sameCompany && (!slotA || !slotB) && companyA && companyB && (
        <EmptyHint
          title={`Missing ${framework} report${!slotA && !slotB ? 's' : ''}`}
          message={
            !slotA && !slotB
              ? `Neither ${companyA} nor ${companyB} has been evaluated against ${framework} yet.`
              : !slotA
                ? `${companyA} hasn't been evaluated against ${framework} yet.`
                : `${companyB} hasn't been evaluated against ${framework} yet.`
          }
        />
      )}

      {fetchError && (
        <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-800 text-sm">
          {fetchError}
        </div>
      )}

      {loadingReports && (
        <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 flex flex-col items-center justify-center">
          <Loader2 className="w-8 h-8 text-forest-600 animate-spin mb-3" />
          <p className="text-sm text-ink-600">Loading both reports&hellip;</p>
        </div>
      )}

      <AnimatePresence mode="wait">
        {!loadingReports && reportA && reportB && summaryStats && (
          <motion.div
            key={`${companyA}-${companyB}-${framework}-content`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4 }}
            className="space-y-6"
          >
            {/* KPI strip */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Compliance rate"
                a={summaryStats.rateA}
                b={summaryStats.rateB}
                companyA={companyA}
                companyB={companyB}
                format={(v) => `${v.toFixed(1)}%`}
                higherIsBetter
              />
              <KpiCard
                label="Clauses fully supported"
                a={summaryStats.supportedA}
                b={summaryStats.supportedB}
                companyA={companyA}
                companyB={companyB}
                format={(v) => `${v}`}
                higherIsBetter
              />
              <KpiCard
                label="Partial coverage"
                a={summaryStats.partialA}
                b={summaryStats.partialB}
                companyA={companyA}
                companyB={companyB}
                format={(v) => `${v}`}
                neutral
              />
              <DiffSummaryCard
                agreements={summaryStats.agreements}
                disagreements={summaryStats.disagreements}
                onlyA={summaryStats.onlyA}
                onlyB={summaryStats.onlyB}
                winner={summaryStats.winner}
                gap={summaryStats.gap}
                companyA={companyA}
                companyB={companyB}
              />
            </div>

            {/* Per-section compliance chart — radar for 3–10 sections, bar chart otherwise */}
            <SectionComplianceChart
              radarData={radarData}
              companyA={companyA}
              companyB={companyB}
            />

            {/* Status distribution side-by-side */}
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-forest-700 mb-1">
                Status distribution
              </p>
              <h3 className="font-display text-xl font-bold text-ink-900 mb-5">
                Overall clause breakdown
              </h3>
              <div className="grid md:grid-cols-2 gap-6">
                <DistributionColumn
                  company={companyA}
                  color={COMPANY_A_COLOR}
                  summary={reportA.summary}
                />
                <DistributionColumn
                  company={companyB}
                  color={COMPANY_B_COLOR}
                  summary={reportB.summary}
                />
              </div>
            </div>

            {/* Clause-by-clause diff table */}
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 overflow-hidden">
              <div className="p-6 pb-4 border-b border-ink-100 flex items-start justify-between flex-wrap gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-forest-700 mb-1">
                    Clause-by-clause diff
                  </p>
                  <h3 className="font-display text-xl font-bold text-ink-900">
                    Where they agree and where they don&rsquo;t
                  </h3>
                  <p className="text-sm text-ink-600 mt-1">
                    {summaryStats.disagreements} disagreement
                    {summaryStats.disagreements === 1 ? '' : 's'},{' '}
                    {summaryStats.agreements} agreement
                    {summaryStats.agreements === 1 ? '' : 's'} across {diffRows.length} clauses.
                  </p>
                </div>
                <FilterPills value={diffFilter} onChange={setDiffFilter} />
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-clay-50 text-left">
                    <tr className="text-[11px] uppercase tracking-wide text-ink-500">
                      <th className="px-6 py-3 font-semibold">Clause</th>
                      <th className="px-4 py-3 font-semibold">Section</th>
                      <th className="px-4 py-3 font-semibold text-center">
                        <span className="inline-flex items-center gap-1.5">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: COMPANY_A_COLOR }}
                          />
                          {companyA}
                        </span>
                      </th>
                      <th className="px-4 py-3 font-semibold text-center">
                        <span className="inline-flex items-center gap-1.5">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: COMPANY_B_COLOR }}
                          />
                          {companyB}
                        </span>
                      </th>
                      <th className="px-4 py-3 font-semibold text-center">Verdict</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.map((row) => (
                      <tr
                        key={row.clause_id}
                        className={`border-t border-ink-100 ${
                          row.agreement && !row.isMissingEither
                            ? 'bg-white'
                            : 'bg-amber-50/40'
                        }`}
                      >
                        <td className="px-6 py-3.5 align-top max-w-md">
                          <p className="font-medium text-ink-900 leading-snug">{row.title}</p>
                          <p className="text-[11px] font-mono text-ink-400 mt-0.5">
                            {row.clause_id}
                          </p>
                        </td>
                        <td className="px-4 py-3.5 align-top">
                          <span className="inline-block px-2 py-0.5 rounded-md bg-clay-100 border border-clay-200 text-[11px] font-medium text-ink-700">
                            {row.section}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 align-top text-center">
                          <StatusPill status={row.statusA} />
                        </td>
                        <td className="px-4 py-3.5 align-top text-center">
                          <StatusPill status={row.statusB} />
                        </td>
                        <td className="px-4 py-3.5 align-top text-center">
                          <VerdictBadge row={row} companyA={companyA} companyB={companyB} />
                        </td>
                      </tr>
                    ))}
                    {filteredRows.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-6 py-10 text-center text-ink-500 text-sm">
                          {diffFilter === 'agreements'
                            ? 'No clauses with full agreement.'
                            : diffFilter === 'disagreements'
                              ? 'No disagreements. Both companies score identically across the board.'
                              : 'No clauses to display.'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div className="p-5 bg-clay-50/50 border-t border-ink-100 flex flex-wrap gap-3 justify-end">
                <Link
                  to={`/reports/${reportA.report_id}`}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-forest-300 text-forest-800 bg-white hover:bg-forest-50 text-xs font-semibold transition-colors"
                >
                  Open {companyA}&rsquo;s full report
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
                <Link
                  to={`/reports/${reportB.report_id}`}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border text-xs font-semibold transition-colors"
                  style={{
                    borderColor: '#e8c5c5',
                    color: '#8a3a3a',
                    backgroundColor: '#ffffff',
                  }}
                >
                  Open {companyB}&rsquo;s full report
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────

const SectionComplianceChart = ({ radarData, companyA, companyB }) => {
  // Radar looks good for 3–10 axes. Outside that range it either degenerates
  // (< 3 axes become a line) or turns into unreadable mush (too many axes).
  // Fall back to a grouped horizontal bar chart in those cases.
  const useRadar = radarData.length >= 3 && radarData.length <= 10

  const header = (
    <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-forest-700 mb-1">
          Per-section compliance
        </p>
        <h3 className="font-display text-xl font-bold text-ink-900">
          Where each company is strongest
        </h3>
        <p className="text-sm text-ink-600 mt-1">
          {useRadar
            ? 'Each axis shows the % of clauses that are at least partially supported under that section.'
            : radarData.length < 3
              ? 'Only a couple of sections exist for this framework, so the comparison is shown as grouped bars.'
              : 'Many sections in this framework — shown as a grouped bar chart for readability.'}
        </p>
      </div>
      <LegendPill colorA={COMPANY_A_COLOR} colorB={COMPANY_B_COLOR} a={companyA} b={companyB} />
    </div>
  )

  if (radarData.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6">
        {header}
        <p className="text-sm text-ink-500 py-8 text-center">No section data available.</p>
      </div>
    )
  }

  if (useRadar) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6">
        {header}
        <div className="w-full h-[380px]">
          <ResponsiveContainer>
            <RadarChart data={radarData} outerRadius="78%">
              <PolarGrid stroke="#e1e3e5" />
              <PolarAngleAxis
                dataKey="section"
                tick={{ fill: '#5f646f', fontSize: 11, fontWeight: 500 }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fill: '#9fa4ac', fontSize: 10 }}
                tickFormatter={(v) => `${v}%`}
              />
              <Radar
                name={companyA}
                dataKey={companyA}
                stroke={COMPANY_A_COLOR}
                fill={COMPANY_A_COLOR}
                fillOpacity={0.32}
                strokeWidth={2}
              />
              <Radar
                name={companyB}
                dataKey={companyB}
                stroke={COMPANY_B_COLOR}
                fill={COMPANY_B_COLOR}
                fillOpacity={0.28}
                strokeWidth={2}
              />
              <Tooltip
                contentStyle={{
                  background: '#ffffff',
                  border: '1px solid #e1e3e5',
                  borderRadius: 12,
                  fontSize: 12,
                }}
                formatter={(value) => `${value}%`}
              />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  // Grouped horizontal bar chart fallback. Height scales with number of sections.
  const rowHeight = 52
  const chartHeight = Math.max(180, radarData.length * rowHeight + 40)

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6">
      {header}
      <div className="w-full" style={{ height: chartHeight }}>
        <ResponsiveContainer>
          <BarChart
            data={radarData}
            layout="vertical"
            margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
            barCategoryGap={12}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e1e3e5" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fill: '#9fa4ac', fontSize: 11 }}
              stroke="#e1e3e5"
            />
            <YAxis
              type="category"
              dataKey="section"
              width={120}
              tick={{ fill: '#3d4047', fontSize: 12, fontWeight: 500 }}
              stroke="#e1e3e5"
            />
            <Tooltip
              cursor={{ fill: 'rgba(61,130,105,0.05)' }}
              contentStyle={{
                background: '#ffffff',
                border: '1px solid #e1e3e5',
                borderRadius: 12,
                fontSize: 12,
              }}
              formatter={(value) => `${value}%`}
            />
            <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" />
            <Bar
              dataKey={companyA}
              fill={COMPANY_A_COLOR}
              radius={[0, 6, 6, 0]}
              maxBarSize={18}
            />
            <Bar
              dataKey={companyB}
              fill={COMPANY_B_COLOR}
              radius={[0, 6, 6, 0]}
              maxBarSize={18}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

const SelectorField = ({ id, label, value, onChange, options, icon }) => (
  <div>
    <label
      htmlFor={id}
      className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
    >
      {label}
    </label>
    <div className="relative">
      <span className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none z-10">
        {icon}
      </span>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`${selectFieldClass} pl-12`}
      >
        {!value && <option value="">Select&hellip;</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400" />
    </div>
  </div>
)

const EmptyHint = ({ title, message }) => (
  <div className="bg-white rounded-2xl shadow-md border border-ink-200 p-10 text-center">
    <div className="w-14 h-14 rounded-full bg-clay-100 border border-clay-200 mx-auto mb-4 flex items-center justify-center">
      <Users className="w-7 h-7 text-clay-600" />
    </div>
    <h3 className="font-display text-lg font-semibold text-ink-900 mb-1">{title}</h3>
    <p className="text-sm text-ink-600 max-w-md mx-auto">{message}</p>
  </div>
)

const KpiCard = ({ label, a, b, companyA, companyB, format, higherIsBetter, neutral }) => {
  let winner = 'tie'
  if (!neutral) {
    if (Math.abs(a - b) > 0.001) {
      winner = higherIsBetter ? (a > b ? 'A' : 'B') : a < b ? 'A' : 'B'
    }
  }
  return (
    <div className="bg-white rounded-2xl shadow-md border border-ink-200 p-5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-500 mb-3">
        {label}
      </p>
      <div className="space-y-2">
        <KpiRow
          company={companyA}
          value={format(a)}
          color={COMPANY_A_COLOR}
          highlighted={winner === 'A'}
        />
        <KpiRow
          company={companyB}
          value={format(b)}
          color={COMPANY_B_COLOR}
          highlighted={winner === 'B'}
        />
      </div>
    </div>
  )
}

const KpiRow = ({ company, value, color, highlighted }) => (
  <div
    className={`flex items-center justify-between rounded-lg px-2 py-1 ${
      highlighted ? 'bg-forest-50 ring-1 ring-forest-200' : ''
    }`}
  >
    <div className="flex items-center gap-2 min-w-0">
      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
      <span className="text-xs text-ink-700 truncate">{company}</span>
    </div>
    <div className="flex items-center gap-1">
      <span className="font-display text-base font-bold tabular-nums text-ink-900">{value}</span>
      {highlighted && <Trophy className="w-3.5 h-3.5 text-forest-700" />}
    </div>
  </div>
)

const DiffSummaryCard = ({
  agreements,
  disagreements,
  onlyA,
  onlyB,
  winner,
  gap,
  companyA,
  companyB,
}) => (
  <div className="bg-gradient-to-br from-forest-600 to-forest-800 text-white rounded-2xl shadow-md p-5">
    <p className="text-[10px] font-semibold uppercase tracking-wide text-forest-100 mb-3">
      Head-to-head
    </p>
    {winner === 'tie' ? (
      <div className="flex items-center gap-2 mb-2">
        <Equal className="w-5 h-5" />
        <p className="font-display text-lg font-bold">Dead heat</p>
      </div>
    ) : (
      <div className="mb-2">
        <p className="font-display text-lg font-bold leading-tight">
          {winner === 'A' ? companyA : companyB}
        </p>
        <p className="text-xs text-forest-100">leads by {gap.toFixed(1)} pp</p>
      </div>
    )}
    <div className="border-t border-forest-500/40 pt-3 mt-3 space-y-1.5 text-xs">
      <div className="flex justify-between">
        <span className="text-forest-100">Agreements</span>
        <span className="font-semibold tabular-nums">{agreements}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-forest-100">Disagreements</span>
        <span className="font-semibold tabular-nums">{disagreements}</span>
      </div>
      {(onlyA > 0 || onlyB > 0) && (
        <div className="flex justify-between">
          <span className="text-forest-100">Only one evaluated</span>
          <span className="font-semibold tabular-nums">{onlyA + onlyB}</span>
        </div>
      )}
    </div>
  </div>
)

const LegendPill = ({ colorA, colorB, a, b }) => (
  <div className="inline-flex items-center gap-4 px-4 py-2 rounded-full border border-ink-200 bg-white">
    <div className="flex items-center gap-1.5">
      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colorA }} />
      <span className="text-xs font-medium text-ink-800">{a}</span>
    </div>
    <div className="flex items-center gap-1.5">
      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colorB }} />
      <span className="text-xs font-medium text-ink-800">{b}</span>
    </div>
  </div>
)

const DistributionColumn = ({ company, color, summary }) => {
  const total = summary?.total_clauses || 0
  const sup = summary?.supported || 0
  const par = summary?.partial || 0
  const nsp = summary?.not_supported || 0
  const rate = (summary?.compliance_rate || 0) * 100

  return (
    <div className="rounded-xl border border-ink-200 p-5 bg-clay-50/30">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
          <p className="font-display font-semibold text-ink-900 truncate">{company}</p>
        </div>
        <p className="font-display text-xl font-bold tabular-nums" style={{ color }}>
          {rate.toFixed(1)}%
        </p>
      </div>
      <div className="space-y-2.5">
        <DistBar
          icon={<CheckCircle2 className="w-3.5 h-3.5" />}
          label="Supported"
          value={sup}
          total={total}
          color="#2a6752"
        />
        <DistBar
          icon={<AlertTriangle className="w-3.5 h-3.5" />}
          label="Partial"
          value={par}
          total={total}
          color="#c4a574"
        />
        <DistBar
          icon={<XCircle className="w-3.5 h-3.5" />}
          label="Not supported"
          value={nsp}
          total={total}
          color="#c45c5c"
        />
      </div>
    </div>
  )
}

const DistBar = ({ icon, label, value, total, color }) => {
  const pct = total > 0 ? (value / total) * 100 : 0
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] mb-1">
        <div className="flex items-center gap-1.5 text-ink-700">
          <span style={{ color }}>{icon}</span>
          <span>{label}</span>
        </div>
        <div className="tabular-nums text-ink-900 font-semibold">
          {value} <span className="text-ink-400 font-normal">({pct.toFixed(0)}%)</span>
        </div>
      </div>
      <div className="h-1.5 bg-white rounded-full overflow-hidden border border-ink-100">
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

const StatusPill = ({ status }) => {
  if (status === null || status === undefined) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-ink-200 bg-clay-50 text-ink-500 text-[11px] font-medium">
        <MinusCircle className="w-3 h-3" />
        Missing
      </span>
    )
  }
  const map = {
    supported: {
      label: 'Supported',
      bg: 'bg-forest-50',
      border: 'border-forest-200',
      text: 'text-forest-800',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    partial: {
      label: 'Partial',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      text: 'text-amber-800',
      icon: <AlertTriangle className="w-3 h-3" />,
    },
    not_supported: {
      label: 'Not supported',
      bg: 'bg-red-50',
      border: 'border-red-200',
      text: 'text-red-800',
      icon: <XCircle className="w-3 h-3" />,
    },
  }
  const cfg = map[status] || map.not_supported
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border ${cfg.bg} ${cfg.border} ${cfg.text} text-[11px] font-medium`}
    >
      {cfg.icon}
      {cfg.label}
    </span>
  )
}

const VerdictBadge = ({ row, companyA, companyB }) => {
  if (row.isMissingEither) {
    return <span className="text-[11px] text-ink-400">—</span>
  }
  if (row.agreement) {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-ink-500">
        <Equal className="w-3 h-3" /> Match
      </span>
    )
  }
  const leader = row.delta > 0 ? companyA : companyB
  const color = row.delta > 0 ? COMPANY_A_COLOR : COMPANY_B_COLOR
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-semibold"
      style={{ color }}
      title={`${leader} is stronger on this clause`}
    >
      <Trophy className="w-3 h-3" />
      {leader}
    </span>
  )
}

const FilterPills = ({ value, onChange }) => {
  const tabs = [
    { id: 'disagreements', label: 'Disagreements' },
    { id: 'all', label: 'All clauses' },
    { id: 'agreements', label: 'Agreements' },
  ]
  return (
    <div className="inline-flex p-1 bg-clay-100 rounded-xl border border-clay-200">
      {tabs.map((t) => {
        const active = value === t.id
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            className={`relative px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              active ? 'text-forest-900' : 'text-ink-600 hover:text-ink-900'
            }`}
          >
            {active && (
              <motion.span
                layoutId="diff-filter-active"
                className="absolute inset-0 bg-white rounded-lg shadow-sm border border-ink-100"
                transition={{ type: 'spring', stiffness: 320, damping: 28 }}
              />
            )}
            <span className="relative">{t.label}</span>
          </button>
        )
      })}
    </div>
  )
}

export default CompaniesCompare
