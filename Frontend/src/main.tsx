// Frontend/src/main.tsx
import React, { Suspense, useEffect } from "react";
import ReactDOM from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import { HashRouter, Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";

import "leaflet/dist/leaflet.css";
import "mapbox-gl/dist/mapbox-gl.css";
import App from "./App";
import "./index.css";

import { FooterTabs } from "@/components/FooterTabs";
import AdminRouteWrapper from "@/components/admin/AdminRouteWrapper";
import { OrganizationSchema } from "@/components/seo/OrganizationSchema";
import { WebsiteSchema } from "@/components/seo/WebsiteSchema";
import { Toaster } from "@/components/ui/toaster";
import { useScreenTracking } from "@/hooks/useScreenTracking";
import { initI18n } from "@/i18n";
import { initAnalytics } from "@/lib/analytics";
import { registerServiceWorker } from "@/lib/pwa";
import { loadRecaptchaScript } from "@/lib/recaptcha";
import { useHtmlLang } from "@/lib/seo/useHtmlLang";
import { initTheme } from "@/lib/theme/darkMode";
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
const AdminEventSubmissionsPage = React.lazy(() => import("@/pages/admin/AdminEventSubmissionsPage"));
const AdminEventSubmissionDetailPage = React.lazy(() => import("@/pages/admin/AdminEventSubmissionDetailPage"));
const AdminBulletinModeration = React.lazy(() => import("@/pages/admin/AdminBulletinModeration"));
const AdminAuthenticatedClaimsPage = React.lazy(() => import("@/pages/admin/AdminAuthenticatedClaimsPage"));
const AdminOutreachContactsPage = React.lazy(() => import("@/pages/admin/AdminOutreachContactsPage"));
const AdminOutreachMetricsPage = React.lazy(() => import("@/pages/admin/AdminOutreachMetricsPage"));
const AdminAuthenticatedClaimDetailPage = React.lazy(() => import("@/pages/admin/AdminAuthenticatedClaimDetailPage"));
const DiasporaPulsePage = React.lazy(() => import("@/pages/DiasporaPulsePage"));
const PollDetailPage = React.lazy(() => import("@/pages/PollDetailPage"));
const LocationDetailPage = React.lazy(() => import("@/pages/LocationDetailPage"));
const ClaimPage = React.lazy(() => import("@/pages/ClaimPage"));
const AccountPage = React.lazy(() => import("@/pages/AccountPage"));
const ChatPage = React.lazy(() => import("@/pages/ChatPage"));
const ChatTopicPage = React.lazy(() => import("@/pages/ChatTopicPage"));

// Vite base path is configured in vite.config.ts (defaults to "/" for Render deployment)

initTheme();
initI18n();
initAnalytics();

// Load reCAPTCHA Enterprise script (non-blocking, graceful degradation if fails)
loadRecaptchaScript().catch((error) => {
  console.debug("reCAPTCHA script load failed (non-critical):", error);
});

// Register service worker for PWA functionality (non-blocking)
registerServiceWorker().catch((error) => {
  console.debug("Service worker registration failed (non-critical):", error);
});

function AppLayout() {
  const navigate = useNavigate();

  // Track screen views on route changes
  useScreenTracking();

  // Update HTML lang attribute based on i18n state
  useHtmlLang();

  // Listen for navigation messages from service worker (for push notification deep linking)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data && event.data.type === 'navigate' && event.data.url) {
        // Service worker sends URL with hash for HashRouter
        const url = event.data.url;
        // Ensure URL starts with # for HashRouter
        const hashUrl = url.startsWith('#') ? url : `#${url}`;
        console.log('[App] Service worker navigation request to:', hashUrl);
        
        // Get the path without the leading #
        const path = hashUrl.substring(1);
        
        // Use React Router's navigate() - this is the proper way for HashRouter
        // It will update the hash and trigger all React Router hooks
        navigate(path, { replace: false });
      }
    };

    // Listen for messages from service worker
    if (navigator.serviceWorker) {
      navigator.serviceWorker.addEventListener('message', handleMessage);
      
      return () => {
        navigator.serviceWorker?.removeEventListener('message', handleMessage);
      };
    }
  }, [navigate]);

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
            <Route path="/chat" element={
              <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
                <ChatPage />
              </Suspense>
            } />
            <Route path="/chat/topic/:id" element={
              <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
                <ChatTopicPage />
              </Suspense>
            } />
            <Route path="/account" element={
              <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
                <AccountPage />
              </Suspense>
            } />
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
          </Route>
          <Route path="/ui-kit" element={<UiKit />} />
          <Route path="/login" element={<LoginPage />} />
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
          <Route path="/admin/event-submissions" element={
            <AdminRouteWrapper>
              <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
                <AdminEventSubmissionsPage />
              </Suspense>
            </AdminRouteWrapper>
          } />
          <Route path="/admin/event-submissions/:id" element={
            <AdminRouteWrapper>
              <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
                <AdminEventSubmissionDetailPage />
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
          <Route path="/admin/outreach-metrics" element={
            <AdminRouteWrapper>
              <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
                <AdminOutreachMetricsPage />
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