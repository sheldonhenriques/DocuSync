import { NextResponse } from 'next/server'

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const repo = searchParams.get('repo') // e.g. "owner/repo"
  const prNumber = searchParams.get('pr')
  const token = req.headers.get('Authorization')?.split(' ')[1]

  if (!repo || !prNumber || !token) {
    return NextResponse.json({ error: 'Missing repo, pr or token' }, { status: 400 })
  }

  try {
    // Fetch pull request info to get base and head refs
    const prRes = await fetch(`https://api.github.com/repos/${repo}/pulls/${prNumber}`, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (!prRes.ok) {
      const err = await prRes.text()
      return NextResponse.json({ error: `Failed to fetch PR info: ${err}` }, { status: 500 })
    }

    const pr = await prRes.json()
    const baseRef = pr.base.ref
    const headRef = pr.head.ref

    const filePath = 'Readme.md'
    // Fetch list of changed files
    // const filesRes = await fetch(`https://api.github.com/repos/${repo}/pulls/${prNumber}/files`, {
    //   headers: { Authorization: `Bearer ${token}` }
    // })

    // const files = await filesRes.json()

    // const markdownFile = files.find((f: any) => f.filename.toLowerCase().endsWith('.md'))

    // if (!markdownFile) {
    //   return NextResponse.json({
    //     original: '(No markdown file found in this PR)',
    //     proposed: '(No markdown file found in this PR)'
    //   })
    // }

    // const filePath = markdownFile.filename

    // Fetch raw file contents from both branches
    const [baseRes, headRes] = await Promise.all([
      fetch(`https://raw.githubusercontent.com/${repo}/${baseRef}/${filePath}`),
      fetch(`https://raw.githubusercontent.com/${repo}/${headRef}/${filePath}`)
    ])

    const [original, proposed] = await Promise.all([
      baseRes.ok ? baseRes.text() : '(File not found in base branch)',
      headRes.ok ? headRes.text() : '(File not found in head branch)'
    ])

    return NextResponse.json({ original, proposed })
  } catch (error) {
    console.error('Diff API error:', error)
    return NextResponse.json({ error: 'Unexpected error fetching diff' }, { status: 500 })
  }
}
