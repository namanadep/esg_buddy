import React, { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  BarChart3,
  FileText,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  TrendingUp,
  Search,
  Loader2,
  ChevronDown,
  SlidersHorizontal
} from 'lucide-react'
import { listComplianceReports } from '../lib/api'

const FRAMEWORK_FILTER_OPTIONS = [
  { value: 'all', label: 'All frameworks' },
  { value: 'BRSR', label: 'BRSR' },
  { value: 'GRI', label: 'GRI' },
  { value: 'SASB', label: 'SASB' },
  { value: 'TCFD', label: 'TCFD' },
]

const SORT_OPTIONS = [
  { value: 'date_desc', label: 'Generated date (newest first)' },
  { value: 'date_asc', label: 'Generated date (oldest first)' },
  { value: 'name_asc', label: 'Document name (A–Z)' },
  { value: 'name_desc', label: 'Document name (Z–A)' },
  { value: 'compliance_desc', label: 'Compliance rate (high to low)' },
  { value: 'compliance_asc', label: 'Compliance rate (low to high)' },
  { value: 'framework_asc', label: 'Framework (A–Z)' },
]

/** Strip framework keywords and .pdf extension to get a clean company name. */
function extractCompanyName(filename) {
  return (filename || '')
    .replace(/\.pdf$/i, '')
    .replace(/\b(BRSR|GRI|SASB|TCFD|ESG)\b/gi, '')
    .trim()
}

const selectFieldClass =
  'w-full appearance-none pl-4 pr-11 py-3 bg-white border border-ink-200 rounded-xl text-sm text-ink-900 ' +
  'shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 ' +
  'transition-colors cursor-pointer'

const Reports = () => {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [frameworkFilter, setFrameworkFilter] = useState('all')
  const [companyFilter, setCompanyFilter] = useState('all')
  const [sortBy, setSortBy] = useState('date_desc')

  useEffect(() => {
    const loadReports = async () => {
      try {
        setLoading(true)
        const data = await listComplianceReports()
        setReports(data.reports || [])
      } catch (err) {
        console.error('Error loading reports:', err)
        setError(err.response?.data?.detail || 'Failed to load reports')
      } finally {
        setLoading(false)
      }
    }

    loadReports()
  }, [])

  const uniqueCompanies = useMemo(() => {
    const names = [...new Set(reports.map((r) => extractCompanyName(r.document_filename)))]
    return names.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
  }, [reports])

  const filteredReports = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    let list = reports.filter((report) =>
      !q ||
      report.document_filename.toLowerCase().includes(q) ||
      report.framework.toLowerCase().includes(q)
    )
    if (frameworkFilter !== 'all') {
      list = list.filter(
        (report) => (report.framework || '').toUpperCase() === frameworkFilter
      )
    }
    if (companyFilter !== 'all') {
      list = list.filter((report) => extractCompanyName(report.document_filename) === companyFilter)
    }
    const sorted = [...list]
    sorted.sort((a, b) => {
      switch (sortBy) {
        case 'name_asc':
          return a.document_filename.localeCompare(b.document_filename, undefined, { sensitivity: 'base' })
        case 'name_desc':
          return b.document_filename.localeCompare(a.document_filename, undefined, { sensitivity: 'base' })
        case 'date_asc':
          return new Date(a.generated_at) - new Date(b.generated_at)
        case 'date_desc':
          return new Date(b.generated_at) - new Date(a.generated_at)
        case 'compliance_asc':
          return (a.summary?.compliance_rate || 0) - (b.summary?.compliance_rate || 0)
        case 'compliance_desc':
          return (b.summary?.compliance_rate || 0) - (a.summary?.compliance_rate || 0)
        case 'framework_asc':
          return (a.framework || '').localeCompare(b.framework || '', undefined, { sensitivity: 'base' })
        default:
          return 0
      }
    })
    return sorted
  }, [reports, searchQuery, frameworkFilter, sortBy])

  const filtersActive =
    frameworkFilter !== 'all' || companyFilter !== 'all' || sortBy !== 'date_desc' || searchQuery.trim() !== ''

  const clearListFilters = () => {
    setSearchQuery('')
    setFrameworkFilter('all')
    setCompanyFilter('all')
    setSortBy('date_desc')
  }
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'supported':
        return <CheckCircle2 className="w-4 h-4" />
      case 'partial':
        return <AlertTriangle className="w-4 h-4" />
      case 'not_supported':
        return <XCircle className="w-4 h-4" />
      default:
        return null
    }
  }
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'supported':
        return 'bg-green-100 text-green-700'
      case 'partial':
        return 'bg-yellow-100 text-yellow-700'
      case 'not_supported':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }
  
  if (loading) {
    return (
      <div className="min-h-[calc(100vh-80px)] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-forest-600 animate-spin" />
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="min-h-[calc(100vh-80px)] py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <AlertTriangle className="w-12 h-12 text-red-600 mx-auto mb-4" />
            <h3 className="font-semibold text-red-900 mb-2">Error Loading Reports</h3>
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-[calc(100vh-80px)] py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="mb-12">
            <h1 className="font-display text-4xl font-bold text-ink-900 mb-4">
              Compliance Reports
            </h1>
            <p className="text-lg text-ink-600">
              View and analyze ESG compliance evaluation reports
            </p>
          </div>
          
          {/* Search + list filters */}
          <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6 mb-8 space-y-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400 pointer-events-none" />
              <input
                type="text"
                placeholder="Search by document name or framework..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white border border-ink-200 rounded-xl text-sm text-ink-900 shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 transition-colors"
                aria-label="Search reports"
              />
            </div>

            <div className="rounded-xl border border-ink-100 bg-clay-50/60 p-4 sm:p-5 space-y-4">
              <div className="flex items-center gap-2 text-ink-800">
                <SlidersHorizontal className="w-4 h-4 text-forest-600 shrink-0" aria-hidden />
                <h2 className="font-display text-lg font-semibold text-ink-900">
                  List filters
                </h2>
              </div>
              <p className="text-xs text-ink-600 -mt-1">
                Narrow by framework or company document, and reorder by date, name, or compliance rate.
              </p>

              <div className="grid sm:grid-cols-3 gap-4">
                <div>
                  <label
                    htmlFor="report-framework-filter"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Filter by framework
                  </label>
                  <div className="relative">
                    <select
                      id="report-framework-filter"
                      value={frameworkFilter}
                      onChange={(e) => setFrameworkFilter(e.target.value)}
                      className={selectFieldClass}
                    >
                      {FRAMEWORK_FILTER_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400"
                      aria-hidden
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="report-company-filter"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Filter by company
                  </label>
                  <div className="relative">
                    <select
                      id="report-company-filter"
                      value={companyFilter}
                      onChange={(e) => setCompanyFilter(e.target.value)}
                      className={selectFieldClass}
                    >
                      <option value="all">All companies</option>
                      {uniqueCompanies.map((company) => (
                        <option key={company} value={company}>
                          {company}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400"
                      aria-hidden
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="report-sort"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Sort by
                  </label>
                  <div className="relative">
                    <select
                      id="report-sort"
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value)}
                      className={selectFieldClass}
                    >
                      {SORT_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400"
                      aria-hidden
                    />
                  </div>
                </div>
              </div>
            </div>

            {filtersActive && (
              <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-ink-200">
                <p className="text-sm text-ink-600">
                  Showing <span className="font-semibold text-ink-900">{filteredReports.length}</span> of{' '}
                  {reports.length} report{reports.length !== 1 ? 's' : ''}
                </p>
                <button
                  type="button"
                  onClick={clearListFilters}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-forest-800 hover:text-forest-950 px-4 py-2 rounded-xl border border-forest-200 bg-white hover:bg-forest-50 shadow-sm transition-colors"
                >
                  <XCircle className="w-4 h-4 text-forest-600" aria-hidden />
                  Reset search &amp; filters
                </button>
              </div>
            )}
          </div>
          
          {/* Reports List */}
          {reports.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 text-center">
              <BarChart3 className="w-16 h-16 text-ink-300 mx-auto mb-4" />
              <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                No reports yet
              </h3>
              <p className="text-ink-600 mb-6">
                Run a compliance evaluation to generate your first report
              </p>
              <Link
                to="/documents"
                className="inline-flex items-center px-6 py-3 gradient-forest text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
              >
                Go to Documents
              </Link>
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 text-center">
              <Search className="w-16 h-16 text-ink-300 mx-auto mb-4" />
              <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                No matches
              </h3>
              <p className="text-ink-600 mb-6">
                Nothing matches your search or filters. Try clearing them or picking a different framework.
              </p>
              <button
                type="button"
                onClick={clearListFilters}
                className="inline-flex items-center px-6 py-3 border border-forest-600 text-forest-800 rounded-xl font-semibold hover:bg-forest-50 transition-colors"
              >
                Reset search &amp; filters
              </button>
            </div>
          ) : (
            <div className="grid gap-6">
              {filteredReports.map((report, index) => (
                <motion.div
                  key={report.report_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Link
                    to={`/reports/${report.report_id}`}
                    className="block bg-white rounded-2xl shadow-lg border border-ink-200 hover:border-forest-300 transition-all duration-300 hover:shadow-xl overflow-hidden"
                  >
                    <div className="p-6">
                      <div className="flex items-start justify-between mb-6">
                        <div className="flex items-start space-x-4 flex-1">
                          <div className="w-14 h-14 bg-forest-100 rounded-xl flex items-center justify-center flex-shrink-0">
                            <BarChart3 className="w-7 h-7 text-forest-600" />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-3 mb-2">
                              <span className="px-3 py-1 bg-forest-100 text-forest-700 text-xs font-semibold rounded-full">
                                {report.framework}
                              </span>
                              <div className="flex items-center space-x-2 text-sm text-ink-500">
                                <Calendar className="w-4 h-4" />
                                <span>
                                  {new Date(report.generated_at).toLocaleDateString()}
                                </span>
                              </div>
                            </div>
                            
                            <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                              {report.document_filename}
                            </h3>
                            
                            <div className="flex items-center space-x-4 text-sm text-ink-600">
                              <div className="flex items-center space-x-2">
                                <FileText className="w-4 h-4" />
                                <span>{report.summary.total_clauses} clauses evaluated</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <div className="text-right ml-4">
                          <div className="flex items-center space-x-2 mb-1">
                            <TrendingUp className="w-5 h-5 text-forest-600" />
                            <span className="text-3xl font-display font-bold text-forest-600" title={`${(report.summary.compliance_rate * 100).toFixed(2)}% (supported + partial) / total`}>
                              {(report.summary.compliance_rate * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="text-sm text-ink-500 font-medium">
                            Compliance Rate
                          </div>
                        </div>
                      </div>
                      
                      {/* Summary Stats */}
                      <div className="grid grid-cols-3 gap-4">
                        {[
                          { key: 'supported', label: 'Supported', value: report.summary.supported },
                          { key: 'partial', label: 'Partial', value: report.summary.partial },
                          { key: 'not_supported', label: 'Not Supported', value: report.summary.not_supported },
                        ].map((stat) => (
                          <div
                            key={stat.key}
                            className={`p-4 rounded-xl ${getStatusColor(stat.key)} border border-current/20`}
                          >
                            <div className="flex items-center space-x-2 mb-1">
                              {getStatusIcon(stat.key)}
                              <span className="text-xs font-semibold uppercase tracking-wide">
                                {stat.label}
                              </span>
                            </div>
                            <div className="text-2xl font-display font-bold">
                              {stat.value}
                            </div>
                          </div>
                        ))}
                      </div>
                      
                      {/* Confidence Bar */}
                      <div className="mt-6 pt-6 border-t border-ink-100">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-ink-700">
                            Average Confidence
                          </span>
                          <span className="text-sm font-bold text-ink-900">
                            {Math.round(report.summary.average_confidence * 100)}%
                          </span>
                        </div>
                        <div className="h-2 bg-clay-100 rounded-full overflow-hidden">
                          <div
                            className="h-full gradient-forest"
                            style={{ width: `${report.summary.average_confidence * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

export default Reports
