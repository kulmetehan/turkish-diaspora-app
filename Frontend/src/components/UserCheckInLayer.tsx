import { useEffect, useMemo, useRef } from "react";
import type { Map as MapboxMap } from "mapbox-gl";
import mapboxgl from "mapbox-gl";
import type { CheckInItem } from "@/lib/api";
import { CLUSTER_CONFIG } from "@/lib/config";
import { isMobile } from "@/lib/utils";
import { registerClusterSprites } from "@/components/markerLayerUtils";
import { roundDPR, renderSvgToCanvas, toBitmap } from "@/lib/map/categoryIcons";

const SRC_ID = "tda-user-checkins";
const L_CLUSTER = "tda-user-checkins-clusters";
const L_CLUSTER_COUNT = "tda-user-checkins-cluster-count";
const L_POINT = "tda-user-checkins-point";

interface UserCheckInLayerProps {
  map: MapboxMap | null;
  checkIns: CheckInItem[];
}

function buildCheckInGeoJSON(checkIns: CheckInItem[]) {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:19',message:'buildCheckInGeoJSON called',data:{checkInsCount:checkIns.length,checkIns:checkIns.map(c=>({location_id:c.location_id,lat:c.lat,lng:c.lng,usersCount:c.users.length,count:c.count}))},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  // #endregion
  const geoJson = {
    type: "FeatureCollection" as const,
    features: checkIns.map((item) => {
      const firstUser = item.users[0];
      const userCount = item.count || item.users.length;
      const iconId = firstUser?.avatar_url && firstUser?.user_id
        ? `tda-checkin-avatar-${firstUser.user_id}`
        : FALLBACK_AVATAR_ID;
      
      return {
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [item.lng, item.lat],
        },
        properties: {
          id: `checkin-${item.location_id}`,
          location_id: item.location_id,
          user_count: userCount,
          icon: iconId,
          avatar_url: firstUser?.avatar_url || null,
        },
      };
    }),
  };
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:35',message:'buildCheckInGeoJSON result',data:{featuresCount:geoJson.features.length,features:geoJson.features.map(f=>({id:f.properties.id,coords:f.geometry.coordinates,icon:f.properties.icon}))},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion
  return geoJson;
}

function getClusterConfig() {
  const mobile = isMobile();
  return {
    clusterMaxZoom: mobile ? CLUSTER_CONFIG.MOBILE_MAX_ZOOM : CLUSTER_CONFIG.MAX_ZOOM,
    clusterRadius: mobile
      ? CLUSTER_CONFIG.RADIUS * CLUSTER_CONFIG.MOBILE_RADIUS_MULTIPLIER
      : CLUSTER_CONFIG.RADIUS,
  };
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


// Track registered sprites to avoid race conditions in React Strict Mode
const registeredSprites = new Set<string>();

// Track registered avatar images to avoid race conditions in React Strict Mode
const registeredAvatars = new Set<string>();
const FALLBACK_AVATAR_ID = "tda-checkin-fallback";
const AVATAR_SIZE = 40; // Size for avatar images (matches current single user size)

/**
 * Load avatar image from URL and wrap it in SVG with red border, then convert to ImageBitmap
 */
async function loadAvatarImage(url: string, size: number = AVATAR_SIZE): Promise<ImageBitmap> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous"; // Handle CORS
    
    img.onload = () => {
      // Create SVG wrapper with red border
      const borderWidth = 2;
      const svgSize = size;
      const avatarSize = size - borderWidth * 2; // Avatar size inside border
      
      // Create a canvas to draw the avatar image
      const canvas = document.createElement("canvas");
      canvas.width = svgSize;
      canvas.height = svgSize;
      const ctx = canvas.getContext("2d");
      
      if (!ctx) {
        reject(new Error("Canvas context unavailable"));
        return;
      }
      
      // Draw shadow first (offset slightly)
      ctx.shadowColor = "rgba(0, 0, 0, 0.2)";
      ctx.shadowBlur = 4;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 2;
      
      // Draw red circle background (border)
      ctx.beginPath();
      ctx.arc(svgSize / 2, svgSize / 2, svgSize / 2 - borderWidth / 2, 0, Math.PI * 2);
      ctx.fillStyle = "#e10600";
      ctx.fill();
      
      // Reset shadow
      ctx.shadowColor = "transparent";
      ctx.shadowBlur = 0;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 0;
      
      // Draw avatar image as circle (clipped)
      ctx.save();
      ctx.beginPath();
      ctx.arc(svgSize / 2, svgSize / 2, avatarSize / 2, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(img, borderWidth, borderWidth, avatarSize, avatarSize);
      ctx.restore();
      
      // Convert to ImageBitmap
      if (typeof createImageBitmap === "function") {
        createImageBitmap(canvas)
          .then(resolve)
          .catch(reject);
      } else {
        reject(new Error("createImageBitmap is not supported"));
      }
    };
    
    img.onerror = () => {
      reject(new Error(`Failed to load avatar image from ${url}`));
    };
    
    img.src = url;
  });
}

/**
 * Register avatar image with Mapbox map
 */
function registerAvatarImage(
  map: MapboxMap,
  imageId: string,
  image: ImageBitmap,
  dpr: number
): void {
  if (!map || typeof map.addImage !== "function") return;
  
  try {
    map.addImage(imageId, image as any, { pixelRatio: dpr });
    console.debug(`[UserCheckInLayer] Registered avatar image ${imageId}`);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    if (errorMessage.includes("already exists") || errorMessage.includes("An image with the name")) {
      // Image already exists - expected in React Strict Mode
      console.debug(`[UserCheckInLayer] Avatar image ${imageId} already registered`);
    } else {
      console.warn(`[UserCheckInLayer] Failed to register avatar image ${imageId}:`, error);
      throw error;
    }
  }
}

/**
 * Create fallback avatar SVG with initials and gradient background
 */
function createFallbackAvatarSVG(initials: string, size: number): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <defs>
      <linearGradient id="avatar-gradient-${size}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#e10600;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#ff4444;stop-opacity:1" />
      </linearGradient>
    </defs>
    <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}" fill="url(#avatar-gradient-${size})" />
    <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}" fill="none" stroke="#e10600" stroke-width="2" />
    <text x="${size / 2}" y="${size / 2}" font-family="Arial, sans-serif" font-size="${size * 0.4}" font-weight="600" fill="white" text-anchor="middle" dominant-baseline="central">${initials}</text>
  </svg>`;
}

/**
 * Register fallback avatar image (initials-based)
 */
async function registerFallbackAvatar(map: MapboxMap, dpr: number): Promise<void> {
  if (!map || typeof map.addImage !== "function") return;
  
  // Check if already registered
  if (registeredAvatars.has(FALLBACK_AVATAR_ID) || map.hasImage?.(FALLBACK_AVATAR_ID)) {
    return;
  }
  
  // Mark as being processed IMMEDIATELY to prevent race conditions
  registeredAvatars.add(FALLBACK_AVATAR_ID);
  
  try {
    const initials = "??"; // Default initials for fallback
    const svg = createFallbackAvatarSVG(initials, AVATAR_SIZE);
    const canvas = await renderSvgToCanvas(svg, AVATAR_SIZE, dpr);
    const bitmap = await toBitmap(canvas);
    
    try {
      registerAvatarImage(map, FALLBACK_AVATAR_ID, bitmap, dpr);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes("already exists") || errorMessage.includes("An image with the name")) {
        // Already registered, skip silently
        return;
      }
      // Registration failed - remove from Set to allow retry
      registeredAvatars.delete(FALLBACK_AVATAR_ID);
      throw error;
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    if (errorMessage.includes("already exists") || errorMessage.includes("An image with the name")) {
      // Already registered, skip silently
      return;
    }
    // Registration failed - remove from Set to allow retry
    registeredAvatars.delete(FALLBACK_AVATAR_ID);
    console.warn(`[UserCheckInLayer] Failed to register fallback avatar:`, error);
  }
}

/**
 * Ensure all required avatar images are registered with Mapbox
 */
async function ensureAvatarImages(map: MapboxMap, checkIns: CheckInItem[]): Promise<void> {
  if (!map || typeof map.addImage !== "function") return;
  
  const dpr = roundDPR(typeof window !== "undefined" ? window.devicePixelRatio : 1);
  
  // Always register fallback avatar first
  await registerFallbackAvatar(map, dpr);
  
  // Collect unique avatar URLs from check-ins
  const avatarTasks: Promise<void>[] = [];
  const processedUserIds = new Set<string>();
  
  for (const item of checkIns) {
    const firstUser = item.users[0];
    if (!firstUser?.avatar_url || !firstUser?.user_id) continue;
    
    // Skip if already processed or registered
    if (processedUserIds.has(firstUser.user_id)) continue;
    
    const imageId = `tda-checkin-avatar-${firstUser.user_id}`;
    
    // Check if already registered
    if (registeredAvatars.has(imageId) || map.hasImage?.(imageId)) {
      processedUserIds.add(firstUser.user_id);
      continue;
    }
    
    // Mark as being processed IMMEDIATELY to prevent race conditions
    registeredAvatars.add(imageId);
    processedUserIds.add(firstUser.user_id);
    
    // Create async task to load and register avatar
    const task = (async () => {
      try {
        const bitmap = await loadAvatarImage(firstUser.avatar_url!, AVATAR_SIZE);
        
        try {
          registerAvatarImage(map, imageId, bitmap, dpr);
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          if (errorMessage.includes("already exists") || errorMessage.includes("An image with the name")) {
            // Already registered, skip silently
            return;
          }
          // Registration failed - remove from Set to allow retry
          registeredAvatars.delete(imageId);
          throw error;
        }
      } catch (error) {
        // Image load failed - remove from Set and fallback will be used
        registeredAvatars.delete(imageId);
        console.warn(`[UserCheckInLayer] Failed to load avatar for user ${firstUser.user_id}:`, error);
        // Don't throw - fallback avatar will be used via coalesce expression
      }
    })();
    
    avatarTasks.push(task);
  }
  
  // Wait for all avatar images to load (or fail gracefully)
  await Promise.allSettled(avatarTasks);
}

async function ensureClusterSprites(map: MapboxMap) {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:146',message:'ensureClusterSprites called',data:{hasMap:!!map,hasAddImage:typeof map?.addImage==='function',hasHasImage:typeof map?.hasImage==='function',registeredSpritesCount:registeredSprites.size},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
  // #endregion
  if (!map || typeof map.addImage !== "function") return;

  const dpr = roundDPR(typeof window !== "undefined" ? window.devicePixelRatio : 1);
  const CLUSTER_BG_RGBA = "rgba(225, 6, 0, 0.3)";
  const CLUSTER_RADIUS = 12;

  function generateClusterSprite(size: number): string {
    const filterId = `checkin-cluster-shadow-${size}`;
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <defs>
        <filter id="${filterId}" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
          <feOffset dx="0" dy="1" result="offsetblur"/>
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.3"/>
          </feComponentTransfer>
          <feMerge>
            <feMergeNode/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      <rect x="0" y="0" width="${size}" height="${size}" rx="${CLUSTER_RADIUS}" ry="${CLUSTER_RADIUS}" 
            fill="${CLUSTER_BG_RGBA}" stroke="none" filter="url(#${filterId})" />
    </svg>`;
  }

  const spriteConfigs = [
    { id: "tda-checkin-cluster-small", size: 32 },
    { id: "tda-checkin-cluster-medium", size: 40 },
    { id: "tda-checkin-cluster-large", size: 48 },
  ];

  for (const config of spriteConfigs) {
    // Check both our tracking set and Mapbox's hasImage (defensive check)
    if (registeredSprites.has(config.id) || map.hasImage?.(config.id)) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:178',message:'Sprite already registered, skipping',data:{spriteId:config.id,inSet:registeredSprites.has(config.id),hasImage:map.hasImage?.(config.id)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
      // #endregion
      continue;
    }

    // Mark as being processed IMMEDIATELY to prevent race conditions
    // This ensures that concurrent calls in React Strict Mode will skip this sprite
    registeredSprites.add(config.id);

    try {
      const svg = generateClusterSprite(config.size);
      const canvas = await renderSvgToCanvas(svg, config.size, dpr);
      const bitmap = await toBitmap(canvas);
      // Wrap addImage in try-catch to catch the error immediately
      try {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:188',message:'Attempting to add sprite image',data:{spriteId:config.id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
        // #endregion
        map.addImage(config.id, bitmap as any, { pixelRatio: dpr });
        console.debug(`[UserCheckInLayer] Registered sprite ${config.id}`);
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:191',message:'Sprite registered successfully',data:{spriteId:config.id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
        // #endregion
      } catch (addImageError) {
        // If error is about image already existing, it's already tracked in Set, so just ignore silently
        const errorMessage = addImageError instanceof Error ? addImageError.message : String(addImageError);
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:195',message:'addImage error caught',data:{spriteId:config.id,errorMessage,isAlreadyExists:errorMessage.includes("already exists")||errorMessage.includes("An image with the name")},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
        // #endregion
        if (errorMessage.includes("already exists") || errorMessage.includes("An image with the name")) {
          // Image already exists - already tracked in Set, skip silently
          // This is expected in React strict mode
          continue;
        }
        // Re-throw other errors - but remove from Set since registration failed
        registeredSprites.delete(config.id);
        throw addImageError;
      }
    } catch (error) {
      // Catch any other errors (e.g., from SVG generation or canvas conversion)
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes("already exists") || errorMessage.includes("An image with the name")) {
        // Image already exists - already tracked in Set, skip silently
        continue;
      }
      // Registration failed - remove from Set to allow retry
      registeredSprites.delete(config.id);
      // Only warn for other errors
      console.warn(`[UserCheckInLayer] Failed to register check-in cluster sprite ${config.id}:`, error);
    }
  }
}

function ensureLayers(map: MapboxMap, config: { clusterMaxZoom: number; clusterRadius: number }) {
  console.debug("[UserCheckInLayer] ensureLayers called");
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:208',message:'ensureLayers called',data:{config,sourceExists:!!map.getSource(SRC_ID),layerExists:!!map.getLayer(L_CLUSTER)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
  // #endregion
  
  if (!map.getSource(SRC_ID)) {
    console.debug("[UserCheckInLayer] Adding source:", SRC_ID);
    map.addSource(SRC_ID, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
      cluster: true,
      clusterMaxZoom: config.clusterMaxZoom,
      clusterRadius: config.clusterRadius,
      promoteId: "id",
    } as any);
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:220',message:'Source added',data:{srcId:SRC_ID,config},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
  } else {
    console.debug("[UserCheckInLayer] Source already exists:", SRC_ID);
  }

  if (!map.getLayer(L_CLUSTER)) {
    console.debug("[UserCheckInLayer] Adding layer:", L_CLUSTER);
    map.addLayer({
      id: L_CLUSTER,
      type: "symbol",
      source: SRC_ID,
      filter: ["has", "point_count"],
      layout: {
        "icon-image": [
          "step",
          ["get", "point_count"],
          "tda-checkin-cluster-small",
          25,
          "tda-checkin-cluster-medium",
          100,
          "tda-checkin-cluster-large",
        ],
        "icon-size": 1.0,
        "icon-anchor": "center",
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
        // Add text-field to show cluster count numbers
        "text-field": [
          "to-string",
          ["get", "point_count"],
        ],
        "text-size": [
          "step",
          ["get", "point_count"],
          12, // 12px for small clusters (≤24)
          25,
          14, // 14px for medium clusters (25-99)
          100,
          16, // 16px for large clusters (100+)
        ],
        "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
        "text-offset": [0, 0], // Center text on icon
        "text-optional": false, // Always show text (count is essential)
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": "#ffffff", // White text on semi-transparent red background
        "text-halo-color": "#e10600", // Red halo for readability
        "text-halo-width": 1.5,
        "text-halo-blur": 0.5,
      },
    });
    console.debug("[UserCheckInLayer] Layer added:", L_CLUSTER);
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:254',message:'Layer added with text-field',data:{layerId:L_CLUSTER,sourceId:SRC_ID},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
  } else {
    console.debug("[UserCheckInLayer] Layer already exists:", L_CLUSTER);
  }

  // Create symbol layer for individual check-in points (non-clustered)
  if (!map.getLayer(L_POINT)) {
    console.debug("[UserCheckInLayer] Adding layer:", L_POINT);
    map.addLayer({
      id: L_POINT,
      type: "symbol",
      source: SRC_ID,
      filter: ["!", ["has", "point_count"]], // Only non-clustered points
      layout: {
        "icon-image": [
          "coalesce",
          ["image", ["get", "icon"]],
          ["image", FALLBACK_AVATAR_ID],
        ],
        "icon-size": 1.6, // Scale to ~64px (40px * 1.6) to match location marker size
        "icon-anchor": "center",
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
        // Add text-field for user count badge when multiple users
        "text-field": [
          "case",
          [">", ["get", "user_count"], 1],
          [
            "concat",
            "+",
            ["to-string", ["-", ["get", "user_count"], 1]],
          ],
          "",
        ],
        "text-size": 10,
        "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
        "text-offset": [0.4, 0.4], // Position badge at bottom-right
        "text-anchor": "left",
        "text-optional": true, // Only show when user_count > 1
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": "#ffffff",
        "text-halo-color": "#e10600",
        "text-halo-width": 1,
        "text-halo-blur": 0.5,
      },
    });
    console.debug("[UserCheckInLayer] Layer added:", L_POINT);
  } else {
    console.debug("[UserCheckInLayer] Layer already exists:", L_POINT);
  }
}

function removeLayers(map: MapboxMap) {
  const layers = [L_CLUSTER_COUNT, L_POINT, L_CLUSTER];
  for (const layerId of layers) {
    try {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
    } catch {
      // Ignore
    }
  }
}

export default function UserCheckInLayer({ map, checkIns }: UserCheckInLayerProps) {
  console.debug("[UserCheckInLayer] Component rendered. map:", !!map, "checkIns count:", checkIns?.length || 0, "checkIns:", checkIns);
  
  const layersReadyRef = useRef(false);
  const checkInsDataRef = useRef<Map<number, CheckInItem>>(new Map());
  const clusterClickHandlerRef = useRef<((e: any) => void) | null>(null);
  const pointClickHandlerRef = useRef<((e: any) => void) | null>(null);
  const config = useMemo(() => getClusterConfig(), []);

  useEffect(() => {
    checkInsDataRef.current.clear();
    checkIns.forEach((item) => {
      checkInsDataRef.current.set(item.location_id, item);
    });
  }, [checkIns]);

  useEffect(() => {
    if (!map) return;

    function tryInitLayers() {
      if (layersReadyRef.current) return;
      // Register cluster sprites and avatar images, then create layers
      // Use checkIns from closure or checkInsDataRef as fallback
      const currentCheckIns = checkIns.length > 0 ? checkIns : Array.from(checkInsDataRef.current.values());
      Promise.resolve(ensureClusterSprites(map))
        .then(() => ensureAvatarImages(map, currentCheckIns))
        .then(() => {
          ensureLayers(map, config);
          // Verify layers were created
          if (map.getLayer(L_CLUSTER)) {
            layersReadyRef.current = true;
            
            // Register cluster click handler after layers are ready
            const handleClusterClick = (e: any) => {
              const features = map.queryRenderedFeatures(e.point, {
                layers: [L_CLUSTER],
              });

              if (!features.length) return;

              const feature = features[0];
              const clusterId = feature.properties?.cluster_id;

              if (clusterId !== undefined) {
                const source = map.getSource(SRC_ID) as any;
                if (source?.getClusterExpansionZoom) {
                  source.getClusterExpansionZoom(clusterId, (err: unknown, zoom: number) => {
                    if (err) {
                      return;
                    }
                    const center = (feature.geometry as any).coordinates;
                    // Ensure we zoom at least to clusterMaxZoom + 1 to show individual markers
                    const targetZoom = Math.max(zoom, config.clusterMaxZoom + 1);
                    map.easeTo({ center, zoom: targetZoom });
                  });
                }
              }
            };
            
            map.on("click", L_CLUSTER, handleClusterClick);
            clusterClickHandlerRef.current = handleClusterClick;
            
            // Register point click handler for individual check-ins
            const handlePointClick = (e: any) => {
              const features = map.queryRenderedFeatures(e.point, {
                layers: [L_POINT],
              });

              if (!features.length) return;

              const feature = features[0];
              const locationId = feature.properties?.location_id;
              const userCount = feature.properties?.user_count || 1;
              
              if (!locationId) return;
              
              // Get check-in data for popup
              const checkInData = checkInsDataRef.current.get(locationId);
              if (!checkInData) return;
              
              const users = checkInData.users;
              const popupHtml = `
                <div style="padding: 8px; min-width: 200px;">
                  <div style="font-weight: 600; margin-bottom: 8px; font-size: 14px;">
                    ${userCount} ${userCount === 1 ? "persoon" : "personen"} hier
                  </div>
                  <div style="display: flex; flex-direction: column; gap: 6px;">
                    ${users.slice(0, 10).map((user) => `
                      <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background-image: url(${user.avatar_url || ""}); background-size: cover; background-position: center; border: 2px solid #e10600; ${
                          !user.avatar_url
                            ? "background: linear-gradient(135deg, #e10600 0%, #ff4444 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 12px;"
                            : ""
                        }">
                          ${!user.avatar_url ? getInitials(user.display_name) : ""}
                        </div>
                        <span style="font-size: 13px;">${user.display_name || "Anoniem"}</span>
                      </div>
                    `).join("")}
                    ${userCount > 10 ? `<div style="font-size: 12px; color: #666; margin-top: 4px;">+${userCount - 10} meer</div>` : ""}
                  </div>
                </div>
              `;

              new mapboxgl.Popup({ offset: 25 })
                .setLngLat([checkInData.lng, checkInData.lat])
                .setHTML(popupHtml)
                .addTo(map);
            };
            
            map.on("click", L_POINT, handlePointClick);
            pointClickHandlerRef.current = handlePointClick;
            
            // Add mouse cursor handlers
            const handleMouseEnter = () => {
              try {
                map.getCanvas().style.cursor = "pointer";
              } catch {
                // Ignore
              }
            };
            
            const handleMouseLeave = () => {
              try {
                map.getCanvas().style.cursor = "";
              } catch {
                // Ignore
              }
            };
            
            map.on("mouseenter", L_POINT, handleMouseEnter);
            map.on("mouseleave", L_POINT, handleMouseLeave);
          } else {
            console.warn("[UserCheckInLayer] Layer failed to initialize");
            layersReadyRef.current = true; // Still mark as ready to avoid blocking
          }
        })
        .catch((error) => {
          // Catch any errors from ensureClusterSprites (e.g., sprite registration errors)
          // These are expected in React strict mode and can be ignored
          const errorMessage = error instanceof Error ? error.message : String(error);
          if (errorMessage.includes("already exists") || errorMessage.includes("An image with the name")) {
            // Sprite already exists, which is fine - continue with layer initialization
            console.debug("[UserCheckInLayer] Sprite registration error (expected in strict mode), continuing");
          } else {
            console.warn("[UserCheckInLayer] Error in ensureClusterSprites or ensureAvatarImages:", error);
          }
          // Still try to initialize layers even if sprite/avatar registration failed
          // Avatar images will fallback to default via coalesce expression
          ensureLayers(map, config);
          if (map.getLayer(L_CLUSTER)) {
            layersReadyRef.current = true;
            // Register cluster click handler even if sprite registration failed
            const handleClusterClick = (e: any) => {
              const features = map.queryRenderedFeatures(e.point, {
                layers: [L_CLUSTER],
              });
              if (!features.length) return;
              const feature = features[0];
              const clusterId = feature.properties?.cluster_id;
              if (clusterId !== undefined) {
                const source = map.getSource(SRC_ID) as any;
                if (source?.getClusterExpansionZoom) {
                  source.getClusterExpansionZoom(clusterId, (err: unknown, zoom: number) => {
                    if (err) return;
                    const center = (feature.geometry as any).coordinates;
                    // Ensure we zoom at least to clusterMaxZoom + 1 to show individual markers
                    const targetZoom = Math.max(zoom, config.clusterMaxZoom + 1);
                    map.easeTo({ center, zoom: targetZoom });
                  });
                }
              }
            };
            map.on("click", L_CLUSTER, handleClusterClick);
            clusterClickHandlerRef.current = handleClusterClick;
            
            // Register point click handler for individual check-ins (if layer exists)
            if (map.getLayer(L_POINT)) {
              const handlePointClick = (e: any) => {
                const features = map.queryRenderedFeatures(e.point, {
                  layers: [L_POINT],
                });

                if (!features.length) return;

                const feature = features[0];
                const locationId = feature.properties?.location_id;
                const userCount = feature.properties?.user_count || 1;
                
                if (!locationId) return;
                
                // Get check-in data for popup
                const checkInData = checkInsDataRef.current.get(locationId);
                if (!checkInData) return;
                
                const users = checkInData.users;
                const popupHtml = `
                  <div style="padding: 8px; min-width: 200px;">
                    <div style="font-weight: 600; margin-bottom: 8px; font-size: 14px;">
                      ${userCount} ${userCount === 1 ? "persoon" : "personen"} hier
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                      ${users.slice(0, 10).map((user) => `
                        <div style="display: flex; align-items: center; gap: 8px;">
                          <div style="width: 32px; height: 32px; border-radius: 50%; background-image: url(${user.avatar_url || ""}); background-size: cover; background-position: center; border: 2px solid #e10600; ${
                            !user.avatar_url
                              ? "background: linear-gradient(135deg, #e10600 0%, #ff4444 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 12px;"
                              : ""
                          }">
                            ${!user.avatar_url ? getInitials(user.display_name) : ""}
                          </div>
                          <span style="font-size: 13px;">${user.display_name || "Anoniem"}</span>
                        </div>
                      `).join("")}
                      ${userCount > 10 ? `<div style="font-size: 12px; color: #666; margin-top: 4px;">+${userCount - 10} meer</div>` : ""}
                    </div>
                  </div>
                `;

                new mapboxgl.Popup({ offset: 25 })
                  .setLngLat([checkInData.lng, checkInData.lat])
                  .setHTML(popupHtml)
                  .addTo(map);
              };
              
              map.on("click", L_POINT, handlePointClick);
              pointClickHandlerRef.current = handlePointClick;
              
              // Add mouse cursor handlers
              const handleMouseEnter = () => {
                try {
                  map.getCanvas().style.cursor = "pointer";
                } catch {
                  // Ignore
                }
              };
              
              const handleMouseLeave = () => {
                try {
                  map.getCanvas().style.cursor = "";
                } catch {
                  // Ignore
                }
              };
              
              map.on("mouseenter", L_POINT, handleMouseEnter);
              map.on("mouseleave", L_POINT, handleMouseLeave);
            }
          } else {
            layersReadyRef.current = true; // Still mark as ready to avoid blocking
          }
        });
    }

    // Check if style is ready using same pattern as MarkerLayer
    let hasStyle = false;
    try {
      const style = map.getStyle?.();
      hasStyle = !!style && !!(style as any).sources;
    } catch {
      hasStyle = false;
    }


    if (!hasStyle) {
      // Style not ready yet: wait for load event
      const handleLoad = () => {
        tryInitLayers();
      };
      map.once("load", handleLoad);
      return () => {
        try {
          map.off("load", handleLoad);
        } catch {
          // Ignore
        }
      };
    }

    // Style is ready: initialize immediately
    tryInitLayers();

    return () => {
      // Remove click handlers
      if (clusterClickHandlerRef.current) {
        try {
          map.off("click", L_CLUSTER, clusterClickHandlerRef.current);
          clusterClickHandlerRef.current = null;
        } catch {
          // Ignore
        }
      }
      if (pointClickHandlerRef.current) {
        try {
          map.off("click", L_POINT, pointClickHandlerRef.current);
          map.off("mouseenter", L_POINT);
          map.off("mouseleave", L_POINT);
          pointClickHandlerRef.current = null;
        } catch {
          // Ignore
        }
      }
      removeLayers(map);
      try {
        if (map.getSource(SRC_ID)) {
          map.removeSource(SRC_ID);
        }
      } catch {
        // Ignore
      }
      layersReadyRef.current = false;
    };
  }, [map, config]);

  useEffect(() => {
    console.debug("[UserCheckInLayer] Data update effect triggered. checkIns:", checkIns.length, "map:", !!map, "layersReady:", layersReadyRef.current);
    
    if (!map || !layersReadyRef.current) {
      console.debug("[UserCheckInLayer] Skipping data update - map:", !!map, "layersReady:", layersReadyRef.current);
      return;
    }

    // Check if style is loaded
    const hasStyle = map.getStyle() && map.isStyleLoaded();
    if (!hasStyle) {
      console.debug("[UserCheckInLayer] Style not loaded yet, skipping data update");
      return;
    }

    const source = map.getSource(SRC_ID) as any;
    if (!source) {
      console.warn("[UserCheckInLayer] Source not found, ensuring layers...");
      void ensureClusterSprites(map)
        .then(() => ensureAvatarImages(map, checkIns))
        .then(() => {
          ensureLayers(map, config);
          layersReadyRef.current = true;
          // Retry setting data after layers are created
          const retrySource = map.getSource(SRC_ID) as any;
          if (retrySource?.setData) {
            const geoJson = buildCheckInGeoJSON(checkIns);
            retrySource.setData(geoJson);
            console.debug("[UserCheckInLayer] Data set after layer creation");
          }
        });
      return;
    }

    // Ensure avatar images are registered before setting data
    void ensureAvatarImages(map, checkIns)
      .then(() => {
        if (source.setData) {
          const geoJson = buildCheckInGeoJSON(checkIns);
          console.debug("[UserCheckInLayer] Setting GeoJSON data:", geoJson.features.length, "features");
          if (geoJson.features.length > 0) {
            console.debug("[UserCheckInLayer] GeoJSON sample:", JSON.stringify(geoJson.features[0] || {}, null, 2));
          }
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:459',message:'Before setData',data:{featuresCount:geoJson.features.length,sourceExists:!!source,hasSetData:!!source.setData},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
          // #endregion
          try {
            source.setData(geoJson);
            console.debug("[UserCheckInLayer] Data set successfully");
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:466',message:'After setData success',data:{featuresCount:geoJson.features.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
            
            // Verify the data was set
            const verifySource = map.getSource(SRC_ID) as any;
            if (verifySource?._data) {
              const featureCount = verifySource._data.features?.length || 0;
              console.debug("[UserCheckInLayer] Verified data in source:", featureCount, "features");
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:473',message:'Verified source data',data:{featureCount,expectedCount:geoJson.features.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
              // #endregion
            } else {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:476',message:'Source _data not available',data:{hasSource:!!verifySource},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
              // #endregion
            }
          } catch (error) {
            console.error("[UserCheckInLayer] Error setting data:", error);
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:476',message:'setData error',data:{error:String(error),errorMessage:error instanceof Error?error.message:'unknown'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
          }
        } else {
          console.warn("[UserCheckInLayer] Source setData method not available");
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'UserCheckInLayer.tsx:479',message:'setData method not available',data:{hasSource:!!source,sourceType:typeof source},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
          // #endregion
        }
      })
      .catch((error) => {
        console.warn("[UserCheckInLayer] Error ensuring avatar images:", error);
        // Still try to set data - fallback avatar will be used
        if (source.setData) {
          const geoJson = buildCheckInGeoJSON(checkIns);
          try {
            source.setData(geoJson);
          } catch (setDataError) {
            console.error("[UserCheckInLayer] Error setting data after avatar registration failure:", setDataError);
          }
        }
      });
  }, [map, checkIns, config]);


  // Toggle cluster layer visibility based on zoom (markers are always visible)
  useEffect(() => {
    if (!map || !layersReadyRef.current) return;

    const updateClusterVisibility = () => {
      const zoom = map.getZoom();
      const clusterMaxZoom = config.clusterMaxZoom;
      const source = map.getSource(SRC_ID) as any;
      
      if (!source) return;

      try {
        const clusterLayer = map.getLayer(L_CLUSTER);
        if (clusterLayer) {
          if (zoom > clusterMaxZoom) {
            map.setLayoutProperty(L_CLUSTER, "visibility", "none");
            console.debug("[UserCheckInLayer] Hiding cluster layer at zoom", zoom);
          } else {
            map.setLayoutProperty(L_CLUSTER, "visibility", "visible");
            console.debug("[UserCheckInLayer] Showing cluster layer at zoom", zoom);
          }
        }
      } catch (error) {
        console.warn("[UserCheckInLayer] Error toggling cluster layer visibility:", error);
      }
    };

    updateClusterVisibility();
    map.on("zoomend", updateClusterVisibility);
    map.on("moveend", updateClusterVisibility);

    return () => {
      map.off("zoomend", updateClusterVisibility);
      map.off("moveend", updateClusterVisibility);
    };
  }, [map, config]);


  return null;
}
