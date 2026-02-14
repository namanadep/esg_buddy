import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
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
  Loader2
} from 'lucide-react'
import { getComplianceReport, getClauseEvaluationDetail } from '../lib/api'

const ReportDetail = () => {
  const { reportId } = useParams()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedClause, setExpandedClause] = useState(null)
  const [clauseDetail, setClauseDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [filterStatus, setFilterStatus] = useState('all')
  
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
      case 'inferred':
        return <Info className="w-5 h-5" />
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
      case 'inferred':
        return 'bg-blue-100 text-blue-700 border-blue-200'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }
  
  const filteredEvaluations = filterStatus === 'all' 
    ? report.evaluations 
    : report.evaluations.filter(e => e.final_status === filterStatus)
  
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
              
              <div className="text-right ml-6">
                <div className="flex items-center justify-end space-x-2 mb-1">
                  <TrendingUp className="w-6 h-6 text-forest-600" />
                  <span className="text-4xl font-display font-bold text-forest-600">
                    {Math.round(report.summary.compliance_rate * 100)}%
                  </span>
                </div>
                <div className="text-sm text-ink-500 font-medium">
                  Overall Compliance
                </div>
              </div>
            </div>
            
            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
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
                { key: 'inferred', label: 'Inferred', value: report.summary.inferred }
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
          
          {/* Filters */}
          <div className="bg-white rounded-xl shadow-lg border border-ink-200 p-4 mb-6">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-ink-700 mr-2">Filter by status:</span>
              {['all', 'supported', 'partial', 'not_supported', 'inferred'].map((status) => (
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
                        <span>{evaluation.retrieved_evidence?.length || 0} evidence chunks</span>
                        <span>•</span>
                        <span>Confidence: {Math.round(evaluation.final_confidence * 100)}%</span>
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
                          
                          {/* Evidence */}
                          <div>
                            <h4 className="font-semibold text-ink-900 mb-3 flex items-center">
                              <FileText className="w-4 h-4 mr-2 text-forest-600" />
                              Retrieved Evidence ({clauseDetail.retrieved_evidence.length})
                            </h4>
                            <div className="space-y-3">
                              {clauseDetail.retrieved_evidence.map((evidence) => (
                                <div
                                  key={evidence.chunk_id}
                                  className="p-4 bg-clay-50 rounded-xl border border-ink-200"
                                >
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
                                </div>
                              ))}
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
    </div>
  )
}

export default ReportDetail
