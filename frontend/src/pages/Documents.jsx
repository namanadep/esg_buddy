import React, { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  FileText, 
  Calendar, 
  File, 
  Trash2,
  Play,
  AlertCircle,
  Loader2,
  Search,
  XCircle,
  ChevronDown,
  SlidersHorizontal
} from 'lucide-react'
import { listDocuments, deleteDocument } from '../lib/api'
import LiveEvaluation from '../components/LiveEvaluation'

/** Guess framework from filename for list filtering / badges (no server field). */
function inferFrameworkFromFilename(filename) {
  const u = (filename || '').toUpperCase()
  if (u.includes('TCFD')) return 'TCFD'
  if (u.includes('SASB')) return 'SASB'
  if (u.includes('BRSR')) return 'BRSR'
  if (u.includes('GRI')) return 'GRI'
  return 'Other'
}

const FRAMEWORK_FILTER_OPTIONS = [
  { value: 'all', label: 'All documents' },
  { value: 'BRSR', label: 'BRSR' },
  { value: 'GRI', label: 'GRI' },
  { value: 'SASB', label: 'SASB' },
  { value: 'TCFD', label: 'TCFD' },
  { value: 'Other', label: 'Other / unspecified' },
]

const SORT_OPTIONS = [
  { value: 'date_desc', label: 'Upload date (newest first)' },
  { value: 'date_asc', label: 'Upload date (oldest first)' },
  { value: 'name_asc', label: 'Name (A–Z)' },
  { value: 'name_desc', label: 'Name (Z–A)' },
  { value: 'pages_desc', label: 'Page count (high to low)' },
  { value: 'pages_asc', label: 'Page count (low to high)' },
]

const selectFieldClass =
  'w-full appearance-none pl-4 pr-11 py-3 bg-white border border-ink-200 rounded-xl text-sm text-ink-900 ' +
  'shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 ' +
  'transition-colors cursor-pointer'

const Documents = () => {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [liveEval, setLiveEval] = useState(null) // { documentId, framework, filename }
  const [searchQuery, setSearchQuery] = useState('')
  const [frameworkFilter, setFrameworkFilter] = useState('all')
  const [sortBy, setSortBy] = useState('date_desc')
  const [selectedFramework, setSelectedFramework] = useState('BRSR')
  
  useEffect(() => {
    loadDocuments()
  }, [])
  
  const loadDocuments = async () => {
    try {
      const data = await listDocuments()
      setDocuments(data.documents || [])
    } catch (error) {
      console.error('Error loading documents:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleDelete = async (documentId) => {
    if (!confirm('Are you sure you want to delete this document?')) return
    
    try {
      await deleteDocument(documentId)
      await loadDocuments()
    } catch (error) {
      console.error('Error deleting document:', error)
      alert('Failed to delete document')
    }
  }
  
  const handleEvaluate = (documentId, filename) => {
    setLiveEval({
      documentId,
      framework: selectedFramework,
      filename,
    })
  }
  
  const filteredDocuments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    let list = documents.filter((doc) =>
      !q || doc.filename.toLowerCase().includes(q)
    )
    if (frameworkFilter !== 'all') {
      list = list.filter(
        (doc) => inferFrameworkFromFilename(doc.filename) === frameworkFilter
      )
    }
    const sorted = [...list]
    sorted.sort((a, b) => {
      switch (sortBy) {
        case 'name_asc':
          return a.filename.localeCompare(b.filename, undefined, { sensitivity: 'base' })
        case 'name_desc':
          return b.filename.localeCompare(a.filename, undefined, { sensitivity: 'base' })
        case 'date_asc':
          return new Date(a.upload_date) - new Date(b.upload_date)
        case 'date_desc':
          return new Date(b.upload_date) - new Date(a.upload_date)
        case 'pages_asc':
          return (a.page_count || 0) - (b.page_count || 0)
        case 'pages_desc':
          return (b.page_count || 0) - (a.page_count || 0)
        default:
          return 0
      }
    })
    return sorted
  }, [documents, searchQuery, frameworkFilter, sortBy])

  const filtersActive =
    frameworkFilter !== 'all' || sortBy !== 'date_desc' || searchQuery.trim() !== ''

  const clearListFilters = () => {
    setSearchQuery('')
    setFrameworkFilter('all')
    setSortBy('date_desc')
  }

  /** Match Reports list framework pill: forest accent */
  const frameworkBadgeClass = (fw) =>
    fw === 'Other'
      ? 'bg-clay-100 text-ink-700 border-clay-200'
      : 'bg-forest-100 text-forest-800 border-forest-200'

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
          <div className="flex items-center justify-between mb-12">
            <div>
              <h1 className="font-display text-4xl font-bold text-ink-900 mb-4">
                Documents
              </h1>
              <p className="text-lg text-ink-600">
                Manage your uploaded ESG documents
              </p>
            </div>
            
            <Link
              to="/upload"
              className="px-6 py-3 gradient-forest text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
            >
              Upload New
            </Link>
          </div>
          
          {/* Search, list filters, evaluation framework */}
          <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6 mb-8 space-y-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400 pointer-events-none" />
              <input
                type="text"
                placeholder="Search by file name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white border border-ink-200 rounded-xl text-sm text-ink-900 shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 transition-colors"
                aria-label="Search documents by name"
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
                Narrow and order the list. Framework tags come from words in each file name (GRI, BRSR, SASB, TCFD).
              </p>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="doc-framework-filter"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Filter by name hint
                  </label>
                  <div className="relative">
                    <select
                      id="doc-framework-filter"
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
                    htmlFor="doc-sort"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Sort by
                  </label>
                  <div className="relative">
                    <select
                      id="doc-sort"
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

            <div className="rounded-xl border border-forest-200/80 bg-forest-50/40 p-4 sm:p-5">
              <label
                htmlFor="doc-eval-framework"
                className="block text-xs font-medium uppercase tracking-wide text-forest-800 mb-1.5"
              >
                Framework for evaluation
              </label>
              <p className="text-xs text-ink-600 mb-3">
                Used when you press play on a document (separate from the list filters above).
              </p>
              <div className="relative max-w-md">
                <select
                  id="doc-eval-framework"
                  value={selectedFramework}
                  onChange={(e) => setSelectedFramework(e.target.value)}
                  className={selectFieldClass}
                >
                  <option value="GRI">GRI</option>
                  <option value="BRSR">BRSR</option>
                  <option value="SASB">SASB</option>
                  <option value="TCFD">TCFD</option>
                </select>
                <ChevronDown
                  className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400"
                  aria-hidden
                />
              </div>
            </div>

            {filtersActive && (
              <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-ink-200">
                <p className="text-sm text-ink-600">
                  Showing <span className="font-semibold text-ink-900">{filteredDocuments.length}</span> of{' '}
                  {documents.length} document{documents.length !== 1 ? 's' : ''}
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
          
          {/* Documents List */}
          {documents.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 text-center">
              <FileText className="w-16 h-16 text-ink-300 mx-auto mb-4" />
              <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                No documents found
              </h3>
              <p className="text-ink-600 mb-6">
                Upload your first ESG document to get started
              </p>
              <Link
                to="/upload"
                className="inline-flex items-center px-6 py-3 gradient-forest text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
              >
                Upload Document
              </Link>
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 text-center">
              <Search className="w-16 h-16 text-ink-300 mx-auto mb-4" />
              <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                No matches
              </h3>
              <p className="text-ink-600 mb-6">
                Nothing matches your search or filters. Try clearing them or broadening the file name hint.
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
              {filteredDocuments.map((doc, index) => {
                const fwHint = inferFrameworkFromFilename(doc.filename)
                return (
                <motion.div
                  key={doc.document_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-white rounded-2xl shadow-lg border border-ink-200 hover:border-forest-300 transition-all duration-300 overflow-hidden"
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4 flex-1">
                        <div className="w-14 h-14 bg-forest-100 rounded-xl flex items-center justify-center flex-shrink-0">
                          <FileText className="w-7 h-7 text-forest-600" />
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <h3 className="font-display text-xl font-semibold text-ink-900">
                              {doc.filename}
                            </h3>
                            <span
                              className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${frameworkBadgeClass(fwHint)}`}
                            >
                              {fwHint === 'Other' ? 'Unspecified' : fwHint}
                            </span>
                          </div>

                          <div className="flex flex-wrap items-center gap-4 text-sm text-ink-600">
                            <div className="flex items-center space-x-2">
                              <File className="w-4 h-4" />
                              <span>{doc.page_count} pages</span>
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <Calendar className="w-4 h-4" />
                              <span>
                                {new Date(doc.upload_date).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2 ml-4">
                        <button
                          onClick={() => handleEvaluate(doc.document_id, doc.filename)}
                          className="p-3 bg-forest-50 text-forest-600 hover:bg-forest-100 rounded-xl transition-colors"
                          title="Run Compliance Evaluation"
                        >
                          <Play className="w-5 h-5" />
                        </button>
                        
                        <button
                          onClick={() => handleDelete(doc.document_id)}
                          className="p-3 bg-red-50 text-red-600 hover:bg-red-100 rounded-xl transition-colors"
                          title="Delete Document"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                    
                  </div>
                </motion.div>
                )
              })}
            </div>
          )}
          
          {/* Info Note */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-8 flex items-start space-x-3 p-4 bg-forest-50/80 border border-forest-200/80 rounded-xl"
          >
            <AlertCircle className="w-5 h-5 text-forest-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-ink-700">
              <strong className="text-ink-900">Tip:</strong> Use <em>List filters</em> to find files; choose{' '}
              <em>Framework for evaluation</em> before running compliance with the play button.
            </div>
          </motion.div>
        </motion.div>
      </div>

      {/* Live streaming evaluation modal */}
      {liveEval && (
        <LiveEvaluation
          documentId={liveEval.documentId}
          framework={liveEval.framework}
          documentFilename={liveEval.filename}
          onClose={() => setLiveEval(null)}
        />
      )}
    </div>
  )
}

export default Documents
