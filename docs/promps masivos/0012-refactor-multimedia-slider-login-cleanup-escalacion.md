# 0012 — Refactor multimedia: slider scroll-snap, limpieza de login, verificación de escalación a admin

## Contexto

Tres cambios menores de UX y verificación operativa:
1. El multimedia en los comentarios de tickets se veía muy pequeño (tiles fijas de 144×96 px). Se reemplaza por un slider horizontal scroll-snap, una media por slide a ancho completo.
2. La página de login tiene tarjetas de "features técnicos" (JWT, Responsive, Contexto local) que son ruido para usuarios operativos. Se limpian. El título pasa de "MicroTV" a "YCC".
3. Verificar que `tecnico_campo` y `encargado_deposito` puedan escalar un ticket al rol admin desde el frontend y el backend.

---

## Cambio 1 — Slider scroll-snap en multimedia de comentarios de tickets

### Síntoma
Los adjuntos (imagen/video) dentro del historial de comentarios de un ticket se renderizan como tiles fijas de 144×96 px en un flex-wrap. En mobile quedan muy pequeños y no aprovechan el ancho disponible.

### Causa raíz
`ticket-execution-page.component.html` líneas ~157–160: atributos HTML `width="144" height="96"` hardcodeados en `<img>` y `<video>`.
`ticket-execution-page.component.scss` línea ~418: `.ticket-execution-page__timeline-attachments` usa `display: flex; flex-wrap: wrap; gap: 0.45rem` — no hay control de tamaño sobre los media elements.

### Fix

**Archivo:** `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.html`

Dentro del bloque `@if (event.attachments.length)`, envolver cada ítem del `@for` con un `<div class="ticket-execution-page__timeline-attachment-slide">` y eliminar los atributos `width="144" height="96"` de `<img>` y `<video>`:

```html
@if (event.attachments.length) {
  <div class="ticket-execution-page__timeline-attachments">
    @for (attachment of event.attachments; track attachment.id) {
      <div class="ticket-execution-page__timeline-attachment-slide">
        @if (timelineAttachmentUrl(attachment); as attachmentUrl) {
          @if (attachment.kind === 'image') {
            <img [src]="attachmentUrl" [alt]="attachment.fileName" (click)="openAttachmentInNewTab(attachmentUrl)" />
          } @else if (attachment.kind === 'video') {
            <video controls preload="metadata" (click)="openAttachmentInNewTab(attachmentUrl)">
              <source [src]="attachmentUrl" [type]="attachment.fileType || 'video/mp4'" />
            </video>
          } @else {
            <a [href]="attachmentUrl" target="_blank" rel="noopener noreferrer">{{ attachment.fileName }}</a>
          }
        } @else {
          <span>{{ attachment.fileName }}</span>
        }
      </div>
    }
  </div>
}
```

**Archivo:** `microtv-crm-frontend/src/app/features/tickets/components/ticket-execution-page/ticket-execution-page.component.scss`

Reemplazar el bloque de `.ticket-execution-page__timeline-attachments` y su regla `.ticket-execution-page__timeline-attachments a` por:

```scss
.ticket-execution-page__timeline-attachments {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  margin-top: 0.7rem;
  border-radius: 0.6rem;

  &::-webkit-scrollbar {
    display: none;
  }
}

.ticket-execution-page__timeline-attachment-slide {
  flex: 0 0 100%;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 0.6rem;
  background: rgba(23, 24, 26, 0.04);

  img,
  video {
    width: 100%;
    height: auto;
    max-height: 22rem;
    object-fit: contain;
    display: block;
    cursor: pointer;
  }

  a {
    display: inline-flex;
    align-items: center;
    padding: 0.3rem 0.6rem;
    border-radius: 999px;
    border: 1px solid rgba(23, 24, 26, 0.1);
    color: var(--text-primary);
    font-size: 0.78rem;
    font-weight: 600;
    text-decoration: none;
  }
}
```

---

## Cambio 2 — Limpieza de la página de login + título a YCC

### Síntoma
La página de login muestra tres tarjetas con features técnicos ("JWT validado en backend", "Contexto local mínimo", "Responsive de verdad") que son ruido para usuarios operativos. El título dice "para MicroTV" pero el sistema ya opera bajo YCC.

### Fix

**Archivo:** `microtv-crm-frontend/src/app/features/auth/components/login-page/login-page.component.html`

1. Cambiar el `<h1>`:
```html
<!-- Antes -->
<h1 class="login-page__title">Sistema interno de gestión operativa para MicroTV.</h1>

<!-- Después -->
<h1 class="login-page__title">Sistema interno de gestión operativa para YCC.</h1>
```

2. Eliminar el bloque completo `<div class="login-page__highlights">` con sus tres `<div class="login-page__highlight">` hijos (JWT, Contexto local, Responsive).

**Archivo:** `microtv-crm-frontend/src/app/features/auth/components/login-page/login-page.component.scss`

Eliminar las reglas `.login-page__highlights` y `.login-page__highlight` (quedan huérfanas una vez eliminado el HTML).

---

## Cambio 3 — Verificación de escalación de tickets a admin

### Estado
**Ya implementado end-to-end. No requiere cambios de código.**

### Verificación backend (`ticket_service.py`)

| Método | Comportamiento |
|---|---|
| `list_assignable_roles()` | Para actores `tecnico`/`deposito`, inyecta el ID del rol `admin` en la lista devuelta → el rol admin aparece en el dropdown del frontend |
| `_ensure_assignment_access()` | Guard 1 llama a `_can_escalate_to_admin()` antes de rechazar; Guard 2 solo bloquea si el rol *actual* del ticket no está en los roles del actor (no el rol destino) |
| `_can_escalate_to_admin()` | Devuelve `true` cuando el rol destino normaliza a `"admin"` Y el actor tiene `"tecnico"` o `"deposito"` |
| `_normalize_role_key()` | `tecnico_campo` → `"tecnico"` ✓ · `encargado_deposito` → `"deposito"` ✓ |

### Verificación frontend

| Pieza | Comportamiento |
|---|---|
| `ticketRoles()` signal | Poblado desde `GET /tickets/roles` → recibe admin en la lista para estos actores |
| `canReassign` computed | Devuelve `true` cuando `ticket.assigned_role_id` está en los role IDs propios del actor → el menú abre ✓ |

### Acción recomendada
Revisar `microtv-crm-backend/tests/` y agregar un test de integración para el path de escalación si no existe:

```python
# Caso: tecnico_campo asigna ticket (rol=tecnico) al rol admin
def test_tecnico_can_escalate_to_admin_role(ticket_service, tecnico_actor, ticket_in_tecnico_role, admin_role):
    result = ticket_service.assign_ticket(
        actor=tecnico_actor,
        ticket_id=ticket_in_tecnico_role.ticket_id,
        assigned_role_id=admin_role.crm_role_id,
        assigned_user_id=None,
        notes="Escalando a admin",
    )
    assert result.assigned_role_id == admin_role.crm_role_id
```

---

## Checklist de verificación

- [ ] `ng serve` → login muestra "para YCC", sin tarjetas de features técnicos
- [ ] Abrir un comentario de ticket con múltiples adjuntos → slider horizontal funciona, cada media ocupa el ancho completo del card, swipe en mobile operativo
- [ ] Login como `tecnico_campo`, abrir ticket asignado al rol tecnico → rol `admin` visible en el dropdown de asignación, escalación guarda con HTTP 200
- [ ] `pytest microtv-crm-backend/tests/` → test de escalación pasa
