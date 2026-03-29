import React, { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckSquare, 
  Search,
  ChevronDown,
  ChevronRight,
  Shield,
  FileText,
  Tag,
  Loader2,
  SlidersHorizontal,
  XCircle
} from 'lucide-react'
import { getClauses, getClauseDetail } from '../lib/api'

const FW_ORDER = { GRI: 0, BRSR: 1, SASB: 2, TCFD: 3 }

const REQUIREMENT_OPTIONS = [
  { value: 'all', label: 'All requirements' },
  { value: 'mandatory', label: 'Mandatory only' },
  { value: 'voluntary', label: 'Voluntary only' },
]

const SECTION_OPTIONS = [
  { value: 'all', label: 'Any section' },
  { value: 'assigned', label: 'Has section label' },
  { value: 'none', label: 'No section label' },
]

const ID_PATTERN_OPTIONS = [
  { value: 'all', label: 'Any clause ID' },
  { value: 'core', label: 'ID contains “Core”' },
]

const SORT_OPTIONS = [
  { value: 'framework_then_id', label: 'Framework, then clause ID (A–Z)' },
  { value: 'id_asc', label: 'Clause ID (A–Z)' },
  { value: 'id_desc', label: 'Clause ID (Z–A)' },
  { value: 'title_asc', label: 'Title (A–Z)' },
  { value: 'title_desc', label: 'Title (Z–A)' },
  { value: 'mandatory_first', label: 'Mandatory first' },
  { value: 'voluntary_first', label: 'Voluntary first' },
]

const selectFieldClass =
  'w-full appearance-none pl-4 pr-11 py-3 bg-white border border-ink-200 rounded-xl text-sm text-ink-900 ' +
  'shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 ' +
  'transition-colors cursor-pointer'

function clauseMandatory(c) {
  return c.mandatory !== false
}

function compareClauseIds(a, b) {
  return a.clause_id.localeCompare(b.clause_id, undefined, { sensitivity: 'base' })
}

function compareTitles(a, b) {
  return (a.title || '').localeCompare(b.title || '', undefined, { sensitivity: 'base' })
}

const Clauses = () => {
  const [allClauses, setAllClauses] = useState([])  // Store all clauses
  const [loading, setLoading] = useState(true)
  const [selectedFramework, setSelectedFramework] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [requirementFilter, setRequirementFilter] = useState('all')
  const [sectionFilter, setSectionFilter] = useState('all')
  const [idPatternFilter, setIdPatternFilter] = useState('all')
  const [sortBy, setSortBy] = useState('framework_then_id')
  const [expandedClause, setExpandedClause] = useState(null)
  const [clauseDetail, setClauseDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  
  // Load all clauses once on mount
  useEffect(() => {
    const loadAllClauses = async () => {
      setLoading(true)
      try {
        const data = await getClauses(null)  // null = fetch all frameworks
        setAllClauses(data.clauses || [])
      } catch (error) {
        console.error('Error loading clauses:', error)
      } finally {
        setLoading(false)
      }
    }
    loadAllClauses()
  }, [])
  
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
  
  const filteredClauses = useMemo(() => {
    let result =
      selectedFramework === 'all'
        ? allClauses
        : allClauses.filter(
            (c) => c.framework?.toUpperCase() === selectedFramework.toUpperCase()
          )

    const q = searchQuery.trim().toLowerCase()
    if (q) {
      result = result.filter(
        (clause) =>
          clause.title?.toLowerCase().includes(q) ||
          clause.clause_id?.toLowerCase().includes(q) ||
          clause.description?.toLowerCase().includes(q) ||
          clause.section?.toLowerCase().includes(q) ||
          (clause.evidence_types || []).some((t) => String(t).toLowerCase().includes(q))
      )
    }

    if (requirementFilter === 'mandatory') {
      result = result.filter((c) => clauseMandatory(c))
    } else if (requirementFilter === 'voluntary') {
      result = result.filter((c) => !clauseMandatory(c))
    }

    if (sectionFilter === 'assigned') {
      result = result.filter((c) => (c.section || '').trim().length > 0)
    } else if (sectionFilter === 'none') {
      result = result.filter((c) => !(c.section || '').trim())
    }

    if (idPatternFilter === 'core') {
      result = result.filter((c) => (c.clause_id || '').toLowerCase().includes('core'))
    }

    const sorted = [...result]
    sorted.sort((a, b) => {
      switch (sortBy) {
        case 'id_asc':
          return compareClauseIds(a, b)
        case 'id_desc':
          return compareClauseIds(b, a)
        case 'title_asc':
          return compareTitles(a, b)
        case 'title_desc':
          return compareTitles(b, a)
        case 'mandatory_first': {
          const ma = clauseMandatory(a) ? 0 : 1
          const mb = clauseMandatory(b) ? 0 : 1
          if (ma !== mb) return ma - mb
          return compareClauseIds(a, b)
        }
        case 'voluntary_first': {
          const va = clauseMandatory(a) ? 1 : 0
          const vb = clauseMandatory(b) ? 1 : 0
          if (va !== vb) return va - vb
          return compareClauseIds(a, b)
        }
        case 'framework_then_id':
        default: {
          const fa = FW_ORDER[a.framework] ?? 99
          const fb = FW_ORDER[b.framework] ?? 99
          if (fa !== fb) return fa - fb
          return compareClauseIds(a, b)
        }
      }
    })

    return sorted
  }, [
    allClauses,
    selectedFramework,
    searchQuery,
    requirementFilter,
    sectionFilter,
    idPatternFilter,
    sortBy,
  ])

  const filtersActive =
    requirementFilter !== 'all' ||
    sectionFilter !== 'all' ||
    idPatternFilter !== 'all' ||
    sortBy !== 'framework_then_id' ||
    searchQuery.trim() !== ''

  const clearListFilters = () => {
    setSearchQuery('')
    setRequirementFilter('all')
    setSectionFilter('all')
    setIdPatternFilter('all')
    setSortBy('framework_then_id')
  }
  
  const frameworkCounts = useMemo(
    () => ({
      all: allClauses.length,
      GRI: allClauses.filter((c) => c.framework === 'GRI').length,
      BRSR: allClauses.filter((c) => c.framework === 'BRSR').length,
      SASB: allClauses.filter((c) => c.framework === 'SASB').length,
      TCFD: allClauses.filter((c) => c.framework === 'TCFD').length,
    }),
    [allClauses]
  )
  
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
          
          {/* Search, framework, advanced filters */}
          <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-6 mb-8 space-y-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400 pointer-events-none" />
              <input
                type="text"
                placeholder="Search clauses (title, ID, description, section, evidence types)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white border border-ink-200 rounded-xl text-sm text-ink-900 shadow-sm hover:border-ink-300 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 transition-colors"
                aria-label="Search clauses"
              />
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-ink-600 mb-2">
                Framework
              </p>
              <div className="flex flex-wrap gap-2">
                {['all', 'GRI', 'BRSR', 'SASB', 'TCFD'].map((framework) => (
                  <button
                    key={framework}
                    type="button"
                    onClick={() => setSelectedFramework(framework)}
                    className={`px-4 py-2 rounded-xl font-medium text-sm transition-all duration-200 border ${
                      selectedFramework === framework
                        ? 'bg-forest-600 text-white border-forest-600 shadow-md'
                        : 'bg-clay-50 text-ink-700 border-ink-200 hover:bg-clay-100 hover:border-ink-300'
                    }`}
                  >
                    {framework === 'all' ? 'All' : framework}
                    <span
                      className={`ml-2 text-xs tabular-nums ${
                        selectedFramework === framework ? 'text-white/90' : 'text-ink-500'
                      }`}
                    >
                      ({frameworkCounts[framework]})
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-ink-100 bg-clay-50/60 p-4 sm:p-5 space-y-4">
              <div className="flex items-center gap-2 text-ink-800">
                <SlidersHorizontal className="w-4 h-4 text-forest-600 shrink-0" aria-hidden />
                <h2 className="font-display text-lg font-semibold text-ink-900">
                  Sort &amp; filter
                </h2>
              </div>
              <p className="text-xs text-ink-600 -mt-1">
                Refine the list below. Framework pills above limit which clauses are loaded into this view.
              </p>

              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label
                    htmlFor="clause-sort"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Sort by
                  </label>
                  <div className="relative">
                    <select
                      id="clause-sort"
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

                <div>
                  <label
                    htmlFor="clause-requirement"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Requirement
                  </label>
                  <div className="relative">
                    <select
                      id="clause-requirement"
                      value={requirementFilter}
                      onChange={(e) => setRequirementFilter(e.target.value)}
                      className={selectFieldClass}
                    >
                      {REQUIREMENT_OPTIONS.map((o) => (
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
                    htmlFor="clause-section"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Section label
                  </label>
                  <div className="relative">
                    <select
                      id="clause-section"
                      value={sectionFilter}
                      onChange={(e) => setSectionFilter(e.target.value)}
                      className={selectFieldClass}
                    >
                      {SECTION_OPTIONS.map((o) => (
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
                    htmlFor="clause-id-pattern"
                    className="block text-xs font-medium uppercase tracking-wide text-ink-600 mb-1.5"
                  >
                    Clause ID pattern
                  </label>
                  <div className="relative">
                    <select
                      id="clause-id-pattern"
                      value={idPatternFilter}
                      onChange={(e) => setIdPatternFilter(e.target.value)}
                      className={selectFieldClass}
                    >
                      {ID_PATTERN_OPTIONS.map((o) => (
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
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-ink-200">
                <p className="text-sm text-ink-600">
                  Showing{' '}
                  <span className="font-semibold text-ink-900 tabular-nums">{filteredClauses.length}</span>
                  {selectedFramework !== 'all' ? (
                    <>
                      {' '}
                      matching filters
                      {frameworkCounts[selectedFramework] != null && (
                        <>
                          {' '}
                          (of{' '}
                          <span className="font-semibold text-ink-900 tabular-nums">
                            {frameworkCounts[selectedFramework]}
                          </span>{' '}
                          in {selectedFramework})
                        </>
                      )}
                    </>
                  ) : (
                    allClauses.length > 0 && (
                      <>
                        {' '}
                        of <span className="font-semibold text-ink-900 tabular-nums">{allClauses.length}</span>
                      </>
                    )
                  )}
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
          
          {/* Clauses List */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-forest-600 animate-spin" />
            </div>
          ) : filteredClauses.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-lg border border-ink-200 p-12 text-center">
              <CheckSquare className="w-16 h-16 text-ink-300 mx-auto mb-4" />
              <h3 className="font-display text-xl font-semibold text-ink-900 mb-2">
                {allClauses.length === 0 ? 'No clauses loaded' : 'No matching clauses'}
              </h3>
              <p className="text-ink-600 mb-6">
                {allClauses.length === 0
                  ? 'Clauses will appear here after the backend finishes parsing standards.'
                  : 'Try another framework tab, clearing search, or resetting sort & filters.'}
              </p>
              {allClauses.length > 0 && filtersActive && (
                <button
                  type="button"
                  onClick={clearListFilters}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-forest-200 bg-forest-50 text-forest-900 font-medium text-sm hover:bg-forest-100 transition-colors"
                >
                  <XCircle className="w-4 h-4" aria-hidden />
                  Reset search &amp; filters
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4" key={selectedFramework}>
              {filteredClauses.map((clause, index) => (
                <motion.div
                  key={`${selectedFramework}-${clause.clause_id}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(index * 0.02, 0.3) }}
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
                          {clauseMandatory(clause) && (
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
                                            : 'bg-forest-50 text-forest-800 border border-forest-200'
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
