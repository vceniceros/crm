-- v4.1 hardening migration for CRM task module.
-- Preconditions:
--   1. schema-propuesto-v4.sql is the base contract.
--   2. 20260414_task_schema_v4_delta.sql was already applied.
-- Goal:
--   Backfill transitional task-domain columns and then harden the database
--   with checks, NOT NULLs, domain constraints, and cross-table validation.

BEGIN;

-- =====================================================
-- FASE A - PRECHECKS
-- =====================================================

-- 1. Template subtasks that still lack role or assignment policy.
SELECT
    template_subtask_id,
    template_id,
    subtask_title,
    responsible_role_key,
    next_assignment_policy
FROM template_subtasks
WHERE responsible_role_key IS NULL
   OR next_assignment_policy IS NULL;

-- 2. Subtasks with contradictory lifecycle fields.
SELECT
    subtask_id,
    task_id,
    status,
    is_completed,
    completed_at,
    completion_notes,
    responsible_role_key,
    template_subtask_id
FROM subtasks
WHERE status IS NULL
   OR (status = 'completed' AND (is_completed IS DISTINCT FROM TRUE OR completed_at IS NULL))
   OR (status <> 'completed' AND (is_completed IS DISTINCT FROM FALSE OR completed_at IS NOT NULL))
   OR (responsible_role_key IS NULL)
   OR (is_completed = TRUE AND completion_notes IS NULL);

-- 3. Tasks with contradictory finalization fields.
SELECT
    task_id,
    status,
    is_finalized,
    finalized_at,
    finalized_by_crm_user_id
FROM tasks
WHERE (status = 'COMPLETED' AND (is_finalized IS DISTINCT FROM TRUE OR finalized_at IS NULL))
   OR (status <> 'COMPLETED' AND is_finalized IS TRUE)
   OR (is_finalized IS TRUE AND finalized_at IS NULL)
   OR (finalized_at IS NOT NULL AND finalized_by_crm_user_id IS NULL);

-- 4. Checklist items still missing type after the integration delta.
SELECT
    sci.checklist_item_id,
    sci.subtask_id,
    sci.template_checklist_item_id,
    sci.item_type,
    s.template_subtask_id
FROM subtask_checklist_items AS sci
JOIN subtasks AS s ON s.subtask_id = sci.subtask_id
WHERE sci.item_type IS NULL;

-- 5. Invalid textual enum values introduced by the integration delta.
SELECT 'template_subtasks.next_assignment_policy' AS source, template_subtask_id::text AS row_id, next_assignment_policy AS invalid_value
FROM template_subtasks
WHERE next_assignment_policy IS NOT NULL
  AND next_assignment_policy NOT IN ('role_queue_auto', 'default_user_auto', 'manual_required')
UNION ALL
SELECT 'subtasks.status', subtask_id::text, status
FROM subtasks
WHERE status IS NOT NULL
  AND status NOT IN ('locked', 'pending_assignment', 'assigned', 'in_progress', 'completed', 'rejected', 'on_hold')
UNION ALL
SELECT 'subtasks.next_assignment_policy', subtask_id::text, next_assignment_policy
FROM subtasks
WHERE next_assignment_policy IS NOT NULL
  AND next_assignment_policy NOT IN ('role_queue_auto', 'default_user_auto', 'manual_required')
UNION ALL
SELECT 'template_subtask_checklist_items.item_type', template_checklist_item_id::text, item_type
FROM template_subtask_checklist_items
WHERE item_type IS NOT NULL
  AND item_type NOT IN ('checkbox', 'text')
UNION ALL
SELECT 'subtask_checklist_items.item_type', checklist_item_id::text, item_type
FROM subtask_checklist_items
WHERE item_type IS NOT NULL
  AND item_type NOT IN ('checkbox', 'text')
UNION ALL
SELECT 'task_comments.comment_type', task_comment_id::text, comment_type
FROM task_comments
WHERE comment_type IS NOT NULL
  AND comment_type NOT IN ('general', 'transition', 'progress')
UNION ALL
SELECT 'subtask_transitions.action', subtask_transition_id::text, action
FROM subtask_transitions
WHERE action IS NOT NULL
  AND action NOT IN ('claim_subtask', 'start_subtask', 'close_subtask', 'reject_subtask', 'put_on_hold')
UNION ALL
SELECT 'subtask_transitions.from_status', subtask_transition_id::text, from_status
FROM subtask_transitions
WHERE from_status IS NOT NULL
  AND from_status NOT IN ('locked', 'pending_assignment', 'assigned', 'in_progress', 'completed', 'rejected', 'on_hold')
UNION ALL
SELECT 'subtask_transitions.to_status', subtask_transition_id::text, to_status
FROM subtask_transitions
WHERE to_status IS NOT NULL
  AND to_status NOT IN ('locked', 'pending_assignment', 'assigned', 'in_progress', 'completed', 'rejected', 'on_hold');

-- 6. Potentially invalid checkbox/text value combinations.
SELECT
    sci.checklist_item_id,
    sci.subtask_id,
    sci.item_type,
    scp.is_checked,
    scp.text_value
FROM subtask_checklist_items AS sci
JOIN subtask_checklist_progress AS scp ON scp.checklist_item_id = sci.checklist_item_id
WHERE (sci.item_type = 'checkbox' AND scp.text_value IS NOT NULL)
   OR (sci.item_type = 'text' AND COALESCE(scp.is_checked, FALSE) = TRUE);

-- =====================================================
-- FASE B - BACKFILL
-- =====================================================

-- 1. Fill template-level role and policy defaults where missing.
UPDATE template_subtasks
SET next_assignment_policy = 'role_queue_auto'
WHERE next_assignment_policy IS NULL;

UPDATE template_subtasks
SET close_comment_required = TRUE
WHERE close_comment_required IS NULL;

-- 2. Propagate template semantics into instantiated subtasks where available.
UPDATE subtasks AS s
SET responsible_role_key = ts.responsible_role_key,
    default_responsible_crm_user_id = COALESCE(s.default_responsible_crm_user_id, ts.default_responsible_crm_user_id),
    close_comment_required = COALESCE(s.close_comment_required, ts.close_comment_required, TRUE),
    next_assignment_policy = COALESCE(s.next_assignment_policy, ts.next_assignment_policy, 'role_queue_auto')
FROM template_subtasks AS ts
WHERE s.template_subtask_id = ts.template_subtask_id
  AND (
      s.responsible_role_key IS NULL
      OR s.default_responsible_crm_user_id IS NULL
      OR s.close_comment_required IS NULL
      OR s.next_assignment_policy IS NULL
  );

UPDATE subtasks
SET close_comment_required = TRUE
WHERE close_comment_required IS NULL;

UPDATE subtasks
SET next_assignment_policy = 'role_queue_auto'
WHERE next_assignment_policy IS NULL;

-- 3. Normalize subtask lifecycle state from existing v4 fields.
UPDATE subtasks
SET status = CASE
    WHEN is_completed = TRUE OR completed_at IS NOT NULL THEN 'completed'
    WHEN current_assigned_crm_user_id IS NOT NULL THEN 'assigned'
    WHEN responsible_role_key IS NOT NULL THEN 'pending_assignment'
    ELSE 'locked'
END
WHERE status IS NULL;

UPDATE subtasks
SET is_completed = TRUE,
    completed_at = COALESCE(completed_at, updated_at, created_at)
WHERE status = 'completed'
  AND (is_completed IS DISTINCT FROM TRUE OR completed_at IS NULL);

UPDATE subtasks
SET completion_notes = COALESCE(completion_notes, 'Completada durante migracion v4.1')
WHERE status = 'completed'
  AND completion_notes IS NULL;

UPDATE subtasks
SET is_completed = FALSE,
    completed_at = NULL
WHERE status <> 'completed'
  AND (is_completed IS DISTINCT FROM FALSE OR completed_at IS NOT NULL);

-- 4. Normalize task lifecycle state from existing v4 fields.
UPDATE tasks
SET is_finalized = TRUE,
    finalized_at = COALESCE(finalized_at, updated_at, created_at)
WHERE status = 'COMPLETED'
  AND (is_finalized IS DISTINCT FROM TRUE OR finalized_at IS NULL);

UPDATE tasks
SET is_finalized = FALSE,
    finalized_at = NULL,
    finalized_by_crm_user_id = NULL
WHERE status <> 'COMPLETED'
  AND (is_finalized IS TRUE OR finalized_at IS NOT NULL OR finalized_by_crm_user_id IS NOT NULL);

-- 5. Backfill instantiated checklist items from template definitions where possible.
UPDATE subtask_checklist_items AS sci
SET template_checklist_item_id = tci.template_checklist_item_id,
    item_type = COALESCE(sci.item_type, tci.item_type)
FROM subtasks AS s
JOIN template_subtask_checklist_items AS tci
    ON tci.template_subtask_id = s.template_subtask_id
WHERE sci.subtask_id = s.subtask_id
    AND tci.item_order = sci.item_order
  AND s.template_subtask_id IS NOT NULL
  AND (
      sci.template_checklist_item_id IS NULL
      OR sci.item_type IS NULL
  );

UPDATE template_subtask_checklist_items
SET item_type = 'checkbox'
WHERE item_type IS NULL;

UPDATE subtask_checklist_items
SET item_type = 'checkbox'
WHERE item_type IS NULL;

-- 6. Normalize task comments and audit payloads.
UPDATE task_comments
SET comment_type = 'transition'
WHERE comment_type IS NULL;

UPDATE task_audit_events
SET payload_json = '{}'::jsonb
WHERE payload_json IS NULL;

-- 7. Normalize text item progress semantics.
UPDATE subtask_checklist_progress AS scp
SET is_checked = FALSE
FROM subtask_checklist_items AS sci
WHERE sci.checklist_item_id = scp.checklist_item_id
  AND sci.item_type = 'text'
  AND scp.is_checked IS DISTINCT FROM FALSE;

UPDATE subtask_checklist_progress AS scp
SET text_value = NULL
FROM subtask_checklist_items AS sci
WHERE sci.checklist_item_id = scp.checklist_item_id
  AND sci.item_type = 'checkbox'
  AND scp.text_value IS NOT NULL;

-- 8. Abort before hardening if backfill could not resolve required fields.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM template_subtasks
        WHERE responsible_role_key IS NULL
    ) THEN
        RAISE EXCEPTION 'v4.1 hardening aborted: template_subtasks still contains NULL responsible_role_key values';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM subtasks
        WHERE responsible_role_key IS NULL
    ) THEN
        RAISE EXCEPTION 'v4.1 hardening aborted: subtasks still contains NULL responsible_role_key values';
    END IF;

    -- template_checklist_item_id is intentionally nullable: instantiated
    -- checklist rows keep their own historical label/order/type snapshots.
END $$;

-- =====================================================
-- FASE C - CONSTRAINTS Y ENDURECIMIENTO
-- =====================================================

-- 1. NOT NULL after successful backfill.
ALTER TABLE template_subtasks
    ALTER COLUMN responsible_role_key SET NOT NULL;

ALTER TABLE subtasks
    ALTER COLUMN responsible_role_key SET NOT NULL;

ALTER TABLE subtask_checklist_items
    ALTER COLUMN template_checklist_item_id DROP NOT NULL;

-- 2. Domain checks for new textual enums.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_template_subtasks_next_assignment_policy'
    ) THEN
        ALTER TABLE template_subtasks
            ADD CONSTRAINT chk_template_subtasks_next_assignment_policy
            CHECK (next_assignment_policy IN ('role_queue_auto', 'default_user_auto', 'manual_required')) NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_subtasks_status_domain'
    ) THEN
        ALTER TABLE subtasks
            ADD CONSTRAINT chk_subtasks_status_domain
            CHECK (status IN ('locked', 'pending_assignment', 'assigned', 'in_progress', 'completed', 'rejected', 'on_hold')) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_subtasks_next_assignment_policy'
    ) THEN
        ALTER TABLE subtasks
            ADD CONSTRAINT chk_subtasks_next_assignment_policy
            CHECK (next_assignment_policy IN ('role_queue_auto', 'default_user_auto', 'manual_required')) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_subtasks_completed_consistency'
    ) THEN
        ALTER TABLE subtasks
            ADD CONSTRAINT chk_subtasks_completed_consistency
            CHECK (
                (status = 'completed' AND is_completed = TRUE AND completed_at IS NOT NULL)
                OR (status <> 'completed' AND is_completed = FALSE AND completed_at IS NULL)
            ) NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_template_subtask_checklist_items_item_type'
    ) THEN
        ALTER TABLE template_subtask_checklist_items
            ADD CONSTRAINT chk_template_subtask_checklist_items_item_type
            CHECK (item_type IN ('checkbox', 'text')) NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_subtask_checklist_items_item_type'
    ) THEN
        ALTER TABLE subtask_checklist_items
            ADD CONSTRAINT chk_subtask_checklist_items_item_type
            CHECK (item_type IN ('checkbox', 'text')) NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_task_comments_comment_type'
    ) THEN
        ALTER TABLE task_comments
            ADD CONSTRAINT chk_task_comments_comment_type
            CHECK (comment_type IN ('general', 'transition', 'progress')) NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_subtask_transitions_action'
    ) THEN
        ALTER TABLE subtask_transitions
            ADD CONSTRAINT chk_subtask_transitions_action
            CHECK (action IN ('claim_subtask', 'start_subtask', 'close_subtask', 'reject_subtask', 'put_on_hold')) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_subtask_transitions_from_status'
    ) THEN
        ALTER TABLE subtask_transitions
            ADD CONSTRAINT chk_subtask_transitions_from_status
            CHECK (from_status IN ('locked', 'pending_assignment', 'assigned', 'in_progress', 'completed', 'rejected', 'on_hold')) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_subtask_transitions_to_status'
    ) THEN
        ALTER TABLE subtask_transitions
            ADD CONSTRAINT chk_subtask_transitions_to_status
            CHECK (to_status IN ('locked', 'pending_assignment', 'assigned', 'in_progress', 'completed', 'rejected', 'on_hold')) NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_tasks_finalization_consistency'
    ) THEN
        ALTER TABLE tasks
            ADD CONSTRAINT chk_tasks_finalization_consistency
            CHECK (
                (status = 'COMPLETED' AND is_finalized = TRUE AND finalized_at IS NOT NULL)
                OR (status <> 'COMPLETED' AND is_finalized = FALSE AND finalized_at IS NULL AND finalized_by_crm_user_id IS NULL)
            ) NOT VALID;
    END IF;
END $$;

-- 3. Remove transitional defaults once data is normalized.
ALTER TABLE template_subtasks
    ALTER COLUMN next_assignment_policy DROP DEFAULT;

ALTER TABLE subtasks
    ALTER COLUMN next_assignment_policy DROP DEFAULT,
    ALTER COLUMN status DROP DEFAULT;

ALTER TABLE subtask_checklist_items
    ALTER COLUMN item_type DROP DEFAULT;

ALTER TABLE task_comments
    ALTER COLUMN comment_type DROP DEFAULT;

-- payload_json keeps its default because audit events are append-only and
-- the backend may legitimately emit empty payloads for low-detail events.

-- 4. Cross-table validation for checkbox/text values.
CREATE OR REPLACE FUNCTION validate_subtask_checklist_progress_consistency()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    resolved_item_type VARCHAR(50);
BEGIN
    SELECT sci.item_type
    INTO resolved_item_type
    FROM subtask_checklist_items AS sci
    WHERE sci.checklist_item_id = NEW.checklist_item_id;

    IF resolved_item_type IS NULL THEN
        RAISE EXCEPTION 'Checklist item % does not exist for progress validation', NEW.checklist_item_id;
    END IF;

    IF resolved_item_type = 'checkbox' AND NEW.text_value IS NOT NULL THEN
        RAISE EXCEPTION 'Checkbox checklist items cannot store text_value';
    END IF;

    IF resolved_item_type = 'text' AND COALESCE(NEW.is_checked, FALSE) = TRUE THEN
        RAISE EXCEPTION 'Text checklist items cannot be marked with is_checked = TRUE';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_subtask_checklist_progress_consistency ON subtask_checklist_progress;

CREATE TRIGGER trg_validate_subtask_checklist_progress_consistency
BEFORE INSERT OR UPDATE ON subtask_checklist_progress
FOR EACH ROW
EXECUTE FUNCTION validate_subtask_checklist_progress_consistency();

-- 5. Validate all NOT VALID constraints after backfill.
ALTER TABLE template_subtasks VALIDATE CONSTRAINT chk_template_subtasks_next_assignment_policy;
ALTER TABLE subtasks VALIDATE CONSTRAINT chk_subtasks_status_domain;
ALTER TABLE subtasks VALIDATE CONSTRAINT chk_subtasks_next_assignment_policy;
ALTER TABLE subtasks VALIDATE CONSTRAINT chk_subtasks_completed_consistency;
ALTER TABLE template_subtask_checklist_items VALIDATE CONSTRAINT chk_template_subtask_checklist_items_item_type;
ALTER TABLE subtask_checklist_items VALIDATE CONSTRAINT chk_subtask_checklist_items_item_type;
ALTER TABLE task_comments VALIDATE CONSTRAINT chk_task_comments_comment_type;
ALTER TABLE subtask_transitions VALIDATE CONSTRAINT chk_subtask_transitions_action;
ALTER TABLE subtask_transitions VALIDATE CONSTRAINT chk_subtask_transitions_from_status;
ALTER TABLE subtask_transitions VALIDATE CONSTRAINT chk_subtask_transitions_to_status;
ALTER TABLE tasks VALIDATE CONSTRAINT chk_tasks_finalization_consistency;

-- =====================================================
-- FASE D - INDICES Y COMENTARIOS
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_subtasks_role_status
    ON subtasks(responsible_role_key, status);

CREATE INDEX IF NOT EXISTS idx_subtask_checklist_items_template_item
    ON subtask_checklist_items(template_checklist_item_id);

CREATE INDEX IF NOT EXISTS idx_subtask_transitions_action
    ON subtask_transitions(action, created_at);

COMMENT ON COLUMN subtasks.status IS
'Estado operativo de la subtarea: locked, pending_assignment, assigned, in_progress, completed, rejected, on_hold.';

COMMENT ON COLUMN subtask_checklist_items.item_type IS
'Tipo semantico del item instanciado: checkbox o text. Debe reflejar el template.';

COMMENT ON COLUMN subtask_checklist_progress.text_value IS
'Valor textual del item cuando item_type = text. Debe ser NULL para checkbox.';

COMMIT;
