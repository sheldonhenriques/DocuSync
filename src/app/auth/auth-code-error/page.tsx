'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

function AuthErrorContent() {
  const searchParams = useSearchParams()
  const error = searchParams.get('error')
  const errorDescription = searchParams.get('error_description')

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Authentication Error</h1>
          <p className="text-gray-600 mb-4">
            There was an error during the authentication process.
          </p>
          
          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-3 mb-4">
              <p className="text-sm text-red-800">
                <strong>Error:</strong> {error}
              </p>
              {errorDescription && (
                <p className="text-sm text-red-800 mt-1">
                  <strong>Description:</strong> {errorDescription}
                </p>
              )}
            </div>
          )}
          
          <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
            <h3 className="text-sm font-semibold text-yellow-800 mb-2">Common issues:</h3>
            <ul className="text-sm text-yellow-700 text-left space-y-1">
              <li>• Check your Supabase environment variables in .env.local</li>
              <li>• Verify GitHub OAuth app configuration in Supabase</li>
              <li>• Ensure redirect URL matches: http://localhost:3000/auth/callback</li>
              <li>• Check that GitHub provider is enabled in Supabase</li>
            </ul>
          </div>
          
          <a
            href="/"
            className="inline-block bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Return Home
          </a>
        </div>
      </div>
    </div>
  )
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AuthErrorContent />
    </Suspense>
  )
}