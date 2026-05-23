# 0028 — Fix: UX multimedia, duración de video, desync de audio y export PDF

## Contexto

Correcciones de MVP para producción:

1. UX de captura multimedia en comentarios (foto y video requieren doble tap)
2. Límite de duración de video ignorado desde `.env`
3. Desync de audio en grabaciones de video
4. PDF export crashea con imágenes portrait grandes (`LayoutError`)

---

## Issue 1 — UX multimedia: auto-captura y auto-start de grabación

### Diagnóstico

- `PhotoCaptureComponent`: al tocar "Tomar foto" abre el preview + muestra botón "Capturar foto". El usuario debe hacer **2 taps** para obtener la foto.
- `VideoRecorderComponent`: al tocar "Grabar video" abre el preview + muestra botón "Grabar". El usuario debe hacer **2 taps** para arrancar.

El objetivo es que un solo tap sea suficiente: tocás → captura / tocás → arranca grabación.

### Cambios

**`microtv-crm-frontend/src/app/shared/ui/photo-capture/photo-capture.component.ts`**
- En `startPreview()` (ya llamado en `ngAfterViewInit`), encadenar `.then(() => this.capture())` para auto-capturar en cuanto la cámara esté lista.

**`microtv-crm-frontend/src/app/shared/ui/photo-capture/photo-capture.component.html`**
- Eliminar el botón "Capturar foto" — queda solo "Cancelar".

**`microtv-crm-frontend/src/app/shared/ui/video-recorder/video-recorder.component.ts`**
- Implementar `AfterViewInit` y llamar `this.start()` en `ngAfterViewInit()` para auto-arrancar la grabación.

**`microtv-crm-frontend/src/app/shared/ui/video-recorder/video-recorder.component.html`**
- Eliminar el bloque `@else { <button>Grabar</button> }` — solo quedan "Detener" y "Cancelar".

---

## Issue 2 — Duración de video no lee del `.env`

### Diagnóstico

`crm-api.config.ts` ya soporta `runtimeConfig?.videoMaxDurationSeconds` con fallback `30`, pero `sync-runtime-env.mjs` nunca lee `VIDEO_MAX_DURATION_SECONDS` del `.env`. El campo nunca se inyecta en `runtime-config.js` → el fallback de 30 s se impone siempre.

### Cambios

**`microtv-crm-frontend/scripts/sync-runtime-env.mjs`**
- Añadir: `const videoMaxDurationSeconds = parseNumber(envValues.VIDEO_MAX_DURATION_SECONDS, 30);`
- Incluir `videoMaxDurationSeconds` en el objeto JSON generado en `runtimeConfigContents`.

**`microtv-crm-frontend/.env.example`**
- Añadir `VIDEO_MAX_DURATION_SECONDS=30` junto a `VIDEO_MAX_SIZE_MB` en la sección de multimedia.

---

## Issue 3 — Desync de audio en grabación de video

### Diagnóstico

Dos causas en `video-recorder.service.ts`:

1. **`this.recorder.start()` sin timeslice** — el browser acumula un único chunk hasta el `stop()`. En mobile Chrome/Safari esto no garantiza que los tracks de audio y video estén correctamente interleaved → desync en el archivo final.

2. **`audio: true`** — activa el pipeline completo de DSP del browser (echo cancellation, noise suppression, AGC), que introduce latencia variable en el track de audio que no existe en el track de video → drift progresivo.

### Cambios

**`microtv-crm-frontend/src/app/core/services/video-recorder.service.ts`**
- Cambiar `audio: true` → `audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }`. El preview es `muted`, no hay riesgo de feedback.
- Cambiar `this.recorder.start()` → `this.recorder.start(250)`. Timeslice de 250 ms fuerza chunks A+V interleaved cada cuarto de segundo durante toda la grabación, como hace la cámara nativa.

---

## Issue 4 — PDF export crashea con imágenes portrait (`LayoutError`)

### Diagnóstico

`_embed_image` en `ticket_export_service.py` calcula:

```python
display_w = min(max_width_pt, w)   # 396.85 pt (14 cm) vs px — da 396.85 por suerte
display_h = display_w * aspect      # sin ningún cap de altura
```

Para una imagen portrait de 1200 × 2131 px: `display_h = 396.85 × 1.776 = 705.5 pt`. El frame disponible es `~702 pt` → `reportlab.platypus.doctemplate.LayoutError`.

No existe ningún límite de altura en el código actual.

### Cambio

**`microtv-crm-backend/src/crm_backend/services/ticket_export_service.py`** — método `_embed_image`

Después de calcular `display_w` y `display_h`, agregar cap proporcional de altura:

```python
MAX_HEIGHT_PT = 680  # margen seguro respecto al frame ~702 pt
if display_h > MAX_HEIGHT_PT:
    scale = MAX_HEIGHT_PT / display_h
    display_h = MAX_HEIGHT_PT
    display_w = display_w * scale
```

Escala proporcionalmente sin tocar el resto de la lógica de embedding.

---

## Archivos a modificar

| Archivo | Motivo |
|---|---|
| `microtv-crm-frontend/src/app/shared/ui/photo-capture/photo-capture.component.ts` | Auto-captura |
| `microtv-crm-frontend/src/app/shared/ui/photo-capture/photo-capture.component.html` | Eliminar botón "Capturar foto" |
| `microtv-crm-frontend/src/app/shared/ui/video-recorder/video-recorder.component.ts` | Auto-start + AfterViewInit |
| `microtv-crm-frontend/src/app/shared/ui/video-recorder/video-recorder.component.html` | Eliminar botón "Grabar" |
| `microtv-crm-frontend/src/app/core/services/video-recorder.service.ts` | Timeslice 250 ms + audio constraints |
| `microtv-crm-frontend/scripts/sync-runtime-env.mjs` | Leer `VIDEO_MAX_DURATION_SECONDS` del `.env` |
| `microtv-crm-frontend/.env.example` | Documentar `VIDEO_MAX_DURATION_SECONDS` |
| `microtv-crm-backend/src/crm_backend/services/ticket_export_service.py` | Cap de altura en imágenes PDF |

---

## Verificación

1. `npm run build` sin errores de TypeScript ni compilación.
2. **Photo**: tap en "Tomar foto" → cámara abre y captura automáticamente sin segundo tap.
3. **Video**: tap en "Grabar video" → grabación arranca sola, solo aparece "Detener" y "Cancelar".
4. **Audio sync**: grabar video de 15–20 s con audio → reproducir el `.webm` descargado → audio y video sincronizados sin delay.
5. **Duración**: poner `VIDEO_MAX_DURATION_SECONDS=60` en `.env`, re-correr `node scripts/sync-runtime-env.mjs`, verificar que el timer muestre `0s / 60s`.
6. **PDF**: exportar ticket con ≥5 imágenes portrait (relación alto/ancho > 1.5) → descarga el ZIP sin error 500.
