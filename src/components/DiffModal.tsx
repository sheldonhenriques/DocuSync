'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { diffLines } from 'diff'

interface DiffModalProps {
  isOpen: boolean
  onClose: () => void
  prData: {
    id: number
    title: string
    author: string
    repository: string
    branch: string
  } | null
  onApprove: () => void
  onEdit: () => void
  onDiscard: () => void
}

export default function DiffModal({ isOpen, onClose, prData, onApprove, onEdit, onDiscard }: DiffModalProps) {
  const [activeTab, setActiveTab] = useState<'side-by-side' | 'unified'>('side-by-side')
  const [showLineNumbers, setShowLineNumbers] = useState(true)
  const [diff, setDiff] = useState<{ original: string, proposed: string }>({ original: '', proposed: '' })
  const { githubToken } = useAuth()

  useEffect(() => {
    const fetchDiff = async () => {
      if (!prData) return
      try {
        const res = await fetch(`/api/github/diff?repo=${prData.repository}&pr=${prData.id}`, {
          headers: {
            Authorization: `Bearer ${githubToken}`,
          }
        })
        const data = await res.json()
        setDiff(data)
      } catch (err) {
        console.error('Failed to fetch diff:', err)
      }
    }

    if (isOpen && prData) fetchDiff()
  }, [isOpen, prData, githubToken])

  const renderSideBySideView = () => {
    const changes = diffLines(diff.original, diff.proposed)

    let originalLine = 1
    let proposedLine = 1

    const left = []
    const right = []

    changes.forEach((part) => {
      const lines = part.value.split('\n')

      lines.forEach((line, index) => {
        if (line === '' && index === lines.length - 1) return

        if (!part.added) {
          left.push({
            line,
            type: part.removed ? 'removed' : 'common',
            lineNumber: originalLine++,
          })
        }

        if (!part.removed) {
          right.push({
            line,
            type: part.added ? 'added' : 'common',
            lineNumber: proposedLine++,
          })
        }
      })
    })

    return (
      <div className="grid grid-cols-2 gap-4 h-full">
        {/* Original (Left) */}
        <div className="border rounded-lg overflow-hidden">
          <div className="bg-red-50 border-b border-red-200 px-4 py-2">
            <h4 className="text-sm font-medium text-red-800">Original Documentation</h4>
          </div>
          <div className="p-4 bg-white overflow-auto h-96 font-mono text-sm">
            {left.map(({ line, type, lineNumber }, index) => (
              <div key={`left-${index}`} className="flex">
                {showLineNumbers && (
                  <div className="w-12 text-gray-400 text-right pr-2 py-1 border-r">
                    {lineNumber}
                  </div>
                )}
                <div
                  className={`flex-1 px-2 py-1 ${
                    type === 'removed'
                      ? 'bg-red-50 text-red-800'
                      : 'text-gray-800'
                  }`}
                >
                  {type === 'removed' ? '- ' : '  '}{line}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Proposed (Right) */}
        <div className="border rounded-lg overflow-hidden">
          <div className="bg-green-50 border-b border-green-200 px-4 py-2">
            <h4 className="text-sm font-medium text-green-800">Proposed Documentation</h4>
          </div>
          <div className="p-4 bg-white overflow-auto h-96 font-mono text-sm">
            {right.map(({ line, type, lineNumber }, index) => (
              <div key={`right-${index}`} className="flex">
                {showLineNumbers && (
                  <div className="w-12 text-gray-400 text-right pr-2 py-1 border-r">
                    {lineNumber}
                  </div>
                )}
                <div
                  className={`flex-1 px-2 py-1 ${
                    type === 'added'
                      ? 'bg-green-50 text-green-800'
                      : 'text-gray-800'
                  }`}
                >
                  {type === 'added' ? '+ ' : '  '}{line}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }
  

  const renderUnifiedView = () => {
    const changes = diffLines(diff.original, diff.proposed)
    let lineNumber = 1

    return (
      <div className="border rounded-lg overflow-hidden">
        <div className="bg-gray-50 border-b border-gray-200 px-4 py-2">
          <h4 className="text-sm font-medium text-gray-800">Unified Diff View</h4>
        </div>
        <div className="bg-white overflow-auto h-96">
          <div className="font-mono text-sm">
            {changes.flatMap((part, index) => {
              const lines = part.value.split('\n')
              return lines.map((line, i) => {
                if (!line && i === lines.length - 1) return null
                const isAdded = part.added
                const isRemoved = part.removed
                const prefix = isAdded ? '+ ' : isRemoved ? '- ' : '  '
                const lineClass = isAdded
                  ? 'bg-green-50 text-green-800'
                  : isRemoved
                  ? 'bg-red-50 text-red-800'
                  : 'bg-white text-gray-800'

                const renderedLine = (
                  <div key={`${index}-${i}`} className="flex">
                    {showLineNumbers && (
                      <div className="w-12 text-gray-400 text-right pr-2 py-1 border-r">
                        {lineNumber++}
                      </div>
                    )}
                    <div className={`flex-1 px-2 py-1 ${lineClass}`}>
                      {prefix}{line}
                    </div>
                  </div>
                )

                return renderedLine
              })
            })}
          </div>
        </div>
      </div>
    )
  }

  if (!isOpen || !prData) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl h-5/6 flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Documentation Review</h2>
            <p className="text-sm text-gray-600 mt-1">
              {prData.repository} • {prData.branch} • {prData.title}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-4">
            <div className="flex bg-white rounded-lg border">
              <button
                onClick={() => setActiveTab('side-by-side')}
                className={`px-3 py-2 text-sm font-medium rounded-l-lg transition-colors ${
                  activeTab === 'side-by-side'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Side by Side
              </button>
              <button
                onClick={() => setActiveTab('unified')}
                className={`px-3 py-2 text-sm font-medium rounded-r-lg transition-colors ${
                  activeTab === 'unified'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Unified
              </button>
            </div>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={showLineNumbers}
                onChange={(e) => setShowLineNumbers(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Show line numbers</span>
            </label>
          </div>

          <div className="text-sm text-gray-600">
            <span className="text-red-600">- Removed</span>
            <span className="mx-2">•</span>
            <span className="text-green-600">+ Added</span>
          </div>
        </div>

        <div className="flex-1 p-6 overflow-hidden">
          {activeTab === 'side-by-side' ? renderSideBySideView() : renderUnifiedView()}
        </div>

        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="text-sm text-gray-600">
            AI-generated documentation based on code changes in this PR
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onDiscard}
              className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-md transition-colors"
            >
              Discard
            </button>
            <button
              onClick={onEdit}
              className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors"
            >
              Edit Documentation
            </button>
            <button
              onClick={onApprove}
              className="px-6 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
            >
              Approve & Merge
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
