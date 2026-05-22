# 0026 — Base de conocimientos: Full Production-Ready Plan

> **Fecha:** 2026-05-22  
> **Tipo:** Auditoría + Planning  
> **Estado:** Pendiente de implementación  
> **Prerequisito:** Leer antes de implementar cualquier cambio al módulo de Base de conocimientos.

---

## A. Executive Summary

Agregar un nuevo módulo "Base de conocimientos" al CRM MicroTV/YCC. El objetivo es centralizar procedimientos internos, manuales, guías de resolución de problemas, instructivos de instalación e instrucciones operativas de campo.

El módulo es **completamente aditivo**: no modifica ningún módulo existente. Reutiliza la infraestructura de media storage, servicios, repositorios, autenticación y PDF del sistema actual.

**Stack de implementación:**
- Backend: FastAPI + SQLAlchemy 2.0 + repositorio DDD + ReportLab (ya instalado) + estrategia de media existente
- Frontend: Angular 21 + Angular Material + html2canvas/jspdf (ya instalados) + `ngx-markdown` (nuevo) + `dompurify` (nuevo)
- DB: 4 tablas nuevas via migración SQL (patrón existente en `sql/`)

---

## B. Estado Actual Confirmado

| Componente | Estado | Notas |
|---|---|---|
| Módulo "Base de conocimientos" | ❌ NO EXISTE | Feature completamente nueva |
| Tablas en DB | ❌ NO EXISTEN | Requiere migración SQL |
| Endpoints de API | ❌ NO EXISTEN | Requiere nuevos routers |
| Sidebar entry | ❌ NO EXISTE | Requiere `layout-data.json` + permission key |
| Markdown rendering | ❌ SIN LIBRERÍA | Requiere `ngx-markdown` + `dompurify` |
| Media storage (imágenes KB) | ❌ SIN CONFIG | Requiere paths en `Settings` |
| PDF export | ✅ LIBRERÍAS INSTALADAS | `html2canvas` + `jspdf` — mismo patrón que reportes |
| Auth / roles | ✅ EXISTENTE | Reutilizar `authGuard` + `adminOnlyGuard` |
| Strategy de media upload | ✅ EXISTENTE | Extender `TaskMediaStorageFacade` pattern |

---

## C. Flujo Esperado (end-to-end)

```
1. Cualquier usuario autenticado accede a "Base de conocimientos" desde el sidebar
2. Ve el listado de artículos con buscador por título/categoría/contenido
3. [Opcional] Filtra por categoría
4. Abre un artículo → se renderiza el Markdown como HTML limpio
5. Exporta el artículo como PDF (html2canvas + jspdf, mismo patrón que reportes)
6. Para crear/editar: abre el editor con dos modos:
   a. "Cargar Markdown": textarea para pegar Markdown preparado externamente
   b. "Modo escritura": toolbar con botones de formato + textarea
7. En el editor puede subir imágenes (se guardan en media storage, se insertan como referencia Markdown)
8. Puede adjuntar videos que se muestran bajo "Videos asociados" en la vista de detalle
9. Solo admin puede eliminar artículos (soft delete)
```

---

## D. Modelo de Datos — Propuesta

### D1. Tablas Nuevas

```sql
-- knowledge_categories: taxonomía de artículos
CREATE TABLE knowledge_categories (
    article_category_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 VARCHAR(100) NOT NULL,
    slug                 VARCHAR(100) NOT NULL UNIQUE,
    description          TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- knowledge_articles: artículos con soft delete
CREATE TABLE knowledge_articles (
    article_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    title                VARCHAR(255) NOT NULL,
    slug                 VARCHAR(255) NOT NULL UNIQUE,
    category_id          UUID         REFERENCES knowledge_categories(article_category_id) ON DELETE SET NULL,
    content_md           TEXT         NOT NULL DEFAULT '',
    status               VARCHAR(20)  NOT NULL DEFAULT 'published'
                             CHECK (status IN ('draft', 'published')),
    created_by_user_id   UUID         NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    updated_by_user_id   UUID         REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at           TIMESTAMPTZ  NULL,     -- soft delete
    is_auto_draft        BOOLEAN      NOT NULL DEFAULT FALSE  -- TRUE para drafts creados automáticamente por el editor
);

-- knowledge_article_versions: snapshot inmutable antes de cada actualización
CREATE TABLE knowledge_article_versions (
    version_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id           UUID         NOT NULL REFERENCES knowledge_articles(article_id) ON DELETE CASCADE,
    version_number       INTEGER      NOT NULL,
    title                VARCHAR(255) NOT NULL,
    category_id          UUID,
    content_md           TEXT         NOT NULL,
    status               VARCHAR(20)  NOT NULL,
    saved_by_user_id     UUID         NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_article_version UNIQUE (article_id, version_number)
);

-- knowledge_article_attachments: imágenes y videos adjuntos
CREATE TABLE knowledge_article_attachments (
    attachment_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id           UUID         NOT NULL REFERENCES knowledge_articles(article_id) ON DELETE CASCADE,
    file_type            VARCHAR(10)  NOT NULL CHECK (file_type IN ('image', 'video')),
    mime_type            VARCHAR(100) NOT NULL,
    original_filename    VARCHAR(255) NOT NULL,
    stored_filename      VARCHAR(255) NOT NULL,
    file_url             VARCHAR(500) NOT NULL,
    storage_path         VARCHAR(500) NOT NULL,
    size_bytes           INTEGER,
    created_by_user_id   UUID         NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

### D2. Índices

```sql
CREATE INDEX ix_knowledge_articles_title       ON knowledge_articles(title);
CREATE INDEX ix_knowledge_articles_slug        ON knowledge_articles(slug);
CREATE INDEX ix_knowledge_articles_category_id ON knowledge_articles(category_id);
CREATE INDEX ix_knowledge_articles_status      ON knowledge_articles(status);
CREATE INDEX ix_knowledge_articles_deleted_at  ON knowledge_articles(deleted_at);
CREATE INDEX ix_knowledge_article_attachments_article_id ON knowledge_article_attachments(article_id);
CREATE INDEX ix_knowledge_article_attachments_file_type  ON knowledge_article_attachments(file_type);
CREATE INDEX ix_knowledge_article_versions_article_id    ON knowledge_article_versions(article_id);
```

### D3. Seeds Opcionales

```sql
INSERT INTO knowledge_categories (name, slug, description) VALUES
  ('Instalaciones DVR',          'instalaciones-dvr',          'Guías paso a paso de instalación de equipos DVR'),
  ('Cableado y red',             'cableado-y-red',             'Procedimientos de cableado estructurado y networking'),
  ('Mantenimiento preventivo',   'mantenimiento-preventivo',   'Rutinas de mantenimiento periódico'),
  ('Resolución de problemas',    'resolucion-de-problemas',    'Guías de diagnóstico y solución de fallas'),
  ('Procedimientos internos',    'procedimientos-internos',    'Normas y procesos administrativos del equipo')
ON CONFLICT DO NOTHING;
```

> ⚠️ Usar `article_category_id` como PK de `knowledge_categories` para no colisionar con el modelo `CrmCategory` ya existente en el sistema.

---

## E. Cambios en Backend

### E1. `core/config.py` — Agregar config de media

```python
knowledge_images_max_bytes: int = 8 * 1024 * 1024    # 8 MB
knowledge_videos_max_bytes: int = 128 * 1024 * 1024   # 128 MB

@property
def knowledge_images_dir(self) -> Path:
    return self.crm_media_root_path / "knowledge" / "images"

@property
def knowledge_videos_dir(self) -> Path:
    return self.crm_media_root_path / "knowledge" / "videos"
```

### E2. `models/knowledge.py` — Modelos ORM

Nuevas clases: `KnowledgeCategory`, `KnowledgeArticle`, `KnowledgeArticleAttachment`, `KnowledgeArticleVersion`.

Patrón idéntico a `task_template.py`:
- IDs: `Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))`
- Timestamps: `DateTime(timezone=True)`, `server_default=func.now()`
- Soft delete: `deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
- Relaciones: `relationship(..., lazy="selectin")`

### E3. `schemas/knowledge.py` — Schemas Pydantic

```python
class KnowledgeCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    article_category_id: str
    name: str
    slug: str
    description: str | None

class KnowledgeArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    article_id: str
    title: str
    slug: str
    category: KnowledgeCategoryResponse | None
    status: str
    excerpt: str | None  # Primeros 200 chars de content_md, generado en servicio
    created_by_display_name: str
    created_at: datetime
    updated_at: datetime

class KnowledgeArticleDetail(KnowledgeArticleListItem):
    content_md: str
    attachments: list[KnowledgeAttachmentResponse] = []

class KnowledgeAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    attachment_id: str
    file_type: str
    mime_type: str
    original_filename: str
    file_url: str
    size_bytes: int | None
    created_at: datetime

class CreateKnowledgeArticleRequest(BaseModel):
    title: str = Field(default="", max_length=255)
    category_id: str | None = None
    content_md: str = Field(default="")
    status: Literal["draft", "published"] = "published"
    is_auto_draft: bool = False  # True cuando el frontend crea un draft vacío al abrir el editor

    @model_validator(mode="after")
    def validate_title_for_published(self) -> "CreateKnowledgeArticleRequest":
        if not self.is_auto_draft and self.status == "published":
            if len(self.title.strip()) < 3:
                raise ValueError("El título es obligatorio para artículos publicados (mínimo 3 caracteres).")
        return self

class UpdateKnowledgeArticleRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    category_id: str | None = None
    content_md: str | None = None
    status: Literal["draft", "published"] | None = None

class KnowledgeArticleFilterParams(BaseModel):
    search: str | None = None
    category_id: str | None = None
    status: Literal["draft", "published"] | None = "published"
```

### E4. `repositories/knowledge_repository.py` — Repositorio

```python
class KnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, filters: KnowledgeArticleFilterParams) -> list[KnowledgeArticle]:
        # WHERE deleted_at IS NULL + filtros de search/category/status
        # Usar ilike para búsqueda en title y content_md
        ...

    def get_by_id(self, article_id: str) -> KnowledgeArticle | None:
        # WHERE article_id = ? AND deleted_at IS NULL
        ...

    def get_by_slug(self, slug: str) -> KnowledgeArticle | None: ...

    def save(self, article: KnowledgeArticle) -> KnowledgeArticle:
        self._session.add(article)
        self._session.commit()
        self._session.refresh(article)
        return self.get_by_id(article.article_id) or article

    def soft_delete(self, article: KnowledgeArticle) -> None:
        article.deleted_at = func.now()
        self._session.commit()

    def list_categories(self) -> list[KnowledgeCategory]: ...

    def save_attachment(self, attachment: KnowledgeArticleAttachment) -> KnowledgeArticleAttachment: ...

    def get_attachment(self, attachment_id: str) -> KnowledgeArticleAttachment | None: ...

    def slug_exists(self, slug: str, exclude_id: str | None = None) -> bool:
        # WHERE slug = ? AND (exclude_id IS NULL OR article_id != exclude_id) AND deleted_at IS NULL
        ...

    def save_version_snapshot(self, article: KnowledgeArticle, saved_by_user_id: str) -> None:
        # Calcula el próximo version_number y persiste un KnowledgeArticleVersion inmutable
        ...

    def delete_attachment(self, attachment: KnowledgeArticleAttachment) -> None:
        self._session.delete(attachment)
        self._session.commit()
```

### E5. `infrastructure/knowledge_media_storage.py` — Facade de Media

`KnowledgeMediaStorageFacade` siguiendo exactamente el patrón de `TaskMediaStorageFacade`:

```python
class KnowledgeMediaStorageFacade:
    def __init__(self, settings: Settings):
        self._strategies = [
            ImageKnowledgeMediaStrategy(settings),   # JPEG, PNG, WEBP — knowledge_images_dir
            VideoKnowledgeMediaStrategy(settings),   # MP4, WEBM — knowledge_videos_dir
        ]

    async def store(self, upload: UploadFile) -> StoredTaskMedia:
        content = await upload.read()
        return self._resolve_strategy(upload).store(upload, content)

    def delete(self, stored_media: StoredTaskMedia) -> None: ...
```

Config:
- Imágenes: allowlist JPEG/PNG/WEBP, max `knowledge_images_max_bytes`, dir `knowledge_images_dir`
- Videos: allowlist MP4/WEBM, max `knowledge_videos_max_bytes`, dir `knowledge_videos_dir`
- Filenames: siempre `str(uuid4()) + extension` — nunca usar `original_filename` como `stored_filename`

### E6. `services/knowledge_service.py` — Servicio de Aplicación

```python
class KnowledgeApplicationService:
    def __init__(
        self,
        *,
        repository: KnowledgeRepository,
        media_storage: KnowledgeMediaStorageFacade,
        settings: Settings,
    ): ...

    def list_articles(self, actor: ResolvedCrmSession, filters: KnowledgeArticleFilterParams) -> list[KnowledgeArticle]:
        return self._repository.list(filters)

    def get_article(self, actor: ResolvedCrmSession, article_id: str) -> KnowledgeArticle:
        article = self._repository.get_by_id(article_id)
        if article is None:
            raise KnowledgeNotFoundError(f"Artículo {article_id} no encontrado.")
        return article

    def create_article(self, actor: ResolvedCrmSession, payload: CreateKnowledgeArticleRequest) -> KnowledgeArticle:
        slug = self._generate_slug(payload.title)
        article = KnowledgeArticle(
            article_id=str(uuid4()),
            title=payload.title,
            slug=slug,
            category_id=payload.category_id,
            content_md=payload.content_md,
            status=payload.status,
            created_by_user_id=actor.crm_user.crm_user_id,
            updated_by_user_id=actor.crm_user.crm_user_id,
        )
        return self._repository.save(article)

    def update_article(self, actor: ResolvedCrmSession, article_id: str, payload: UpdateKnowledgeArticleRequest) -> KnowledgeArticle:
        article = self.get_article(actor, article_id)
        # Guardar snapshot SOLO si hay cambios en campos relevantes (evitar snapshots vacíos)
        _has_relevant_changes = any([
            payload.title is not None and payload.title != article.title,
            payload.category_id is not None and payload.category_id != article.category_id,
            payload.content_md is not None and payload.content_md != article.content_md,
            payload.status is not None and payload.status != article.status,
        ])
        if _has_relevant_changes:
            self._repository.save_version_snapshot(article, saved_by_user_id=actor.crm_user.crm_user_id)
        if payload.title is not None:
            article.title = payload.title
            article.slug = self._generate_slug(payload.title, exclude_id=article.article_id)
        if payload.content_md is not None:
            article.content_md = payload.content_md
        if payload.category_id is not None:
            article.category_id = payload.category_id
        if payload.status is not None:
            article.status = payload.status
        article.updated_by_user_id = actor.crm_user.crm_user_id
        return self._repository.save(article)

    def delete_article(self, actor: ResolvedCrmSession, article_id: str) -> None:
        # SOLO admin puede eliminar (actor.role_keys usa el alias corto "admin", no "admin_crm")
        if "admin" not in actor.role_keys:
            raise KnowledgeAccessDeniedError("Solo los administradores pueden eliminar artículos.")
        article = self.get_article(actor, article_id)
        self._repository.soft_delete(article)

    async def upload_attachment(self, actor: ResolvedCrmSession, article_id: str, upload_file: UploadFile) -> KnowledgeArticleAttachment:
        article = self.get_article(actor, article_id)
        stored = await self._media_storage.store(upload_file)
        attachment = KnowledgeArticleAttachment(
            attachment_id=str(uuid4()),
            article_id=article.article_id,
            file_type="image" if stored.attachment_type == "PHOTO" else "video",
            mime_type=stored.mime_type,
            original_filename=upload_file.filename or stored.file_name,
            stored_filename=stored.file_name,
            file_url=stored.file_url,
            storage_path=stored.storage_path,
            size_bytes=stored.file_size_bytes,
            created_by_user_id=actor.crm_user.crm_user_id,
        )
        return self._repository.save_attachment(attachment)

    def delete_attachment(self, actor: ResolvedCrmSession, article_id: str, attachment_id: str) -> None:
        article = self.get_article(actor, article_id)
        attachment = self._repository.get_attachment(attachment_id)
        if attachment is None or attachment.article_id != article.article_id:
            raise KnowledgeNotFoundError("Adjunto no encontrado.")
        # Admin puede eliminar siempre. No-admin solo puede eliminar su propio adjunto mientras el artículo sea draft.
        is_admin = "admin" in actor.role_keys
        is_own_attachment = attachment.created_by_user_id == actor.crm_user.crm_user_id
        article_is_draft = article.status == "draft"
        if not is_admin and not (is_own_attachment and article_is_draft):
            raise KnowledgeAccessDeniedError(
                "Solo el administrador puede eliminar adjuntos de artículos publicados."
            )
        stored_media = StoredTaskMedia(
            file_name=attachment.stored_filename,
            file_url=attachment.file_url,
            storage_path=attachment.storage_path,
            mime_type=attachment.mime_type,
            file_size_bytes=attachment.size_bytes or 0,
            attachment_type="PHOTO" if attachment.file_type == "image" else "VIDEO",
        )
        self._media_storage.delete(stored_media)
        self._repository.delete_attachment(attachment)

    def list_categories(self) -> list[KnowledgeCategory]:
        return self._repository.list_categories()

    def _generate_slug(self, title: str, exclude_id: str | None = None) -> str:
        """Genera un slug único. Si hay colisión, agrega sufijo -2, -3, etc."""
        import re, unicodedata
        normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
        base_slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:240] or "sin-titulo"
        candidate = base_slug
        counter = 2
        while self._repository.slug_exists(candidate, exclude_id=exclude_id):
            candidate = f"{base_slug}-{counter}"
            counter += 1
        return candidate
```

### E7. `api/endpoints/knowledge_base.py` — Endpoints

```python
router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])

GET  /knowledge-base/categories
     → list[KnowledgeCategoryResponse]

GET  /knowledge-base/articles?search=&category_id=&status=
     → list[KnowledgeArticleListItem]
     → Requiere: authGuard (todos los roles)

GET  /knowledge-base/articles/{article_id}
     → KnowledgeArticleDetail
     → Requiere: authGuard

POST /knowledge-base/articles
     → body: CreateKnowledgeArticleRequest
     → 201: KnowledgeArticleDetail
     → Requiere: authGuard (todos los roles)

PUT  /knowledge-base/articles/{article_id}
     → body: UpdateKnowledgeArticleRequest
     → 200: KnowledgeArticleDetail
     → Requiere: authGuard (todos los roles)

DELETE /knowledge-base/articles/{article_id}
     → 204
     → Requiere: authGuard; servicio verifica role_key "admin"

POST /knowledge-base/articles/{article_id}/attachments
     → body: multipart/form-data, field: file
     → 201: KnowledgeAttachmentResponse
     → Requiere: authGuard

DELETE /knowledge-base/articles/{article_id}/attachments/{attachment_id}
     → 204
     → Requiere: authGuard
```

> No hay endpoint de export-pdf: se genera en el frontend (ver sección G.6).

### E8. Archivos Backend Modificados

| Archivo | Cambio |
|---|---|
| `core/config.py` | +4 líneas (knowledge media paths) |
| `main.py` | +2 dirs en lista `media_dirs` del lifespan |
| `api/dependencies.py` | +3 factories: `get_knowledge_repository`, `get_knowledge_media_storage`, `get_knowledge_application_service` |
| `api/router.py` | +2 líneas: import + `include_router` |

---

## F. Migración de Base de Datos

Crear: **`microtv-crm-backend/sql/20260522_knowledge_base.sql`**

Patrón idéntico a `sql/20260520_crm_categories.sql` — raw SQL, ejecutable con `psql`.

Contenido: tablas `knowledge_categories`, `knowledge_articles`, `knowledge_article_versions`, `knowledge_article_attachments` + índices + seeds opcionales.

> **No se usa Alembic** — el CRM backend usa migraciones SQL planas en `sql/`. Ver `sql/migrate_prod.sh` para el proceso de aplicación.

---

## G. Cambios en Frontend

### G1. Librerías npm a agregar

```bash
npm install ngx-markdown dompurify @types/dompurify
```

| Librería | Uso | Ya instalada |
|---|---|---|
| `ngx-markdown` | Render Markdown → HTML en Angular | ❌ Agregar |
| `dompurify` | Sanitización de HTML renderizado | ❌ Agregar |
| `@types/dompurify` | Tipos TypeScript | ❌ Agregar |
| `html2canvas` | PDF export: captura del DOM | ✅ Ya instalada |
| `jspdf` | PDF export: generación del PDF | ✅ Ya instalada |

> **No se agrega ningún editor WYSIWYG** (TipTap, Quill, ProseMirror). El "Modo escritura" es un textarea + toolbar custom que inserta sintaxis Markdown, idéntico al editor de GitLab issues.

### G2. `src/app/core/models/knowledge.model.ts`

```typescript
export interface KnowledgeCategory {
  article_category_id: string;
  name: string;
  slug: string;
  description: string | null;
}

export interface KnowledgeArticleListItem {
  article_id: string;
  title: string;
  slug: string;
  category: KnowledgeCategory | null;
  status: 'draft' | 'published';
  excerpt: string | null;
  created_by_display_name: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeAttachment {
  attachment_id: string;
  file_type: 'image' | 'video';
  mime_type: string;
  original_filename: string;
  file_url: string;
  size_bytes: number | null;
  created_at: string;
}

export interface KnowledgeArticleDetail extends KnowledgeArticleListItem {
  content_md: string;
  attachments: KnowledgeAttachment[];
}

export interface CreateKnowledgeArticlePayload {
  title: string;
  category_id?: string | null;
  content_md: string;
  status: 'draft' | 'published';
  is_auto_draft?: boolean;
}

export interface UpdateKnowledgeArticlePayload {
  title?: string;
  category_id?: string | null;
  content_md?: string;
  status?: 'draft' | 'published';
}
```

### G3. `src/app/core/services/knowledge-base.service.ts`

Patrón idéntico a `TaskManagementService`:

```typescript
@Injectable({ providedIn: 'root' })
export class KnowledgeBaseService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);

  listArticles(params?: { search?: string; category_id?: string }): Observable<KnowledgeArticleListItem[]> {
    return this.request<KnowledgeArticleListItem[]>('get', '/knowledge-base/articles', undefined, params);
  }

  getArticle(id: string): Observable<KnowledgeArticleDetail> {
    return this.request<KnowledgeArticleDetail>('get', `/knowledge-base/articles/${id}`);
  }

  createArticle(payload: CreateKnowledgeArticlePayload): Observable<KnowledgeArticleDetail> {
    return this.request<KnowledgeArticleDetail>('post', '/knowledge-base/articles', payload);
  }

  updateArticle(id: string, payload: UpdateKnowledgeArticlePayload): Observable<KnowledgeArticleDetail> {
    return this.request<KnowledgeArticleDetail>('put', `/knowledge-base/articles/${id}`, payload);
  }

  deleteArticle(id: string): Observable<void> {
    return this.request<void>('delete', `/knowledge-base/articles/${id}`);
  }

  listCategories(): Observable<KnowledgeCategory[]> {
    return this.request<KnowledgeCategory[]>('get', '/knowledge-base/categories');
  }

  uploadAttachment(articleId: string, file: File): Observable<KnowledgeAttachment> {
    const headers = this.buildAuthHeaders();
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<KnowledgeAttachment>(
      `${crmApiConfig.baseUrl}/knowledge-base/articles/${articleId}/attachments`,
      formData, { headers }
    );
  }

  deleteAttachment(articleId: string, attachmentId: string): Observable<void> {
    return this.request<void>('delete', `/knowledge-base/articles/${articleId}/attachments/${attachmentId}`);
  }

  private request<T>(method: 'get' | 'post' | 'put' | 'patch' | 'delete', path: string, body?: unknown, params?: Record<string, string | undefined>): Observable<T> { ... }
  private buildAuthHeaders(): HttpHeaders { ... }
}
```

### G4. `src/app/features/knowledge-base/components/knowledge-base-page/`

Página de listado:

```typescript
// knowledge-base-page.component.ts
@Component({
  selector: 'app-knowledge-base-page',
  standalone: true,
  imports: [
    MatCardModule, MatButtonModule, MatIconModule, MatFormFieldModule,
    MatInputModule, MatSelectModule, MatProgressSpinnerModule, RouterModule,
    MatChipsModule, MatTooltipModule,
  ],
})
export class KnowledgeBasePageComponent {
  // Signals
  articles = signal<KnowledgeArticleListItem[]>([]);
  categories = signal<KnowledgeCategory[]>([]);
  loading = signal(true);
  searchQuery = signal('');
  selectedCategory = signal<string | null>(null);

  // Derived
  isAdmin = computed(() => this.session.sessionSnapshot()?.user.role_keys.includes('admin') ?? false);

  onDeleteArticle(article: KnowledgeArticleListItem): void {
    // MatDialog de confirmación con mensaje "¿Seguro que querés eliminar este artículo?"
    // + nota "Solo los administradores pueden eliminar artículos"
  }
}
```

**Template — textos en español:**
- Título de página: "Base de conocimientos"
- Botón crear: "Crear artículo"
- Buscador placeholder: "Buscar por título, categoría o contenido"
- Filtro de categoría: "Todas las categorías"
- Estado vacío: "Todavía no hay artículos cargados"
- Acciones: "Ver", "Editar", "Eliminar" (solo admin)
- Nota en delete: "Solo los administradores pueden eliminar artículos"

### G5. `src/app/features/knowledge-base/components/knowledge-article-detail/`

Vista de detalle con render Markdown y PDF export:

**Template:**
```html
<article id="kb-export-header">
  <h1>{{ article().title }}</h1>
  <div class="meta">
    <span>{{ article().category?.name }}</span>
    <span>{{ article().created_by_display_name }}</span>
    <span>Última actualización: {{ article().updated_at | date:'dd/MM/yyyy' }}</span>
  </div>
</article>

<section id="kb-export-content">
  <markdown [data]="article().content_md" [sanitize]="true"></markdown>
</section>

@if (videoAttachments().length > 0) {
  <section id="kb-export-videos">
    <h2>Videos asociados</h2>
    @for (video of videoAttachments(); track video.attachment_id) {
      <div class="video-item">
        <video controls [src]="video.file_url"></video>
        <p>{{ video.original_filename }}</p>
      </div>
    }
  </section>
}

<div class="actions">
  <button mat-stroked-button (click)="exportPdf()" [disabled]="exportingPdf()">
    <mat-icon>picture_as_pdf</mat-icon>
    @if (!exportingPdf()) { Exportar PDF } @else { Generando... }
  </button>
  <button mat-stroked-button [routerLink]="['/knowledge-base', article().article_id, 'edit']">
    <mat-icon>edit</mat-icon> Editar
  </button>
  @if (isAdmin()) {
    <button mat-stroked-button color="warn" (click)="onDelete()">
      <mat-icon>delete</mat-icon> Eliminar
    </button>
  }
</div>
```

**PDF export** — mismo patrón que `report-detail.component.ts`:

> **⚠️ Limitación MVP — paginación:** `appendCanvasToPdf()` se reutiliza de `report-detail.component.ts`. html2canvas captura cada sección como imagen única; si `#kb-export-content` supera la altura de una página A4, el contenido será recortado. Artículos muy largos pueden quedar incompletos en el PDF. Recomendación: dividir artículos extensos en secciones más cortas. Paginación real queda como deuda técnica (FT8).

```typescript
async exportPdf(): Promise<void> {
  this.exportingPdf.set(true);
  try {
    const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
      import('html2canvas'),
      import('jspdf'),
    ]);
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
    const sections = ['kb-export-header', 'kb-export-content', 'kb-export-videos']
      .map(id => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);

    let isFirstPage = true;
    for (const section of sections) {
      const canvas = await html2canvas(section, { backgroundColor: '#ffffff', scale: 2, useCORS: true });
      isFirstPage = this.appendCanvasToPdf(pdf, canvas, isFirstPage);
    }
    pdf.save(`base-conocimientos-${this.article().slug}.pdf`);
  } finally {
    this.exportingPdf.set(false);
  }
}
```

### G6. `src/app/features/knowledge-base/components/knowledge-markdown-editor/`

Editor Markdown reutilizable (componente puro, sin dependencias de API):

```typescript
@Component({
  selector: 'app-knowledge-markdown-editor',
  standalone: true,
  imports: [MatTabsModule, MatButtonModule, MatIconModule, MatTooltipModule, FormsModule, MarkdownModule],
})
export class KnowledgeMarkdownEditorComponent {
  @Input() content = '';
  @Output() contentChange = new EventEmitter<string>();
  @Input() articleId: string | null = null;  // Para uploads (null en draft nuevo)
  @Output() attachmentUploaded = new EventEmitter<KnowledgeAttachment>();

  // Dos tabs: "Modo escritura" y "Vista previa"
  // Toolbar visible solo en "Modo escritura"
}
```

**Toolbar — inserta sintaxis Markdown en posición del cursor:**

| Botón | Símbolo insertado |
|---|---|
| Título | `# ` al inicio de línea |
| Subtítulo | `## ` al inicio de línea |
| Negrita | `**texto**` |
| Cursiva | `*texto*` |
| Lista con viñetas | `- ` al inicio de línea |
| Lista numerada | `1. ` al inicio de línea |
| Enlace | `[texto](url)` |
| Código en línea | `` `código` `` |
| Bloque de código | ` ```\ncódigo\n``` ` |
| Cita | `> ` al inicio de línea |
| Insertar imagen | dispara input `type="file"` → upload → `![imagen](url)` |

**Paste de imagen:**
```typescript
@HostListener('paste', ['$event'])
onPaste(event: ClipboardEvent): void {
  const items = Array.from(event.clipboardData?.items ?? []);
  const imageItem = items.find(item => item.type.startsWith('image/'));
  if (imageItem) {
    event.preventDefault();
    const file = imageItem.getAsFile();
    if (file) this.uploadAndInsertImage(file);
  }
}
```

**Configuración de seguridad para `ngx-markdown` (requerida — configurar en `app.config.ts`):**
```typescript
provideMarkdown({
  markedOptions: {
    provide: MARKED_OPTIONS,
    useValue: {
      gfm: true,
      breaks: true,
      pedantic: false,
      // ⚠️ No pasar renderer.html → HTML crudo en Markdown queda deshabilitado
    } satisfies MarkedOptions,
  },
  sanitize: true,  // DomSanitizer de Angular como primera capa
})
// DOMPurify como segunda capa (configurar al bootstrap):
DOMPurify.setConfig({
  FORBID_TAGS: ['script', 'iframe', 'style', 'object', 'embed', 'svg', 'form', 'input'],
  FORBID_ATTR: ['onerror', 'onclick', 'onload', 'onmouseover', 'onmouseout', 'style', 'srcdoc'],
});
```

**Tabs:**
- Tab 1 — "Modo escritura": `<textarea>` + toolbar (visible)
- Tab 2 — "Cargar Markdown": `<textarea>` limpio (solo pegado)
- Tab 3 — "Vista previa": `<markdown [sanitize]="true" [data]="content">` con la config de seguridad aplicada

### G7. `src/app/features/knowledge-base/components/knowledge-article-editor/`

Formulario de creación/edición:

**Estrategia de draft para uploads en nuevo artículo:**
1. Al abrir el editor en modo "crear": llamar `createArticle({ title: '', status: 'draft', is_auto_draft: true })` inmediatamente para obtener un `article_id` real
2. Uploads de imágenes se hacen contra ese `article_id`
3. Al guardar el artículo final: `updateArticle(article_id, { title, content_md, category_id, status: 'published' })`
4. Si el usuario cancela sin guardar: el draft queda en DB con `status='draft'`; se puede agregar un job de limpieza posterior

```typescript
@Component({ ... })
export class KnowledgeArticleEditorComponent {
  isEditMode = computed(() => this.route.snapshot.params['id'] !== undefined);
  articleId = signal<string | null>(null);
  title = signal('');
  contentMd = signal('');
  selectedCategoryId = signal<string | null>(null);
  categories = signal<KnowledgeCategory[]>([]);
  saving = signal(false);

  async ngOnInit(): Promise<void> {
    this.categories.set(await firstValueFrom(this.knowledgeService.listCategories()));
    if (this.isEditMode()) {
      const article = await firstValueFrom(this.knowledgeService.getArticle(this.route.snapshot.params['id']));
      // Poblar campos con data existente
    } else {
      // Crear draft automático — is_auto_draft: true relaja la validación de título en el backend
      const draft = await firstValueFrom(this.knowledgeService.createArticle({ title: '', status: 'draft', content_md: '', is_auto_draft: true }));
      this.articleId.set(draft.article_id);
    }
  }

  async save(): Promise<void> {
    if (!this.title() || this.title().length < 3) return;
    // updateArticle con status: 'published'
    this.router.navigate(['/knowledge-base', this.articleId()]);
  }
}
```

**Template — campos:**
- "Título" (MatInput, requerido)
- "Categoría" (MatSelect con opción "Sin categoría")
- `<app-knowledge-markdown-editor>` para el contenido
- Sección "Archivos adjuntos" para videos y imágenes adicionales (reusa UI de ticket-attachments-section)
- Botones: "Guardar" (primary), "Cancelar" (stroked)

**Validación client-side:**
- Título mínimo 3 caracteres
- Botón "Guardar" deshabilitado mientras hay uploads en curso

### G8. Archivos Frontend Modificados

**`src/mocks/layout-data.json`** — agregar en la sección "CRM":
```json
{ "id": "knowledge-base", "moduleKey": "knowledge-base", "label": "Base de conocimientos", "icon": "menu_book", "route": "/knowledge-base" }
```

**`src/app/core/models/permission.model.ts`** — agregar al tipo `MockModuleKey`:
```typescript
| 'knowledge-base'
```

**`src/app/core/services/mock-access-control.service.ts`** — agregar acceso para todos los roles:
```typescript
'knowledge-base': true  // Todos los roles autenticados pueden acceder
```

**`src/app/app.routes.ts`** — agregar 4 rutas lazy-loaded:
```typescript
{
  path: 'knowledge-base',
  canActivate: [authGuard],
  loadComponent: () => import('./features/knowledge-base/components/knowledge-base-page/knowledge-base-page.component')
    .then(m => m.KnowledgeBasePageComponent),
  data: { title: 'Base de conocimientos' }
},
{
  path: 'knowledge-base/new',
  canActivate: [authGuard],
  loadComponent: () => import('./features/knowledge-base/components/knowledge-article-editor/knowledge-article-editor.component')
    .then(m => m.KnowledgeArticleEditorComponent),
  data: { title: 'Nuevo artículo' }
},
{
  path: 'knowledge-base/:id',
  canActivate: [authGuard],
  loadComponent: () => import('./features/knowledge-base/components/knowledge-article-detail/knowledge-article-detail.component')
    .then(m => m.KnowledgeArticleDetailComponent),
  data: { title: 'Artículo' }
},
{
  path: 'knowledge-base/:id/edit',
  canActivate: [authGuard],
  loadComponent: () => import('./features/knowledge-base/components/knowledge-article-editor/knowledge-article-editor.component')
    .then(m => m.KnowledgeArticleEditorComponent),
  data: { title: 'Editar artículo' }
},
```

---

## H. Contratos de API

### H1. Listado de artículos (autenticado)

```
GET /knowledge-base/articles?search=dvr&category_id=uuid&status=published

→ 200: [
    {
      "article_id": "uuid",
      "title": "Instalación DVR básico",
      "slug": "instalacion-dvr-basico",
      "category": { "article_category_id": "uuid", "name": "Instalaciones DVR", ... },
      "status": "published",
      "excerpt": "Este manual describe los pasos...",
      "created_by_display_name": "Juan Pérez",
      "created_at": "2026-05-22T10:00:00Z",
      "updated_at": "2026-05-22T10:00:00Z"
    }
  ]
```

### H2. Detalle de artículo (autenticado)

```
GET /knowledge-base/articles/{article_id}

→ 200: {
    ...KnowledgeArticleListItem,
    "content_md": "# Instalación DVR básico\n\nPasos a seguir...",
    "attachments": [
      { "attachment_id": "uuid", "file_type": "image", "file_url": "/media/knowledge/images/abc.jpg", ... },
      { "attachment_id": "uuid", "file_type": "video", "file_url": "/media/knowledge/videos/xyz.mp4", ... }
    ]
  }
→ 404: artículo no encontrado o eliminado
```

### H3. Crear artículo (autenticado, todos los roles)

```
POST /knowledge-base/articles
Content-Type: application/json

{ "title": "Instalación DVR básico", "category_id": "uuid", "content_md": "...", "status": "published" }

→ 201: KnowledgeArticleDetail
→ 422: validación fallida
```

### H4. Actualizar artículo (autenticado, todos los roles)

```
PUT /knowledge-base/articles/{article_id}
Content-Type: application/json

{ "title": "...", "content_md": "...", "status": "published" }

→ 200: KnowledgeArticleDetail
→ 404: no encontrado
→ 422: validación fallida
```

### H5. Eliminar artículo (autenticado, SOLO admin)

```
DELETE /knowledge-base/articles/{article_id}

→ 204: eliminado (soft delete, deleted_at = NOW())
→ 403: rol insuficiente
→ 404: no encontrado
```

### H6. Subir adjunto (autenticado, todos los roles)

```
POST /knowledge-base/articles/{article_id}/attachments
Content-Type: multipart/form-data
Body: file (binary)

Validaciones ejecutadas por el backend:
  1. Artículo existe y no está eliminado
  2. MIME type en allowlist (JPEG, PNG, WEBP para imágenes; MP4, WEBM para videos)
  3. Tamaño ≤ knowledge_images_max_bytes o knowledge_videos_max_bytes según tipo
  4. Nombre de archivo guardado siempre como uuid4, nunca el original

→ 201: KnowledgeAttachmentResponse
→ 404: artículo no encontrado
→ 413: archivo demasiado grande
→ 415: tipo no permitido
```

---

## I. Matriz de Permisos

| Acción | admin_crm | ejecutivo | tecnico_campo | encargado_deposito |
|---|---|---|---|---|
| Ver listado de artículos | ✅ | ✅ | ✅ | ✅ |
| Ver detalle de artículo | ✅ | ✅ | ✅ | ✅ |
| Crear artículo | ✅ | ✅ | ✅ | ✅ |
| Editar artículo | ✅ | ✅ | ✅ | ✅ |
| **Eliminar artículo** | ✅ | ❌ | ❌ | ❌ |
| Exportar PDF | ✅ | ✅ | ✅ | ✅ |
| Subir adjunto | ✅ | ✅ | ✅ | ✅ |
| Eliminar adjunto (artículo publicado) | ✅ | ❌ | ❌ | ❌ |
| Eliminar adjunto propio (artículo draft) | ✅ | ✅ | ✅ | ✅ |

**Backend enforces:**
- `delete_article()`: verifica `"admin" not in actor.role_keys` → `KnowledgeAccessDeniedError`. **Nota:** `actor.role_keys` usa el alias corto `"admin"` (NO `"admin_crm"`), consistente con `ticket_service.py` y `ticket_export_service.py`.
- `delete_attachment()`: admin puede eliminar siempre; no-admin solo puede eliminar su propio adjunto mientras el artículo sea draft.

**Frontend:** botón "Eliminar artículo" solo visible si `session.role_keys.includes('admin')`.

---

## J. Seguridad

| Riesgo | Severidad | Mitigación |
|---|---|---|
| XSS via Markdown con HTML embebido | ALTA | HTML crudo **completamente deshabilitado** en config de `marked`. `ngx-markdown` con `[sanitize]="true"` + DOMPurify como segunda capa. Tags bloqueados: `<script>`, `<iframe>`, `<style>`, `<object>`, `<embed>`, `<svg>`, `<form>`. Attrs bloqueados: `onerror`, `onclick`, `onload`, `style`, `srcdoc`. Nunca `bypassSecurityTrustHtml`. |
| MIME spoofing en uploads | ALTA | Allowlist estricto (JPEG/PNG/WEBP/MP4/WEBM); reusa validación de `TaskMediaStorageFacade` |
| Path traversal en nombres de archivo | ALTA | `stored_filename = str(uuid4()) + ext`; `original_filename` solo para display |
| Eliminación por no-admin | ALTA | Enforced en capa de servicio; frontend oculta el botón |
| PDF con scripts | MEDIA | html2canvas captura DOM post-sanitización; scripts no ejecutados en el PDF |
| Attachment cross-article | MEDIA | `delete_attachment()` valida `attachment.article_id == article.article_id` |
| Paths internos de storage expuestos | MEDIA | Retornar solo `file_url` pública `/media/...`, nunca `storage_path` |
| Drafts huérfanos (create sin save) | BAJA | Job de limpieza periódico: **primero** recolectar adjuntos de los drafts → eliminar archivos físicos via `KnowledgeMediaStorageFacade.delete()` → **luego** DELETE en DB. `ON DELETE CASCADE` solo elimina filas de `knowledge_article_attachments`, **no los archivos en disco**. |

---

## K. Fases de Implementación

### Fase 1 — Base de datos
1. Escribir `sql/20260522_knowledge_base.sql` con las 4 tablas + índices + seeds
2. Aplicar migración en dev y staging

### Fase 2 — Backend Foundation *(pasos 3-6 paralelos entre sí)*
3. `config.py` — 4 líneas de config de media
4. `models/knowledge.py` — modelos ORM
5. `schemas/knowledge.py` — schemas Pydantic
6. `infrastructure/knowledge_media_storage.py` — facade de media

### Fase 3 — Backend Logic *(depende de Fase 2)*
7. `repositories/knowledge_repository.py`
8. `services/knowledge_service.py` *(depende de 7)*
9. `api/endpoints/knowledge_base.py` *(depende de 8)*
10. `api/dependencies.py` + `api/router.py` + `main.py` *(depende de 9)*

### Fase 4 — Frontend Foundation *(paralelo con Fase 3)*
11. `npm install ngx-markdown dompurify @types/dompurify`
12. `permission.model.ts` + `mock-access-control.service.ts` + `layout-data.json`
13. `core/models/knowledge.model.ts`
14. `core/services/knowledge-base.service.ts`
15. `app.routes.ts` — 4 rutas

### Fase 5 — Frontend Components *(depende de Fase 4)*
16. `knowledge-markdown-editor/` — componente reutilizable *(no depende de API)*
17. `knowledge-base-page/` — listado de artículos *(paralelo con 16)*
18. `knowledge-article-detail/` + exportPdf() *(depende de 16)*
19. `knowledge-article-editor/` — create/edit form *(depende de 16, 17)*

### Fase 6 — Verificación
20. `npm run build` — sin errores nuevos
21. Test manual backend: POST artículo → 201; DELETE como no-admin → 403
22. Test manual frontend:
    - Sidebar muestra "Base de conocimientos" para todos los roles
    - Pegar Markdown con imágenes en "Cargar Markdown" → preview renderiza correctamente
    - Upload de imagen desde toolbar → referencia Markdown insertada
    - "Exportar PDF" genera `base-conocimientos-{slug}.pdf` con contenido
    - Desde mobile (tecnico): layout responsive
    - Como `tecnico_campo`: botón "Eliminar" no visible; endpoint devuelve 403

---

## L. Checklist QA

### Artículos

- [ ] Listado muestra todos los artículos publicados para todos los roles
- [ ] Buscador filtra por título, categoría y contenido
- [ ] Filtro por categoría funciona
- [ ] Estado vacío "Todavía no hay artículos cargados" visible cuando no hay artículos
- [ ] "Crear artículo" navega al editor para todos los roles
- [ ] "Editar" navega al editor para todos los roles
- [ ] "Eliminar" visible SOLO para admin
- [ ] Confirmación de eliminación muestra "¿Seguro que querés eliminar este artículo?"
- [ ] Eliminado desaparece de la lista (soft delete)

### Editor

- [ ] "Cargar Markdown" acepta paste de Markdown completo
- [ ] "Modo escritura" muestra toolbar con botones de formato
- [ ] Cada botón inserta sintaxis Markdown en la posición del cursor
- [ ] Tab "Vista previa" renderiza el Markdown del textarea
- [ ] Pegar imagen del portapapeles → upload → referencia insertada en el contenido
- [ ] Subir imagen desde toolbar → upload → referencia insertada
- [ ] Guardar artículo nuevo navega al detalle
- [ ] Cancelar no genera artículos publicados vacíos

### Vista de detalle

- [ ] Markdown renderizado como HTML con headings, listas, links, código, quotes
- [ ] Imágenes inline dentro del contenido se muestran correctamente
- [ ] Sección "Videos asociados" visible si hay videos adjuntos
- [ ] Videos reproducibles en el navegador
- [ ] "Exportar PDF" genera PDF con: título, categoría, autor, fecha, contenido, lista de videos
- [ ] Filename del PDF es `base-conocimientos-{slug}.pdf`

### Seguridad

- [ ] `<script>alert(1)</script>` en Markdown → NO ejecutado en render
- [ ] Upload de `.exe`, `.html`, `.svg` rechazado con error claro
- [ ] Upload de imagen válida > 8 MB rechazado con error claro
- [ ] `storage_path` NO incluido en ninguna respuesta de API
- [ ] DELETE como `tecnico_campo` → 403

### Regresión (no debe romperse)

- [ ] Módulo de Pedidos/Tasks sin cambios
- [ ] Módulo de Tickets sin cambios
- [ ] Módulo de Inventario sin cambios
- [ ] Upload de adjuntos en tareas y tickets no afectado
- [ ] Formulario de satisfacción no afectado
- [ ] `npm run build` pasa sin errores preexistentes

---

## M. Casos de Prueba Mínimos

### Backend (pytest)

```python
# 1. Crear artículo exitoso
test_create_knowledge_article_success
# → POST /knowledge-base/articles → 201, article_id retornado

# 2. Listar artículos con filtro de búsqueda
test_list_knowledge_articles_search
# → GET /knowledge-base/articles?search=dvr → solo artículos con "dvr" en título/contenido

# 3. Eliminar artículo como no-admin
test_delete_knowledge_article_forbidden_for_non_admin
# → DELETE /knowledge-base/articles/{id} como tecnico_campo → 403

# 4. Eliminar artículo como admin
test_delete_knowledge_article_success_as_admin
# → DELETE /knowledge-base/articles/{id} con role_key "admin" → 204, deleted_at seteado

# 5. Upload de imagen válida
test_upload_knowledge_article_image_success
# → POST /knowledge-base/articles/{id}/attachments JPEG válido → 201, file_url retornado

# 6. Upload de tipo inválido
test_upload_knowledge_article_invalid_mime
# → POST con .exe → 415

# 7. Upload demasiado grande
test_upload_knowledge_article_oversized
# → POST > 8MB → 413

# 8. Artículo no encontrado
test_get_knowledge_article_not_found
# → GET /knowledge-base/articles/invalid-id → 404

# 9. Artículo soft-deleted no retornado
test_get_knowledge_article_soft_deleted
# → después de DELETE → GET → 404

# 10. slug generado correctamente
test_knowledge_article_slug_generation
# → title "Instalación DVR básico" → slug "instalacion-dvr-basico"
```

### Frontend (manual / Cypress)

```
11. Sidebar muestra "Base de conocimientos" con ícono menu_book
12. Navegar a /knowledge-base: carga listado correctamente
13. Crear artículo con "Cargar Markdown": pegar markdown y guardar → renderiza en detalle
14. Crear artículo con "Modo escritura": usar botón negrita → inserta **texto**
15. Campo vacío al guardar: muestra validación (título requerido)
16. Como admin: botón "Eliminar" visible y funcional
17. Como tecnico_campo: botón "Eliminar" NO visible
18. "Exportar PDF": descarga .pdf con el contenido del artículo
```

---

## N. Archivos a Crear / Modificar (Resumen)

### Backend — Nuevos archivos

| Archivo | Descripción |
|---|---|
| `sql/20260522_knowledge_base.sql` | Migración SQL: 4 tablas + índices + seeds |
| `src/crm_backend/models/knowledge.py` | Modelos ORM: KnowledgeCategory, KnowledgeArticle, KnowledgeArticleVersion, KnowledgeArticleAttachment |
| `src/crm_backend/schemas/knowledge.py` | Schemas Pydantic v2 request/response |
| `src/crm_backend/repositories/knowledge_repository.py` | KnowledgeRepository |
| `src/crm_backend/infrastructure/knowledge_media_storage.py` | KnowledgeMediaStorageFacade + strategies |
| `src/crm_backend/services/knowledge_service.py` | KnowledgeApplicationService |
| `src/crm_backend/api/endpoints/knowledge_base.py` | Router con 8 endpoints |

### Backend — Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/crm_backend/core/config.py` | +4 líneas: knowledge_images_max_bytes, knowledge_videos_max_bytes, knowledge_images_dir, knowledge_videos_dir |
| `src/crm_backend/main.py` | +2 dirs en lista `media_dirs` |
| `src/crm_backend/api/dependencies.py` | +3 factories de DI |
| `src/crm_backend/api/router.py` | +2 líneas: import + include_router |

### Frontend — Nuevos archivos

| Archivo | Descripción |
|---|---|
| `src/app/core/models/knowledge.model.ts` | Interfaces TypeScript |
| `src/app/core/services/knowledge-base.service.ts` | KnowledgeBaseService |
| `src/app/features/knowledge-base/components/knowledge-base-page/` | Listado de artículos |
| `src/app/features/knowledge-base/components/knowledge-article-detail/` | Vista de detalle + PDF export |
| `src/app/features/knowledge-base/components/knowledge-article-editor/` | Formulario create/edit |
| `src/app/features/knowledge-base/components/knowledge-markdown-editor/` | Editor Markdown reutilizable |

### Frontend — Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/app/app.routes.ts` | +4 rutas lazy-loaded |
| `src/mocks/layout-data.json` | +1 item en sección "CRM" |
| `src/app/core/models/permission.model.ts` | +1 entry: `'knowledge-base'` |
| `src/app/core/services/mock-access-control.service.ts` | +1 regla de acceso |
| `package.json` | +3 paquetes: ngx-markdown, dompurify, @types/dompurify |

---

## O. Decisiones de Diseño Confirmadas

### ✅ DC-1 — PDF: frontend (html2canvas + jspdf), no backend

**Resolución:** La exportación PDF se genera en el frontend usando las librerías ya instaladas (`html2canvas` + `jspdf`), siguiendo exactamente el patrón del módulo de Reportes.

**Justificación:**
- Las librerías ya están instaladas; no agrega dependencias nuevas al backend
- El frontend ya renderiza el Markdown como HTML sanitizado → html2canvas captura exactamente lo que el usuario ve
- Patrón consistente con el módulo de Reportes existente
- No requiere Markdown→PDF conversion en el servidor

**Impacto:** El endpoint `GET /knowledge-base/articles/{id}/export-pdf` NO existe. La acción "Exportar PDF" vive enteramente en `KnowledgeArticleDetailComponent`.

**Limitación MVP — paginación:** `appendCanvasToPdf()` se reutiliza de `report-detail.component.ts`. Si el contenido del artículo supera la altura de una página A4, será recortado. Documentado como limitación aceptable (ver FT8 en deuda técnica).

---

### ✅ DC-2 — Editor Markdown: textarea + toolbar custom, sin WYSIWYG

**Resolución:** El editor usa un `<textarea>` como base en ambos modos. El "Modo escritura" agrega una barra de herramientas que inserta sintaxis Markdown en el cursor. No se agrega ningún editor WYSIWYG (TipTap, Quill, ProseMirror, etc.).

**Justificación:**
- Compatible con Angular Material existente sin conflictos de estilos
- Sin librerías pesadas con su propio DOM shadow y patrones de estado
- El contenido se almacena siempre como Markdown puro — nunca HTML
- El patrón es idéntico al editor de GitLab issues / GitHub issues

---

### ✅ DC-3 — Draft al crear: crear artículo inmediatamente, actualizar al guardar

**Resolución:** Al abrir el editor en modo "crear", se llama `POST /knowledge-base/articles` de inmediato con `{ status: 'draft', is_auto_draft: true }` para obtener un `article_id` real. El flag `is_auto_draft: true` relaja la validación de título en el backend (permite título vacío solo para este caso). Uploads de imágenes durante la creación se hacen contra ese ID. Al guardar, se llama `PUT` con el contenido final y `status='published'` (el backend exige título ≥ 3 caracteres al publicar).

**Justificación:**
- Permite uploads de imágenes inline durante la creación sin endpoint temporal
- No requiere lógica de "provisional_id" ni bind posterior
- El flag `is_auto_draft` distingue drafts intencionales de drafts huérfanos con seguridad

**Regla de limpieza:** El job **no puede usar solo SQL**. Antes de eliminar las filas debe:
1. `SELECT * FROM knowledge_article_attachments a JOIN knowledge_articles art ON a.article_id = art.article_id WHERE art.status='draft' AND art.is_auto_draft=TRUE AND art.created_at < NOW() - INTERVAL '24h'`
2. Por cada adjunto: llamar `KnowledgeMediaStorageFacade.delete(stored_media)` para eliminar el archivo físico del disco.
3. Luego: `DELETE FROM knowledge_articles WHERE status='draft' AND is_auto_draft=TRUE AND created_at < NOW() - INTERVAL '24h'` (el `ON DELETE CASCADE` elimina las filas de adjuntos en DB, pero **no los archivos en disco**).

---

### ✅ DC-4 — Soft delete: solo admin, mediante `deleted_at`

**Resolución:** Los artículos eliminados tienen `deleted_at = NOW()`. El listado y el detalle siempre filtran `WHERE deleted_at IS NULL`. La eliminación es irreversible desde la UI (no hay "restaurar" en MVP).

---

### ✅ DC-5 — Sanitización: ngx-markdown [sanitize]="true" + DOMPurify

**Resolución:** HTML crudo en Markdown está **completamente deshabilitado** via configuración de `marked` (no se registra renderer HTML personalizado). `ngx-markdown` con `[sanitize]="true"` actúa como primera capa. DOMPurify con lista explícita de tags/attrs prohibidos actúa como segunda capa antes de cualquier `innerHTML` directo. Está prohibido usar `bypassSecurityTrustHtml` en este módulo. Tags prohibidos: `<script>`, `<iframe>`, `<style>`, `<object>`, `<embed>`, `<svg>`, `<form>`. Attrs prohibidos: `onerror`, `onclick`, `onload`, `onmouseover`, `style`, `srcdoc`.

---

### ✅ DC-6 — Categorías: seeds fijos, solo lectura desde la UI

**Resolución:** Las categorías son creadas por seeds en la migración SQL y son **read-only desde la UI** en MVP. No se construye CRUD de categorías.

**Justificación:**
- Las 5 categorías semilla cubren todos los casos de uso del MVP
- CRUD de categorías introduce pantallas y permisos adicionales que no aportan valor inmediato
- El endpoint `GET /knowledge-base/categories` solo lista; no hay `POST`, `PUT` ni `DELETE` de categorías

**Expansión futura:** CRUD de categorías se agrega como feature separada si se solicita explícitamente.

---

## P. Deuda Técnica y Mejoras Futuras

| # | Mejora | Prioridad |
|---|---|---|
| FT1 | Vista de diff de versiones: UI para comparar versiones (snapshots en `knowledge_article_versions` ya implementados en MVP) | Media |
| FT2 | Tags/etiquetas en artículos para filtrado granular | Baja |
| FT3 | Endpoint de limpieza de drafts huérfanos como background task: recolectar adjuntos → `KnowledgeMediaStorageFacade.delete()` por cada archivo físico → DELETE en DB. `ON DELETE CASCADE` no borra archivos en disco. | Media |
| FT4 | Signed URLs para acceso a media de conocimiento (si los artículos contienen información sensible) | Baja |
| FT5 | Endpoint de búsqueda con full-text search PostgreSQL (`tsvector`) para mejor relevancia | Media |
| FT6 | Rate limiting en POST de adjuntos (actualmente solo autenticación como barrera) | Media |
| FT7 | Estadísticas de uso: views por artículo, búsquedas más frecuentes | Baja |
| FT8 | Paginación real en PDF export: recortar contenido por altura de página A4 en lugar de escalar | Baja |

---

*Fin del documento de planning.*
