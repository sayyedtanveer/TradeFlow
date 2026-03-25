/**
 * CENTRALIZED ROLE CONFIGURATION
 * 
 * Single source of truth for all roles in the system.
 * Follows DRY principle - roles defined once, used everywhere.
 * 
 * Industry Best Practices:
 * - Enum for type safety
 * - Metadata config for UI labels, permissions, descriptions
 * - Helper functions for common operations
 * - Backend/Frontend case normalization
 */

import { LucideIcon, Shield, Users, Wrench, Eye } from "lucide-react"

export enum UserRole {
  ADMIN = "ADMIN",
  MANAGER = "MANAGER",
  OPERATOR = "OPERATOR",
  VIEWER = "VIEWER",
}

/**
 * Role metadata - UI labels, icons, descriptions, permissions
 * This is the ONLY place role strings should appear (except as enum values)
 */
export const ROLE_CONFIG: Record<UserRole, {
  label: string
  description: string
  icon: LucideIcon
  color: string
  sortOrder: number
}> = {
  [UserRole.ADMIN]: {
    label: "Administrator",
    description: "Full access to all modules and settings",
    icon: Shield,
    color: "text-red-600",
    sortOrder: 1,
  },
  [UserRole.MANAGER]: {
    label: "Manager",
    description: "View and edit inventory, manufacturing, and sales",
    icon: Users,
    color: "text-blue-600",
    sortOrder: 2,
  },
  [UserRole.OPERATOR]: {
    label: "Operator",
    description: "Limited access - inventory and manufacturing operations",
    icon: Wrench,
    color: "text-green-600",
    sortOrder: 3,
  },
  [UserRole.VIEWER]: {
    label: "Viewer",
    description: "Read-only access to reports and dashboards",
    icon: Eye,
    color: "text-gray-600",
    sortOrder: 4,
  },
}

/**
 * Available roles for user creation/editing
 * Use this instead of hardcoding role options in forms
 */
export const AVAILABLE_ROLES = Object.entries(ROLE_CONFIG)
  .map(([role, config]) => ({
    value: role,
    label: config.label,
    description: config.description,
  }))
  .sort((a, b) => ROLE_CONFIG[a.value as UserRole].sortOrder - ROLE_CONFIG[b.value as UserRole].sortOrder)

/**
 * Module-level role access matrix
 * Maps which roles can access which modules
 * Alternative to hardcoding roles in 4+ places
 */
export const MODULE_ROLES: Record<string, UserRole[]> = {
  dashboard: [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR, UserRole.VIEWER],
  products: [UserRole.ADMIN, UserRole.MANAGER],
  bom: [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR],
  manufacturing: [UserRole.ADMIN, UserRole.MANAGER],
  inventory: [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR, UserRole.VIEWER],
  workOrders: [UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR],
  sales: [UserRole.ADMIN, UserRole.MANAGER, UserRole.VIEWER],
  reports: [UserRole.ADMIN, UserRole.MANAGER],
  users: [UserRole.ADMIN],
  settings: [UserRole.ADMIN],
}

/**
 * Helper: Normalize backend role (lowercase) to frontend enum (uppercase)
 * Backend returns "admin", we need UserRole.ADMIN
 */
export function normalizeRole(role: string | undefined): UserRole | undefined {
  if (!role) return undefined
  const normalized = role.toUpperCase()
  if (Object.values(UserRole).includes(normalized as UserRole)) {
    return normalized as UserRole
  }
  console.warn(`Unknown role: ${role}`)
  return undefined
}

/**
 * Helper: Get role label for display
 */
export function getRoleLabel(role: UserRole | string | undefined): string {
  const normalized = normalizeRole(role as string)
  return normalized ? ROLE_CONFIG[normalized].label : "Unknown"
}

/**
 * Helper: Check if role can access module
 */
export function canAccessModule(role: UserRole | string | undefined, module: string): boolean {
  const normalized = normalizeRole(role as string)
  if (!normalized) return false
  const allowedRoles = MODULE_ROLES[module] || []
  return allowedRoles.includes(normalized)
}

/**
 * Helper: Get all roles that can access a module
 */
export function getRolesForModule(module: string): UserRole[] {
  return MODULE_ROLES[module] || []
}
