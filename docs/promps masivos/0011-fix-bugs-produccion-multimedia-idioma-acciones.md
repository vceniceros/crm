# 0011 — Fix bugs de producción: multimedia, idioma, acciones post-cierre, auto-asignación, formulario

## Contexto

Se detectaron 6 bugs en producción, todos en el frontend. El backend ya tiene los mensajes en español y la lógica correcta.

---

## Bug 1 — Los adjuntos multimedia en comentarios redirigen al dashboard

### Síntoma
Al tocar una imagen o video adjunto en el historial de comentarios de un ticket, la app navega al dashboard en lugar de mostrar el archivo.

### Causa raíz
En `ticket-execution-page.component.html` (líneas 149–157), los adjuntos se renderizan como:

```html
<a [href]="attachment.previewUrl || attachment.publicUrl" target="_blank" rel="noopener noreferrer">
  {{ attachment.fileName }}
</a>
```

El `publicUrl` que devuelve el backend es un path relativo (`/media/tasks/images/abc123.jpg`). El router de Angular intercepta esa navegación y cae al fallback de la app (dashboard).

### Fix
**Archivo:** `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts`
- Inyectar el token `CRM_API_CONFIG` (ya usado en `task-attachments-section.component.ts`).
- Agregar método `toAbsoluteMediaUrl(path: string | null | undefined): string | null` usando el mismo patrón de normalización de `task-attachments-section.component.ts` líneas 117–145: si el path es absoluto (https://, blob:, data:) usarlo tal cual; si es relativo, prepender `backendOrigin`.

**Archivo:** `ticket-execution-page.component.html` líneas 149–157
- Reemplazar el `<a href>` por thumbnails inline:
  - `<img>` para adjuntos de tipo imagen
  - `<video controls preload="metadata">` para videos
  - En ambos casos, `(click)` abre la URL absoluta en `window.open(url, '_blank')`

**Referencia:** `task-attachments-section.component.ts` (mismo proyecto) — patrón `toAbsoluteUrl()`.

---

## Bug 2 — Panel de requisitos de cierre en inglés

### Síntoma
Al intentar cerrar un ticket sin haber cumplido los requisitos, el panel de advertencias muestra texto en inglés.

### Causa raíz
`ticket-execution-page.component.html` líneas ~302 y ~308 tienen strings hardcodeados en inglés. Los toasts de `errorMessage` en el TS ya están en español, pero el panel HTML no.

### Fix
**Archivo:** `ticket-execution-page.component.html` líneas ~291–310

| Texto actual (inglés) | Texto correcto (español) |
|---|---|
| "Register your arrival at the client's location before closing. Add a comment with location." | "Registrá tu llegada al cliente antes de cerrar. Agregá un comentario con ubicación." |
| "This ticket requires at least one video evidence attachment." | "Este ticket requiere al menos un video de evidencia adjunto." |

---

## Bug 3 — Botones "Exportar historial" y "Generar encuesta" desaparecen al cerrar un ticket

### Síntoma
Al cerrar un ticket, las opciones de exportar historial y enviar formulario de satisfacción no aparecen en la vista de ejecución ni en la tabla de historial.

### Causa raíz
`canAccessPostClosureActions()` en `ticket-execution-page.component.ts` (líneas 287–294) requiere que se cumplan **los tres** criterios:
1. `ticket.status === 'CLOSED'`
2. `Boolean(ticket.approved_by_executive)` ← **no se está seteando en producción**
3. `isAdmin() || isExecutive()`

El mismo problema aplica en `tickets-page.component.ts` línea 302 donde se computa `isExecutiveApprovedClosed`:
```ts
isExecutiveApprovedClosed: ticket.status === 'CLOSED' && Boolean(ticket.approved_by_executive),
```

### Fix
**Archivo:** `ticket-execution-page.component.ts` línea ~291
- Cambiar la condición de `canAccessPostClosureActions`: eliminar el check de `approved_by_executive`. Quedar solo con:
```ts
return ticket.status === 'CLOSED' && (this.isAdmin() || this.isExecutive());
```

**Archivo:** `tickets-page.component.ts` línea ~302
- Cambiar el mapeo de `isExecutiveApprovedClosed`:
```ts
isExecutiveApprovedClosed: ticket.status === 'CLOSED',
```

> **Nota:** El backend sigue siendo la fuente de verdad. Si el endpoint de export requiere `approved_by_executive`, mostrará un error descriptivo. El frontend solo deja de ocultarlo sin razón.

---

## Bug 4 — Botón "Asignarme" no aparece para usuarios de todos los roles

### Síntoma
El botón "Asignarme" en la pestaña "Sin asignar en mi rol" no aparece para usuarios con roles distintos de `tecnico` y `deposito`.

### Causa raíz
`canSelfAssignUnassignedTickets` en `tickets-page.component.ts` línea ~381:
```ts
readonly canSelfAssignUnassignedTickets = computed(() => {
  const roles = this.currentRoles();
  return roles.some((role) => role === 'tecnico' || role === 'deposito');
});
```
El filtro hardcodea dos roles. Cualquier otro rol (incluyendo nuevos roles o variantes) nunca puede auto-asignarse desde el frontend, aunque el backend lo permitiría.

### Fix
**Archivo:** `tickets-page.component.ts` línea ~381
- Cambiar la implementación para permitir a cualquier usuario con al menos un rol:
```ts
readonly canSelfAssignUnassignedTickets = computed(() => this.currentRoles().length > 0);
```
El tab "Sin asignar en mi rol" ya filtra del backend solo los tickets del rol del usuario — no es necesario un gate adicional en el frontend.

---

## Bug 5 — Controles inconsistentes en el formulario de creación de ticket

### Síntoma
En el diálogo de creación de ticket, los dos checkboxes de requisitos usan componentes distintos y están en idiomas distintos.

### Causa raíz
`create-ticket-dialog.component.html` líneas 80–86:
```html
<!-- OK: checkbox en español -->
<mat-checkbox formControlName="requires_arrival_comment">
  Requiere comentario de llegada
</mat-checkbox>

<!-- MAL: slide-toggle en inglés -->
<mat-slide-toggle formControlName="requires_video_evidence">
  Requires video evidence to close
</mat-slide-toggle>
```

### Fix
**Archivo:** `create-ticket-dialog.component.html` líneas 84–86
- Cambiar `<mat-slide-toggle>` → `<mat-checkbox>`
- Traducir el label: `"Requires video evidence to close"` → `"Requiere video de evidencia para cerrar"`

Ambos controles quedan como `mat-checkbox` con labels en español.

---

## Bug 6 — Android: adjuntar multimedia en comentario solo muestra galería

### Síntoma
En dispositivos Android, al adjuntar multimedia a un comentario de ticket, la app abre directamente la galería sin dar opción de abrir la cámara.

### Causa raíz
`ticket-attachments-section.component.html` tiene un único `<input type="file" capture="environment">`. El atributo `capture` en algunos navegadores Android es ignorado y en otros fuerza solo cámara (sin galería). El comportamiento es inconsistente.

### Fix
**Archivo:** `ticket-attachments-section.component.html` líneas 15–27
- Reemplazar el único input + botón por dos inputs hidden + dos botones explícitos:

```html
<!-- Input para cámara -->
<input
  #cameraInput
  type="file"
  accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime,.mov"
  capture="environment"
  hidden
  (change)="onFileSelection($event)"
/>

<!-- Input para galería -->
<input
  #galleryInput
  type="file"
  accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime,.mov"
  multiple
  hidden
  (change)="onFileSelection($event)"
/>

<button mat-stroked-button type="button" (click)="cameraInput.click()">
  <mat-icon>photo_camera</mat-icon>
  <span>Cámara</span>
</button>

<button mat-stroked-button type="button" (click)="galleryInput.click()">
  <mat-icon>photo_library</mat-icon>
  <span>Galería</span>
</button>
```

**Archivo:** `ticket-attachments-section.component.ts`
- Sin cambios de lógica. El handler `onFileSelection($event)` existente funciona igual para ambos inputs.

---

## Archivos a modificar

| Archivo | Bugs |
|---|---|
| `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.html` | 1, 2 |
| `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.ts` | 1, 3 |
| `microtv-crm-frontend/src/app/features/tickets/components/tickets-page/tickets-page.component.ts` | 3, 4 |
| `microtv-crm-frontend/src/app/features/tickets/components/create-ticket-dialog/create-ticket-dialog.component.html` | 5 |
| `microtv-crm-frontend/src/app/features/tickets/components/ticket-attachments-section/ticket-attachments-section.component.html` | 6 |

**Referencia (solo lectura):**
- `microtv-crm-frontend/src/app/features/tasks/components/task-attachments-section/task-attachments-section.component.ts` — patrón `toAbsoluteUrl()` para el bug 1

---

## Checklist de verificación post-implementación

- [ -] Bug 1: Tocar un adjunto en el historial de un comentario abre la imagen/video en una nueva pestaña del navegador, no navega al dashboard: estan los links pero la imagen y el video esta rotos, es como si no estuviese bien puesta la ruta
- [x] Bug 2: El panel de requisitos de cierre muestra texto en español: esta correcto
- [ x] Bug 3: En un ticket `CLOSED`, el usuario admin/ejecutivo ve los botones "Exportar historial" y "Generar encuesta": esta correcto
- [x ] Bug 4: Un usuario de cualquier rol puede auto-asignarse tickets en la pestaña "Sin asignar en mi rol": esta correcto
- [ x] Bug 5: Ambos controles en el formulario de creación son `mat-checkbox` con labels en español : esta correcto
- [x] Bug 6 (Android): Al adjuntar multimedia en un comentario, se muestran dos botones — "Cámara" y "Galería" — que abren el origen correcto cada uno: esta correcto
