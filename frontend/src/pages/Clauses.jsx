import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckSquare, 
  Filter, 
  Search,
  ChevronDown,
  ChevronRight,
  Shield,
  FileText,
  Tag,
  Loader2
} from 'lucide-react'
import { getClauses, getClauseDetail } from '../lib/api'

const Clauses = () => {
  const [clauses, setClauses] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedFramework, setSelectedFramework] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedClause, setExpandedClause] = useState(null)
  const [clauseDetail, setClauseDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  
  useEffect(() => {
    loadClauses()
  }, [selectedFramework])
  
  const loadClauses = async () => {
    setLoading(true)
    try {
      const framework = selectedFramework === 'all' ? null : selectedFramework
      const data = await getClauses(framework)
      setClauses(data.clauses || [])
    } catch (error) {
      console.error('Error loading clauses:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const loadClauseDetail = async (clauseId) => {
    setLoadingDetail(true)
    try {
      const data = await getClauseDetail(clauseId)
      setClauseDetail(data)
    } catch (error) {
      console.error('Error loading clause detail:', error)
    } finally {
      setLoadingDetail(false)
    }
  }
  
  const handleClauseClick = (clauseId) => {
    if (expandedClause === clauseId) {
      setExpandedClause(null)
      setClauseDetail(null)
    } else {
      setExpandedClause(clauseId)
      loadClauseDetail(clauseId)
    }
  }
  
  const filteredClauses = clauses.filter(clause =>
    clause.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    clause.clause_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    clause.description.toLowerCase().includes(searchQuery.toLowerCase())
  )
  
  const frameworkCounts = {
    all: clauses.length,
    GRI: clauses.filter(c => c.framework === 'GRI').length,
    BRSR: clauses.filter(c => c.framework === 'BRSR').length,
    SASB: clauses.filter(c => c.framework === 'SASB').length,
    TCFD: clauses.filter(c => c.framework === 'TCFD').length,
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
              ESG Clauses
            </h1>
            <p className="text-lg text-ink-600">
              Browse and explore ESG compliance clauses from major frameworks
            </p>
          </div>
          
          {/* Filters */}
          <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6 mb-8">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-ink-400" />
                <input
                  type="text"
                  placeholder="Search clauses..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 bg-clay-50 border border-ink-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-forest-500 focus:border-transparent"
                />
              </div>
              
              {/* Framework Filter */}
              <div className="flex items-center space-x-2">
                {['all', 'GRI', 'BRSR', 'SASB', 'TCFD'].map((framework) => (
                  <button
                    key={framework}
                    onClick={() => setSelectedFramework(framework)}
                    className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${
                      selectedFramework === framework
                        ? 'bg-forest-600 text-white shadow-lg'
                        : 'bg-clay-100 text-ink-700 hover:bg-clay-200'
                    }`}
                  >
                    {framework.toUpperCase()}
                    <span className="ml-2 text-xs opacity-75">
                      ({frameworkCounts[framework]})
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
          
          {/* Clauses List */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-forest-600 animate-spin" />
            </div>
          ) : filteredClauses.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 text-center">
              <CheckSquare className="w-16 h-16 text-ink-300 mx-auto mb-4" />
              <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                No clauses found
              </h3>
              <p className="text-ink-600">
                Try adjusting your search or filter criteria
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredClauses.map((clause, index) => (
                <motion.div
                  key={clause.clause_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.02 }}
                  className="bg-white rounded-xl shadow-lg border border-ink-200 overflow-hidden hover:border-forest-300 transition-all duration-300"
                >
                  {/* Clause Header */}
                  <button
                    onClick={() => handleClauseClick(clause.clause_id)}
                    className="w-full p-6 flex items-center justify-between hover:bg-clay-50/50 transition-colors"
                  >
                    <div className="flex items-start space-x-4 flex-1 text-left">
                      <div className="w-10 h-10 bg-forest-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                        <CheckSquare className="w-5 h-5 text-forest-600" />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-3 mb-2">
                          <span className="px-3 py-1 bg-forest-100 text-forest-700 text-xs font-semibold rounded-full">
                            {clause.framework}
                          </span>
                          {clause.mandatory && (
                            <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-semibold rounded-full">
                              MANDATORY
                            </span>
                          )}
                        </div>
                        
                        <h3 className="font-display text-lg font-semibold text-ink-900 mb-1">
                          {clause.clause_id}
                        </h3>
                        
                        <p className="text-sm text-ink-700 font-medium mb-2">
                          {clause.title}
                        </p>
                        
                        <p className="text-sm text-ink-600 line-clamp-2">
                          {clause.description}
                        </p>
                      </div>
                    </div>
                    
                    <div className="ml-4">
                      {expandedClause === clause.clause_id ? (
                        <ChevronDown className="w-6 h-6 text-ink-400" />
                      ) : (
                        <ChevronRight className="w-6 h-6 text-ink-400" />
                      )}
                    </div>
                  </button>
                  
                  {/* Clause Detail */}
                  <AnimatePresence>
                    {expandedClause === clause.clause_id && (
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
                            {/* Full Description */}
                            <div>
                              <h4 className="font-semibold text-ink-900 mb-2 flex items-center">
                                <FileText className="w-4 h-4 mr-2 text-forest-600" />
                                Full Description
                              </h4>
                              <p className="text-sm text-ink-600 leading-relaxed">
                                {clauseDetail.description}
                              </p>
                            </div>
                            
                            {/* Evidence Types */}
                            <div>
                              <h4 className="font-semibold text-ink-900 mb-2 flex items-center">
                                <Shield className="w-4 h-4 mr-2 text-forest-600" />
                                Required Evidence Types
                              </h4>
                              <div className="flex flex-wrap gap-2">
                                {clauseDetail.evidence_types.map((type) => (
                                  <span
                                    key={type}
                                    className="px-3 py-1 bg-clay-100 text-ink-700 text-xs font-medium rounded-full"
                                  >
                                    {type}
                                  </span>
                                ))}
                              </div>
                            </div>
                            
                            {/* Keywords */}
                            {clauseDetail.keywords && clauseDetail.keywords.length > 0 && (
                              <div>
                                <h4 className="font-semibold text-ink-900 mb-2 flex items-center">
                                  <Tag className="w-4 h-4 mr-2 text-forest-600" />
                                  Keywords
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                  {clauseDetail.keywords.map((keyword, idx) => (
                                    <span
                                      key={idx}
                                      className="px-3 py-1 bg-forest-50 text-forest-700 text-xs font-medium rounded-full"
                                    >
                                      {keyword}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Validation Rules */}
                            {clauseDetail.validation_rules && clauseDetail.validation_rules.length > 0 && (
                              <div>
                                <h4 className="font-semibold text-ink-900 mb-3">
                                  Validation Rules ({clauseDetail.validation_rules.length})
                                </h4>
                                <div className="space-y-2">
                                  {clauseDetail.validation_rules.map((rule) => (
                                    <div
                                      key={rule.rule_id}
                                      className="p-3 bg-clay-50 rounded-lg border border-ink-200"
                                    >
                                      <div className="flex items-center justify-between mb-1">
                                        <span className="text-xs font-mono text-ink-600">
                                          {rule.rule_id}
                                        </span>
                                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                                          rule.mandatory
                                            ? 'bg-red-100 text-red-700'
                                            : 'bg-blue-100 text-blue-700'
                                        }`}>
                                          {rule.mandatory ? 'Mandatory' : 'Optional'}
                                        </span>
                                      </div>
                                      <p className="text-sm text-ink-700">
                                        <span className="font-medium">{rule.rule_type}:</span> {rule.description}
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
          )}
          
          {/* Summary Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            {Object.entries(frameworkCounts).filter(([key]) => key !== 'all').map(([framework, count]) => (
              <div
                key={framework}
                className="p-4 bg-white rounded-xl border border-ink-200 text-center"
              >
                <div className="text-2xl font-display font-bold text-forest-600 mb-1">
                  {count}
                </div>
                <div className="text-sm text-ink-600 font-medium">
                  {framework} Clauses
                </div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

export default Clauses
