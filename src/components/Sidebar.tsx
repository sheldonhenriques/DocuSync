'use client'

import { useState } from 'react'

interface Repository {
  id: string
  name: string
  fullName: string
  icon: string
  color: string
}

const mockRepositories: Repository[] = [
  {
    id: 'ea-prod',
    name: 'EA Prod',
    fullName: 'docusync/ea-production',
    icon: 'E',
    color: 'bg-purple-500'
  },
  {
    id: 'social-media',
    name: 'Social Media',
    fullName: 'docusync/social-media-api',
    icon: 'S',
    color: 'bg-blue-500'
  },
  {
    id: 'new-ea',
    name: 'New EA',
    fullName: 'docusync/new-ea-platform',
    icon: 'N',
    color: 'bg-teal-500'
  }
]

interface SidebarProps {
  selectedRepo: string | null
  onSelectRepo: (repoId: string) => void
}

export default function Sidebar({ selectedRepo, onSelectRepo }: SidebarProps) {

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">DocuSync</h1>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 px-3 py-4">
        <div className="space-y-1">
          {mockRepositories.map((repo) => (
            <button
              key={repo.id}
              onClick={() => onSelectRepo(repo.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 text-left rounded-lg transition-colors ${
                selectedRepo === repo.id
                  ? 'bg-gray-100 text-gray-900'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <div className={`w-8 h-8 ${repo.color} rounded-lg flex items-center justify-center flex-shrink-0`}>
                <span className="text-white font-semibold text-sm">{repo.icon}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{repo.name}</div>
                <div className="text-xs text-gray-500 truncate">{repo.fullName}</div>
              </div>
              <div className="w-2 h-2 bg-gray-300 rounded-full flex-shrink-0"></div>
            </button>
          ))}
        </div>

        <button className="w-full flex items-center gap-3 px-3 py-2 mt-4 text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg transition-colors">
          <div className="w-8 h-8 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </div>
          <span className="font-medium">Add Repository</span>
        </button>
      </div>

      {/* Bottom Navigation */}
      <div className="p-3 border-t border-gray-200 space-y-1">
        <button className="w-full flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>Settings</span>
        </button>
        
        <button className="w-full flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-lg transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Documentation</span>
        </button>
      </div>

      {/* User Profile */}
      <div className="p-3 border-t border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center">
            <span className="text-white font-semibold text-sm">U</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 truncate">
              Developer
            </div>
            <div className="text-xs text-gray-500">Online</div>
          </div>
        </div>
      </div>
    </div>
  )
}