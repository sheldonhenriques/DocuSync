'use client'

import { useState } from 'react'

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

const mockDocumentationDiff = {
  original: `# Authentication Middleware

## Overview
Basic authentication for API routes.

## Usage
\`\`\`javascript
app.use(auth);
\`\`\`

## Parameters
- None`,
  
  proposed: `# Authentication Middleware

## Overview
JWT-based authentication middleware that provides secure access control for API routes. This middleware validates JSON Web Tokens and ensures only authenticated users can access protected endpoints.

## Features
- JWT token validation
- Automatic token refresh
- Role-based access control
- Request rate limiting
- Detailed error logging

## Usage
\`\`\`javascript
import { authMiddleware } from './middleware/auth';

// Apply to all routes
app.use(authMiddleware);

// Apply to specific routes
app.use('/api/protected', authMiddleware);

// With role-based access
app.use('/api/admin', authMiddleware.requireRole('admin'));
\`\`\`

## Configuration
\`\`\`javascript
const authConfig = {
  jwtSecret: process.env.JWT_SECRET,
  tokenExpiry: '24h',
  refreshThreshold: '2h',
  rateLimitWindow: 15 * 60 * 1000, // 15 minutes
  rateLimitMax: 100 // requests per window
};
\`\`\`

## Parameters
- \`req\`: Express request object
- \`res\`: Express response object  
- \`next\`: Express next function

## Returns
- Calls \`next()\` on successful authentication
- Returns 401 error for invalid/missing tokens
- Returns 403 error for insufficient permissions

## Error Handling
The middleware handles various authentication errors:
- \`INVALID_TOKEN\`: Token is malformed or expired
- \`MISSING_TOKEN\`: No token provided in request
- \`INSUFFICIENT_PERMISSIONS\`: User lacks required role`
}

export default function DiffModal({ isOpen, onClose, prData, onApprove, onEdit, onDiscard }: DiffModalProps) {
  const [activeTab, setActiveTab] = useState<'side-by-side' | 'unified'>('side-by-side')
  const [showLineNumbers, setShowLineNumbers] = useState(true)

  if (!isOpen || !prData) return null

  const renderSideBySideView = () => (
    <div className="grid grid-cols-2 gap-4 h-full">
      <div className="border rounded-lg overflow-hidden">
        <div className="bg-red-50 border-b border-red-200 px-4 py-2">
          <h4 className="text-sm font-medium text-red-800">Original Documentation</h4>
        </div>
        <div className="p-4 bg-white overflow-auto h-96">
          <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
            {mockDocumentationDiff.original}
          </pre>
        </div>
      </div>
      
      <div className="border rounded-lg overflow-hidden">
        <div className="bg-green-50 border-b border-green-200 px-4 py-2">
          <h4 className="text-sm font-medium text-green-800">Proposed Documentation</h4>
        </div>
        <div className="p-4 bg-white overflow-auto h-96">
          <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
            {mockDocumentationDiff.proposed}
          </pre>
        </div>
      </div>
    </div>
  )

  const renderUnifiedView = () => {
    const originalLines = mockDocumentationDiff.original.split('\n')
    const proposedLines = mockDocumentationDiff.proposed.split('\n')
    
    return (
      <div className="border rounded-lg overflow-hidden">
        <div className="bg-gray-50 border-b border-gray-200 px-4 py-2">
          <h4 className="text-sm font-medium text-gray-800">Unified Diff View</h4>
        </div>
        <div className="bg-white overflow-auto h-96">
          <div className="font-mono text-sm">
            {originalLines.map((line, index) => (
              <div key={`original-${index}`} className="flex">
                {showLineNumbers && (
                  <div className="w-12 text-gray-400 text-right pr-2 py-1 bg-red-50 border-r">
                    {index + 1}
                  </div>
                )}
                <div className="flex-1 px-2 py-1 bg-red-50 text-red-800">
                  <span className="text-red-600">- </span>{line}
                </div>
              </div>
            ))}
            {proposedLines.map((line, index) => (
              <div key={`proposed-${index}`} className="flex">
                {showLineNumbers && (
                  <div className="w-12 text-gray-400 text-right pr-2 py-1 bg-green-50 border-r">
                    {index + 1}
                  </div>
                )}
                <div className="flex-1 px-2 py-1 bg-green-50 text-green-800">
                  <span className="text-green-600">+ </span>{line}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl h-5/6 flex flex-col">
        {/* Header */}
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

        {/* Controls */}
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

        {/* Diff Content */}
        <div className="flex-1 p-6 overflow-hidden">
          {activeTab === 'side-by-side' ? renderSideBySideView() : renderUnifiedView()}
        </div>

        {/* Action Buttons */}
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