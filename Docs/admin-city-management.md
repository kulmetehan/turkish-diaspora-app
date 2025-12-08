---
title: City Management (Admin UI)
status: active
last_updated: 2025-01-22
scope: admin-ops
owners: [tda-core]
---

# City Management (Admin UI)

Complete guide for managing cities and districts through the admin interface, replacing manual YAML editing with a web-based management system.

## Overview

The City Management interface (`#/admin/cities`) allows authenticated admins to configure discovery grids for cities and districts through a user-friendly web interface. All changes are written directly to the database (`cities_config` and `districts_config` tables), making them immediately available to Discovery Train and other services without requiring git commits.

### Key Features

- **Full CRUD operations** for cities and districts
- **Automatic validation** of coordinates and configuration data
- **Automatic bounding box calculation** from center coordinates
- **Backup system** with automatic timestamped backups
- **Coordinate precision** support for 6 decimal places
- **Expandable districts view** per city with edit/delete functionality

## Accessing the Cities Page

1. Log in to the admin interface at `#/login`
2. After authentication, navigate to `#/admin/cities`
3. You will see an overview of all configured cities with their metrics and readiness status

For authentication setup, see [`Docs/admin-auth.md`](./admin-auth.md). For navigation help, see [`Docs/admin-navigation.md`](./admin-navigation.md).

## Adding a New City

1. Click the "Add City" button in the top right of the Cities page
2. Fill in the form:
   - **City Name**: Display name (e.g., "Rotterdam", "Den Haag")
   - **Country Code**: 2-letter ISO code (default: NL)
   - **Center Latitude**: City center latitude with 6 decimal precision (e.g., `52.157284`)
   - **Center Longitude**: City center longitude with 6 decimal precision (e.g., `4.493417`)
3. Optionally add districts during city creation (see "Adding Districts" below)
4. Click "Create" to save

The city key is automatically generated from the city name (lowercase, underscores for spaces). For example, "Den Haag" becomes `den_haag`.

### Coordinate Requirements

- Latitude: Must be between -90 and 90 degrees
- Longitude: Must be between -180 and 180 degrees
- Precision: 6 decimal places (approximately 10 cm accuracy)
- Format: Decimal degrees in WGS84 coordinate system

## Editing City Information

1. Find the city card in the Cities overview
2. Click the "Edit" button
3. Update any of the following fields:
   - City name
   - Country code
   - Center latitude
   - Center longitude
4. Click "Update" to save changes

Note: Center coordinates are loaded from the city configuration when editing, ensuring accuracy.

## Managing Districts

### Viewing Districts

1. On any city card, locate the "Districts" section
2. Click "Expand Districts" (or "▶ Expand") to view all districts for that city
3. Each district displays:
   - District name
   - Center coordinates (6 decimal precision)
   - Edit and Delete buttons

### Adding a District

1. On a city card, click "Add District"
2. Fill in the form:
   - **District Name**: Display name (e.g., "Centrum", "Zuid")
   - **Center Latitude**: District center latitude (6 decimal precision)
   - **Center Longitude**: District center longitude (6 decimal precision)
3. The bounding box is automatically calculated:
   - Latitude range: `center_lat ± 0.015`
   - Longitude range: `center_lng ± 0.015`
4. Click "Create" to save

### Editing a District

1. Expand the districts section for a city
2. Click "Edit" on the district you want to modify
3. Update the district name or center coordinates
4. The bounding box will be recalculated if coordinates change
5. Click "Update" to save

### Deleting a District

1. Expand the districts section for a city
2. Click "Delete" on the district you want to remove
3. Confirm the deletion in the dialog
4. The district is immediately removed from the configuration

## Coordinate Precision Requirements

Coordinates are displayed and entered with 6 decimal places of precision:

- **6 decimal places** ≈ **10 cm accuracy** (suitable for city/district centers)
- Example: `52.157284, 4.493417`
- Input fields use `step="0.000001"` to support this precision
- Current values are displayed below input fields with 6 decimal precision

### Finding Coordinates

Use tools like:
- Google Maps: Right-click → "What's here?" → copy coordinates
- OpenStreetMap: Right-click → "Show address" → coordinates shown
- GPS devices or mobile apps

Ensure coordinates are in WGS84 format (decimal degrees).

## Automatic Bounding Box Calculation

When adding or updating districts, bounding boxes are automatically calculated from center coordinates:

- **Latitude delta**: ±0.015 degrees (approximately ±1.67 km)
- **Longitude delta**: ±0.015 degrees (approximately ±1.04 km at 52° latitude)

Formula:
```
lat_min = center_lat - 0.015
lat_max = center_lat + 0.015
lng_min = center_lng - 0.015
lng_max = center_lng + 0.015
```

This provides a conservative bounding box that captures all relevant POIs in the district while avoiding oversampling.

## Backup Mechanism

Before each write operation, an automatic backup is created:

- **Backup location**: `Infra/config/cities.yml.backup.{YYYYMMDD_HHMMSS}`
- **Maximum backups**: 5 (older backups are automatically removed)
- **Backup timing**: Only created on successful writes
- **Recovery**: Backups can be manually restored if needed

Example backup filename: `cities.yml.backup.20250122_143022`

### Manual Backup Recovery

If needed, restore from a backup:

1. Locate the backup file in `Infra/config/`
2. Copy the backup file to `cities.yml`
3. Restart the backend to load the restored configuration

## API Reference

All operations use the following REST endpoints:

### Cities

- **GET** `/api/v1/admin/cities` - List all cities with readiness metrics
- **GET** `/api/v1/admin/cities/{city_key}` - Get full city details including districts
- **POST** `/api/v1/admin/cities` - Create a new city
- **PUT** `/api/v1/admin/cities/{city_key}` - Update city information
- **DELETE** `/api/v1/admin/cities/{city_key}` - Delete a city (also deletes all districts)

### Districts

- **POST** `/api/v1/admin/cities/{city_key}/districts` - Add a district to a city
- **PUT** `/api/v1/admin/cities/{city_key}/districts/{district_key}` - Update a district
- **DELETE** `/api/v1/admin/cities/{city_key}/districts/{district_key}` - Delete a district

All endpoints require admin authentication (see [`Docs/admin-auth.md`](./admin-auth.md)).

## Troubleshooting

### City not appearing after creation

- Verify the backend has been restarted or reloaded the configuration
- Check browser console for API errors
- Verify authentication is still valid

### Districts not loading when expanding

- Check network tab for failed API calls
- Verify the city key exists in the configuration
- Check backend logs for errors loading city details

### Coordinate validation errors

- Ensure coordinates are within valid ranges:
  - Latitude: -90 to 90
  - Longitude: -180 to 180
- Verify 6 decimal precision is used
- Check for typos or incorrect coordinate format

### YAML write errors

- Verify file permissions on `Infra/config/cities.yml`
- Check disk space availability
- Review backend logs for detailed error messages
- Restore from backup if configuration is corrupted

### Backup not created

- Check file permissions on `Infra/config/` directory
- Verify disk space is available
- Backups are only created on successful writes (errors skip backup)

## Related Documentation

- [`Docs/city-grid.md`](./city-grid.md) - YAML structure and how discovery uses city configurations
- [`Docs/admin-auth.md`](./admin-auth.md) - Authentication setup and other admin features
- [`Docs/discovery-config.md`](./discovery-config.md) - Category configuration for discovery

## Implementation Details

### Backend Components

- **Router**: `Backend/api/routers/admin_cities.py` - API endpoints
- **Service**: `Backend/services/cities_config_service.py` - YAML read/write and validation
- **Models**: `Backend/app/models/admin_cities.py` - Pydantic request/response models

### Frontend Components

- **Page**: `Frontend/src/pages/AdminCitiesPage.tsx` - Main cities overview page
- **Dialogs**: 
  - `Frontend/src/components/admin/CityFormDialog.tsx` - City add/edit form
  - `Frontend/src/components/admin/DistrictFormDialog.tsx` - District add/edit form
- **API Client**: `Frontend/src/lib/apiAdmin.ts` - API wrapper functions

### Configuration File

- **Location**: `Infra/config/cities.yml`
- **Format**: YAML with anchors and references
- **Backup location**: `Infra/config/cities.yml.backup.{timestamp}`

## Best Practices

1. **Always verify coordinates** before saving (use maps or GPS tools)
2. **Test with discovery bot** after adding new cities/districts (dry-run mode)
3. **Keep backups** before making bulk changes
4. **Use consistent naming** for city keys (lowercase, underscores)
5. **Verify districts** appear correctly after adding (expand to check)
6. **Coordinate with team** if multiple admins are editing simultaneously

