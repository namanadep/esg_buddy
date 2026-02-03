import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  BarChart3, 
  FileText, 
  Calendar,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  TrendingUp,
  Search,
  Loader2
} from 'lucide-react'

const Reports = () => {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  
  // Mock data for demonstration - replace with actual API call
  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setReports([
        {
          report_id: 'report_1',
          document_filename: 'annual_report_2023.pdf',
          framework: 'GRI',
          summary: {
            total_clauses: 45,
            supported: 32,
            partial: 8,
            not_supported: 3,
            inferred: 2,
            compliance_rate: 0.76,
            average_confidence: 0.82
          },
          generated_at: '2024-01-15T10:30:00'
        },
        {
          report_id: 'report_2',
          document_filename: 'esg_policy_2024.pdf',
          framework: 'BRSR',
          summary: {
            total_clauses: 38,
            supported: 28,
            partial: 6,
            not_supported: 4,
            inferred: 0,
            compliance_rate: 0.74,
            average_confidence: 0.79
          },
          generated_at: '2024-01-14T15:45:00'
        }
      ])
      setLoading(false)
    }, 500)
  }, [])
  
  const filteredReports = reports.filter(report =>
    report.document_filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    report.framework.toLowerCase().includes(searchQuery.toLowerCase())
  )
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'supported':
        return <CheckCircle2 className="w-4 h-4" />
      case 'partial':
        return <AlertTriangle className="w-4 h-4" />
      case 'not_supported':
        return <XCircle className="w-4 h-4" />
      case 'inferred':
        return <Info className="w-4 h-4" />
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
      case 'inferred':
        return 'bg-blue-100 text-blue-700'
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
          
          {/* Search */}
          <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6 mb-8">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-ink-400" />
              <input
                type="text"
                placeholder="Search reports..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-clay-50 border border-ink-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-forest-500 focus:border-transparent"
              />
            </div>
          </div>
          
          {/* Reports List */}
          {filteredReports.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 text-center">
              <BarChart3 className="w-16 h-16 text-ink-300 mx-auto mb-4" />
              <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                No reports found
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
                            <span className="text-3xl font-display font-bold text-forest-600">
                              {Math.round(report.summary.compliance_rate * 100)}%
                            </span>
                          </div>
                          <div className="text-sm text-ink-500 font-medium">
                            Compliance Rate
                          </div>
                        </div>
                      </div>
                      
                      {/* Summary Stats */}
                      <div className="grid grid-cols-4 gap-4">
                        {[
                          { key: 'supported', label: 'Supported', value: report.summary.supported },
                          { key: 'partial', label: 'Partial', value: report.summary.partial },
                          { key: 'not_supported', label: 'Not Supported', value: report.summary.not_supported },
                          { key: 'inferred', label: 'Inferred', value: report.summary.inferred }
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
