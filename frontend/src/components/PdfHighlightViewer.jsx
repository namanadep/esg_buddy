import { useEffect, useRef } from 'react'
import { Worker, Viewer } from '@react-pdf-viewer/core'
import { searchPlugin } from '@react-pdf-viewer/search'
import '@react-pdf-viewer/core/lib/styles/index.css'
import '@react-pdf-viewer/search/lib/styles/index.css'

const PdfHighlightViewer = ({ fileUrl, pageNumber, searchText }) => {
  const searchPluginInstance = searchPlugin()
  const { highlight, clearHighlights, jumpToNextMatch } = searchPluginInstance

  // Trigger highlight after viewer renders
  const highlightTimerRef = useRef(null)

  const handleDocumentLoad = () => {
    if (!searchText) return
    clearHighlights()
    // Small delay to let the text layer render before searching
    highlightTimerRef.current = setTimeout(() => {
      highlight([{ keyword: searchText, matchCase: false }])
        .then(() => jumpToNextMatch())
        .catch(() => {})
    }, 600)
  }

  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current)
    }
  }, [])

  return (
    <Worker workerUrl="/pdf.worker.min.js">
      <div style={{ height: '560px' }} className="w-full overflow-hidden">
        <Viewer
          fileUrl={fileUrl}
          initialPage={pageNumber - 1}
          plugins={[searchPluginInstance]}
          onDocumentLoad={handleDocumentLoad}
          theme={{ theme: 'light' }}
          defaultScale={1.0}
        />
      </div>
    </Worker>
  )
}

export default PdfHighlightViewer
