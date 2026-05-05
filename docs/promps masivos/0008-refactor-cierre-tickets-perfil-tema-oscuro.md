Implement a **set of functional refactors and improvements** in the CRM, wired end-to-end:

- real frontend connected to real backend
- real database persistence
- no mocks
- respecting the existing project structure
- respecting the design patterns already in use in each module
- minimal but complete changes

## General rules

No decorative implementations.
No mocks.
The frontend must be wired to the backend and the backend must talk to the real database.
Each change must be self-contained: a ticket created before `requires_video_evidence` existed must behave exactly as it did before.

---

## Feature 1 — Close a ticket by marking an existing comment as the solution

Currently the only way to close a ticket is through the close action panel (primary action `close`), which requires a new mandatory comment and, in most cases, a video attachment.

Add an **alternative close path**: mark an already-published timeline comment as the solution to the ticket. This closes the ticket using that comment as closure evidence without requiring any additional attachments.

### Business rules

- Only comments of type `general` can be marked as a solution.
- Only users who can already close the ticket (`canCloseTicket()`) can see and use this action.
- Marking a comment as a solution applies the same existing close logic:
  - field technician → status `PENDING_APPROVAL`
  - admin or executive → status `CLOSED` directly
- The `solution_comment_id` field on the `tickets` table must point to the marked comment.
- **The video requirement is not re-checked** on this close path.
- The existing manual close flow (primary action panel) **does not change**.

### Database migration

```sql
ALTER TABLE tickets
  ADD COLUMN solution_comment_id UUID
  REFERENCES ticket_comments(ticket_comment_id)
  ON DELETE SET NULL;
```

### Backend

- `models/ticket.py`: add `solution_comment_id` nullable FK field + relationship.
- `schemas/tickets.py`: expose `solution_comment_id` in `TicketResponse`.
- `services/ticket_service.py`: add method `mark_comment_as_solution(ticket, comment_id, actor)` that validates the comment type, sets the field, and executes the close logic (reusing the existing `close_ticket()` with a `via_solution_comment=True` flag that skips the video validation).
- `api/endpoints/tickets.py`: add endpoint `POST /tickets/{ticket_id}/comments/{comment_id}/mark-as-solution`.

### Frontend

- `ticket-management.model.ts`: add `solution_comment_id: string | null` to `TicketDetail`.
- `ticket-management.service.ts`: add method `markCommentAsSolution(ticketId, commentId)`.
- `ticket-execution-page.component.html`: inside the timeline comment loop, add a `mat-icon-button` with icon `check_circle` and tooltip "Mark as solution", visible only when `canCloseTicket()` and `comment.comment_type === 'general'`.
- `ticket-execution-page.component.ts`: add method `markCommentAsSolution(commentId)` that opens a `MatDialog` confirmation dialog and then calls the service. Update the ticket in the view on success.

---

## Feature 2 — Video-required flag on ticket creation

Currently all tickets require a video evidence attachment to be closed. Make this rule **configurable per ticket at creation time**.

### Business rules

- New `requires_video_evidence` boolean column on `tickets`, `DEFAULT TRUE`.
- If `requires_video_evidence = true`: current behavior is preserved unchanged on both frontend and backend.
- If `requires_video_evidence = false`: video is optional — it can still be attached but the close is not blocked if none is present.
- The validation must exist in **both layers** (frontend gate + backend HTTP 422 when the flag is `true` and no video is provided).

### Database migration

```sql
ALTER TABLE tickets
  ADD COLUMN requires_video_evidence BOOLEAN NOT NULL DEFAULT TRUE;
```

### Backend

- `models/ticket.py`: add `requires_video_evidence: Mapped[bool]` with default `True`.
- `schemas/tickets.py`: expose in `CreateTicketRequest` (required field, default `true`) and in `TicketResponse`.
- `services/ticket_service.py` in `close_ticket()`: if `ticket.requires_video_evidence` is `True`, verify that at least one of the provided `attachment_ids` corresponds to a `TicketAttachment` with `attachment_type = VIDEO`; raise HTTP 422 otherwise.

### Frontend

- `create-ticket-dialog.component.ts/.html`: add `requiresVideoEvidence` boolean form control (default `true`) as a `mat-slide-toggle` labeled "Requires video evidence to close".
- `ticket-execution-page.component.ts`:
  - Replace the hardcoded `hasPendingCloseVideoEvidence()` check in `canExecutePrimaryAction()` and `closeTicket()` with: `!this.ticket()?.requires_video_evidence || this.hasPendingCloseVideoEvidence()`.
  - Add computed `isCloseBlockedByVideoRequirement = computed(() => Boolean(this.ticket()?.requires_video_evidence && !this.hasPendingCloseVideoEvidence() && this.canCloseOrTransition()))`.

---

## Feature 3 — Close-blocking reasons panel with clear UX

When the user selects the close action and cannot execute it, the interface must explain **exactly why** instead of simply disabling the button or showing a generic error message.

### Expected behavior

- Show an informational panel only when `selectedPrimaryAction() === 'close'` and at least one blocking condition is active.
- The panel lists each unmet requirement with a warning icon and clear text:
  - `isCloseBlockedByArrivalRequirement()` → "Register your arrival at the client's location before closing. Add a comment with location."
  - `isCloseBlockedByVideoRequirement()` → "This ticket requires at least one video evidence attachment."
- Already-met requirements are shown with a check icon and strikethrough text or success color.
- This panel replaces the use of `errorMessage` for these specific conditions (`errorMessage` continues to exist for API errors).

### Frontend

- `ticket-execution-page.component.html`: add the `<div class="close-requirements-panel">` panel inside the primary close action section.
- `ticket-execution-page.component.scss`: style the panel with fulfilled/unfulfilled requirement items.

---

## Feature 4 — Dark theme contrast fixes

Multiple CRM components display dark text on a dark background in dark mode, making the interface unreadable. Perform a full audit and fix pass.

### Process

1. **Audit**: `grep_search` across all `src/app/**/*.scss` for hardcoded color values (`color:`, `background-color:`, `background:`) with literal dark/light values (`#000`, `#fff`, `black`, `white`, `rgba(0,0,0`, `rgba(255,255,255`) that have no corresponding `html.theme-dark &` override.
2. **Material overlay audit**: check `mat-select` panels, `mat-autocomplete`, `mat-datepicker`, `mat-menu`, `mat-tooltip`, `mat-dialog`, `mat-snack-bar` — these frequently inherit `color-scheme: light` and render black text on a white background in dark mode.
3. **Global fix** in `styles.css`: complete or correct `html.theme-dark` overrides for all missing custom property values.
4. **Fix in `material-theme.scss`**: verify that the `html.theme-dark` block applies `color-scheme: dark` before Material tokens resolve.
5. **Per-component fix**: for each `.scss` file identified in the audit, add `html.theme-dark &` scoped blocks with the necessary overrides.

### Design rule

In dark mode, no component may have `#000000` text or `color: black` without an explicit override. The `--text-primary` token must be used instead of hardcoded colors wherever possible.

---

## Feature 5 — Settings menu rework + new user profile module

### 5a — Simplified settings menu

The current settings menu exposes technical options that are never configured through the UI. Simplify it radically.

**New settings menu content:**

| Tab | Visible to |
|-----|------------|
| User management | `admin` and `ejecutivo` |

Only that tab. All other tabs (Users & roles CRM, Categories, Priorities & statuses, Templates, SLA, Notifications) must be removed from the view until explicitly decided to reintroduce them.

**Improved user creation/edit flow:**

The current flow uses chained `window.prompt()` calls. Replace it with a real `MatDialog` form component:
- email
- display_name
- password (create only — hidden on edit)
- roles (multi-select or chips)

The same dialog is used for both creating and editing users.

### 5b — New `/profile` module

Every authenticated user (all roles) must be able to access `/profile` and self-manage their basic information.

**Module features:**

1. **Change display name** (`display_name`): editable field + save button → `PATCH /me`.
2. **Change email**: editable field + save button → `PATCH /me` (syncs to auth backend).
3. **Reset password**: "Send password reset email" button → `POST /me/request-password-reset` → backend reuses the existing auth service `forgot-password` flow.
4. **Profile picture**: shows current avatar (or initials placeholder if none); upload button → `POST /me/avatar` → file saved to `public/avatars/{crm_user_id}.{ext}` → URL stored in `crm_users.avatar_url`.

### Database migration

```sql
ALTER TABLE crm_users
  ADD COLUMN avatar_url VARCHAR(500);
```

### Backend — new `/me` endpoints

New file `api/endpoints/me.py`:

```
GET  /me                         → MeResponse (display_name, email, avatar_url, roles)
PATCH /me                        → MePatchRequest { display_name?, email? } → MeResponse
POST  /me/avatar                 → multipart UploadFile → saves to public/avatars/ → MeResponse
POST  /me/request-password-reset → no body → calls auth service forgot-password → 204
```

Register the router in the backend's main router file.

### Frontend

- New folder `src/app/features/profile/` with `profile-page.component.ts/.html/.scss`.
- Route `/profile` in `app.routes.ts` protected by `authGuard` only (all roles).
- `sidebar-user-switcher.component.html`: the sidebar user block must include a link or action that navigates to `/profile`. If `avatar_url` is set, display it as the avatar image instead of the initials placeholder.
- `layout-data.json` or the navigation service: add a "My Profile" nav item pointing to `/profile`, visible to all roles.

---

## Expected verification on completion

1. Create a ticket with `requires_video_evidence = false` → close it without attaching any video → must succeed on both frontend and backend.
2. Create a ticket with `requires_video_evidence = true` → attempt to close without a video → frontend shows the blocking panel; if attempted directly via API, backend returns HTTP 422.
3. Open an active ticket → publish a general comment → click "Mark as solution" → ticket moves to `CLOSED` or `PENDING_APPROVAL` depending on the actor's role.
4. Select the "Close ticket" action with unmet requirements → the blocking panel lists the specific reasons; the button remains disabled but the reason is now unambiguous.
5. As any role: navigate to `/profile` → change display name → save → the sidebar reflects the new name immediately.
6. As `admin`: open `/settings` → only the "User management" tab is visible → create a new user via the dialog → user appears in the list.
7. Toggle dark mode → open dropdown, mat-select, mat-menu, mat-datepicker, mat-dialog → no black text on black background anywhere.
