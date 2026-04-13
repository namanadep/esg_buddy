/* eslint-disable react/prop-types */
import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageCircle,
  X,
  Send,
  Sparkles,
  Loader2,
  ExternalLink,
  Bot,
  User,
  AlertCircle,
} from 'lucide-react'
import { chatWithReport } from '../lib/api'

const SUGGESTED_QUESTIONS = [
  'Does this report cover Scope 3 emissions?',
  'What climate risks does the company disclose?',
  'Are there any emissions reduction targets?',
  'Is there information about board diversity?',
]

const makeId = () =>
  typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`

/**
 * Floating RAG chat panel for the report detail page.
 * Lets the user ask questions against the source document of this specific report.
 */
const ReportChat = ({ reportId, documentFilename, pdfUrl }) => {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  // Reset history when switching reports
  useEffect(() => {
    setMessages([])
    setError(null)
  }, [reportId])

  useEffect(() => {
    const container = scrollRef.current
    if (!container) return
    const lastMsg = messages[messages.length - 1]
    // When a new assistant reply arrives, jump so its FIRST line sits near the top
    // of the chat viewport. For user messages or the loading indicator, pin to bottom
    // so the user can see what they just sent.
    if (!sending && lastMsg && lastMsg.role === 'assistant') {
      const el = container.querySelector(`[data-msg-id="${lastMsg.id}"]`)
      if (el) {
        const elRect = el.getBoundingClientRect()
        const containerRect = container.getBoundingClientRect()
        container.scrollTop += elRect.top - containerRect.top - 8
        return
      }
    }
    container.scrollTop = container.scrollHeight
  }, [messages, sending])

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus()
    }
  }, [open])

  const sendQuestion = async (questionText) => {
    const q = (questionText ?? input).trim()
    if (!q || sending) return

    setError(null)
    setInput('')
    const userMsg = { id: makeId(), role: 'user', content: q }
    setMessages((prev) => [...prev, userMsg])
    setSending(true)

    try {
      const data = await chatWithReport(reportId, q)
      const assistantMsg = {
        id: makeId(),
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Something went wrong'
      setError(detail)
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: 'assistant',
          content: `Sorry, I couldn't answer that. ${detail}`,
          error: true,
        },
      ])
    } finally {
      setSending(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    sendQuestion()
  }

  return (
    <>
      {/* Floating launcher button */}
      <AnimatePresence>
        {!open && (
          <motion.button
            key="launcher"
            type="button"
            onClick={() => setOpen(true)}
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 24 }}
            className="fixed bottom-6 right-6 z-40 gradient-forest text-white rounded-full shadow-xl px-5 py-3.5 flex items-center gap-2 hover:shadow-2xl transition-shadow"
            aria-label="Open chat with this report"
          >
            <div className="relative">
              <MessageCircle className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-amber-300 rounded-full ring-2 ring-forest-600 animate-pulse" />
            </div>
            <span className="font-semibold text-sm">Ask this report</span>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 260, damping: 26 }}
            className="fixed bottom-6 right-6 z-50 w-[min(96vw,440px)] h-[min(78vh,620px)] bg-white rounded-2xl shadow-2xl border border-ink-200 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="px-5 py-4 gradient-forest text-white flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-white/15 border border-white/20 flex items-center justify-center shrink-0">
                  <Sparkles className="w-4.5 h-4.5" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-display font-semibold text-base leading-tight">
                    Chat with this report
                  </h3>
                  {documentFilename && (
                    <p className="text-[11px] text-white/80 truncate">{documentFilename}</p>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg hover:bg-white/10 transition-colors shrink-0"
                aria-label="Close chat"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages */}
            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto overscroll-contain px-4 py-4 bg-clay-50/40 space-y-4"
            >
              {messages.length === 0 && (
                <div className="space-y-4">
                  <div className="flex items-start gap-2">
                    <div className="w-8 h-8 rounded-full bg-forest-100 border border-forest-200 flex items-center justify-center shrink-0">
                      <Bot className="w-4 h-4 text-forest-700" />
                    </div>
                    <div className="rounded-2xl rounded-tl-sm bg-white border border-ink-200 px-4 py-3 text-sm text-ink-800 leading-relaxed">
                      Hi! I&rsquo;ve indexed this report. Ask me anything and I&rsquo;ll answer using
                      the exact passages from the source PDF, with page citations.
                    </div>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-2 pl-10">
                      Try asking
                    </p>
                    <div className="pl-10 flex flex-col gap-2">
                      {SUGGESTED_QUESTIONS.map((q) => (
                        <button
                          key={q}
                          type="button"
                          onClick={() => sendQuestion(q)}
                          className="text-left text-xs px-3 py-2 rounded-xl bg-white border border-ink-200 hover:border-forest-400 hover:bg-forest-50 transition-colors text-ink-700"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} pdfUrl={pdfUrl} />
              ))}

              {sending && (
                <div className="flex items-start gap-2">
                  <div className="w-8 h-8 rounded-full bg-forest-100 border border-forest-200 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4 text-forest-700" />
                  </div>
                  <div className="rounded-2xl rounded-tl-sm bg-white border border-ink-200 px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <Loader2 className="w-3.5 h-3.5 text-forest-600 animate-spin" />
                      <span className="text-xs text-ink-500">Searching the report...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {error && !sending && (
              <div className="px-4 py-2 bg-red-50 border-t border-red-200 text-xs text-red-800 flex items-center gap-2">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{error}</span>
              </div>
            )}

            {/* Input */}
            <form
              onSubmit={handleSubmit}
              className="p-3 border-t border-ink-200 bg-white shrink-0 flex items-end gap-2"
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    sendQuestion()
                  }
                }}
                rows={1}
                placeholder="Ask about emissions, targets, risks..."
                disabled={sending}
                className="flex-1 resize-none px-3 py-2.5 rounded-xl border border-ink-200 bg-clay-50/50 text-sm text-ink-900 placeholder-ink-400 focus:outline-none focus:ring-2 focus:ring-forest-500/30 focus:border-forest-400 max-h-28 overscroll-contain disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="shrink-0 w-10 h-10 rounded-xl gradient-forest text-white flex items-center justify-center shadow-md hover:shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                aria-label="Send question"
              >
                {sending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

const MessageBubble = ({ message, pdfUrl }) => {
  const isUser = message.role === 'user'
  if (isUser) {
    return (
      <div data-msg-id={message.id} className="flex items-start gap-2 justify-end">
        <div className="rounded-2xl rounded-tr-sm bg-forest-600 text-white px-4 py-2.5 text-sm leading-relaxed max-w-[80%] whitespace-pre-wrap">
          {message.content}
        </div>
        <div className="w-8 h-8 rounded-full bg-ink-100 border border-ink-200 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-ink-600" />
        </div>
      </div>
    )
  }

  return (
    <div data-msg-id={message.id} className="flex items-start gap-2">
      <div className="w-8 h-8 rounded-full bg-forest-100 border border-forest-200 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-forest-700" />
      </div>
      <div className="max-w-[85%] space-y-2">
        <div
          className={`rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap border ${
            message.error
              ? 'bg-red-50 border-red-200 text-red-900'
              : 'bg-white border-ink-200 text-ink-800'
          }`}
        >
          {message.content}
        </div>
        {!!message.citations?.length && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-500">
              Sources ({message.citations.length})
            </p>
            <div className="flex flex-col gap-1.5">
              {message.citations.slice(0, 5).map((c) => {
                const href = pdfUrl ? `${pdfUrl}#page=${c.page_number}&zoom=page-width` : null
                const snippet = (c.text || '').replace(/\s+/g, ' ').trim().slice(0, 140)
                return (
                  <div
                    key={c.chunk_id}
                    className="rounded-lg border border-ink-200 bg-white px-3 py-2 text-[11px] text-ink-700"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-semibold text-ink-800">
                        Page {c.page_number}
                        {c.section ? ` • ${c.section}` : ''}
                      </span>
                      {href && (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-forest-700 hover:text-forest-900 font-semibold"
                        >
                          <ExternalLink className="w-3 h-3" />
                          Open
                        </a>
                      )}
                    </div>
                    <p className="text-ink-600 line-clamp-2 leading-snug">
                      &ldquo;{snippet}
                      {c.text && c.text.length > 140 ? '...' : ''}&rdquo;
                    </p>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ReportChat
