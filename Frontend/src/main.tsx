// Frontend/src/main.tsx
import React, { Suspense } from "react";
import ReactDOM from "react-dom/client";
import { HashRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import "leaflet/dist/leaflet.css";
import "mapbox-gl/dist/mapbox-gl.css";
import App from "./App";
import "./index.css";

import { FooterTabs } from "@/components/FooterTabs";
import RequireAdmin from "@/components/auth/RequireAdmin";
import { Toaster } from "@/components/ui/toaster";
import { initTheme } from "@/lib/theme/darkMode";
import { initI18n } from "@/i18n";
const AdminHomePage = React.lazy(() => import("@/pages/AdminHomePage"));
const AdminCitiesPage = React.lazy(() => import("@/pages/AdminCitiesPage"));
const AdminEventSourcesPage = React.lazy(() => import("@/pages/admin/AdminEventSourcesPage"));
const AdminEventsPage = React.lazy(() => import("@/pages/AdminEventsPage"));
const WorkersDashboardPage = React.lazy(() => import("@/pages/WorkersDashboardPage"));
const WorkerRunDetailPage = React.lazy(() => import("@/pages/WorkerRunDetailPage"));
import LoginPage from "@/pages/LoginPage";
import UiKit from "@/pages/UiKit";
import AccountPage from "@/pages/AccountPage";
import EventsPage from "@/pages/EventsPage";
import FeedPage from "@/pages/FeedPage";
import NewsPage from "@/pages/NewsPage";

// Vite levert dit via 'base' (bv. "/turkish-diaspora-app/") voor GitHub Pages builds.

initTheme();
initI18n();

function AppLayout() {
  return (
    <div className="flex min-h-[100svh] flex-col bg-background overflow-hidden">
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
      <FooterTabs />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HashRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/map" replace />} />
          <Route path="/map" element={<App />} />
          <Route path="/feed" element={<FeedPage />} />
          <Route path="/news" element={<NewsPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/account" element={<AccountPage />} />
        </Route>
        <Route path="/ui-kit" element={<UiKit />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin" element={
          <RequireAdmin>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminHomePage />
            </Suspense>
          </RequireAdmin>
        } />
        <Route path="/admin/cities" element={
          <RequireAdmin>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminCitiesPage />
            </Suspense>
          </RequireAdmin>
        } />
        <Route path="/admin/workers" element={
          <RequireAdmin>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <WorkersDashboardPage />
            </Suspense>
          </RequireAdmin>
        } />
        <Route path="/admin/event-sources" element={
          <RequireAdmin>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminEventSourcesPage />
            </Suspense>
          </RequireAdmin>
        } />
        <Route path="/admin/events" element={
          <RequireAdmin>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <AdminEventsPage />
            </Suspense>
          </RequireAdmin>
        } />
        <Route path="/admin/workers/runs/:runId" element={
          <RequireAdmin>
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Laden...</div>}>
              <WorkerRunDetailPage />
            </Suspense>
          </RequireAdmin>
        } />
        {/* Catch-all naar map */}
        <Route path="*" element={<Navigate to="/map" replace />} />
      </Routes>
      <Toaster position="top-right" />
    </HashRouter>
  </React.StrictMode>
);