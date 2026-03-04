/**
 * Next.js Middleware for Clerk Authentication & Authorization
 *
 * Enforces:
 * - Route protection (authenticated users only)
 * - Role-based access control (Partner, Associate, Analyst)
 * - Organization-based tenant isolation
 * - Audit logging for access
 */

import { authMiddleware, clerkClient } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

// ============================================================================
// Role-Based Access Control (RBAC) Configuration
// ============================================================================

interface RouteConfig {
  roles: string[];
  description: string;
}

const ROUTE_CONFIG: Record<string, RouteConfig> = {
  // Public routes (no auth required)
  "/": { roles: ["public"], description: "Landing page" },
  "/sign-in": { roles: ["public"], description: "Sign in" },
  "/sign-up": { roles: ["public"], description: "Sign up" },

  // Dashboard (all authenticated users)
  "/dashboard": { roles: ["partner", "associate", "analyst"], description: "Deal dashboard" },

  // Deals (all authenticated users)
  "/deals": { roles: ["partner", "associate", "analyst"], description: "Deal list" },
  "/deals/[id]": { roles: ["partner", "associate", "analyst"], description: "Deal detail" },

  // Document upload and review (Partner, Associate)
  "/deals/[id]/upload": { roles: ["partner", "associate"], description: "Document upload" },
  "/deals/[id]/review": { roles: ["partner", "associate"], description: "Clause review" },

  // Settings & administration (Partner only)
  "/settings": { roles: ["partner"], description: "Organization settings" },
  "/settings/team": { roles: ["partner"], description: "Team management" },
  "/settings/playbooks": { roles: ["partner"], description: "Playbook configuration" },

  // Exports (Partner, Associate)
  "/deals/[id]/export": { roles: ["partner", "associate"], description: "Deal export" },

  // Read-only access (all roles)
  "/deals/[id]/view": { roles: ["partner", "associate", "analyst"], description: "View deal" },
  "/contracts/[id]/view": { roles: ["partner", "associate", "analyst"], description: "View contract" },
};

// ============================================================================
// Custom Metadata & Claims
// ============================================================================

interface ClerkUser {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
}

interface UserMetadata {
  role: "partner" | "associate" | "analyst" | "admin";
  tenant_id: string;
  organization_id: string;
  permissions: string[];
}

// ============================================================================
// Middleware Function
// ============================================================================

export default authMiddleware(async (auth, req: NextRequest) => {
  // Public routes - no auth required
  if (isPublicRoute(req)) {
    return NextResponse.next();
  }

  // Protected routes - auth required
  if (!auth.userId) {
    // Store the requested URL for post-login redirect
    const signInUrl = new URL("/sign-in", req.url);
    signInUrl.searchParams.set("redirect_url", req.url);
    return NextResponse.redirect(signInUrl);
  }

  // Extract user info
  const userId = auth.userId;
  const userEmail = auth.user?.emailAddresses?.[0]?.emailAddress || "";

  // Get user metadata from Clerk
  const userMetadata = await getUserMetadata(userId);

  if (!userMetadata) {
    // User not found in metadata - redirect to onboarding
    return NextResponse.redirect(new URL("/onboarding", req.url));
  }

  // Check role-based access
  const pathname = req.nextUrl.pathname;
  const allowedRoles = getRequiredRoles(pathname);

  if (
    allowedRoles.length > 0 &&
    !allowedRoles.includes(userMetadata.role)
  ) {
    // User role not authorized for this route
    return NextResponse.redirect(new URL("/unauthorized", req.url));
  }

  // Set headers for downstream use
  const requestHeaders = new Headers(req.headers);
  requestHeaders.set("x-user-id", userId);
  requestHeaders.set("x-user-email", userEmail);
  requestHeaders.set("x-tenant-id", userMetadata.tenant_id);
  requestHeaders.set("x-user-role", userMetadata.role);
  requestHeaders.set("x-organization-id", userMetadata.organization_id);

  // Log access for audit trail
  await auditLog({
    user_id: userId,
    action: "route_access",
    resource: pathname,
    details: {
      method: req.method,
      role: userMetadata.role,
      tenant_id: userMetadata.tenant_id,
    },
  });

  // Create response with updated headers
  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // Set tenant context in response cookies (for Supabase RLS)
  response.cookies.set("x-tenant-id", userMetadata.tenant_id, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 7, // 7 days
  });

  return response;
});

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Check if route is public (no auth required)
 */
function isPublicRoute(req: NextRequest): boolean {
  const publicRoutes = [
    "/",
    "/sign-in",
    "/sign-up",
    "/pricing",
    "/features",
    "/api/webhooks",
  ];

  const pathname = req.nextUrl.pathname;
  return publicRoutes.some((route) => pathname.startsWith(route));
}

/**
 * Get required roles for a given route
 */
function getRequiredRoles(pathname: string): string[] {
  // Try exact match first
  const config = ROUTE_CONFIG[pathname];
  if (config) {
    return config.roles;
  }

  // Try pattern matching
  for (const [pattern, config] of Object.entries(ROUTE_CONFIG)) {
    if (pathMatches(pathname, pattern)) {
      return config.roles;
    }
  }

  // Default to requiring authentication
  return ["partner", "associate", "analyst", "admin"];
}

/**
 * Simple path pattern matching
 * Supports [id], [slug], etc. placeholders
 */
function pathMatches(pathname: string, pattern: string): boolean {
  const patternParts = pattern.split("/");
  const pathParts = pathname.split("/");

  if (patternParts.length !== pathParts.length) {
    return false;
  }

  return patternParts.every((part, idx) => {
    if (part.startsWith("[") && part.endsWith("]")) {
      // Placeholder - matches anything
      return true;
    }
    return part === pathParts[idx];
  });
}

/**
 * Get user metadata from Clerk
 */
async function getUserMetadata(userId: string): Promise<UserMetadata | null> {
  try {
    const client = await clerkClient();
    const user = await client.users.getUser(userId);

    // Extract metadata from Clerk user object
    const metadata = user.publicMetadata as Record<string, unknown> || {};

    return {
      role: (metadata.role as UserMetadata["role"]) || "analyst",
      tenant_id: (metadata.tenant_id as string) || "",
      organization_id: (metadata.organization_id as string) || "",
      permissions: (metadata.permissions as string[]) || [],
    };
  } catch (error) {
    console.error("Failed to get user metadata:", error);
    return null;
  }
}

/**
 * Log access to audit trail
 */
async function auditLog(data: {
  user_id: string;
  action: string;
  resource: string;
  details: Record<string, unknown>;
}): Promise<void> {
  try {
    // Call internal audit API
    await fetch("/api/audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: data.user_id,
        action: data.action,
        resource_type: "route",
        resource_id: data.resource,
        details: data.details,
      }),
    });
  } catch (error) {
    // Silently fail - don't break auth flow due to audit logging failure
    console.error("Audit logging failed:", error);
  }
}

// ============================================================================
// Middleware Configuration
// ============================================================================

export const config = {
  matcher: [
    // Match all routes except static assets and API
    "/((?!_next/static|_next/image|favicon.ico|.*\\.png|.*\\.jpg|.*\\.jpeg|.*\\.svg|api/webhooks).*)",
  ],
};
