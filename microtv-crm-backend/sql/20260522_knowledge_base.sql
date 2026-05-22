CREATE TABLE IF NOT EXISTS knowledge_categories (
    article_category_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 VARCHAR(100) NOT NULL,
    slug                 VARCHAR(100) NOT NULL UNIQUE,
    description          TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_articles (
    article_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    title                VARCHAR(255) NOT NULL,
    slug                 VARCHAR(255) NOT NULL UNIQUE,
    category_id          UUID         REFERENCES knowledge_categories(article_category_id) ON DELETE SET NULL,
    content_md           TEXT         NOT NULL DEFAULT '',
    status               VARCHAR(20)  NOT NULL DEFAULT 'published' CHECK (status IN ('draft', 'published')),
    created_by_user_id   UUID         NOT NULL REFERENCES crm_users(crm_user_id) ON DELETE RESTRICT,
    updated_by_user_id   UUID         REFERENCES crm_users(crm_user_id) ON DELETE SET NULL,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted_at           TIMESTAMPTZ  NULL,
    is_auto_draft        BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS knowledge_article_versions (
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

CREATE TABLE IF NOT EXISTS knowledge_article_attachments (
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

CREATE INDEX IF NOT EXISTS ix_knowledge_articles_title ON knowledge_articles(title);
CREATE INDEX IF NOT EXISTS ix_knowledge_articles_slug ON knowledge_articles(slug);
CREATE INDEX IF NOT EXISTS ix_knowledge_articles_category_id ON knowledge_articles(category_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_articles_status ON knowledge_articles(status);
CREATE INDEX IF NOT EXISTS ix_knowledge_articles_deleted_at ON knowledge_articles(deleted_at);
CREATE INDEX IF NOT EXISTS ix_knowledge_article_attachments_article_id ON knowledge_article_attachments(article_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_article_attachments_file_type ON knowledge_article_attachments(file_type);
CREATE INDEX IF NOT EXISTS ix_knowledge_article_versions_article_id ON knowledge_article_versions(article_id);

INSERT INTO knowledge_categories (name, slug, description) VALUES
  ('Instalaciones DVR', 'instalaciones-dvr', 'Guias paso a paso de instalacion de equipos DVR'),
  ('Cableado y red', 'cableado-y-red', 'Procedimientos de cableado estructurado y networking'),
  ('Mantenimiento preventivo', 'mantenimiento-preventivo', 'Rutinas de mantenimiento periodico'),
  ('Resolucion de problemas', 'resolucion-de-problemas', 'Guias de diagnostico y solucion de fallas'),
  ('Procedimientos internos', 'procedimientos-internos', 'Normas y procesos administrativos del equipo')
ON CONFLICT DO NOTHING;
