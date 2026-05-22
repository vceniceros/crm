-- Fix: knowledge_articles.category_id -> crm_categories instead of knowledge_categories.

-- 1. Drop the old FK to knowledge_categories.
ALTER TABLE knowledge_articles
    DROP CONSTRAINT IF EXISTS knowledge_articles_category_id_fkey;

ALTER TABLE knowledge_articles
    DROP CONSTRAINT IF EXISTS fk_knowledge_articles_crm_category;

-- 2. Clear category_id values that do not exist in crm_categories.
UPDATE knowledge_articles
SET category_id = NULL
WHERE category_id IS NOT NULL
  AND category_id NOT IN (SELECT category_id FROM crm_categories);

-- 3. Add the new FK to crm_categories.
ALTER TABLE knowledge_articles
    ADD CONSTRAINT fk_knowledge_articles_crm_category
    FOREIGN KEY (category_id) REFERENCES crm_categories(category_id) ON DELETE SET NULL;

-- 4. Remove the old standalone knowledge categories table.
DROP TABLE IF EXISTS knowledge_categories;
