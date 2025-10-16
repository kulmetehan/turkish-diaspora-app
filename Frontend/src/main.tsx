// Frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";

// Router
import { BrowserRouter, Routes, Route } from "react-router-dom";

// Pages
import App from "./App";
import AdminPage from "./pages/AdminPage";

// Styles
import "./App.css";
import "leaflet/dist/leaflet.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Publieke kaart/app op de root */}
        <Route path="/" element={<App />} />

        {/* Admin route */}
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
