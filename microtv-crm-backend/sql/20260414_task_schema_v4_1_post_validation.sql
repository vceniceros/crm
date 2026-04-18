-- Post-migration validation script for task schema v4.1 hardening.

-- 1. No contradictory subtask states.
SELECT
    subtask_id,
    task_id,
    status,
    is_completed,
    completed_at,
    completion_notes
FROM subtasks
WHERE (status = 'completed' AND (is_completed IS DISTINCT FROM TRUE OR completed_at IS NULL))
   OR (status <> 'completed' AND (is_completed IS DISTINCT FROM FALSE OR completed_at IS NOT NULL));

-- 2. No contradictory task finalization states.
SELECT
    task_id,
    status,
    is_finalized,
    finalized_at,
    finalized_by_crm_user_id
FROM tasks
WHERE (status = 'COMPLETED' AND (is_finalized IS DISTINCT FROM TRUE OR finalized_at IS NULL))
   OR (status <> 'COMPLETED' AND (is_finalized IS DISTINCT FROM FALSE OR finalized_at IS NOT NULL OR finalized_by_crm_user_id IS NOT NULL));

-- 3. No invalid enum values remain.
SELECT 'template_subtasks.next_assignment_policy' AS source, COUNT(*) AS invalid_rows
FROM template_subtasks
WHERE next_assignment_policy NOT IN ('role_queue_auto', 'default_user_auto', 'manual_required')
UNION ALL
SELECT 'subtasks.status', COUNT(*)
FROM subtasks
WHERE status NOT IN ('locked', 'pending_assignment', 'assigned', 'in_progress', 'completed', 'rejected', 'on_hold')
UNION ALL
SELECT 'subtasks.next_assignment_policy', COUNT(*)
FROM subtasks
WHERE next_assignment_policy NOT IN ('role_queue_auto', 'default_user_auto', 'manual_required')
UNION ALL
SELECT 'template_subtask_checklist_items.item_type', COUNT(*)
FROM template_subtask_checklist_items
WHERE item_type NOT IN ('checkbox', 'text')
UNION ALL
SELECT 'subtask_checklist_items.item_type', COUNT(*)
FROM subtask_checklist_items
WHERE item_type NOT IN ('checkbox', 'text')
UNION ALL
SELECT 'task_comments.comment_type', COUNT(*)
FROM task_comments
WHERE comment_type NOT IN ('general', 'transition', 'progress')
UNION ALL
SELECT 'subtask_transitions.action', COUNT(*)
FROM subtask_transitions
WHERE action NOT IN ('claim_subtask', 'start_subtask', 'close_subtask', 'reject_subtask', 'put_on_hold');

-- 4. No impossible checkbox/text value combinations remain.
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

-- 5. No instantiated subtasks remain without responsible role.
SELECT
    subtask_id,
    task_id,
    template_subtask_id,
    responsible_role_key
FROM subtasks
WHERE responsible_role_key IS NULL;

-- 6. No template subtasks remain without responsible role.
SELECT
    template_subtask_id,
    template_id,
    responsible_role_key
FROM template_subtasks
WHERE responsible_role_key IS NULL;

-- 7. No instantiated checklist items from templated subtasks remain without template linkage.
SELECT
    sci.checklist_item_id,
    sci.subtask_id,
    s.template_subtask_id,
    sci.template_checklist_item_id
FROM subtask_checklist_items AS sci
JOIN subtasks AS s ON s.subtask_id = sci.subtask_id
WHERE s.template_subtask_id IS NOT NULL
  AND sci.template_checklist_item_id IS NULL;