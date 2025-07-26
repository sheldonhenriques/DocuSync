import { NextResponse } from 'next/server'

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const repo = searchParams.get('repo') // e.g. user/repo
  const prNumber = searchParams.get('pr')
  const token = req.headers.get('Authorization')?.split(' ')[1]

  if (!repo || !prNumber || !token) {
    return NextResponse.json({ error: 'Missing repo, pr or token' }, { status: 400 })
  }

  // 1. Fetch PR info to get base and head refs
  const prRes = await fetch(`https://api.github.com/repos/${repo}/pulls/${prNumber}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  const pr = await prRes.json()
  const baseRef = pr.base.ref
  const headRef = pr.head.ref

  // 2. Fetch doc file (assume location)
  const filePath = 'Readme.md'
  const [baseRes, headRes] = await Promise.all([
    fetch(`https://raw.githubusercontent.com/${repo}/${baseRef}/${filePath}`),
    fetch(`https://raw.githubusercontent.com/${repo}/${headRef}/${filePath}`)
  ])

  const [original, proposed] = await Promise.all([
    baseRes.ok ? baseRes.text() : '',
    headRes.ok ? headRes.text() : ''
  ])

  return NextResponse.json({ original, proposed })
}
