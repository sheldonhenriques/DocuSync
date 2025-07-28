'use client';

import { useState } from 'react';
import { apiClient } from '../lib/api';

export default function ConnectionTest() {
  const [backendStatus, setBackendStatus] = useState<any>(null);
  const [supabaseStatus, setSupabaseStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const testConnections = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Test backend connection
      console.log('Testing backend connection...');
      const backendHealth = await apiClient.healthCheck();
      const backendApiTest = await apiClient.apiTest();
      setBackendStatus({ ...backendHealth, ...backendApiTest });
      
      // Test GitHub API access through backend
      console.log('Testing GitHub API access...');
      const githubTest = await apiClient.getRepositoryInfo('microsoft', 'vscode');
      console.log('GitHub API test result:', githubTest);
      
      // Test Supabase connection (import dynamically to avoid SSR issues)
      const { supabase } = await import('../lib/supabase');
      const { data, error: supabaseError } = await supabase
        .from('users')
        .select('count')
        .limit(1);
      
      if (supabaseError) {
        setSupabaseStatus({ error: supabaseError.message });
      } else {
        setSupabaseStatus({ status: 'connected', data, github_api: githubTest ? 'working' : 'failed' });
      }
      
    } catch (err: any) {
      setError(err.message);
      console.error('Connection test failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-4">Connection Test</h2>
      
      <button
        onClick={testConnections}
        disabled={loading}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mb-4 disabled:opacity-50"
      >
        {loading ? 'Testing...' : 'Test Connections'}
      </button>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border rounded p-4">
          <h3 className="font-semibold text-lg mb-2">Backend API</h3>
          {backendStatus ? (
            <div className="text-green-600">
              <p>✅ Status: {backendStatus.status}</p>
              <p>Service: {backendStatus.service}</p>
            </div>
          ) : (
            <p className="text-gray-500">Not tested yet</p>
          )}
        </div>

        <div className="border rounded p-4">
          <h3 className="font-semibold text-lg mb-2">Supabase Database</h3>
          {supabaseStatus ? (
            supabaseStatus.error ? (
              <div className="text-red-600">
                <p>❌ Error: {supabaseStatus.error}</p>
              </div>
            ) : (
              <div className="text-green-600">
                <p>✅ Status: {supabaseStatus.status}</p>
                <p>GitHub API: {supabaseStatus.github_api || 'unknown'}</p>
              </div>
            )
          ) : (
            <p className="text-gray-500">Not tested yet</p>
          )}
        </div>
      </div>

      <div className="mt-6">
        <h3 className="font-semibold text-lg mb-2">Connection Details</h3>
        <div className="bg-gray-100 p-4 rounded text-sm">
          <p><strong>Frontend URL:</strong> http://localhost:3000</p>
          <p><strong>Backend API URL:</strong> {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</p>
          <p><strong>Supabase URL:</strong> {process.env.NEXT_PUBLIC_SUPABASE_URL}</p>
        </div>
      </div>
    </div>
  );
}