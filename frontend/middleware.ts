import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const protectedPrefixes = {
  admin: ["/admin"],
  jury: ["/jury"],
  student: ["/student"],
} as const

export function middleware(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value
  const role = request.cookies.get("role")?.value
  const { pathname } = request.nextUrl
  const isAdminPath = protectedPrefixes.admin.some((prefix) => pathname.startsWith(prefix))
  const isJuryPath = protectedPrefixes.jury.some((prefix) => pathname.startsWith(prefix))
  const isStudentPath = protectedPrefixes.student.some((prefix) => pathname.startsWith(prefix))
  const isProtectedPath = isAdminPath || isJuryPath || isStudentPath

  if (!token && isProtectedPath) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  if (!role && isProtectedPath) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  if (role === "admin" && isAdminPath) {
    return NextResponse.next()
  }

  if (role === "jury" && isJuryPath) {
    return NextResponse.next()
  }

  if (role === "student" && isStudentPath) {
    return NextResponse.next()
  }

  if (token && role && isProtectedPath) {
    return NextResponse.redirect(new URL("/forbidden", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/admin/:path*", "/jury/:path*", "/student/:path*", "/forbidden"],
}
