// src/app/api/github/repos/route.ts
import { NextResponse } from 'next/server'

export async function GET(req: Request) {
  const token = req.headers.get('Authorization')?.split(' ')[1]

  const res = await fetch('https://api.github.com/user/repos', {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
    },
  })

  const data = await res.json()

  return NextResponse.json(
    data.map((r: any) => ({
      id: r.full_name,
      name: r.name,
      fullName: r.full_name,
      icon: r.name[0].toUpperCase(),
      color: 'bg-indigo-500',
    }))
  )
}
