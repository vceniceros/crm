# 0027 — Base de conocimientos: UX/UI Fixes Post-Implementación

> **Fecha:** 2026-05-22
> **Tipo:** Fix / UX
> **Estado:** Pendiente de implementación
> **Prerequisito:** 0026-knowledge-base-module-full-plan.md — feature base ya implementada.

---

## Resumen

Tres correcciones menores al módulo de Base de conocimientos una vez implementado el feature completo:

1. **"Modo escritura" muestra texto plano** — convertir a split-pane con preview en vivo
2. **Contenido pegado al left margin** — centrar artículo en lectura y PDF export
3. **Categorías desacopladas de tickets** — linkear directo a `crm_categories`

---

## Fix 1 — "Modo escritura": split-pane con preview en vivo

### Problema

El tab "Modo escritura" muestra un `<textarea>` con fuente monospace. El texto `**negrita**` se ve literalmente como `**negrita**`, no renderizado. El usuario espera ver el formato resultante mientras escribe.

### Solución

Dentro del tab "Modo escritura", reemplazar el textarea suelto por un layout split 50/50:
- **Panel izquierdo:** toolbar + textarea (escribir Markdown)
- **Panel derecho:** `<markdown [data]="value">` que se actualiza en tiempo real

No se agregan dependencias nuevas — `ngx-markdown` ya está instalado y se usa en el tab "Vista previa".

En mobile (≤720px): colapsar a stack vertical (textarea arriba, preview abajo).

### Archivos a modificar

**`src/app/features/knowledge-base/components/knowledge-markdown-editor/knowledge-markdown-editor.component.html`**

Cambiar el contenido del tab "Modo escritura" de:
```html
<mat-tab label="Modo escritura">
  <div class="toolbar">...</div>
  <textarea #textarea class="kb-editor-textarea" ...></textarea>
</mat-tab>
```

A:
```html
<mat-tab label="Modo escritura">
  <div class="split-pane">
    <div class="write-pane">
      <div class="toolbar">...</div>
      <textarea #textarea class="kb-editor-textarea" ...></textarea>
    </div>
    <div class="preview-pane">
      <markdown [data]="value"></markdown>
    </div>
  </div>
</mat-tab>
```

**`src/app/features/knowledge-base/components/knowledge-markdown-editor/knowledge-markdown-editor.component.scss`**

Agregar:
```scss
.split-pane {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 22rem;
  border-top: 1px solid color-mix(in srgb, var(--mat-sys-outline) 20%, transparent);
}

.write-pane {
  border-right: 1px solid color-mix(in srgb, var(--mat-sys-outline) 20%, transparent);
  display: flex;
  flex-direction: column;
}

.write-pane .kb-editor-textarea {
  flex: 1;
  min-height: 0;
}

.preview-pane {
  padding: 1rem;
  overflow-y: auto;
  font-size: 0.95rem;
  line-height: 1.6;
}

.preview-pane img {
  max-width: 100%;
  border-radius: 6px;
}

@media (max-width: 720px) {
  .split-pane {
    grid-template-columns: 1fr;
  }
  .write-pane {
    border-right: none;
    border-bottom: 1px solid color-mix(in srgb, var(--mat-sys-outline) 20%, transparent);
  }
}
```

---

## Fix 2 — Contenido centrado en lectura y PDF export

### Problema

`.article-body` tiene `max-width: 58rem` pero sin `margin: 0 auto`, por lo que el contenido queda pegado al borde izquierdo tanto en la vista de detalle como en el PDF exportado (html2canvas captura el DOM renderizado, refleja el mismo layout).

### Solución

Agregar `margin: 0 auto` y `padding: 1.5rem 2rem` a `.article-body`. El PDF se beneficia automáticamente.

### Archivos a modificar

**`src/app/features/knowledge-base/components/knowledge-article-detail/knowledge-article-detail.component.scss`**

Cambiar:
```scss
.article-body {
  max-width: 58rem;
  line-height: 1.65;
}
```

A:
```scss
.article-body {
  max-width: 58rem;
  margin: 0 auto;
  padding: 1.5rem 2rem;
  line-height: 1.65;
}
```

---

## Fix 3 — Categorías linkeadas a `crm_categories` (mismas que tickets)

### Problema

Knowledge base tiene su propia tabla `knowledge_categories` con 5 seeds fijos independientes. Los usuarios esperan ver las mismas categorías que usan en tickets/tareas.

### Decisión

Eliminar `knowledge_categories` por completo. `knowledge_articles.category_id` pasa a referenciar `crm_categories(category_id)` directamente.

### Archivos a modificar

#### Backend

**`microtv-crm-backend/sql/20260522_knowledge_base_fix_categories_fk.sql`** *(nuevo archivo)*

```sql
-- Fix: knowledge_articles.category_id → crm_categories en lugar de knowledge_categories

-- 1. Eliminar FK viejo hacia knowledge_categories
ALTER TABLE knowledge_articles
    DROP CONSTRAINT IF EXISTS knowledge_articles_category_id_fkey;

-- 2. Limpiar category_id en artículos que referencien knowledge_categories
--    (si no hay datos en producción, puede saltarse)
UPDATE knowledge_articles SET category_id = NULL
WHERE category_id NOT IN (SELECT category_id FROM crm_categories);

-- 3. Agregar nuevo FK hacia crm_categories
ALTER TABLE knowledge_articles
    ADD CONSTRAINT fk_knowledge_articles_crm_category
    FOREIGN KEY (category_id) REFERENCES crm_categories(category_id) ON DELETE SET NULL;

-- 4. Eliminar tabla knowledge_categories (ya no se usa)
DROP TABLE IF EXISTS knowledge_categories;
```

---

**`src/crm_backend/models/knowledge.py`**

- Eliminar la clase `KnowledgeCategory`
- Importar `CrmCategory` desde `crm_backend.models.settings`
- Cambiar la relación `KnowledgeArticle.category`:

```python
# Eliminar:
# class KnowledgeCategory(Base): ...

# Importar al inicio del archivo:
from crm_backend.models.settings import CrmCategory  # noqa: F401

# En KnowledgeArticle, cambiar:
category: Mapped["CrmCategory | None"] = relationship(
    "CrmCategory",
    foreign_keys=[category_id],
    lazy="selectin",
)
```

---

**`src/crm_backend/repositories/knowledge_repository.py`**

Cambiar `list_categories()`:

```python
# Antes:
def list_categories(self) -> list[KnowledgeCategory]:
    return list(self._session.scalars(
        select(KnowledgeCategory).order_by(KnowledgeCategory.name)
    ))

# Después:
def list_categories(self) -> list[CrmCategory]:
    return list(self._session.scalars(
        select(CrmCategory)
        .where(CrmCategory.is_active == True)  # noqa: E712
        .order_by(CrmCategory.name)
    ))
```

Actualizar el import: `from crm_backend.models.settings import CrmCategory`

---

**`src/crm_backend/schemas/knowledge.py`**

Cambiar `KnowledgeCategoryResponse`:

```python
# Antes:
class KnowledgeCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    article_category_id: str
    name: str
    slug: str
    description: str | None

# Después:
class KnowledgeCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category_id: str
    name: str
    description: str | None
```

> `slug` se elimina — `CrmCategory` no tiene campo slug.

---

**`src/crm_backend/services/knowledge_service.py`**

Cambiar la firma de retorno de `list_categories`:

```python
# Antes:
def list_categories(self) -> list[KnowledgeCategory]:

# Después:
def list_categories(self) -> list[CrmCategory]:
```

#### Frontend

**`src/app/core/models/knowledge.model.ts`**

```typescript
// Antes:
export interface KnowledgeCategory {
  article_category_id: string;
  name: string;
  slug: string;
  description: string | null;
}

// Después:
export interface KnowledgeCategory {
  category_id: string;
  name: string;
  description: string | null;
}
```

---

**`src/app/features/knowledge-base/components/knowledge-base-page/knowledge-base-page.component.html`**

Líneas 22–23, reemplazar `article_category_id` por `category_id`:

```html
<!-- Antes: -->
@for (category of categories(); track category.article_category_id) {
  <mat-option [value]="category.article_category_id">{{ category.name }}</mat-option>

<!-- Después: -->
@for (category of categories(); track category.category_id) {
  <mat-option [value]="category.category_id">{{ category.name }}</mat-option>
```

---

**`src/app/features/knowledge-base/components/knowledge-article-editor/knowledge-article-editor.component.html`**

Líneas 29–30, mismo rename:

```html
<!-- Antes: -->
@for (category of categories(); track category.article_category_id) {
  <mat-option [value]="category.article_category_id">{{ category.name }}</mat-option>

<!-- Después: -->
@for (category of categories(); track category.category_id) {
  <mat-option [value]="category.category_id">{{ category.name }}</mat-option>
```

---

**`src/app/features/knowledge-base/components/knowledge-article-editor/knowledge-article-editor.component.ts`**

Línea 126:

```typescript
// Antes:
this.categoryId = article.category?.article_category_id ?? null;

// Después:
this.categoryId = article.category?.category_id ?? null;
```

---

## Resumen de archivos

| Archivo | Fix | Tipo |
|---------|-----|------|
| `knowledge-markdown-editor.component.html` | #1 | Modificar |
| `knowledge-markdown-editor.component.scss` | #1 | Modificar |
| `knowledge-article-detail.component.scss` | #2 | Modificar |
| `sql/20260522_knowledge_base_fix_categories_fk.sql` | #3 | Nuevo |
| `models/knowledge.py` | #3 | Modificar |
| `repositories/knowledge_repository.py` | #3 | Modificar |
| `schemas/knowledge.py` | #3 | Modificar |
| `services/knowledge_service.py` | #3 | Modificar |
| `knowledge.model.ts` | #3 | Modificar |
| `knowledge-base-page.component.html` | #3 | Modificar |
| `knowledge-article-editor.component.html` | #3 | Modificar |
| `knowledge-article-editor.component.ts` | #3 | Modificar |

---

## Verificación

1. `npm run build` — sin errores nuevos
2. "Modo escritura": escribir `**hola**` → panel derecho muestra **hola** en negrita en tiempo real
3. Vista de detalle: artículo centrado con margen interior visible, no pegado al borde
4. Exportar PDF: contenido con padding izquierdo y derecho
5. Dropdown de categorías en el editor: muestra las mismas categorías que tickets (las activas en `crm_categories`)
6. Artículos existentes con `category_id` nulo siguen funcionando (ON DELETE SET NULL)
