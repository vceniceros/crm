# 0017 — Inventory: Image Viewer, Stock Mínimo, Ubicación en Estantería, Stock Editable + Fix Refresh al Dashboard

## Contexto

Este documento describe cinco mejoras al módulo de inventario (depósito), más un fix de navegación global. Cada cambio está especificado con suficiente detalle para que el agente lo implemente sin suposiciones.

El agente **no debe hacer ninguna suposición**: todo lo necesario está aquí.

---

## Resumen de cambios

| # | Tipo | Descripción |
|---|---|---|
| 1 | Feature | Click en imagen de producto abre modal de visualización |
| 2 | Feature | Stock mínimo configurable por producto con notificación dinámica |
| 3 | Feature | Columnas "Estantería" y "Altura" con edición inline en tabla |
| 4 | Feature | Stock actual editable numéricamente de forma directa |
| 5 | Fix | Refrescar la app no redirige al dashboard, mantiene la URL actual |

---

## Phase 1 — Base de datos

### Step 1 — SQL migration

**Archivo nuevo:** `microtv-crm-backend/sql/20260512_inventory_product_enhancements.sql`

```sql
-- Columna: stock mínimo configurable (reemplaza el umbral hardcodeado de 3)
ALTER TABLE inventory_products
  ADD COLUMN IF NOT EXISTS minimum_stock INTEGER NOT NULL DEFAULT 3
    CONSTRAINT inventory_products_minimum_stock_positive CHECK (minimum_stock >= 1);

-- Columna: letra de estantería (A–Z)
ALTER TABLE inventory_products
  ADD COLUMN IF NOT EXISTS shelf_id VARCHAR(1) NULL
    CONSTRAINT inventory_products_shelf_id_alpha CHECK (shelf_id ~ '^[A-Z]$');

-- Columna: número de altura de estante (entero positivo)
ALTER TABLE inventory_products
  ADD COLUMN IF NOT EXISTS shelf_height SMALLINT NULL
    CONSTRAINT inventory_products_shelf_height_positive CHECK (shelf_height >= 1);
```

### Step 1b — Actualizar `migrate_prod.sh`

**Archivo:** `microtv-crm-backend/sql/migrate_prod.sh`

El script ya auto-descubre todos los `.sql` por glob y los aplica en orden — la nueva migración será ejecutada automáticamente por filename sort.

Lo único que hay que agregar es la verificación final del schema al final del bloque `echo "=== Verificando estado final del schema ==="`.

Localizar esta línea en el script (aprox. línea 147):
```sql
  EXISTS(SELECT 1 FROM information_schema.tables   WHERE table_name='push_subscriptions')                              AS table_push_subscriptions,
```

Agregar estas tres columnas a la misma query SQL de verificación (dentro del string multilinea ya existente), antes del `;` final:
```sql
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='inventory_products' AND column_name='minimum_stock') AS inv_col_minimum_stock,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='inventory_products' AND column_name='shelf_id')      AS inv_col_shelf_id,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='inventory_products' AND column_name='shelf_height')  AS inv_col_shelf_height,
```

Actualizar también el `echo` de headers y el bloque `IFS='|' read -r ...` para incluir las tres nuevas variables, y agregar a la condición de fallo:
```bash
if ! is_truthy "$inv_col_minimum_stock" || ! is_truthy "$inv_col_shelf_id" || ! is_truthy "$inv_col_shelf_height"; then
```

---

## Phase 2 — Backend

### Step 2 — ORM model

**Archivo:** `microtv-crm-backend/src/crm_backend/models/stock_product.py`

Agregar tres `Mapped` columns en `StockProduct`, después de `image_url`:

```python
minimum_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
shelf_id: Mapped[str | None] = mapped_column(String(1), nullable=True)
shelf_height: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
```

Actualizar el classmethod `create()` para aceptar y persistir `minimum_stock` (default `3`):
```python
@classmethod
def create(
    cls,
    *,
    name: str,
    product_code: str | None,
    stock_category_id: str | None,
    initial_stock: int = 0,
    image_url: str | None = None,
    requires_tracking: bool = False,
    minimum_stock: int = 3,          # ← nuevo parámetro
    actor_crm_user_id: str,
    warehouse_id: str,
) -> "StockProduct":
    ...
    instance.minimum_stock = minimum_stock
    ...
```

### Step 3 — Schemas

**Archivo:** `microtv-crm-backend/src/crm_backend/schemas/stock.py`

**3a — Agregar campos a `StockProductResponse`:**
```python
minimum_stock: int
shelf_id: str | None
shelf_height: int | None
```

**3b — Agregar campo a `CreateStockProductRequest`:**
```python
minimum_stock: int = Field(default=3, ge=1)
```

**3c — Dos schemas nuevos al final del archivo:**
```python
class UpdateProductLocationRequest(BaseModel):
    shelf_id: str = Field(..., pattern=r'^[A-Z]$')
    shelf_height: int = Field(..., ge=1)


class SetStockRequest(BaseModel):
    quantity: int = Field(..., ge=0)
    reason: str | None = Field(default=None, max_length=255)
```

**3d — Exportar los dos schemas nuevos desde `schemas/__init__.py`.**

### Step 4 — Servicio

**Archivo:** `microtv-crm-backend/src/crm_backend/services/stock_service.py`

**4a — `CreateStockProductCommand`:** agregar campo `minimum_stock: int = 3`.

**4b — `create_product()`:** pasar `minimum_stock=command.minimum_stock` al llamar `StockProduct.create()`.

**4c — `decrease_stock()`:** reemplazar los dos umbrales hardcodeados `< 3` / `< 3 unidades` por `< product.minimum_stock`:

Antes:
```python
elif stock_now < 3:
    notification_type = NotificationType.STOCK_LOW
    title = f"Stock bajo: {saved_product.visible_product_code} ({stock_now} unidades)"
    body = f"El producto '{saved_product.product_name}' tiene menos de 3 unidades disponibles."
```
Después:
```python
elif stock_now < saved_product.minimum_stock:
    notification_type = NotificationType.STOCK_LOW
    title = f"Stock bajo: {saved_product.visible_product_code} ({stock_now} unidades)"
    body = f"El producto '{saved_product.product_name}' tiene menos de {saved_product.minimum_stock} unidades disponibles."
```

**4d — Nuevo método `update_product_location`:**
```python
def update_product_location(
    self,
    actor: ResolvedCrmSession,
    product_id: str,
    shelf_id: str,
    shelf_height: int,
) -> StockProduct:
    self._ensure_inventory_write_access(actor)
    product = self._get_operable_product(product_id)
    product.shelf_id = shelf_id
    product.shelf_height = shelf_height
    return self._product_repository.save(product)
```

**4e — Nuevo método `set_stock`:**
```python
def set_stock(
    self,
    actor: ResolvedCrmSession,
    product_id: str,
    quantity: int,
) -> StockProduct:
    self._ensure_inventory_write_access(actor)
    product = self._get_operable_product(product_id)

    current = product.current_stock
    if quantity > current:
        product.increase_stock(
            quantity=quantity - current,
            actor_crm_user_id=actor.crm_user.crm_user_id,
            warehouse_id=self._product_repository.get_default_warehouse_id(),
        )
    elif quantity < current:
        product.decrease_stock(
            quantity=current - quantity,
            actor_crm_user_id=actor.crm_user.crm_user_id,
            warehouse_id=self._product_repository.get_default_warehouse_id(),
        )

    saved_product = self._product_repository.save(product)

    # Disparar notificación si el nuevo stock cae bajo el umbral
    if self._notification_service is not None and self._user_repository is not None:
        stock_now = saved_product.current_stock
        if stock_now == 0:
            notification_type = NotificationType.STOCK_OUT
            title = f"Sin stock: {saved_product.visible_product_code}"
            body = f"El producto '{saved_product.product_name}' llegó a 0 unidades."
        elif stock_now < saved_product.minimum_stock:
            notification_type = NotificationType.STOCK_LOW
            title = f"Stock bajo: {saved_product.visible_product_code} ({stock_now} unidades)"
            body = f"El producto '{saved_product.product_name}' tiene menos de {saved_product.minimum_stock} unidades disponibles."
        else:
            notification_type = None

        if notification_type is not None:
            deposito_ids = [u.crm_user_id for u in self._user_repository.list_active_by_role_key("deposito")]
            ejecutivo_ids = [u.crm_user_id for u in self._user_repository.list_active_by_role_key("ejecutivo")]
            recipient_ids = list({*deposito_ids, *ejecutivo_ids})
            self._notification_service.notify_bulk(
                recipient_crm_user_ids=recipient_ids,
                notification_type=notification_type,
                title=title,
                body=body,
                entity_type=NotificationEntityType.STOCK_PRODUCT,
                entity_id=saved_product.product_id,
            )

    return saved_product
```

### Step 5 — Endpoints

**Archivo:** `microtv-crm-backend/src/crm_backend/api/endpoints/stock.py`

**5a — `_build_product_response`:** agregar los tres campos nuevos:
```python
return StockProductResponse(
    ...
    minimum_stock=product.minimum_stock,
    shelf_id=product.shelf_id,
    shelf_height=product.shelf_height,
)
```

**5b — `_parse_create_product_request`:** en la rama `multipart/form-data` agregar:
```python
"minimum_stock": int(form.get("minimum_stock") or 3),
```

**5c — `create_product`:** en `CreateStockProductCommand(...)` agregar:
```python
minimum_stock=payload.minimum_stock,
```

**5d — Dos rutas nuevas:**
```python
@router.patch(
    "/products/{product_id}/location",
    response_model=StockProductResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def update_product_location(
    product_id: str,
    payload: UpdateProductLocationRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    stock_service: StockApplicationService = Depends(get_stock_application_service),
) -> StockProductResponse:
    product = stock_service.update_product_location(
        actor, product_id=product_id, shelf_id=payload.shelf_id, shelf_height=payload.shelf_height
    )
    return _build_product_response(product)


@router.patch(
    "/products/{product_id}/stock",
    response_model=StockProductResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def set_stock(
    product_id: str,
    payload: SetStockRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    stock_service: StockApplicationService = Depends(get_stock_application_service),
) -> StockProductResponse:
    product = stock_service.set_stock(actor, product_id=product_id, quantity=payload.quantity)
    return _build_product_response(product)
```

Importar `UpdateProductLocationRequest` y `SetStockRequest` desde `crm_backend.schemas`.

---

## Phase 3 — Frontend: modelos y servicio

### Step 6 — Model

**Archivo:** `microtv-crm-frontend/src/app/core/models/inventory-product.model.ts`

Agregar en `InventoryProduct`:
```typescript
minimumStock: number;
shelfId: string | null;
shelfHeight: number | null;
```

En `InventoryTableColumn.key`, agregar `'location'` al union type.

### Step 7 — Service

**Archivo:** `microtv-crm-frontend/src/app/core/services/inventory.service.ts`

**7a — `StockProductResponseDto`:** agregar:
```typescript
minimum_stock: number;
shelf_id: string | null;
shelf_height: number | null;
```

**7b — Mapper de producto:** agregar:
```typescript
minimumStock: dto.minimum_stock,
shelfId: dto.shelf_id,
shelfHeight: dto.shelf_height,
```

**7c — Método `setStock`:**
```typescript
setStock(productId: string, quantity: number): Observable<InventoryProduct> {
  const headers = this.buildAuthHeaders();
  if (!headers) return this.failRequest('No hay sesión activa.');
  return this.http
    .patch<StockProductResponseDto>(this.buildUrl(`/stock/products/${productId}/stock`), { quantity }, { headers })
    .pipe(
      tap((dto) => {
        const updated = this.mapProduct(dto);
        this.productsSubject.next(
          this.productsSubject.value.map((p) => (p.productId === updated.productId ? updated : p))
        );
      }),
      map((dto) => this.mapProduct(dto)),
      catchError((err) => this.handleError(err))
    );
}
```

**7d — Método `updateProductLocation`:**
```typescript
updateProductLocation(productId: string, shelfId: string, shelfHeight: number): Observable<InventoryProduct> {
  const headers = this.buildAuthHeaders();
  if (!headers) return this.failRequest('No hay sesión activa.');
  return this.http
    .patch<StockProductResponseDto>(
      this.buildUrl(`/stock/products/${productId}/location`),
      { shelf_id: shelfId, shelf_height: shelfHeight },
      { headers }
    )
    .pipe(
      tap((dto) => {
        const updated = this.mapProduct(dto);
        this.productsSubject.next(
          this.productsSubject.value.map((p) => (p.productId === updated.productId ? updated : p))
        );
      }),
      map((dto) => this.mapProduct(dto)),
      catchError((err) => this.handleError(err))
    );
}
```

---

## Phase 4 — Frontend: UI

### Step 8 — Feature 1: Modal de imagen (nuevo componente compartido)

**Crear componente:** `microtv-crm-frontend/src/app/shared/ui/image-viewer-dialog/`

Tres archivos: `.component.ts`, `.component.html`, `.component.scss`.

**`image-viewer-dialog.component.ts`:**
```typescript
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface ImageViewerDialogData {
  imageUrl: string;
  altText: string;
}

@Component({
  selector: 'app-image-viewer-dialog',
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatIconModule],
  templateUrl: './image-viewer-dialog.component.html',
  styleUrl: './image-viewer-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ImageViewerDialogComponent {
  readonly data = inject<ImageViewerDialogData>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<ImageViewerDialogComponent>);

  close(): void {
    this.dialogRef.close();
  }
}
```

**`image-viewer-dialog.component.html`:**
```html
<div class="image-viewer-dialog">
  <button
    mat-icon-button
    type="button"
    class="image-viewer-dialog__close"
    aria-label="Cerrar imagen"
    (click)="close()"
  >
    <mat-icon>close</mat-icon>
  </button>
  <img
    class="image-viewer-dialog__image"
    [src]="data.imageUrl"
    [alt]="data.altText"
  />
</div>
```

**`image-viewer-dialog.component.scss`:**
```scss
.image-viewer-dialog {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  padding: 0;

  &__close {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    z-index: 10;
    color: #fff;
  }

  &__image {
    display: block;
    max-width: 90vw;
    max-height: 90vh;
    object-fit: contain;
  }
}
```

En los estilos globales (`styles.scss` o similar), agregar el panel class para eliminar padding del dialog:
```scss
.image-viewer-panel {
  .mat-mdc-dialog-container .mdc-dialog__surface {
    padding: 0;
    background: transparent;
    overflow: hidden;
  }
}
```

**`inventory-table.component.ts`:** 
- Inyectar `MatDialog`
- Importar `ImageViewerDialogComponent` y `MatDialogModule`
- Agregar método:
```typescript
openImage(product: InventoryProduct): void {
  if (!product.imageUrl) return;
  this.dialog.open(ImageViewerDialogComponent, {
    data: { imageUrl: product.imageUrl, altText: product.name },
    maxWidth: '95vw',
    maxHeight: '95vh',
    panelClass: 'image-viewer-panel'
  });
}
```

**`inventory-table.component.html`** — en ambos `<img>` (desktop y mobile):
```html
<img
  class="inventory-table__image"
  [src]="imageFor(product)"
  [alt]="'Imagen de ' + product.name"
  (error)="onImageError($event)"
  [class.inventory-table__image--clickable]="product.imageUrl"
  (click)="product.imageUrl && openImage(product)"
/>
```

**`inventory-table.component.scss`:** agregar:
```scss
.inventory-table__image--clickable {
  cursor: zoom-in;
}
```

### Step 9 — Feature 2: Stock mínimo en creación de producto

**Archivo:** `microtv-crm-frontend/src/app/features/inventory/components/create-product-form.types.ts`

Agregar a `CreateProductFormModel`:
```typescript
minimumStock: FormControl<number>;
```

**Archivo:** `microtv-crm-frontend/src/app/features/inventory/components/create-product-dialog/create-product-dialog.component.ts`

En `this.formBuilder.group<CreateProductFormModel>({...})`, agregar:
```typescript
minimumStock: this.formBuilder.control(3, {
  validators: [Validators.required, Validators.min(1)],
  nonNullable: true
})
```

**Archivo:** `create-product-dialog.component.html`

Agregar campo después del campo `initialStock`:
```html
<mat-form-field appearance="outline">
  <mat-label>Stock mínimo</mat-label>
  <input matInput type="number" min="1" formControlName="minimumStock" />
  <mat-hint>Notifica cuando el stock baje de este valor. Por defecto: 3.</mat-hint>
  <mat-error *ngIf="form.controls.minimumStock.hasError('min')">Debe ser al menos 1.</mat-error>
</mat-form-field>
```

**Archivo:** `microtv-crm-frontend/src/app/core/models/create-product.model.ts`

Agregar a `CreateInventoryProductFormValue`:
```typescript
minimumStock: number;
```

**Archivo:** `inventory.service.ts` — en `createProduct()` / el FormData o JSON enviado al backend:
```typescript
formData.append('minimum_stock', String(value.minimumStock));
// o en JSON: minimum_stock: value.minimumStock
```

### Step 10 — Feature 3: Columnas Estantería/Altura con edición inline

**Archivo:** `inventory-table.component.ts`

Agregar a `displayedColumns`:
```typescript
readonly displayedColumns = ['image', 'id', 'name', 'category', 'stock', 'location', 'actions'];
```

Agregar signals y métodos:
```typescript
readonly editingLocationId = signal<string | null>(null);
readonly locationEditShelfId = signal<string>('');
readonly locationEditHeight = signal<number | null>(null);
readonly shelfOptions = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

startEditLocation(product: InventoryProduct): void {
  this.editingLocationId.set(product.productId);
  this.locationEditShelfId.set(product.shelfId ?? '');
  this.locationEditHeight.set(product.shelfHeight ?? null);
}

cancelEditLocation(): void {
  this.editingLocationId.set(null);
}

async confirmEditLocation(productId: string): Promise<void> {
  const shelfId = this.locationEditShelfId();
  const height = this.locationEditHeight();
  if (!shelfId || !height || height < 1) return;

  this.pendingProductId.set(productId);
  try {
    await firstValueFrom(this.inventoryService.updateProductLocation(productId, shelfId, height));
    this.snackBar.open('Ubicación actualizada.', 'Cerrar', { duration: 2500 });
    this.editingLocationId.set(null);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'No se pudo actualizar la ubicación.';
    this.snackBar.open(message, 'Cerrar', { duration: 4500 });
  } finally {
    this.pendingProductId.set(null);
  }
}
```

**Archivo:** `inventory-table.component.html`

Agregar columna `location` en la tabla desktop (antes de `actions`):
```html
<ng-container matColumnDef="location">
  <th mat-header-cell *matHeaderCellDef>Ubicación</th>
  <td mat-cell *matCellDef="let product">
    @if (editingLocationId() === product.productId) {
      <div class="inventory-table__location-edit">
        <select [value]="locationEditShelfId()" (change)="locationEditShelfId.set($any($event.target).value)">
          <option value="">-</option>
          @for (letter of shelfOptions; track letter) {
            <option [value]="letter">{{ letter }}</option>
          }
        </select>
        <input
          type="number"
          min="1"
          [value]="locationEditHeight()"
          (input)="locationEditHeight.set(+$any($event.target).value || null)"
          placeholder="Altura"
          class="inventory-table__location-height-input"
        />
        <button mat-icon-button type="button" aria-label="Confirmar ubicación" (click)="confirmEditLocation(product.productId)">
          <mat-icon>check</mat-icon>
        </button>
        <button mat-icon-button type="button" aria-label="Cancelar" (click)="cancelEditLocation()">
          <mat-icon>close</mat-icon>
        </button>
      </div>
    } @else {
      <span class="inventory-table__location-value">
        {{ product.shelfId ?? '-' }} / {{ product.shelfHeight ?? '-' }}
      </span>
      @if (canManageStock()) {
        <button mat-icon-button type="button" aria-label="Editar ubicación" (click)="startEditLocation(product)">
          <mat-icon>edit</mat-icon>
        </button>
      }
    }
  </td>
</ng-container>
```

En mobile card, agregar bloque similar debajo del bloque de categoría.

### Step 11 — Feature 4: Stock editable

**Archivo:** `inventory-table.component.ts`

Agregar signals y métodos:
```typescript
readonly editingStockId = signal<string | null>(null);
readonly stockEditValue = signal<number | null>(null);

startEditStock(product: InventoryProduct): void {
  this.editingStockId.set(product.productId);
  this.stockEditValue.set(product.stock);
}

cancelEditStock(): void {
  this.editingStockId.set(null);
  this.stockEditValue.set(null);
}

async confirmEditStock(productId: string): Promise<void> {
  const value = this.stockEditValue();
  if (value === null || value < 0) return;

  this.pendingProductId.set(productId);
  try {
    await firstValueFrom(this.inventoryService.setStock(productId, value));
    this.snackBar.open('Stock actualizado.', 'Cerrar', { duration: 2500 });
    this.editingStockId.set(null);
    this.stockEditValue.set(null);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'No se pudo actualizar el stock.';
    this.snackBar.open(message, 'Cerrar', { duration: 4500 });
  } finally {
    this.pendingProductId.set(null);
  }
}
```

**Actualizar `stockTone()`** para usar `product.minimumStock` en lugar del `3` hardcodeado:
```typescript
stockTone(product: InventoryProduct): 'empty' | 'low' | 'healthy' {
  if (product.stock === 0) return 'empty';
  if (product.stock < product.minimumStock) return 'low';
  return 'healthy';
}
```

**Archivo:** `inventory-table.component.html` — columna `stock`:
```html
<ng-container matColumnDef="stock">
  <th mat-header-cell *matHeaderCellDef>{{ labelFor('stock') }}</th>
  <td mat-cell *matCellDef="let product">
    @if (editingStockId() === product.productId) {
      <div class="inventory-table__stock-edit">
        <input
          type="number"
          min="0"
          [value]="stockEditValue()"
          (input)="stockEditValue.set(+$any($event.target).value)"
          class="inventory-table__stock-input"
        />
        <button mat-icon-button type="button" aria-label="Confirmar stock" (click)="confirmEditStock(product.productId)">
          <mat-icon>check</mat-icon>
        </button>
        <button mat-icon-button type="button" aria-label="Cancelar" (click)="cancelEditStock()">
          <mat-icon>close</mat-icon>
        </button>
      </div>
    } @else {
      <span class="inventory-table__stock-pill" [class]="'inventory-table__stock-pill--' + stockTone(product)">
        {{ stockLabel(product) }}
      </span>
      @if (canManageStock()) {
        <button mat-icon-button type="button" aria-label="Editar stock" (click)="startEditStock(product)">
          <mat-icon>edit</mat-icon>
        </button>
      }
    }
  </td>
</ng-container>
```

---

## Phase 5 — Fix: Refresh no redirige al dashboard

### Step 12 — Auth session service

**Archivo:** `microtv-crm-frontend/src/app/core/services/auth-session.service.ts`

**Causa raíz:** en `bootstrap()`, cuando `/auth/me` devuelve error (token expirado), se llama `this.logout({ navigate: true })`. Ese método navega a `/login` sin `redirectTo`, y el login page usa `'/'` como fallback — que resuelve al `DashboardPageComponent`.

**Fix:** en el handler `error` de `bootstrap()`, reemplazar:
```typescript
error: () => this.logout({ navigate: true })
```
por:
```typescript
error: () => {
  const returnUrl = this.router.url;
  this.logout({ navigate: false });
  void this.router.navigate(['/login'], {
    queryParams: returnUrl && returnUrl !== '/' ? { redirectTo: returnUrl } : {}
  });
}
```

Esto preserva la URL actual (ej. `/inventory`) para que después del login el usuario sea devuelto al mismo lugar.

---

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `microtv-crm-backend/sql/20260512_inventory_product_enhancements.sql` | Crear — migración DB |
| `microtv-crm-backend/sql/migrate_prod.sh` | Actualizar — agregar verificación de las 3 columnas nuevas |
| `microtv-crm-backend/src/crm_backend/models/stock_product.py` | Agregar 3 columnas ORM |
| `microtv-crm-backend/src/crm_backend/schemas/stock.py` | Agregar campos + 2 schemas nuevos |
| `microtv-crm-backend/src/crm_backend/schemas/__init__.py` | Exportar 2 schemas nuevos |
| `microtv-crm-backend/src/crm_backend/services/stock_service.py` | `decrease_stock` dinámico + 2 métodos nuevos |
| `microtv-crm-backend/src/crm_backend/api/endpoints/stock.py` | 2 rutas nuevas + actualizar builder y parser |
| `microtv-crm-frontend/src/app/core/models/inventory-product.model.ts` | Agregar 3 campos |
| `microtv-crm-frontend/src/app/core/services/inventory.service.ts` | Actualizar DTO/mapper + 2 métodos nuevos |
| `microtv-crm-frontend/src/app/shared/ui/image-viewer-dialog/` | **Crear** componente nuevo |
| `microtv-crm-frontend/src/styles.scss` (o equivalente) | Agregar `.image-viewer-panel` panel class |
| `microtv-crm-frontend/src/app/features/inventory/components/inventory-table/inventory-table.component.ts` | Features 1, 3, 4 |
| `microtv-crm-frontend/src/app/features/inventory/components/inventory-table/inventory-table.component.html` | Features 1, 3, 4 |
| `microtv-crm-frontend/src/app/features/inventory/components/inventory-table/inventory-table.component.scss` | Cursor zoom-in + estilos edición inline |
| `microtv-crm-frontend/src/app/features/inventory/components/create-product-dialog/create-product-dialog.component.ts` | Feature 2 |
| `microtv-crm-frontend/src/app/features/inventory/components/create-product-dialog/create-product-dialog.component.html` | Feature 2 |
| `microtv-crm-frontend/src/app/features/inventory/components/create-product-form.types.ts` | Feature 2 |
| `microtv-crm-frontend/src/app/core/models/create-product.model.ts` | Feature 2 |
| `microtv-crm-frontend/src/app/core/services/auth-session.service.ts` | Fix 5 |

---

## Verificación

1. Crear producto con `minimumStock: 5` → restar stock hasta 4 → confirmar que llega notificación `stock_low` con el umbral correcto en el body
2. Asignar ubicación `C / 2` a un producto → verificar que la columna muestra `C / 2`
3. Hacer click en imagen de producto con imagen real → abre modal oscuro con la imagen
4. Hacer click en imagen de producto con placeholder → no abre modal
5. Editar stock a `7` directamente → pill del stock se actualiza; si 7 >= minimumStock el tono es `healthy`
6. Iniciar sesión, navegar a `/inventory`, dejar expirar el token, refrescar la página → después de re-login vuelve a `/inventory`, no al dashboard
