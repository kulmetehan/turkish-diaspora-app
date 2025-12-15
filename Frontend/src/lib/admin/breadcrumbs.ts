/**
 * Breadcrumb generation logic for admin pages
 */

import { findNavItemByPath, type NavItem } from "./navigation";

export interface BreadcrumbSegment {
  label: string;
  path: string;
}

/**
 * Generate breadcrumbs from a given path
 */
export function generateBreadcrumbs(path: string): BreadcrumbSegment[] {
  const segments: BreadcrumbSegment[] = [
    { label: "Admin", path: "/admin" },
  ];
  
  // Remove leading /admin if present
  const relativePath = path.startsWith("/admin") ? path.slice(6) : path;
  
  if (!relativePath || relativePath === "/") {
    return segments;
  }
  
  // Split path into segments
  const pathParts = relativePath
    .split("/")
    .filter(Boolean)
    .map((part) => decodeURIComponent(part));
  
  // Build breadcrumb path progressively
  let currentPath = "/admin";
  
  for (let i = 0; i < pathParts.length; i++) {
    currentPath += `/${pathParts[i]}`;
    
    // Try to find a nav item for this path
    const navItem = findNavItemByPath(currentPath);
    
    if (navItem) {
      segments.push({
        label: navItem.label,
        path: currentPath,
      });
    } else {
      // No nav item found, create a label from the path segment
      // Convert kebab-case to Title Case
      const label = pathParts[i]
        .split("-")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
      
      segments.push({
        label,
        path: currentPath,
      });
    }
  }
  
  return segments;
}

/**
 * Get the page title for a given path
 */
export function getPageTitle(path: string): string {
  const navItem = findNavItemByPath(path);
  if (navItem) {
    return navItem.label;
  }
  
  const breadcrumbs = generateBreadcrumbs(path);
  return breadcrumbs[breadcrumbs.length - 1]?.label || "Admin";
}


















