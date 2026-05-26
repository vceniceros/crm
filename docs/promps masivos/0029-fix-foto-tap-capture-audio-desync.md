# 0029 — Fix: tap-to-capture en foto y desync de audio en video

## Contexto

Dos regresiones en el módulo multimedia de comentarios:

1. Desde 0028, al abrir la cámara para tomar una foto la captura se dispara automáticamente sin esperar interacción del usuario.
2. El fix de desync de audio de video planificado en 0028 nunca se aplicó completamente (el `start(250)` sí quedó; las constraints de audio, no).

---

## Fix 1 — Foto: tap en el preview para capturar

### Diagnóstico

En `photo-capture.component.ts`, `startPreview()` encadena `await this.capture()` inmediatamente después de que la cámara inicia el preview → la foto se saca sola, sin que el usuario interactúe.

El flujo deseado: abrir la cámara → ver el preview → tocar la imagen → recién ahí se captura la foto.

### Cambios

**`microtv-crm-frontend/src/app/shared/ui/photo-capture/photo-capture.component.ts`**
- En `startPreview()`, eliminar `await this.capture()`. El método queda solo inicializando el preview.

**`microtv-crm-frontend/src/app/shared/ui/photo-capture/photo-capture.component.html`**
- Agregar `(click)="capture()"` al elemento `<video #preview>` para que un tap/click en el preview dispare la captura.

**`microtv-crm-frontend/src/app/shared/ui/photo-capture/photo-capture.component.scss`**
- Agregar `cursor: pointer` al selector `.photo-capture video`.
- Agregar un pseudo-elemento `::after` sobre el video con un ícono de cámara semitransparente para señalizar que el área es tappable.

---

## Fix 2 — Video: deshabilitar DSP de audio para eliminar desync

### Diagnóstico

`video-recorder.service.ts` usa `audio: true` en `getUserMedia`, lo que activa el pipeline DSP del browser (echo cancellation, noise suppression, AGC). Este pipeline introduce latencia variable en el track de audio que no existe en el track de video → drift progresivo → desync audible.

El timeslice `recorder.start(250)` ya está aplicado desde 0028 — no requiere cambio.

### Cambio

**`microtv-crm-frontend/src/app/core/services/video-recorder.service.ts`**
- Cambiar:
  ```ts
  audio: true
  ```
  por:
  ```ts
  audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }
  ```

El preview de video es `muted`, no hay riesgo de feedback acústico al deshabilitar echo cancellation.

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/app/shared/ui/photo-capture/photo-capture.component.ts` | Remover `await this.capture()` de `startPreview()` |
| `src/app/shared/ui/photo-capture/photo-capture.component.html` | `(click)="capture()"` en `<video>` |
| `src/app/shared/ui/photo-capture/photo-capture.component.scss` | `cursor: pointer` + overlay visual |
| `src/app/core/services/video-recorder.service.ts` | `audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }` |

---

## Verificación

1. `npm run build` sin errores de compilación.
2. **Foto** (mobile): abrir cámara → ver preview → **no se saca foto sola** → tocar la imagen → foto capturada correctamente.
3. **Video** (mobile): grabar ≥ 10 s de video con audio → reproducir → confirmar que el audio está alineado con el video sin drift.
