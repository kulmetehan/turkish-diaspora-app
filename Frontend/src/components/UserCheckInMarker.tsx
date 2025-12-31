import { useEffect, useRef, useState } from "react";
import type { Map as MapboxMap } from "mapbox-gl";
import mapboxgl from "mapbox-gl";
import type { UserCheckIn } from "@/lib/api";

interface UserCheckInMarkerProps {
  locationId: number;
  lat: number;
  lng: number;
  users: UserCheckIn[];
  type: "single" | "cluster";
  count?: number;
  map: MapboxMap;
}

function getInitials(name: string | null | undefined): string {
  if (!name || typeof name !== "string") {
    return "??";
  }
  const trimmed = name.trim();
  if (!trimmed) {
    return "??";
  }
  const parts = trimmed.split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return trimmed.substring(0, 2).toUpperCase();
}

function createAvatarElement(user: UserCheckIn, size: number): HTMLElement {
  const el = document.createElement("div");
  el.style.width = `${size}px`;
  el.style.height = `${size}px`;
  el.style.borderRadius = "50%";
  el.style.overflow = "hidden";
  el.style.backgroundSize = "cover";
  el.style.backgroundPosition = "center";
  el.style.backgroundRepeat = "no-repeat";
  el.style.border = "2px solid #e10600";
  el.style.boxShadow = "0 2px 4px rgba(0,0,0,0.2)";

  if (user.avatar_url) {
    el.style.backgroundImage = `url(${user.avatar_url})`;
  } else {
    // Fallback: gradient with initials
    el.style.background = "linear-gradient(135deg, #e10600 0%, #ff4444 100%)";
    el.style.display = "flex";
    el.style.alignItems = "center";
    el.style.justifyContent = "center";
    el.style.color = "white";
    el.style.fontWeight = "600";
    el.style.fontSize = `${size * 0.4}px`;
    el.textContent = getInitials(user.display_name);
  }

  return el;
}

function renderPopupContent(users: UserCheckIn[], totalCount?: number): string {
  const displayUsers = totalCount ? users.slice(0, 10) : users;
  const remaining = totalCount ? totalCount - displayUsers.length : 0;

  return `
    <div style="padding: 8px; min-width: 200px;">
      <div style="font-weight: 600; margin-bottom: 8px; font-size: 14px;">
        ${totalCount ? `${totalCount} mensen hier` : "Gebruikers hier"}
      </div>
      <div style="display: flex; flex-direction: column; gap: 6px;">
        ${displayUsers
          .map(
            (user) => `
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 32px; height: 32px; border-radius: 50%; background-image: url(${
              user.avatar_url || ""
            }); background-size: cover; background-position: center; ${
              !user.avatar_url
                ? "background: linear-gradient(135deg, #e10600 0%, #ff4444 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 12px;"
                : ""
            }">
              ${!user.avatar_url ? getInitials(user.display_name) : ""}
            </div>
            <span style="font-size: 13px;">${user.display_name || "Anoniem"}</span>
          </div>
        `
          )
          .join("")}
        ${
          remaining > 0
            ? `<div style="font-size: 12px; color: #666; margin-top: 4px;">+${remaining} meer</div>`
            : ""
        }
      </div>
    </div>
  `;
}

export function UserCheckInMarker({
  locationId,
  lat,
  lng,
  users,
  type,
  count,
  map,
}: UserCheckInMarkerProps) {
  const markerRef = useRef<mapboxgl.Marker | null>(null);
  const popupRef = useRef<mapboxgl.Popup | null>(null);
  const [showPopup, setShowPopup] = useState(false);

  useEffect(() => {
    if (!map) {
      console.debug("[UserCheckInMarker] No map, skipping");
      return;
    }

    console.debug("[UserCheckInMarker] Creating marker for location", locationId, "type:", type, "users:", users.length);

    const el = document.createElement("div");
    el.className = "user-checkin-marker-container";
    el.style.position = "relative";
    el.style.width = "48px";
    el.style.height = "48px";
    el.style.cursor = "pointer";

    if (type === "single") {
      // Single user - simple avatar
      const avatar = createAvatarElement(users[0], 40);
      el.appendChild(avatar);
    } else if (type === "cluster" && count) {
      // Multiple users - stacked avatars
      const visibleUsers = users.slice(0, 3);
      const remaining = count - visibleUsers.length;

      visibleUsers.forEach((user, index) => {
        const avatar = createAvatarElement(user, 36);
        avatar.style.position = "absolute";
        avatar.style.left = `${index * 12}px`; // Offset: 12px per avatar
        avatar.style.top = `${index * -4}px`; // Slight vertical offset
        avatar.style.zIndex = `${10 - index}`;
        el.appendChild(avatar);
      });

      // Add "+N" badge if more users
      if (remaining > 0) {
        const badge = document.createElement("div");
        badge.textContent = `+${remaining}`;
        badge.style.position = "absolute";
        badge.style.right = "0";
        badge.style.bottom = "0";
        badge.style.width = "20px";
        badge.style.height = "20px";
        badge.style.borderRadius = "50%";
        badge.style.backgroundColor = "#e10600";
        badge.style.color = "white";
        badge.style.fontSize = "10px";
        badge.style.fontWeight = "600";
        badge.style.display = "flex";
        badge.style.alignItems = "center";
        badge.style.justifyContent = "center";
        badge.style.border = "2px solid #e10600";
        badge.style.zIndex = "20";
        el.appendChild(badge);
      }
    }

    // Create marker
    const marker = new mapboxgl.Marker(el)
      .setLngLat([lng, lat])
      .addTo(map);

    // Click handler
    el.addEventListener("click", () => {
      setShowPopup(true);
    });

    markerRef.current = marker;

    return () => {
      if (popupRef.current) {
        try {
          popupRef.current.remove();
        } catch (error) {
          // Ignore errors
        }
        popupRef.current = null;
      }
      try {
        marker.remove();
      } catch (error) {
        // Ignore errors
      }
      markerRef.current = null;
    };
  }, [map, lat, lng, users, type, count, locationId]);

  // Popup component
  useEffect(() => {
    if (!showPopup || !markerRef.current) return;

    const popup = new mapboxgl.Popup({ offset: 25 })
      .setLngLat([lng, lat])
      .setHTML(renderPopupContent(users, count))
      .addTo(map);

    popupRef.current = popup;

    // Close popup when clicking outside
    const handleMapClick = () => {
      setShowPopup(false);
    };
    map.once("click", handleMapClick);

    return () => {
      popup.remove();
      map.off("click", handleMapClick);
    };
  }, [showPopup, map, lat, lng, users, count]);

  return null;
}

