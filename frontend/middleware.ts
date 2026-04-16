import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const protectedPrefixes = {
  admin: ["/admin"],
  jury: ["/jury"],
  student: ["/student"],
} as const

/**
 * Decode JWT payload without verification (Edge Runtime has no
 * access to the backend SECRET_KEY). The real authorization
 * happens server-side on every API call — this middleware only
 * provides client-side route protection for UX purposes.
 */
function extractRoleFromToken(token: string): string | null {
  try {
    const parts = token.split(".")
    if (parts.length !== 3) return null

    const payload = JSON.parse(
      Buffer.from(parts[1], "base64url").toString("utf-8"),
    )

    return typeof payload.role === "string" ? payload.role : null
  } catch {
    return null
  }
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value
  const { pathname } = request.nextUrl
  const isAdminPath = protectedPrefixes.admin.some((prefix) => pathname.startsWith(prefix))
  const isJuryPath = protectedPrefixes.jury.some((prefix) => pathname.startsWith(prefix))
  const isStudentPath = protectedPrefixes.student.some((prefix) => pathname.startsWith(prefix))
  const isProtectedPath = isAdminPath || isJuryPath || isStudentPath

  if (!token && isProtectedPath) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  // Extract role from JWT payload instead of trusting the "role" cookie
  const role = token ? extractRoleFromToken(token) : null

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
