---
title: Admin Navigation Architecture
status: active
last_updated: 2025-01-22
scope: admin-frontend
owners: [tda-frontend]
---

# Admin Navigation Architecture

Complete guide to the modern admin navigation system with persistent sidebar, breadcrumbs, command palette, and responsive design.

## Overview

The admin interface features a comprehensive navigation system designed for industry-leading UX with:

- **Persistent sidebar navigation** with collapsible groups
- **Breadcrumb navigation** for context awareness
- **Command palette (Cmd+K)** for power users
- **Mobile-responsive design** with drawer navigation
- **Unified layout** across all admin pages

## Architecture

### Component Structure

```
Frontend/src/components/admin/
├── AdminLayout.tsx              # Central layout wrapper
├── AdminSidebar.tsx            # Persistent sidebar navigation
├── AdminSidebarNavGroup.tsx    # Collapsible navigation groups
├── AdminSidebarNavItem.tsx     # Individual navigation items
├── AdminHeader.tsx             # Top header with breadcrumbs
├── AdminBreadcrumbs.tsx        # Breadcrumb navigation
├── AdminUserMenu.tsx           # User dropdown menu
├── AdminCommandPalette.tsx     # Cmd+K command palette
├── AdminMobileDrawer.tsx       # Mobile drawer navigation
└── AdminRouteWrapper.tsx       # Route wrapper (auth + layout)
```

### Configuration Files

```
Frontend/src/lib/admin/
├── navigation.ts               # Navigation structure config
├── breadcrumbs.ts              # Breadcrumb generation logic
└── command-palette.ts          # Command palette config
```

## Navigation Structure

### Navigation Groups

The sidebar is organized into logical groups:

1. **Dashboard** - Overview and main sections
   - Overview
   - Locations
   - Metrics
   - Discovery Coverage
   - AI Policy
   - Tasks
   - News AI Logs

2. **Configuration** - System configuration
   - Cities
   - Event Sources

3. **Operations** - Active operations
   - Workers

4. **Events** - Event management
   - Events Dashboard

5. **System** - System-level features
   - Audit Log (coming soon)

### Route Structure

All admin routes follow this pattern:

```
/admin                          → Dashboard Overview
/admin/locations                → Locations Management
/admin/metrics                  → Metrics Dashboard
/admin/discovery                → Discovery Coverage
/admin/tasks                    → Tasks Panel
/admin/news-ai                  → News AI Logs
/admin/settings/ai-policy       → AI Policy Configuration
/admin/cities                   → Cities Management
/admin/event-sources            → Event Sources
/admin/workers                  → Workers Dashboard
/admin/workers/runs/:runId      → Worker Run Details
/admin/events                   → Events Dashboard
```

## Features

### Persistent Sidebar

The sidebar remains visible on all admin pages (desktop) and provides:

- **Collapsible groups** for better organization
- **Active state indicators** showing current page
- **Icon + label** for each navigation item
- **Badge indicators** for notifications (e.g., "coming soon")
- **Collapse/expand** toggle button

**Desktop behavior:**
- Fixed left sidebar (256px width)
- Collapsible to 64px (icon-only mode)
- Smooth transitions

**Mobile behavior:**
- Hidden by default
- Accessible via hamburger menu in header
- Drawer slides in from left
- Backdrop overlay

### Breadcrumb Navigation

Breadcrumbs appear in the header showing the current navigation path:

- **Automatic generation** from route structure
- **Clickable segments** for navigation
- **Mobile-friendly** with horizontal scroll
- **Context-aware** labels from navigation config

Example: `Admin > Dashboard > Locations`

### Command Palette (Cmd+K)

Power user feature for quick navigation:

- **Keyboard shortcut**: `Cmd+K` (Mac) / `Ctrl+K` (Windows/Linux)
- **Global search** across all admin pages
- **Grouped results** by navigation group
- **Keyboard navigation** (arrow keys, Enter)
- **Icon indicators** for quick visual recognition

### Mobile Navigation

Mobile-optimized experience:

- **Hamburger menu** in header
- **Drawer component** (Vaul library)
- **Swipe gestures** to close
- **Touch-optimized** navigation items
- **Backdrop overlay** for focus

## Usage

### Adding New Routes

1. Add route to navigation config (`Frontend/src/lib/admin/navigation.ts`):

```typescript
{
  id: "my-new-page",
  label: "My New Page",
  icon: "IconName",
  path: "/admin/my-new-page",
  group: "dashboard",
}
```

2. Create page component in `Frontend/src/pages/admin/` or appropriate location

3. Add route to `Frontend/src/main.tsx`:

```typescript
<Route path="/admin/my-new-page" element={
  <AdminRouteWrapper>
    <Suspense fallback={<div>Loading...</div>}>
      <MyNewPage />
    </Suspense>
  </AdminRouteWrapper>
} />
```

4. Breadcrumbs and navigation will automatically work!

### Modifying Navigation Groups

Edit `Frontend/src/lib/admin/navigation.ts` to:
- Reorder groups
- Add/remove navigation items
- Change group labels
- Update icons or paths

### Customizing Breadcrumbs

The breadcrumb generation logic in `Frontend/src/lib/admin/breadcrumbs.ts` automatically:
- Generates breadcrumbs from route paths
- Matches navigation items for labels
- Falls back to formatted path segments

For custom breadcrumb labels, ensure the route exists in navigation config.

## Keyboard Shortcuts

- **Cmd+K / Ctrl+K**: Open command palette
- **Escape**: Close command palette
- **Arrow keys**: Navigate in command palette
- **Enter**: Select item in command palette

## Responsive Breakpoints

- **Mobile**: `< 768px` - Drawer navigation
- **Desktop**: `>= 768px` - Sidebar navigation
- **Tablet**: `768px - 1024px` - Sidebar with responsive width

## Accessibility

- **ARIA labels** on all interactive elements
- **Keyboard navigation** fully supported
- **Focus management** in modals and drawers
- **Screen reader** compatible
- **WCAG 2.1 AA** compliant

## Performance

- **Lazy loading** for all page components
- **Code splitting** per route
- **Optimized animations** with CSS transitions
- **Minimal bundle impact**: ~10KB for new dependencies

## Dependencies

- `cmdk` - Command palette component
- `@radix-ui/react-collapsible` - Collapsible groups
- `vaul` - Mobile drawer (already present)
- `lucide-react` - Icons (already present)

## Migration Notes

The new navigation system replaced the previous tab-based navigation on `/admin`. Key changes:

1. **Tabs → Routes**: All tabs are now separate routes
2. **Persistent Navigation**: Sidebar visible on all pages
3. **Unified Layout**: Consistent layout wrapper across admin
4. **Better Discoverability**: All sections accessible from sidebar

## Troubleshooting

### Sidebar not showing

- Check if route is wrapped with `AdminRouteWrapper`
- Verify `AdminLayout` is properly imported
- Check mobile breakpoint (sidebar hidden on mobile)

### Breadcrumbs not appearing

- Ensure route path matches navigation config
- Check breadcrumb generation logic
- Verify route is registered in navigation.ts

### Command palette not opening

- Check keyboard shortcut handler in `AdminLayout`
- Verify `cmdk` dependency is installed
- Check browser console for errors

## Future Enhancements

- [ ] Recent pages in command palette
- [ ] Custom keyboard shortcuts
- [ ] Navigation search improvements
- [ ] Analytics tracking
- [ ] User preferences (collapsed state, etc.)

## References

- Navigation config: `Frontend/src/lib/admin/navigation.ts`
- Layout component: `Frontend/src/components/admin/AdminLayout.tsx`
- Design system: `Docs/design-system.md`
- Admin auth: `Docs/admin-auth.md`













