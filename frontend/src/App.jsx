import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Upload from './pages/Upload'
import Documents from './pages/Documents'
import Clauses from './pages/Clauses'
import Reports from './pages/Reports'
import ReportDetail from './pages/ReportDetail'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="upload" element={<Upload />} />
          <Route path="documents" element={<Documents />} />
          <Route path="clauses" element={<Clauses />} />
          <Route path="reports" element={<Reports />} />
          <Route path="reports/:reportId" element={<ReportDetail />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
