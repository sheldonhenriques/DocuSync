
'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import InboxPRList from '@/components/InboxPRList'
import DiffModal from '@/components/DiffModal'
import ConnectionTest from '@/components/ConnectionTest'

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
  const [selectedRepo, setSelectedRepo] = useState<string | null>('ea-prod')
  const [selectedPR, setSelectedPR] = useState<PRData | null>(null)
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false)

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

  return (
    <div className="h-screen flex bg-gray-50">
      <Sidebar selectedRepo={selectedRepo} onSelectRepo={handleSelectRepo} />
      
      <div className="flex-1 flex flex-col">
        <div className="p-4">
          <ConnectionTest />
        </div>
        <div className="flex-1">
          <InboxPRList selectedRepo={selectedRepo} onViewDiff={handleViewDiff} />
        </div>
      </div>

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
