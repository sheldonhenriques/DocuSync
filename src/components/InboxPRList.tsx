'use client'

import { useState } from 'react'

interface PRData {
  id: number
  title: string
  description: string
  author: string
  repository: string
  branch: string
  status: 'requires-action' | 'in-progress' | 'completed' | 'error'
  timestamp: string
  hasDocumentation: boolean
}

interface InboxPRListProps {
  selectedRepo: string | null
  onViewDiff: (pr: PRData) => void
}

const mockPRsByRepo: Record<string, PRData[]> = {
  'ea-prod': [
    {
      id: 1,
      title: 'Schedule Twitter/LinkedIn post',
      description: 'Schedule post Using these URL(s), a post was generated for T...',
      author: 'john-doe',
      repository: 'EA Prod',
      branch: 'feature/social-scheduler',
      status: 'requires-action',
      timestamp: '03/17 1:02 AM',
      hasDocumentation: true
    },
    {
      id: 2,
      title: 'Add authentication middleware',
      description: 'JWT-based authentication middleware for API protection...',
      author: 'jane-smith',
      repository: 'EA Prod',
      branch: 'feature/auth-middleware',
      status: 'in-progress',
      timestamp: '03/16 1:04 AM',
      hasDocumentation: true
    },
    {
      id: 3,
      title: 'Database optimization updates',
      description: 'Optimize database queries for better performance...',
      author: 'alex-dev',
      repository: 'EA Prod',
      branch: 'feature/db-optimization',
      status: 'requires-action',
      timestamp: '03/16 1:03 AM',
      hasDocumentation: true
    }
  ],
  'social-media': [
    {
      id: 4,
      title: 'Social media API integration',
      description: 'Integrate with Twitter and LinkedIn APIs for posting...',
      author: 'sarah-dev',
      repository: 'Social Media',
      branch: 'feature/api-integration',
      status: 'requires-action',
      timestamp: '03/15 2:15 PM',
      hasDocumentation: true
    }
  ],
  'new-ea': [
    {
      id: 5,
      title: 'New platform architecture',
      description: 'Design and implement new EA platform architecture...',
      author: 'mike-arch',
      repository: 'New EA',
      branch: 'feature/platform-arch',
      status: 'completed',
      timestamp: '03/14 9:30 AM',
      hasDocumentation: false
    }
  ]
}

type FilterType = 'all' | 'requires-action' | 'in-progress' | 'completed' | 'error'

export default function InboxPRList({ selectedRepo, onViewDiff }: InboxPRListProps) {
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')

  const getStatusBadge = (status: PRData['status']) => {
    const styles = {
      'requires-action': 'bg-green-100 text-green-800 border-green-200',
      'in-progress': 'bg-blue-100 text-blue-800 border-blue-200',
      'completed': 'bg-gray-100 text-gray-800 border-gray-200',
      'error': 'bg-red-100 text-red-800 border-red-200'
    }

    const labels = {
      'requires-action': 'Requires Action',
      'in-progress': 'In Progress',
      'completed': 'Completed',
      'error': 'Error'
    }

    return (
      <span className={`px-3 py-1 text-xs font-semibold rounded-full border-2 ${styles[status]}`}>
        {labels[status]}
      </span>
    )
  }

  const getStatusIcon = (status: PRData['status']) => {
    switch (status) {
      case 'requires-action':
        return (
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
        )
      case 'in-progress':
        return (
          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
        )
      case 'completed':
        return (
          <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
        )
      case 'error':
        return (
          <div className="w-2 h-2 bg-red-500 rounded-full"></div>
        )
      default:
        return null
    }
  }

  const allPRs = selectedRepo ? (mockPRsByRepo[selectedRepo] || []) :
    Object.values(mockPRsByRepo).flat()

  const filteredPRs = allPRs.filter(pr =>
    activeFilter === 'all' || pr.status === activeFilter
  )

  const getStatusCount = (status: FilterType) => {
    if (status === 'all') return allPRs.length
    return allPRs.filter(pr => pr.status === status).length
  }

  return (
    <div className="flex-1 flex flex-col bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {selectedRepo ? mockPRsByRepo[selectedRepo]?.[0]?.repository || 'Repository' : 'All Repositories'}
            </h1>
            <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
              <span>Social Media</span>
              <span>›</span>
              <span>Documentation Tasks</span>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="px-6 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-6">
          {([
            { key: 'all', label: 'All', icon: '📁' },
            { key: 'requires-action', label: 'Requires Action', icon: '⚠️' },
            { key: 'in-progress', label: 'In Progress', icon: '🔄' },
            { key: 'completed', label: 'Completed', icon: '✅' },
            { key: 'error', label: 'Error', icon: '❌' }
          ] as const).map((filter) => (
            <button
              key={filter.key}
              onClick={() => setActiveFilter(filter.key)}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-colors text-sm ${activeFilter === filter.key
                  ? 'bg-white text-gray-900 font-semibold shadow-sm border border-gray-200'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-white'
                }`}
            >
              <span className="text-xl">{filter.icon}</span>
              <span className="tracking-tight">{filter.label}</span>
              <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                {getStatusCount(filter.key)}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* PR List */}
      <div className="flex-1 overflow-auto">
        {filteredPRs.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="text-gray-400 text-4xl mb-2">📭</div>
              <p className="text-gray-500">No tasks found</p>
              <p className="text-sm text-gray-400 mt-1">
                {selectedRepo ? 'No tasks in this repository' : 'Select a repository to view tasks'}
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredPRs.map((pr) => (
              <div
                key={pr.id}
                className="px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer"
                onClick={() => pr.hasDocumentation && onViewDiff(pr)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    {getStatusIcon(pr.status)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-900 truncate">{pr.title}</h3>
                        <span className="text-xs text-gray-500">#{pr.id}</span>
                      </div>
                      <p className="text-sm text-gray-600 truncate mb-2">{pr.description}</p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{pr.author}</span>
                        <span>•</span>
                        <span>{pr.branch}</span>
                        {pr.hasDocumentation && (
                          <>
                            <span>•</span>
                            <span className="text-blue-600">Documentation ready</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 ml-4">
                    {getStatusBadge(pr.status)}
                    <div className="text-right">
                      <div className="text-xs text-gray-500">{pr.timestamp}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}