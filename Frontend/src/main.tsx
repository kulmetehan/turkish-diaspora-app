// Frontend/src/main.tsx
import React, { Suspense } from "react";
import ReactDOM from "react-dom/client";
import { HashRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";

import "leaflet/dist/leaflet.css";
import "mapbox-gl/dist/mapbox-gl.css";
import App from "./App";
import "./index.css";

import { FooterTabs } from "@/components/FooterTabs";
import AdminRouteWrapper from "@/components/admin/AdminRouteWrapper";
import { Toaster } from "@/components/ui/toaster";
import { OrganizationSchema } from "@/components/seo/OrganizationSchema";
import { WebsiteSchema } from "@/components/seo/WebsiteSchema";
import { initI18n } from "@/i18n";
import { initTheme } from "@/lib/theme/darkMode";
import { loadRecaptchaScript } from "@/lib/recaptcha";
import { initAnalytics } from "@/lib/analytics";
import { useScreenTracking } from "@/hooks/useScreenTracking";
import { useHtmlLang } from "@/lib/seo/useHtmlLang";
import LoginPage from "@/pages/LoginPage";
import UiKit from "@/pages/UiKit";
const AdminHomePage = React.lazy(() => import("@/pages/AdminHomePage"));
const AdminCitiesPage = React.lazy(() => import("@/pages/AdminCitiesPage"));
const AdminEventSourcesPage = React.lazy(() => import("@/pages/admin/AdminEventSourcesPage"));
const AdminEventsPage = React.lazy(() => import("@/pages/AdminEventsPage"));
const WorkersDashboardPage = React.lazy(() => import("@/pages/WorkersDashboardPage"));
const WorkerRunDetailPage = React.lazy(() => import("@/pages/WorkerRunDetailPage"));
const LocationsPage = React.lazy(() => import("@/pages/admin/LocationsPage"));
const MetricsPage = React.lazy(() => import("@/pages/admin/MetricsPage"));
const DiscoveryPage = React.lazy(() => import("@/pages/admin/DiscoveryPage"));
const TasksPage = React.lazy(() => import("@/pages/admin/TasksPage"));
const NewsAIPage = React.lazy(() => import("@/pages/admin/NewsAIPage"));
const AdminAIPolicyPage = React.lazy(() => import("@/pages/AdminAIPolicyPage"));
const PrivacyPolicyPage = React.lazy(() => import("@/pages/PrivacyPolicyPage"));
const TermsOfServicePage = React.lazy(() => import("@/pages/TermsOfServicePage"));
const PrikbordPage = React.lazy(() => import("@/pages/PrikbordPage"));
const CommunityGuidelinesPage = React.lazy(() => import("@/pages/CommunityGuidelinesPage"));
const UserAuthPage = React.lazy(() => import("@/pages/UserAuthPage"));
const AdminPollsPage = React.lazy(() => import("@/pages/admin/AdminPollsPage"));
const AdminReportsPage = React.lazy(() => import("@/pages/admin/AdminReportsPage"));
const AdminLocationSubmissionsPage = React.lazy(() => import("@/pages/admin/AdminLocationSubmissionsPage"));
const AdminLocationSubmissionDetailPage = React.lazy(() => import("@/pages/admin/AdminLocationSubmissionDetailPage"));
const AdminBulletinModeration = React.lazy(() => import("@/pages/admin/AdminBulletinModeration"));
const AdminAuthenticatedClaimsPage = React.lazy(() => import("@/pages/admin/AdminAuthenticatedClaimsPage"));
const AdminOutreachContactsPage = React.lazy(() => import("@/pages/admin/AdminOutreachContactsPage"));
const AdminAuthenticatedClaimDetailPage = React.lazy(() => import("@/pages/admin/AdminAuthenticatedClaimDetailPage"));
const DiasporaPulsePage = React.lazy(() => import("@/pages/DiasporaPulsePage"));
const PollDetailPage = React.lazy(() => import("@/pages/PollDetailPage"));
const LocationDetailPage = React.lazy(() => import("@/pages/LocationDetailPage"));
const ClaimPage = React.lazy(() => import("@/pages/ClaimPage"));

// Vite base path is configured in vite.config.ts (defaults to "/" for Render deployment)

initTheme();
initI18n();
initAnalytics();

// Load reCAPTCHA Enterprise script (non-blocking, graceful degradation if fails)
loadRecaptchaScript().catch((error) => {
  console.debug("reCAPTCHA script load failed (non-critical):", error);
});

function AppLayout() {
  // Track screen views on route changes
  useScreenTracking();
  
  // Update HTML lang attribute based on i18n state
  useHtmlLang();

  return (
    <>
      {/* Global SEO schemas */}
      <OrganizationSchema />
      <WebsiteSchema />
      
      <div className="flex min-h-[100svh] flex-col bg-background text-foreground">
        <main className="relative flex-1 overflow-hidden bg-background">
          <Outlet />
        </main>
        <FooterTabs />
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HelmetProvider>
      <HashRouter>
        <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/feed" replace />} />
          <Route path="/map" element={<App initialTab="map" />} />
          <Route path="/news" element={<App initialTab="news" />} />
          <Route path="/events" element={<App initialTab="events" />} />
          <Route path="/feed" element={<App initialTab="feed" />} />
          <Route path="/account" element={<App initialTab="account" />} />
          <Route path="/prikbord" element={
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <PrikbordPage />
            </Suspense>
          } />
          <Route path="/locations/:id" element={
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <LocationDetailPage />
            </Suspense>
          } />
          <Route path="/claim/:token" element={
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <ClaimPage />
            </Suspense>
          } />
        </Route>
        <Route path="/ui-kit" element={<UiKit />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/privacy" element={
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
            <PrivacyPolicyPage />
          </Suspense>
        } />
        <Route path="/terms" element={
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
            <TermsOfServicePage />
          </Suspense>
        } />
        <Route path="/guidelines" element={
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
            <CommunityGuidelinesPage />
          </Suspense>
        } />
        <Route path="/auth" element={
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
            <UserAuthPage />
          </Suspense>
        } />
        <Route path="/pulse" element={
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
            <DiasporaPulsePage />
          </Suspense>
        } />
        <Route path="/polls/:id" element={
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
            <PollDetailPage />
          </Suspense>
        } />
        <Route path="/admin" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminHomePage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/cities" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminCitiesPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/workers" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <WorkersDashboardPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/event-sources" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminEventSourcesPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/events" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminEventsPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/polls" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminPollsPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/reports" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminReportsPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/location-submissions" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminLocationSubmissionsPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/location-submissions/:id" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminLocationSubmissionDetailPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/bulletin" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminBulletinModeration />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/authenticated-claims" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminAuthenticatedClaimsPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/authenticated-claims/:claimId" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminAuthenticatedClaimDetailPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/outreach-contacts" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminOutreachContactsPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/workers/runs/:runId" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <WorkerRunDetailPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/locations" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <LocationsPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/metrics" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <MetricsPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/discovery" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <DiscoveryPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/tasks" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <TasksPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/news-ai" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <NewsAIPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        <Route path="/admin/settings/ai-policy" element={
          <AdminRouteWrapper>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminAIPolicyPage />
            </Suspense>
          </AdminRouteWrapper>
        } />
        {/* Catch-all naar feed */}
        <Route path="*" element={<Navigate to="/feed" replace />} />
        </Routes>
        <Toaster position="top-right" />
      </HashRouter>
    </HelmetProvider>
  </React.StrictMode>
);