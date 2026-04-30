import { normalizeRole } from "@/lib/roles.config"

function decodeJwtPayload(token: string | null | undefined): Record<string, unknown> | null {
  if (!token) return null

  const payload = token.split(".")[1]
  if (!payload) return null

  try {
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/")
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=")
    return JSON.parse(atob(padded)) as Record<string, unknown>
  } catch {
    return null
  }
}

export function isClientSession(params: {
  token?: string | null
  userRole?: string | null
  clientId?: string | null
  pathname?: string
}): boolean {
  const tokenPayload = decodeJwtPayload(params.token)
  const pathname = params.pathname ?? (typeof window !== "undefined" ? window.location.pathname : "")

  return (
    pathname.startsWith("/client") ||
    normalizeRole(params.userRole ?? undefined) === "CLIENT" ||
    Boolean(params.clientId) ||
    Boolean(tokenPayload?.cid)
  )
}
