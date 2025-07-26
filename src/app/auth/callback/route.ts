import { NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase-server'

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const error = searchParams.get('error')
  const next = '/'

  console.log('Callback route hit:', {
    code: code ? 'present' : 'missing',
    error,
    origin,
    searchParams: Object.fromEntries(searchParams.entries())
  })

  // Check if there's an OAuth error from GitHub
  if (error) {
    console.error('OAuth error from provider:', error)
    return Response.redirect(`${origin}/auth/auth-code-error?error=${encodeURIComponent(error)}`)
  }

  if (code) {
    try {
      const { supabase, response } = createClient(request)
      console.log('Attempting to exchange code for session...')
      
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      
      if (exchangeError) {
        console.error('Exchange code error:', exchangeError)
        return Response.redirect(`${origin}/auth/auth-code-error?error=${encodeURIComponent(exchangeError.message)}`)
      }
      
      console.log('Auth success:', { user: data?.user?.email })
      return Response.redirect(`${origin}${next}`)
      
    } catch (err) {
      console.error('Unexpected error:', err)
      return Response.redirect(`${origin}/auth/auth-code-error?error=unexpected_error`)
    }
  }

  console.error('No code parameter found')
  return Response.redirect(`${origin}/auth/auth-code-error?error=no_code`)
}