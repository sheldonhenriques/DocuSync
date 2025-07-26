import { NextResponse } from 'next/server'

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const repo = searchParams.get('repo') // e.g. "username/my-repo"
  const token = req.headers.get('Authorization')?.split(' ')[1]

  if (!repo || !token) {
    return NextResponse.json({ error: 'Missing repo or token' }, { status: 400 })
  }

  const url = `https://api.github.com/repos/${repo}/pulls?state=open`

  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
    },
  })

  if (!res.ok) {
    const errorText = await res.text()
    return NextResponse.json({ error: errorText }, { status: res.status })
  }

  const data = await res.json()

  // Format PR data
  const prs = data.map((pr: any) => ({
    id: pr.number,
    title: pr.title,
    author: pr.user.login,
    avatar: pr.user.avatar_url,
    repository: repo,
    branch: pr.head.ref,
    status: 'pending', // default for now
    createdAt: pr.created_at,
    filesChanged: pr.changed_files ?? 0, // this may require an extra call
    hasDocumentation: false, // you can fill this from your DB later
    description: pr.body || '',
  }))

  return NextResponse.json(prs)
}
