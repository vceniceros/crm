# 0009 — Fix Map CORS/PNA Blocked Requests + Leaflet Fallback

## Problem

When loading a ticket location in production, the map fails with:

```
No se pudo cargar el mapa
AJAXError: Gateway Timeout (504): https://map.microtv.ar/argentina/styles/basic-preview/style.json
```

Browser console:

```
Access to fetch at 'https://map.microtv.ar/argentina/styles/basic-preview/style.json'
from origin 'https://crm.ycc.group' has been blocked by CORS policy:
Permission was denied for this request to access the `local` address space.
```

**Root cause:** Chrome's [Private Network Access (PNA)](https://developer.chrome.com/blog/private-network-access-update) policy blocks requests from a public origin (`crm.ycc.group`) to a resource that resolves to a private/local IP address from the client's perspective. `map.microtv.ar` resolves to `190.137.229.167:8011` which is treated as a private address space by the policy. The tile server cannot receive a `Access-Control-Request-Private-Network` preflight header response because the 504 Gateway Timeout prevents the response from ever arriving.

The secondary issue is that there is no resilience layer: when the tile server is unreachable or the style URL changes, the component immediately shows a hard error with no fallback rendering.

---

## Architecture Decision

**Option A (add PNA headers on map server nginx):** Not available — no access to `map.microtv.ar` nginx.

**Option B (proxy tiles through `crm.ycc.group`):** Chosen. Add a `/map-tiles/` location block to the existing `crm.ycc.group` nginx reverse proxy. The browser only talks to `crm.ycc.group` (public → public), so PNA never triggers. CORS headers are emitted by our own proxy.

**Leaflet + OpenStreetMap fallback:** Silent. If MapLibre fails to initialize (any reason: timeout, CORS, invalid style URL, network error), the component automatically retries with Leaflet and OSM tiles. No UI indicator is shown to the user.

---

## Phase 1 — Server: Nginx Proxy

### 1.1 Add `/map-tiles/` location block to `crm.ycc.group` nginx

Apply this block inside the existing `server { ... }` for `crm.ycc.group`, after the current location blocks. The proxy target is `http://190.137.229.167:8011/`.

```nginx
location /map-tiles/ {
  proxy_pass http://190.137.229.167:8011/;
  proxy_http_version 1.1;
  proxy_set_header Host $http_host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;

  # CORS headers so MapLibre fetch succeeds
  add_header Access-Control-Allow-Origin "https://crm.ycc.group" always;
  add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
  add_header Access-Control-Allow-Headers "Content-Type" always;

  # Preflight fast response
  if ($request_method = 'OPTIONS') {
    add_header Access-Control-Allow-Origin "https://crm.ycc.group";
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
    add_header Access-Control-Max-Age 86400;
    return 204;
  }

  proxy_read_timeout 30s;
  proxy_connect_timeout 10s;
}
```

> **Note:** The `/map-tiles/` prefix does not collide with any existing location blocks (`/api/`, `/media/`, `/images/`, `/videos/`, `/v1/`).

### 1.2 Update `DEPLOY.md` §11

Add the block above to the nginx snippet in `DEPLOY.md` §11 so the runbook stays accurate.

### 1.3 Update `DEPLOY.md` §7.3 and `.env.example`

Change `NEXT_PUBLIC_MAP_STYLE_URL` in both the production `.env` template (§7.3) and `microtv-crm-frontend/.env.example`:

```diff
- NEXT_PUBLIC_MAP_STYLE_URL=https://map.microtv.ar/argentina/styles/basic-preview/style.json
+ NEXT_PUBLIC_MAP_STYLE_URL=https://crm.ycc.group/map-tiles/argentina/styles/basic-preview/style.json
```

### 1.4 Manual steps on production server

> These are out-of-repo server operations, not automated by a script.

```bash
# 1. Edit the nginx vhost for crm.ycc.group (in HestiaCP or directly in /etc/nginx/)
#    Add the /map-tiles/ location block from §1.1

# 2. Test nginx config
sudo nginx -t

# 3. Reload nginx (zero-downtime)
sudo nginx -s reload

# 4. Update the live frontend .env
nano /opt/ycc/microtv-crm-ycc/microtv-crm-frontend/.env
# Change NEXT_PUBLIC_MAP_STYLE_URL to the /map-tiles/ URL

# 5. Sync runtime config and rebuild frontend
cd /opt/ycc/microtv-crm-ycc/microtv-crm-frontend
npm run build

# 6. Restart frontend service
sudo systemctl restart ycc-crm-frontend

# 7. Verify proxy works
curl -I https://crm.ycc.group/map-tiles/argentina/styles/basic-preview/style.json
# Expected: HTTP/2 200 with Content-Type: application/json
```

---

## Phase 2 — Frontend: Leaflet Silent Fallback

### 2.1 Add Leaflet dependency

**File:** `microtv-crm-frontend/package.json`

```json
// dependencies
"leaflet": "^1.9.4"

// devDependencies
"@types/leaflet": "^1.9.14"
```

Install locally: `npm install leaflet @types/leaflet --save` / `--save-dev`

### 2.2 Add Leaflet CSS to angular.json

**File:** `microtv-crm-frontend/angular.json`

Add to the `styles` array of both `build` and `test` targets:

```json
"node_modules/leaflet/dist/leaflet.css"
```

### 2.3 Modify `location-picker-map.component.ts`

**File:** `microtv-crm-frontend/src/app/shared/ui/location-picker-map/location-picker-map.component.ts`

#### Add private fields

```typescript
private leafletInstance: import('leaflet').Map | null = null;
private leafletMarkers: import('leaflet').Marker[] = [];
private leafletModule: typeof import('leaflet') | null = null;
private usingLeafletFallback = false;
```

#### Change the `initializeMap()` catch block

Before (sets error directly):
```typescript
.catch((error: unknown) => {
  this.state.set('error');
  this.errorMessage.set(this.resolveMapErrorMessage(error));
})
```

After (tries Leaflet first):
```typescript
.catch(async (error: unknown) => {
  try {
    await this.initLeafletFallback();
  } catch {
    this.state.set('error');
    this.errorMessage.set(this.resolveMapErrorMessage(error));
  }
})
```

#### New `initLeafletFallback()` method

```typescript
private async initLeafletFallback(): Promise<void> {
  const mapElement = this.mapCanvas?.nativeElement;
  if (!mapElement) throw new Error('No map container');

  const L = await import('leaflet');
  this.leafletModule = L;
  this.usingLeafletFallback = true;

  const center = this.resolveInitialCenter();
  const zoom = this.resolveInitialZoom();

  const map = L.map(mapElement, { preferCanvas: true });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map);
  map.setView([center.lat, center.lon], zoom);

  if (!this.readOnly()) {
    map.on('click', (event: import('leaflet').LeafletMouseEvent) => {
      this.updateSelection({ lat: event.latlng.lat, lon: event.latlng.lng }, true, true);
    });
  }

  this.leafletInstance = map;
  this.state.set('ready');
  this.updateMapContents(true);
  this.observeMapContainer();
}
```

#### Update `updateMapContents()` to branch on Leaflet

Add at the top of `updateMapContents()`:
```typescript
if (this.usingLeafletFallback && this.leafletInstance) {
  this.updateLeafletContents(forceRecenter);
  return;
}
```

#### New `updateLeafletContents()` method

```typescript
private updateLeafletContents(forceRecenter: boolean): void {
  if (!this.leafletInstance || !this.leafletModule) return;
  const L = this.leafletModule;

  // Clear existing markers
  this.leafletMarkers.forEach(m => m.remove());
  this.leafletMarkers = [];

  const markersToRender = this.readOnly()
    ? this.normalizedMarkers()
    : (() => {
        const sel = this.normalizeCoordinates(this.selectedCoordinates())
          ?? this.normalizeCoordinates(this.initialCoordinates());
        return sel ? [{ ...sel, title: this.title(), kind: 'primary' as const }] : [];
      })();

  markersToRender.forEach(marker => {
    const lm = L.marker([marker.lat, marker.lon]).addTo(this.leafletInstance!);
    if (marker.title) lm.bindPopup(marker.title);
    this.leafletMarkers.push(lm);
  });

  if (forceRecenter && markersToRender.length > 0) {
    this.leafletInstance.setView(
      [markersToRender[0].lat, markersToRender[0].lon],
      this.resolveFocusedZoom()
    );
  } else if (forceRecenter) {
    const c = this.resolveFallbackCenter();
    this.leafletInstance.setView([c.lat, c.lon], this.resolveInitialZoom());
  }
}
```

#### Update `ngOnDestroy()`

Add before `this.mapInstance?.remove()`:
```typescript
this.leafletMarkers.forEach(m => m.remove());
this.leafletMarkers = [];
this.leafletInstance?.remove();
this.leafletInstance = null;
this.leafletModule = null;
this.usingLeafletFallback = false;
```

### 2.4 Add Leaflet container override to component SCSS

**File:** `microtv-crm-frontend/src/app/shared/ui/location-picker-map/location-picker-map.component.scss`

```scss
::ng-deep .leaflet-container {
  width: 100%;
  height: 100%;
}
```

---

## Files Changed

| File | Change |
|---|---|
| `DEPLOY.md` | §11 nginx block + §7.3 `.env` template (MAP_STYLE_URL) |
| `microtv-crm-frontend/.env.example` | `NEXT_PUBLIC_MAP_STYLE_URL` → proxied URL |
| `microtv-crm-frontend/package.json` | Add `leaflet` + `@types/leaflet` |
| `microtv-crm-frontend/angular.json` | Add `leaflet/dist/leaflet.css` to styles |
| `microtv-crm-frontend/src/app/shared/ui/location-picker-map/location-picker-map.component.ts` | Leaflet fallback logic |
| `microtv-crm-frontend/src/app/shared/ui/location-picker-map/location-picker-map.component.scss` | Leaflet container overrides |

---

## Verification Checklist

```
[ ] curl https://crm.ycc.group/map-tiles/argentina/styles/basic-preview/style.json
    → HTTP 200, Content-Type: application/json

[ ] Open CRM on Android Chrome (original failing device)
    → No PNA/CORS console errors, map tiles render normally

[ ] Open DevTools → Network → filter /map-tiles/
    → All requests go to crm.ycc.group, none to map.microtv.ar

[ ] Leaflet fallback test (dev only):
    Set NEXT_PUBLIC_MAP_STYLE_URL to an invalid URL, run dev server
    → Map still renders with OSM tiles (no hard error shown)

[ ] Interactive mode under Leaflet fallback:
    Click on map → coordinates emitted correctly via onChange output

[ ] Read-only mode under Leaflet fallback:
    Open ticket with saved coordinates → marker renders at correct position

[ ] Hard-refresh browser after deploy to evict any cached 504 responses
    from the Angular service worker
```

---

## Out of Scope

- Fixing `map.microtv.ar` server-side nginx configuration
- Investigating why `map.microtv.ar` returns 504 (upstream tile server availability is a separate ops issue)
- Addressing the Mixpanel `ERR_CONNECTION_REFUSED` error (separate analytics service, unrelated to maps)
- Caching tiles server-side through the nginx proxy (future optimization)
