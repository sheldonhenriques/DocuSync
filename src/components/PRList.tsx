'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'

interface PRData {
  id: number
  title: string
  author: string
  avatar: string
  repository: string
  branch: string
  status: 'pending' | 'approved' | 'rejected'
  createdAt: string
  filesChanged: number
  hasDocumentation: boolean
  description: string
}

interface PRListProps {
  selectedRepo: string | null
  onViewDiff: (pr: PRData) => void
}

export default function PRList({ selectedRepo, onViewDiff }: PRListProps) {
  const { githubToken } = useAuth()
  const [prs, setPRs] = useState<PRData[]>([])
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all')

  useEffect(() => {
    const fetchPRs = async () => {
      if (!selectedRepo || !githubToken) return

      try {
        const res = await fetch(`/api/github/prs?repo=${selectedRepo}`, {
          headers: {
            Authorization: `Bearer ${githubToken}`,
          },
        })

        if (!res.ok) {
          console.error('Failed to fetch PRs')
          return
        }

        const data = await res.json()
        setPRs(data)
      } catch (error) {
        console.error('Error fetching PRs:', error)
      }
    }

    fetchPRs()
  }, [selectedRepo, githubToken])

  const filteredPRs = prs.filter(pr => filter === 'all' || pr.status === filter)

  const getStatusBadge = (status: PRData['status']) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      approved: 'bg-green-100 text-green-800 border-green-200',
      rejected: 'bg-red-100 text-red-800 border-red-200',
    }

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md">
      <div className="p-6 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">Pull Requests</h2>
          <div className="flex gap-2">
            {(['all', 'pending', 'approved', 'rejected'] as const).map((filterOption) => (
              <button
                key={filterOption}
                onClick={() => setFilter(filterOption)}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                  filter === filterOption
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="divide-y divide-gray-200">
        {filteredPRs.map((pr) => (
          <div key={pr.id} className="p-6 hover:bg-gray-50 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <img
                    src={pr.avatar}
                    alt={pr.author}
                    className="w-8 h-8 rounded-full"
                  />
                  <div>
                    <h3 className="font-medium text-gray-900">{pr.title}</h3>
                    <p className="text-sm text-gray-600">
                      {pr.repository} • {pr.branch} • by {pr.author}
                    </p>
                  </div>
                </div>

                <p className="text-sm text-gray-700 mb-3">{pr.description}</p>

                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <span>{pr.filesChanged} files changed</span>
                  <span>{new Date(pr.createdAt).toLocaleString()}</span>
                  {pr.hasDocumentation && (
                    <span className="flex items-center gap-1 text-blue-600">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Documentation available
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3 ml-4">
                {getStatusBadge(pr.status)}
                <button
                  onClick={() => onViewDiff(pr)}
                  className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors"
                >
                  View Documentation
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredPRs.length === 0 && (
        <div className="p-12 text-center">
          <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p className="text-gray-600">No pull requests found for the selected filter.</p>
        </div>
      )}
    </div>
  )
}

// 'use client'

// import { useState } from 'react'

// interface PRData {
//   id: number
//   title: string
//   author: string
//   avatar: string
//   repository: string
//   branch: string
//   status: 'pending' | 'approved' | 'rejected'
//   createdAt: string
//   filesChanged: number
//   hasDocumentation: boolean
//   description: string
// }

// interface PRListProps {
//   onViewDiff: (pr: PRData) => void
// }

// const mockPRs: PRData[] = [
//   {
//     id: 1,
//     title: "Add user authentication middleware",
//     author: "john-doe",
//     avatar: "https://github.com/github.png",
//     repository: "docusync/backend",
//     branch: "feature/auth-middleware",
//     status: "pending",
//     createdAt: "2 hours ago",
//     filesChanged: 5,
//     hasDocumentation: true,
//     description: "Implements JWT-based authentication middleware for protecting API routes"
//   },
//   {
//     id: 2,
//     title: "Refactor database connection logic",
//     author: "jane-smith",
//     avatar: "https://github.com/github.png",
//     repository: "docusync/backend",
//     branch: "refactor/db-connection",
//     status: "pending",
//     createdAt: "4 hours ago",
//     filesChanged: 3,
//     hasDocumentation: true,
//     description: "Optimizes database connection pooling and error handling"
//   },
//   {
//     id: 3,
//     title: "Update React components to use hooks",
//     author: "alex-dev",
//     avatar: "https://github.com/github.png",
//     repository: "docusync/frontend",
//     branch: "feature/hooks-migration",
//     status: "approved",
//     createdAt: "1 day ago",
//     filesChanged: 12,
//     hasDocumentation: false,
//     description: "Migrates class components to functional components with React hooks"
//   }
// ]

// export default function PRList({ onViewDiff }: PRListProps) {
//   const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all')

//   const filteredPRs = mockPRs.filter(pr => filter === 'all' || pr.status === filter)

//   const getStatusBadge = (status: PRData['status']) => {
//     const styles = {
//       pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
//       approved: 'bg-green-100 text-green-800 border-green-200',
//       rejected: 'bg-red-100 text-red-800 border-red-200'
//     }
    
//     return (
//       <span className={`px-2 py-1 text-xs font-medium rounded-full border ${styles[status]}`}>
//         {status.charAt(0).toUpperCase() + status.slice(1)}
//       </span>
//     )
//   }

//   return (
//     <div className="bg-white rounded-lg shadow-md">
//       <div className="p-6 border-b border-gray-200">
//         <div className="flex justify-between items-center">
//           <h2 className="text-xl font-semibold text-gray-900">Pull Requests</h2>
//           <div className="flex gap-2">
//             {(['all', 'pending', 'approved', 'rejected'] as const).map((filterOption) => (
//               <button
//                 key={filterOption}
//                 onClick={() => setFilter(filterOption)}
//                 className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
//                   filter === filterOption
//                     ? 'bg-blue-100 text-blue-700'
//                     : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
//                 }`}
//               >
//                 {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
//               </button>
//             ))}
//           </div>
//         </div>
//       </div>

//       <div className="divide-y divide-gray-200">
//         {filteredPRs.map((pr) => (
//           <div key={pr.id} className="p-6 hover:bg-gray-50 transition-colors">
//             <div className="flex items-start justify-between">
//               <div className="flex-1">
//                 <div className="flex items-center gap-3 mb-2">
//                   <img
//                     src={pr.avatar}
//                     alt={pr.author}
//                     className="w-8 h-8 rounded-full"
//                   />
//                   <div>
//                     <h3 className="font-medium text-gray-900">{pr.title}</h3>
//                     <p className="text-sm text-gray-600">
//                       {pr.repository} • {pr.branch} • by {pr.author}
//                     </p>
//                   </div>
//                 </div>
                
//                 <p className="text-sm text-gray-700 mb-3">{pr.description}</p>
                
//                 <div className="flex items-center gap-4 text-sm text-gray-600">
//                   <span>{pr.filesChanged} files changed</span>
//                   <span>{pr.createdAt}</span>
//                   {pr.hasDocumentation && (
//                     <span className="flex items-center gap-1 text-blue-600">
//                       <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                         <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
//                       </svg>
//                       Documentation available
//                     </span>
//                   )}
//                 </div>
//               </div>
              
//               <div className="flex items-center gap-3 ml-4">
//                 {getStatusBadge(pr.status)}
//                 {pr.hasDocumentation && (
//                   <button
//                     onClick={() => onViewDiff(pr)}
//                     className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors"
//                   >
//                     View Documentation
//                   </button>
//                 )}
//               </div>
//             </div>
//           </div>
//         ))}
//       </div>
      
//       {filteredPRs.length === 0 && (
//         <div className="p-12 text-center">
//           <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
//           </svg>
//           <p className="text-gray-600">No pull requests found for the selected filter.</p>
//         </div>
//       )}
//     </div>
//   )
// }