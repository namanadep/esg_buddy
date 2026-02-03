import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Upload as UploadIcon, 
  FileText, 
  CheckCircle2,
  AlertCircle,
  Loader2,
  X
} from 'lucide-react'
import { uploadDocument } from '../lib/api'

const Upload = () => {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  
  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }
  
  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile)
        setError(null)
      } else {
        setError('Please upload a PDF file')
      }
    }
  }
  
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile)
        setError(null)
      } else {
        setError('Please upload a PDF file')
      }
    }
  }
  
  const handleUpload = async () => {
    if (!file) return
    
    setUploading(true)
    setError(null)
    setProgress(0)
    
    try {
      const response = await uploadDocument(file, (percent) => {
        setProgress(percent)
      })
      
      setResult(response)
      
      // Redirect to documents page after success
      setTimeout(() => {
        navigate('/documents')
      }, 2000)
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }
  
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }
  
  return (
    <div className="min-h-[calc(100vh-80px)] py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Header */}
          <div className="mb-12">
            <h1 className="font-display text-4xl font-bold text-ink-900 mb-4">
              Upload Document
            </h1>
            <p className="text-lg text-ink-600">
              Upload your ESG report or compliance document for AI-powered analysis
            </p>
          </div>
          
          {/* Upload Area */}
          <div className="bg-white rounded-3xl shadow-lg border border-ink-200 overflow-hidden">
            <div className="p-8">
              {!file ? (
                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  className={`relative border-2 border-dashed rounded-2xl p-12 transition-all duration-300 ${
                    dragActive
                      ? 'border-forest-500 bg-forest-50'
                      : 'border-ink-300 hover:border-forest-400 hover:bg-clay-50/50'
                  }`}
                >
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  
                  <div className="text-center">
                    <div className="w-20 h-20 gradient-forest rounded-2xl flex items-center justify-center mx-auto mb-6">
                      <UploadIcon className="w-10 h-10 text-white" strokeWidth={2} />
                    </div>
                    
                    <h3 className="font-display text-2xl font-semibold text-ink-900 mb-2">
                      Drop your PDF here
                    </h3>
                    
                    <p className="text-ink-600 mb-4">
                      or click to browse
                    </p>
                    
                    <p className="text-sm text-ink-500">
                      Supports PDF files up to 50MB
                    </p>
                  </div>
                </div>
              ) : (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="space-y-6"
                >
                  {/* File Preview */}
                  <div className="flex items-center justify-between p-6 bg-clay-50 rounded-xl border border-ink-200">
                    <div className="flex items-center space-x-4">
                      <div className="w-14 h-14 bg-forest-100 rounded-lg flex items-center justify-center">
                        <FileText className="w-7 h-7 text-forest-600" />
                      </div>
                      <div>
                        <div className="font-semibold text-ink-900">
                          {file.name}
                        </div>
                        <div className="text-sm text-ink-500">
                          {formatFileSize(file.size)}
                        </div>
                      </div>
                    </div>
                    
                    {!uploading && !result && (
                      <button
                        onClick={() => setFile(null)}
                        className="p-2 hover:bg-white rounded-lg transition-colors"
                      >
                        <X className="w-5 h-5 text-ink-500" />
                      </button>
                    )}
                  </div>
                  
                  {/* Upload Progress */}
                  {uploading && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-ink-600 font-medium">
                          Uploading and processing...
                        </span>
                        <span className="text-ink-700 font-semibold">
                          {progress}%
                        </span>
                      </div>
                      <div className="h-3 bg-clay-100 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${progress}%` }}
                          className="h-full gradient-forest"
                        />
                      </div>
                    </div>
                  )}
                  
                  {/* Success Message */}
                  {result && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-start space-x-3 p-4 bg-green-50 border border-green-200 rounded-xl"
                    >
                      <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <div className="font-semibold text-green-900 mb-1">
                          Upload Successful!
                        </div>
                        <div className="text-sm text-green-700">
                          Created {result.chunks_created} chunks. Redirecting...
                        </div>
                      </div>
                    </motion.div>
                  )}
                  
                  {/* Error Message */}
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-start space-x-3 p-4 bg-red-50 border border-red-200 rounded-xl"
                    >
                      <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-red-700">
                        {error}
                      </div>
                    </motion.div>
                  )}
                  
                  {/* Upload Button */}
                  {!uploading && !result && (
                    <button
                      onClick={handleUpload}
                      disabled={!file}
                      className="w-full py-4 gradient-forest text-white rounded-xl font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                      <span className="flex items-center justify-center">
                        {uploading ? (
                          <>
                            <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                            Processing...
                          </>
                        ) : (
                          <>
                            <UploadIcon className="w-5 h-5 mr-2" />
                            Upload & Process
                          </>
                        )}
                      </span>
                    </button>
                  )}
                </motion.div>
              )}
            </div>
          </div>
          
          {/* Info Cards */}
          <div className="grid md:grid-cols-3 gap-6 mt-8">
            {[
              {
                title: 'Processing',
                description: 'Document is chunked into semantic segments for analysis'
              },
              {
                title: 'Embedding',
                description: 'AI generates vector embeddings for semantic search'
              },
              {
                title: 'Ready',
                description: 'Document is ready for compliance evaluation'
              }
            ].map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + index * 0.1 }}
                className="p-6 bg-white/70 rounded-xl border border-ink-200"
              >
                <div className="w-8 h-8 gradient-forest rounded-lg flex items-center justify-center mb-3">
                  <span className="text-white font-bold text-sm">
                    {index + 1}
                  </span>
                </div>
                <h3 className="font-semibold text-ink-900 mb-2">
                  {step.title}
                </h3>
                <p className="text-sm text-ink-600">
                  {step.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Upload
