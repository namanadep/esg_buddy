import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  FileText, 
  Calendar, 
  File, 
  Trash2,
  Play,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Search
} from 'lucide-react'
import { listDocuments, deleteDocument, evaluateCompliance } from '../lib/api'

const Documents = () => {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [evaluating, setEvaluating] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFramework, setSelectedFramework] = useState('GRI')
  
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
  
  const handleEvaluate = async (documentId) => {
    setEvaluating(documentId)
    
    try {
      const result = await evaluateCompliance(documentId, selectedFramework)
      alert(`Evaluation started! Report ID: ${result.report_id}`)
      // Could navigate to the report detail page
    } catch (error) {
      console.error('Error evaluating document:', error)
      alert('Failed to start evaluation')
    } finally {
      setEvaluating(null)
    }
  }
  
  const filteredDocuments = documents.filter(doc =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )
  
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
          
          {/* Search and Filter */}
          <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6 mb-8">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-ink-400" />
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 bg-clay-50 border border-ink-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-forest-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <select
                  value={selectedFramework}
                  onChange={(e) => setSelectedFramework(e.target.value)}
                  className="w-full px-4 py-3 bg-clay-50 border border-ink-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-forest-500 focus:border-transparent"
                >
                  <option value="GRI">GRI Framework</option>
                  <option value="BRSR">BRSR Framework</option>
                  <option value="SASB">SASB Framework</option>
                  <option value="TCFD">TCFD Framework</option>
                </select>
              </div>
            </div>
          </div>
          
          {/* Documents List */}
          {filteredDocuments.length === 0 ? (
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
          ) : (
            <div className="grid gap-6">
              {filteredDocuments.map((doc, index) => (
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
                          <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                            {doc.filename}
                          </h3>
                          
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
                          onClick={() => handleEvaluate(doc.document_id)}
                          disabled={evaluating === doc.document_id}
                          className="p-3 bg-forest-50 text-forest-600 hover:bg-forest-100 rounded-xl transition-colors disabled:opacity-50"
                          title="Run Compliance Evaluation"
                        >
                          {evaluating === doc.document_id ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                          ) : (
                            <Play className="w-5 h-5" />
                          )}
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
                    
                    {evaluating === doc.document_id && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="mt-4 pt-4 border-t border-ink-100"
                      >
                        <div className="flex items-center space-x-3 text-sm">
                          <Loader2 className="w-4 h-4 text-forest-600 animate-spin" />
                          <span className="text-ink-600">
                            Running compliance evaluation against {selectedFramework}...
                          </span>
                        </div>
                      </motion.div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
          
          {/* Info Note */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-8 flex items-start space-x-3 p-4 bg-blue-50 border border-blue-200 rounded-xl"
          >
            <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-700">
              <strong>Tip:</strong> Click the play button to run a compliance evaluation. 
              Select your preferred ESG framework before evaluating.
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

export default Documents
