
'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import Sidebar from '@/components/Sidebar'
import InboxPRList from '@/components/InboxPRList'
import DiffModal from '@/components/DiffModal'

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

export default function Home() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [selectedRepo, setSelectedRepo] = useState<string | null>('ea-prod')
  const [selectedPR, setSelectedPR] = useState<PRData | null>(null)
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  const handleSelectRepo = (repoId: string) => {
    setSelectedRepo(repoId)
  }

  const handleViewDiff = (pr: PRData) => {
    setSelectedPR(pr)
    setIsDiffModalOpen(true)
  }

  const handleCloseDiff = () => {
    setIsDiffModalOpen(false)
    setSelectedPR(null)
  }

  const handleApprove = () => {
    console.log('Approving documentation for PR:', selectedPR?.id)
    // TODO: Implement approval logic
    handleCloseDiff()
  }

  const handleEdit = () => {
    console.log('Editing documentation for PR:', selectedPR?.id)
    // TODO: Implement edit logic
  }

  const handleDiscard = () => {
    console.log('Discarding documentation for PR:', selectedPR?.id)
    // TODO: Implement discard logic
    handleCloseDiff()
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="h-screen flex bg-gray-50">
      <Sidebar selectedRepo={selectedRepo} onSelectRepo={handleSelectRepo} />
      
      <InboxPRList selectedRepo={selectedRepo} onViewDiff={handleViewDiff} />

      <DiffModal
        isOpen={isDiffModalOpen}
        onClose={handleCloseDiff}
        prData={selectedPR}
        onApprove={handleApprove}
        onEdit={handleEdit}
        onDiscard={handleDiscard}
      />
    </div>
  )
}
