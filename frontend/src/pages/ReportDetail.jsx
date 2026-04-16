import React, { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  ChevronDown,
  ChevronRight,
  FileText,
  Calendar,
  TrendingUp,
  Shield,
  Zap,
  Loader2,
  UserCheck,
  ThumbsUp,
  ThumbsDown,
  Target,
  BarChart3,
  Download,
  Eye,
  EyeOff,
  ExternalLink,
  Copy,
  Check,
  Trash2
} from 'lucide-react'
import { getComplianceReport, getClauseEvaluationDetail, overrideClauseEvaluation, getAccuracyMetrics, downloadCompliancePdf, getDocumentFileUrl, deleteComplianceReport } from '../lib/api'
import ReportChat from '../components/ReportChat'

const ReportDetail = () => {
  const { reportId } = useParams()
  const navigate = useNavigate()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedClause, setExpandedClause] = useState(null)
  const [clauseDetail, setClauseDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [filterStatus, setFilterStatus] = useState('all')
  const [overridingClauseId, setOverridingClauseId] = useState(null)
  const [overrideReason, setOverrideReason] = useState({})
  const [accuracyMetrics, setAccuracyMetrics] = useState(null)
  const [loadingAccuracy, setLoadingAccuracy] = useState(false)
  const [expandedVerificationClause, setExpandedVerificationClause] = useState(null)
  const [verificationClauseDetail, setVerificationClauseDetail] = useState(null)
  const [loadingVerificationDetail, setLoadingVerificationDetail] = useState(false)
  const [groundTruthExpanded, setGroundTruthExpanded] = useState(false)
  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const [deletingReport, setDeletingReport] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [previewEvidenceId, setPreviewEvidenceId] = useState(null)
  const [copiedEvidenceId, setCopiedEvidenceId] = useState(null)

  const pdfUrl = report?.document_id ? getDocumentFileUrl(report.document_id) : null

  const handleCopyEvidence = async (evidence) => {
    try {
      await navigator.clipboard.writeText(evidence.text || '')
      setCopiedEvidenceId(evidence.chunk_id)
      setTimeout(() => {
        setCopiedEvidenceId((id) => (id === evidence.chunk_id ? null : id))
      }, 1500)
    } catch (err) {
      console.error('Failed to copy evidence text:', err)
    }
  }

  const CONFIDENCE_THRESHOLD = 0.7

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true)
    try {
      const blob = await downloadCompliancePdf(reportId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const safeName = (report.document_metadata?.filename || report.document_filename || 'report').replace(/\.pdf$/i, '')
      a.download = `${safeName}_${report.framework}_Compliance_Report.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('PDF download failed:', err)
    } finally {
      setDownloadingPdf(false)
    }
  }

  const handleDeleteReport = async () => {
    setDeletingReport(true)
    try {
      await deleteComplianceReport(reportId)
      navigate('/reports')
    } catch (err) {
      console.error('Delete failed:', err)
      setDeletingReport(false)
      setShowDeleteConfirm(false)
    }
  }

  // Fetch real report data from API
  useEffect(() => {
    const loadReport = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await getComplianceReport(reportId)
        setReport(data)
      } catch (err) {
        console.error('Error loading report:', err)
        setError(err.response?.data?.detail || 'Failed to load report')
      } finally {
        setLoading(false)
      }
    }
    
    loadReport()
  }, [reportId])

  useEffect(() => {
    setGroundTruthExpanded(false)
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [reportId])

  // Load accuracy metrics when report loads
  useEffect(() => {
    const loadAccuracy = async () => {
      if (!report) return
      setLoadingAccuracy(true)
      try {
        const data = await getAccuracyMetrics(reportId)
        console.log('Accuracy metrics loaded:', data)
        setAccuracyMetrics(data)
      } catch (err) {
        console.error('Error loading accuracy:', err)
        setAccuracyMetrics({ error: err.message })
      } finally {
        setLoadingAccuracy(false)
      }
    }
    loadAccuracy()
  }, [report, reportId])

  const isAmbiguous = (e) => {
    if (e.override_applied) return false
    const status = e.final_status
    const conf = e.final_confidence ?? 0
    return status === 'partial' || conf < CONFIDENCE_THRESHOLD
  }

  const ambiguousClauses = report ? report.evaluations.filter(isAmbiguous) : []

  const toggleVerificationDetails = async (clauseId) => {
    if (expandedVerificationClause === clauseId) {
      setExpandedVerificationClause(null)
      setVerificationClauseDetail(null)
      return
    }
    setExpandedVerificationClause(clauseId)
    setVerificationClauseDetail(null)
    setLoadingVerificationDetail(true)
    try {
      const detail = await getClauseEvaluationDetail(reportId, clauseId)
      setVerificationClauseDetail(detail)
    } catch (err) {
      console.error('Error loading verification clause detail:', err)
      setVerificationClauseDetail({ error: 'Failed to load details' })
    } finally {
      setLoadingVerificationDetail(false)
    }
  }

  const handleOverride = async (clauseId, newStatus) => {
    setOverridingClauseId(clauseId)
    try {
      await overrideClauseEvaluation(reportId, clauseId, newStatus, overrideReason[clauseId] || 'Human review')
      const data = await getComplianceReport(reportId)
      setReport(data)
      setOverrideReason((prev) => ({ ...prev, [clauseId]: '' }))
    } catch (err) {
      console.error('Override failed:', err)
    } finally {
      setOverridingClauseId(null)
    }
  }

  const handleClauseClick = async (clauseId) => {
    if (expandedClause === clauseId) {
      setExpandedClause(null)
      setClauseDetail(null)
    } else {
      setExpandedClause(clauseId)
      setLoadingDetail(true)
      
      try {
        const detail = await getClauseEvaluationDetail(reportId, clauseId)
        setClauseDetail(detail)
      } catch (error) {
        console.error('Error loading clause detail:', error)
        // TODO: Show error message to user
      } finally {
        setLoadingDetail(false)
      }
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
          <Link
            to="/reports"
            className="inline-flex items-center space-x-2 text-ink-600 hover:text-forest-600 mb-8 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-medium">Back to Reports</span>
          </Link>
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <XCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
            <h3 className="font-semibold text-red-900 mb-2">Error Loading Report</h3>
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      </div>
    )
  }
  
  if (!report) {
    return (
      <div className="min-h-[calc(100vh-80px)] py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link
            to="/reports"
            className="inline-flex items-center space-x-2 text-ink-600 hover:text-forest-600 mb-8 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-medium">Back to Reports</span>
          </Link>
          <div className="bg-clay-50 border border-ink-200 rounded-xl p-6 text-center">
            <Info className="w-12 h-12 text-ink-400 mx-auto mb-4" />
            <h3 className="font-semibold text-ink-900 mb-2">Report Not Found</h3>
            <p className="text-ink-600">The requested report could not be found.</p>
          </div>
        </div>
      </div>
    )
  }
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'supported':
        return <CheckCircle2 className="w-5 h-5" />
      case 'partial':
        return <AlertTriangle className="w-5 h-5" />
      case 'not_supported':
        return <XCircle className="w-5 h-5" />
      default:
        return null
    }
  }
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'supported':
        return 'bg-green-100 text-green-700 border-green-200'
      case 'partial':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      case 'not_supported':
        return 'bg-red-100 text-red-700 border-red-200'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }
  
  const filteredEvaluations = filterStatus === 'all' 
    ? report.evaluations 
    : report.evaluations.filter(e => e.final_status === filterStatus)

  const statusFilterOptions = ['all', 'supported', 'partial', 'not_supported']

  const hasGroundTruthAccuracy = Boolean(
    accuracyMetrics?.metrics && accuracyMetrics?.ground_truth_loaded > 0
  )

  return (
    <div className="min-h-[calc(100vh-80px)] py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Back Button */}
          <Link
            to="/reports"
            className="inline-flex items-center space-x-2 text-ink-600 hover:text-forest-600 mb-8 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-medium">Back to Reports</span>
          </Link>
          
          {/* Header */}
          <div className="bg-white rounded-3xl shadow-lg border border-ink-200 p-8 mb-8">
            <div className="flex items-start justify-between mb-6">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-3">
                  <span className="px-4 py-1.5 bg-forest-100 text-forest-700 text-sm font-semibold rounded-full">
                    {report.framework}
                  </span>
                  <div className="flex items-center space-x-2 text-sm text-ink-500">
                    <Calendar className="w-4 h-4" />
                    <span>
                      {new Date(report.generated_at).toLocaleString()}
                    </span>
                  </div>
                </div>
                
                <h1 className="font-display text-3xl font-bold text-ink-900 mb-2">
                  {report.document_metadata?.filename || report.document_filename}
                </h1>
                
                <p className="text-ink-600">
                  Compliance evaluation against {report.framework} framework
                </p>
              </div>
              
              <div className="text-right ml-6 flex flex-col items-end">
                <div className="flex items-center justify-end space-x-2 mb-1">
                  <TrendingUp className="w-6 h-6 text-forest-600" />
                  <span className="text-4xl font-display font-bold text-forest-600">
                    {(report.summary.compliance_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="text-sm text-ink-500 font-medium mb-3">
                  Overall Compliance
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleDownloadPdf}
                    disabled={downloadingPdf}
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-forest-600 text-white text-sm font-semibold rounded-xl hover:bg-forest-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                  >
                    {downloadingPdf ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4" />
                    )}
                    <span>{downloadingPdf ? 'Generating...' : 'Download PDF'}</span>
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-red-50 text-red-700 text-sm font-semibold rounded-xl border border-red-200 hover:bg-red-100 transition-colors shadow-sm"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            </div>
            
            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-clay-50 rounded-xl border border-ink-200">
                <div className="text-2xl font-display font-bold text-ink-900 mb-1">
                  {report.summary.total_clauses}
                </div>
                <div className="text-xs text-ink-600 font-medium uppercase tracking-wide">
                  Total Clauses
                </div>
              </div>
              
              {[
                { key: 'supported', label: 'Supported', value: report.summary.supported },
                { key: 'partial', label: 'Partial', value: report.summary.partial },
                { key: 'not_supported', label: 'Not Supported', value: report.summary.not_supported },
              ].map((stat) => (
                <div
                  key={stat.key}
                  className={`p-4 rounded-xl border ${getStatusColor(stat.key)}`}
                >
                  <div className="text-2xl font-display font-bold mb-1">
                    {stat.value}
                  </div>
                  <div className="text-xs font-medium uppercase tracking-wide">
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Accuracy Metrics - Ground Truth Comparison (collapsible) */}
          {!loadingAccuracy && accuracyMetrics && (
              <div
                className={`rounded-xl shadow-lg border mb-6 overflow-hidden ${
                  hasGroundTruthAccuracy
                    ? 'bg-blue-50/80 border-blue-200'
                    : 'bg-gray-50/80 border-gray-200'
                }`}
              >
                <button
                  type="button"
                  onClick={() => setGroundTruthExpanded((v) => !v)}
                  className="w-full flex items-center gap-2 p-6 text-left hover:bg-black/[0.03] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 rounded-xl"
                  aria-expanded={groundTruthExpanded}
                  id="ground-truth-accuracy-toggle"
                >
                  {groundTruthExpanded ? (
                    <ChevronDown className="w-5 h-5 shrink-0 text-ink-600" aria-hidden />
                  ) : (
                    <ChevronRight className="w-5 h-5 shrink-0 text-ink-600" aria-hidden />
                  )}
                  <Target
                    className={`w-6 h-6 shrink-0 ${
                      hasGroundTruthAccuracy ? 'text-blue-600' : 'text-gray-600'
                    }`}
                    aria-hidden
                  />
                  <h2 className="font-display text-xl font-bold text-ink-900">
                    Ground Truth Accuracy
                  </h2>
                </button>
                <AnimatePresence initial={false}>
                  {groundTruthExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div
                        className="px-6 pb-6 pt-0 text-sm text-ink-600"
                        role="region"
                        aria-labelledby="ground-truth-accuracy-toggle"
                      >
                        {hasGroundTruthAccuracy ? (
                          <>
                            <p className="mb-4">
                              Verified against{' '}
                              {accuracyMetrics.ground_truth_loaded}
                              {['GRI', 'TCFD', 'SASB'].includes(accuracyMetrics.framework) &&
                              accuracyMetrics.ground_truth_sample_target != null &&
                              accuracyMetrics.ground_truth_loaded <
                                accuracyMetrics.ground_truth_sample_target
                                ? ` of up to ${accuracyMetrics.ground_truth_sample_target}`
                                : ''}{' '}
                              clauses for{' '}
                              {report.document_metadata?.filename || report.document_filename}
                            </p>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                              <div className="bg-white rounded-lg border border-blue-200 p-4">
                                <div className="text-2xl font-display font-bold text-blue-600 mb-1">
                                  {Math.round(accuracyMetrics.metrics.llm_precision * 100)}%
                                </div>
                                <div className="text-xs text-ink-600 font-medium uppercase tracking-wide">
                                  Precision
                                </div>
                              </div>
                              <div className="bg-white rounded-lg border border-blue-200 p-4">
                                <div className="text-2xl font-display font-bold text-blue-600 mb-1">
                                  {Math.round(accuracyMetrics.metrics.llm_recall * 100)}%
                                </div>
                                <div className="text-xs text-ink-600 font-medium uppercase tracking-wide">
                                  Recall
                                </div>
                              </div>
                              <div className="bg-white rounded-lg border border-blue-200 p-4">
                                <div className="text-2xl font-display font-bold text-blue-600 mb-1">
                                  {Math.round(accuracyMetrics.metrics.llm_f1_score * 100)}%
                                </div>
                                <div className="text-xs text-ink-600 font-medium uppercase tracking-wide">
                                  F1 Score
                                </div>
                              </div>
                              <div
                                className="bg-white rounded-lg border border-blue-200 p-4"
                                title="With demo mode off: exact match of predicted vs ground-truth status (supported / partial / not supported)."
                              >
                                <div className="text-2xl font-display font-bold text-blue-600 mb-1">
                                  {Math.round(
                                    (accuracyMetrics.metrics.status_match_accuracy ?? 0) * 100
                                  )}
                                  %
                                </div>
                                <div className="text-xs text-ink-600 font-medium uppercase tracking-wide">
                                  Accuracy
                                </div>
                              </div>
                            </div>
                          </>
                        ) : (
                          <div>
                            {accuracyMetrics.error ? (
                              <p className="text-red-600">
                                Error loading accuracy: {accuracyMetrics.error}
                              </p>
                            ) : accuracyMetrics.note ? (
                              <p>{accuracyMetrics.note}</p>
                            ) : (
                              <>
                                <p className="mb-2">Ground truth not available for this report.</p>
                                <p className="text-xs">
                                  Ground truth JSON exists for selected BRSR, GRI, TCFD, and SASB reports under{' '}
                                  <code className="text-xs bg-ink-100 px-1 rounded">Company Reports/</code>
                                  (e.g. <code className="text-xs bg-ink-100 px-1 rounded">…/SASB Ground Truth/</code> for
                                  Amazon, Apple, Infosys). Call{' '}
                                  <code className="text-xs bg-ink-100 px-1 rounded">POST /accuracy/load-ground-truth</code>{' '}
                                  after adding files.
                                </p>
                                <p className="text-xs mt-1">
                                  Debug: ground_truth_loaded ={' '}
                                  {accuracyMetrics.ground_truth_loaded || 0}
                                </p>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
          )}

          {/* Human Verification Dashboard - always visible */}
          <div className="bg-amber-50/80 rounded-xl shadow-lg border border-amber-200 p-6 mb-6">
            <h2 className="font-display text-xl font-bold text-ink-900 mb-1 flex items-center">
              <UserCheck className="w-6 h-6 mr-2 text-amber-600" />
              Human verification
            </h2>
            {ambiguousClauses.length > 0 ? (
              <>
                <p className="text-sm text-ink-600 mb-4">
                  {ambiguousClauses.length} clause{ambiguousClauses.length !== 1 ? 's' : ''} need your review (partial or uncertain disclosures). Approve or reject to lock the status.
                </p>
                <div className="space-y-3 max-h-[480px] overflow-y-auto pr-2">
                  {ambiguousClauses.map((evaluation) => {
                    const isDetailsOpen = expandedVerificationClause === evaluation.clause_id
                    const detail = isDetailsOpen ? verificationClauseDetail : null
                    return (
                      <div
                        key={evaluation.clause_id}
                        className="bg-white rounded-lg border border-amber-200 overflow-hidden"
                      >
                        <div className="p-4 flex flex-wrap items-center gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-ink-900 truncate">
                              {evaluation.clause?.title || evaluation.clause_id}
                            </div>
                            <div className="text-xs text-ink-600 mt-0.5">
                              <span className="font-mono">{evaluation.clause_id}</span>
                              <span className="mx-2">•</span>
                              <span className="capitalize">{evaluation.final_status.replace('_', ' ')}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <button
                              type="button"
                              onClick={() => toggleVerificationDetails(evaluation.clause_id)}
                              className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium bg-clay-100 text-ink-700 hover:bg-clay-200 border border-ink-200"
                              aria-expanded={isDetailsOpen}
                            >
                              {isDetailsOpen ? (
                                <ChevronDown className="w-4 h-4 mr-1" />
                              ) : (
                                <ChevronRight className="w-4 h-4 mr-1" />
                              )}
                              Details
                            </button>
                            <input
                              type="text"
                              placeholder="Reason (optional)"
                              value={overrideReason[evaluation.clause_id] || ''}
                              onChange={(e) => setOverrideReason((prev) => ({ ...prev, [evaluation.clause_id]: e.target.value }))}
                              className="px-3 py-1.5 text-sm border border-ink-200 rounded-lg w-40 focus:ring-2 focus:ring-forest-500 focus:border-forest-500"
                            />
                            <button
                              onClick={() => handleOverride(evaluation.clause_id, 'supported')}
                              disabled={overridingClauseId === evaluation.clause_id}
                              className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium bg-green-100 text-green-800 hover:bg-green-200 disabled:opacity-50"
                            >
                              {overridingClauseId === evaluation.clause_id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <>
                                  <ThumbsUp className="w-4 h-4 mr-1" />
                                  Approve
                                </>
                              )}
                            </button>
                            <button
                              onClick={() => handleOverride(evaluation.clause_id, 'not_supported')}
                              disabled={overridingClauseId === evaluation.clause_id}
                              className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium bg-red-100 text-red-800 hover:bg-red-200 disabled:opacity-50"
                            >
                              <ThumbsDown className="w-4 h-4 mr-1" />
                              Reject
                            </button>
                          </div>
                        </div>
                        <AnimatePresence>
                          {isDetailsOpen && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.2 }}
                              className="border-t border-amber-200 bg-amber-50/50 overflow-hidden"
                            >
                              <div className="p-4">
                                {loadingVerificationDetail ? (
                                  <div className="flex items-center justify-center py-8">
                                    <Loader2 className="w-6 h-6 text-forest-600 animate-spin" />
                                  </div>
                                ) : detail?.error ? (
                                  <p className="text-sm text-red-600">{detail.error}</p>
                                ) : detail?.llm_evaluation ? (
                                  <div className="space-y-4 text-sm">
                                    <div>
                                      <h4 className="font-semibold text-ink-800 mb-1 flex items-center">
                                        <Zap className="w-4 h-4 mr-2 text-forest-600" />
                                        AI Explanation
                                      </h4>
                                      <p className="text-ink-700 leading-relaxed pl-6">
                                        {detail.llm_evaluation.explanation}
                                      </p>
                                    </div>
                                    {detail.llm_evaluation.reasoning && (
                                      <div>
                                        <h4 className="font-semibold text-ink-800 mb-1">Reasoning</h4>
                                        <p className="text-ink-600 leading-relaxed pl-6">
                                          {detail.llm_evaluation.reasoning}
                                        </p>
                                      </div>
                                    )}
                                    {detail.retrieved_evidence?.length > 0 && (
                                      <div>
                                        <h4 className="font-semibold text-ink-800 mb-2 flex items-center">
                                          <FileText className="w-4 h-4 mr-2 text-forest-600" />
                                          Retrieved Evidence ({detail.retrieved_evidence.length})
                                        </h4>
                                        <div className="space-y-2 pl-6 max-h-48 overflow-y-auto">
                                          {detail.retrieved_evidence.slice(0, 5).map((ev) => (
                                            <div
                                              key={ev.chunk_id}
                                              className="p-3 bg-white rounded-lg border border-ink-200"
                                            >
                                              <div className="flex items-center justify-between gap-2">
                                                <span className="text-xs text-ink-500">
                                                  Page {ev.page_number}
                                                  {ev.similarity_score != null && ` • ${Math.round(ev.similarity_score * 100)}% match`}
                                                </span>
                                                {pdfUrl && (
                                                  <a
                                                    href={`${pdfUrl}#page=${ev.page_number}&zoom=page-width`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-forest-700 hover:text-forest-900"
                                                    title={`Open page ${ev.page_number} in source PDF`}
                                                  >
                                                    <ExternalLink className="w-3 h-3" />
                                                    Jump to page {ev.page_number}
                                                  </a>
                                                )}
                                              </div>
                                              <p className="text-ink-700 mt-1 line-clamp-3">{ev.text}</p>
                                            </div>
                                          ))}
                                          {detail.retrieved_evidence.length > 5 && (
                                            <p className="text-xs text-ink-500">
                                              +{detail.retrieved_evidence.length - 5} more chunk(s)
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                    )}
                                    {detail.rule_results?.length > 0 && (
                                      <div>
                                        <h4 className="font-semibold text-ink-800 mb-1 flex items-center">
                                          <Shield className="w-4 h-4 mr-2 text-forest-600" />
                                          Rule validation
                                        </h4>
                                        <ul className="pl-6 space-y-1">
                                          {detail.rule_results.map((r) => (
                                            <li
                                              key={r.rule_id}
                                              className={r.passed ? 'text-green-700' : 'text-red-700'}
                                            >
                                              {r.rule_id}: {r.passed ? 'Passed' : 'Failed'}
                                              {r.message && ` — ${r.message}`}
                                            </li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                  </div>
                                ) : null}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )
                  })}
                </div>
              </>
            ) : (
              <p className="text-sm text-ink-600">
                No clauses need review. Clauses appear here when they are <strong>partial</strong> or flagged as <strong>uncertain</strong>. You can then approve or reject to lock the status.
              </p>
            )}
          </div>
          
          {/* Filters */}
          <div className="bg-white rounded-xl shadow-lg border border-ink-200 p-4 mb-6">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-ink-700 mr-2">Filter by status:</span>
              {statusFilterOptions.map((status) => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    filterStatus === status
                      ? 'bg-forest-600 text-white shadow-lg'
                      : 'bg-clay-100 text-ink-700 hover:bg-clay-200'
                  }`}
                >
                  {status === 'all' ? 'All' : status.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
          
          {/* Evaluations List */}
          <div className="space-y-3">
            {filteredEvaluations.map((evaluation, index) => (
              <motion.div
                key={evaluation.clause_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.01 }}
                className="bg-white rounded-xl shadow-md border border-ink-200 overflow-hidden hover:border-forest-300 transition-colors"
              >
                {/* Evaluation Header */}
                <button
                  onClick={() => handleClauseClick(evaluation.clause_id)}
                  className="w-full p-4 flex items-center justify-between hover:bg-clay-50/50 transition-colors"
                >
                  <div className="flex items-center space-x-4 flex-1">
                    <div className={`p-2 rounded-lg ${getStatusColor(evaluation.final_status)}`}>
                      {getStatusIcon(evaluation.final_status)}
                    </div>
                    
                    <div className="flex-1 text-left min-w-0">
                      <h3 className="font-semibold text-ink-900 mb-1">
                        {evaluation.clause?.title || evaluation.clause_id}
                      </h3>
                      <div className="flex items-center space-x-4 text-xs text-ink-600">
                        <span className="font-mono">{evaluation.clause_id}</span>
                        <span>•</span>
                        <span>Top {evaluation.evidence_count ?? evaluation.retrieved_evidence?.length ?? 0} evidence chunks</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4 ml-4">
                    <div className="text-right">
                      <div className={`text-sm font-semibold capitalize ${getStatusColor(evaluation.final_status)} px-3 py-1 rounded-full`}>
                        {evaluation.final_status.replace('_', ' ')}
                      </div>
                    </div>
                    
                    {expandedClause === evaluation.clause_id ? (
                      <ChevronDown className="w-5 h-5 text-ink-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-ink-400" />
                    )}
                  </div>
                </button>
                
                {/* Evaluation Detail */}
                <AnimatePresence>
                  {expandedClause === evaluation.clause_id && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.3 }}
                      className="border-t border-ink-200"
                    >
                      {loadingDetail ? (
                        <div className="p-6 flex items-center justify-center">
                          <Loader2 className="w-6 h-6 text-forest-600 animate-spin" />
                        </div>
                      ) : clauseDetail ? (
                        <div className="p-6 space-y-6">
                          {/* LLM Explanation */}
                          <div>
                            <h4 className="font-semibold text-ink-900 mb-3 flex items-center">
                              <Zap className="w-4 h-4 mr-2 text-forest-600" />
                              AI Analysis
                              {clauseDetail.llm_evaluation.revised && (
                                <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">
                                  REVISED
                                </span>
                              )}
                            </h4>
                            <div className="p-4 bg-forest-50 rounded-xl border border-forest-200">
                              <p className="text-sm text-ink-700 leading-relaxed mb-3">
                                <strong>Explanation:</strong> {clauseDetail.llm_evaluation.explanation}
                              </p>
                              <p className="text-sm text-ink-600 leading-relaxed">
                                {clauseDetail.llm_evaluation.reasoning}
                              </p>
                            </div>
                          </div>
                          
                          {/* Chain-of-Thought Reasoning */}
                          {clauseDetail.llm_evaluation.reasoning_steps && clauseDetail.llm_evaluation.reasoning_steps.length > 0 && (
                            <div>
                              <h4 className="font-semibold text-ink-900 mb-3 flex items-center">
                                <Zap className="w-4 h-4 mr-2 text-forest-600" />
                                Chain-of-Thought Reasoning
                              </h4>
                              <div className="space-y-2">
                                {clauseDetail.llm_evaluation.reasoning_steps.map((step, idx) => (
                                  <div
                                    key={idx}
                                    className="p-3 bg-blue-50 rounded-lg border border-blue-200"
                                  >
                                    <p className="text-sm text-ink-700 leading-relaxed">
                                      {step}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {/* Self-Reflection */}
                          {clauseDetail.llm_evaluation.reflection && (
                            <div>
                              <h4 className="font-semibold text-ink-900 mb-3 flex items-center">
                                <Zap className="w-4 h-4 mr-2 text-forest-600" />
                                Self-Reflection
                              </h4>
                              <div className="p-4 bg-purple-50 rounded-xl border border-purple-200 space-y-3">
                                <p className="text-sm text-ink-700 leading-relaxed">
                                  <strong>Critical Review:</strong> {clauseDetail.llm_evaluation.reflection}
                                </p>
                                
                                {clauseDetail.llm_evaluation.reflection_issues && clauseDetail.llm_evaluation.reflection_issues.length > 0 && (
                                  <div>
                                    <p className="text-xs font-semibold text-purple-700 mb-2">Issues Identified:</p>
                                    <ul className="space-y-1">
                                      {clauseDetail.llm_evaluation.reflection_issues.map((issue, idx) => (
                                        <li key={idx} className="text-sm text-ink-600 flex items-start">
                                          <span className="mr-2">•</span>
                                          <span>{issue}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                          
                          {/* Evidence — with source PDF preview */}
                          <div>
                            <h4 className="font-semibold text-ink-900 mb-3 flex items-center">
                              <FileText className="w-4 h-4 mr-2 text-forest-600" />
                              Retrieved Evidence ({clauseDetail.retrieved_evidence.length})
                            </h4>
                            <div className="space-y-3">
                              {clauseDetail.retrieved_evidence.map((evidence) => {
                                const isPreviewOpen = previewEvidenceId === evidence.chunk_id
                                const isCopied = copiedEvidenceId === evidence.chunk_id
                                const pageAnchor = pdfUrl
                                  ? `${pdfUrl}#page=${evidence.page_number}&zoom=page-width`
                                  : null
                                return (
                                  <div
                                    key={evidence.chunk_id}
                                    className="bg-clay-50 rounded-xl border border-ink-200 overflow-hidden"
                                  >
                                    <div className="p-4">
                                      <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-semibold text-ink-600">
                                          Page {evidence.page_number}
                                          {evidence.section && ` • ${evidence.section}`}
                                        </span>
                                        <span className="text-xs px-2 py-1 bg-forest-100 text-forest-700 rounded-full font-semibold">
                                          {Math.round(evidence.similarity_score * 100)}% match
                                        </span>
                                      </div>
                                      <p className="text-sm text-ink-700 leading-relaxed">
                                        {evidence.text}
                                      </p>

                                      {/* Source PDF actions */}
                                      <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-ink-200/60">
                                        {pdfUrl ? (
                                          <>
                                            <button
                                              type="button"
                                              onClick={() =>
                                                setPreviewEvidenceId(
                                                  isPreviewOpen ? null : evidence.chunk_id
                                                )
                                              }
                                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-forest-600 text-white text-xs font-semibold shadow-sm hover:bg-forest-700 transition-colors"
                                            >
                                              {isPreviewOpen ? (
                                                <>
                                                  <EyeOff className="w-3.5 h-3.5" />
                                                  Hide source page
                                                </>
                                              ) : (
                                                <>
                                                  <Eye className="w-3.5 h-3.5" />
                                                  View page {evidence.page_number} in source PDF
                                                </>
                                              )}
                                            </button>
                                            <a
                                              href={pageAnchor}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-200 bg-white text-xs font-semibold text-ink-700 hover:bg-ink-50 transition-colors"
                                            >
                                              <ExternalLink className="w-3.5 h-3.5" />
                                              Open in new tab
                                            </a>
                                          </>
                                        ) : (
                                          <span className="text-xs text-ink-500">
                                            Source PDF unavailable
                                          </span>
                                        )}
                                        <button
                                          type="button"
                                          onClick={() => handleCopyEvidence(evidence)}
                                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-200 bg-white text-xs font-semibold text-ink-700 hover:bg-ink-50 transition-colors"
                                          title="Copy evidence text so you can Ctrl+F for it in the PDF"
                                        >
                                          {isCopied ? (
                                            <>
                                              <Check className="w-3.5 h-3.5 text-forest-600" />
                                              Copied
                                            </>
                                          ) : (
                                            <>
                                              <Copy className="w-3.5 h-3.5" />
                                              Copy text
                                            </>
                                          )}
                                        </button>
                                      </div>
                                    </div>

                                    {/* Inline PDF preview anchored to the evidence page */}
                                    <AnimatePresence initial={false}>
                                      {isPreviewOpen && pageAnchor && (
                                        <motion.div
                                          initial={{ height: 0, opacity: 0 }}
                                          animate={{ height: 'auto', opacity: 1 }}
                                          exit={{ height: 0, opacity: 0 }}
                                          transition={{ duration: 0.25 }}
                                          className="border-t border-ink-200 bg-white"
                                        >
                                          <div className="px-4 py-2 bg-amber-50 border-b border-amber-200 flex items-start gap-2">
                                            <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                                            <p className="text-xs text-amber-900 leading-snug">
                                              Showing page <strong>{evidence.page_number}</strong> of the original PDF. Use <kbd className="px-1.5 py-0.5 rounded bg-white border border-amber-200 text-[10px] font-mono">Ctrl+F</kbd> inside the viewer and paste the copied text to highlight the exact passage.
                                            </p>
                                          </div>
                                          <iframe
                                            key={pageAnchor}
                                            src={pageAnchor}
                                            title={`Source PDF page ${evidence.page_number}`}
                                            className="w-full h-[560px] bg-white"
                                          />
                                        </motion.div>
                                      )}
                                    </AnimatePresence>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                          
                          {/* Rule Results */}
                          {clauseDetail.rule_results.length > 0 && (
                            <div>
                              <h4 className="font-semibold text-ink-900 mb-3 flex items-center">
                                <Shield className="w-4 h-4 mr-2 text-forest-600" />
                                Rule Validation Results
                              </h4>
                              <div className="space-y-2">
                                {clauseDetail.rule_results.map((rule) => (
                                  <div
                                    key={rule.rule_id}
                                    className={`p-3 rounded-lg border ${
                                      rule.passed
                                        ? 'bg-green-50 border-green-200'
                                        : 'bg-red-50 border-red-200'
                                    }`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span className="text-xs font-mono text-ink-600">
                                        {rule.rule_id}
                                      </span>
                                      <span className={`text-xs px-2 py-1 rounded-full font-semibold ${
                                        rule.passed
                                          ? 'bg-green-100 text-green-700'
                                          : 'bg-red-100 text-red-700'
                                      }`}>
                                        {rule.passed ? 'Passed' : 'Failed'}
                                      </span>
                                    </div>
                                    <p className="text-sm text-ink-700 mt-1">
                                      {rule.message}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : null}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Delete confirmation modal */}
      <AnimatePresence>
        {showDeleteConfirm && (
          <motion.div
            key="delete-overlay"
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
              className="bg-white rounded-2xl shadow-2xl border border-ink-200 w-full max-w-md p-6"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                  <Trash2 className="w-5 h-5 text-red-600" />
                </div>
                <h3 className="font-display font-bold text-lg text-ink-900">Delete this report?</h3>
              </div>
              <p className="text-sm text-ink-600 mb-6">
                This will permanently delete the compliance report for{' '}
                <strong>{report?.document_metadata?.filename || report?.document_filename}</strong>.
                This action cannot be undone.
              </p>
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deletingReport}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-ink-700 bg-clay-100 hover:bg-clay-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteReport}
                  disabled={deletingReport}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-red-600 hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {deletingReport ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                  {deletingReport ? 'Deleting...' : 'Delete report'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating RAG chat panel — ask questions about the source PDF */}
      <ReportChat
        reportId={reportId}
        documentFilename={report?.document_metadata?.filename}
        pdfUrl={pdfUrl}
      />
    </div>
  )
}

export default ReportDetail
