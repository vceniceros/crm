# Prompt para Copilot — Migración de endurecimiento v4.1

Quiero que prepares una **migración de endurecimiento v4.1** para el módulo de tareas del CRM, partiendo de este contexto:

* El contrato base sigue siendo `schema-propuesto-v4.sql`.
* Ya existe un **delta mínimo de integración** aplicado o preparado, que agregó soporte para:

  * `responsible_role_key`
  * `next_assignment_policy`
  * `subtasks.status`
  * `item_type`
  * `text_value`
  * `task_comments`
  * `subtask_transitions`
  * `task_audit_events`
* El backend ya fue corregido para adaptarse al contrato v4 y al delta mínimo.
* **No tocar frontend.**
* **No rediseñar el módulo completo.**
* **No cambiar nombres formales ya consolidados del schema.**
* **No aflojar invariantes existentes.**
* La meta de v4.1 es **endurecer el dominio en base de datos** para evitar estados contradictorios y datos semánticamente inválidos.

## Objetivo de esta migración v4.1

Construir una migración **segura y progresiva** que:

1. haga **backfill** de datos existentes si hace falta,
2. valide que no queden filas incompatibles,
3. recién después agregue `CHECK`, `NOT NULL`, remoción de defaults transicionales e índices/constraints faltantes.

La migración debe estar pensada para evitar dolores posteriores.
No quiero una migración destructiva ni frágil.

---

## Qué quiero que produzcas

Entregá exactamente estos artefactos:

### 1. Diagnóstico corto

Un resumen técnico de:

* qué invariantes del dominio faltan endurecer,
* cuáles son críticos,
* cuáles requieren backfill previo,
* cuáles pueden agregarse directamente.

### 2. SQL de migración v4.1

Un archivo SQL nuevo, por ejemplo:

* `20260414_task_schema_v4_1_hardening.sql`

Debe venir **ordenado por fases**:

#### Fase A — Prechecks

Consultas SQL de diagnóstico para detectar filas incompatibles antes de endurecer.

#### Fase B — Backfill

Updates mínimos para normalizar datos legacy o transicionales.

#### Fase C — Constraints y endurecimiento

Agregar:

* `CHECK`
* `NOT NULL`
* validaciones de dominio
* remoción de defaults transicionales si corresponde

#### Fase D — Índices y comentarios

Índices que falten y comentarios SQL si hacen falta.

### 3. Script de validación post-migración

Consultas SQL para verificar que:

* no quedaron estados cruzados inválidos,
* no quedaron ítems con combinaciones imposibles,
* no quedaron subtareas sin rol si ya deberían tenerlo.

### 4. Impacto en backend

Lista mínima de lugares del backend a revisar después de endurecer:

* modelos ORM
* repositorios
* services
* tests

No reescribas el backend, solo indicar qué validar.

---

## Reglas estrictas

### Regla 1 — Cambios mínimos

No reestructures tablas si se puede endurecer sobre lo que ya existe.

### Regla 2 — Sin renombres

No renombrar tablas ni columnas ya consolidadas.

### Regla 3 — Sin degradar contrato

No volver nullable algo que hoy debe ser obligatorio.

### Regla 4 — Backfill antes de constraint

Si una columna hoy está nullable o con default transicional por compatibilidad:

* primero detectar y completar datos,
* después endurecer.

### Regla 5 — No inventar lógica nueva

La migración debe expresar el dominio ya implementado, no inventar otro.

---

## Invariantes que quiero endurecer sí o sí

### A. Coherencia de `subtasks`

Revisar y endurecer la coherencia entre:

* `subtasks.status`
* `subtasks.is_completed`
* `subtasks.completed_at`
* `subtasks.completion_notes`

Objetivo mínimo esperado:

* si `status = 'completed'` entonces:

  * `is_completed = TRUE`
  * `completed_at IS NOT NULL`
* si `status <> 'completed'` entonces:

  * no debe quedar `is_completed = TRUE`
* revisar si conviene exigir o no `completion_notes` en todos los completados o dejar el check actual
* no permitir combinaciones contradictorias

### B. Coherencia de `tasks`

Revisar y endurecer la coherencia entre:

* `tasks.status`
* `tasks.is_finalized`
* `tasks.finalized_at`
* `tasks.finalized_by_crm_user_id`

Objetivo mínimo esperado:

* si `status = 'COMPLETED'` entonces:

  * `is_finalized = TRUE`
  * `finalized_at IS NOT NULL`
* si `is_finalized = TRUE`, el estado no puede ser otro que `COMPLETED`

### C. Coherencia de items checkbox/text

Revisar y endurecer la coherencia entre:

* `template_subtask_checklist_items.item_type`
* `subtask_checklist_items.item_type`
* `subtask_checklist_progress.is_checked`
* `subtask_checklist_progress.text_value`

Objetivo mínimo esperado:

* `item_type` debe estar validado por dominio
* si el item es `checkbox`, no debe tener `text_value`
* si el item es `text`, no debe depender semánticamente de `is_checked = TRUE`
* si encontrás una mejor forma de expresar esto sin romper el modelo actual, aplicala, pero sin rediseño total

### D. Endurecimiento de campos transicionales

Evaluar cuáles de estos deben pasar a `NOT NULL` luego de backfill:

* `template_subtasks.responsible_role_key`
* `subtasks.responsible_role_key`
* `subtask_checklist_items.template_checklist_item_id`

Y cuáles defaults conviene remover después del backfill:

* `template_subtasks.next_assignment_policy`
* `subtasks.next_assignment_policy`
* `subtasks.status`
* `subtask_checklist_items.item_type`
* `task_comments.comment_type`
* `task_audit_events.payload_json` solo si realmente corresponde

### E. Validaciones de dominio faltantes

Agregar checks si hoy faltan para:

* `next_assignment_policy`
* `task_comments.comment_type`
* `subtask_transitions.action`
* `subtasks.status`
* cualquier enum textual nuevo introducido por el delta mínimo

### F. Integridad útil en transiciones

Revisar si conviene agregar validaciones para:

* `subtask_transitions.from_status`
* `subtask_transitions.to_status`

No quiero una FK a tabla catálogo si complica demasiado.
Un `CHECK` razonable alcanza si mantiene simpleza y claridad.

---

## Qué quiero evitar

No hagas esto:

* no rediseñar subtasks desde cero
* no partir tablas nuevas innecesarias
* no mover la lógica de comments/transitions a otro subsistema
* no tocar tickets, stock, auth ni otros módulos
* no meter sobreingeniería
* no escribir migraciones “mágicas” difíciles de mantener

---

## Estilo esperado de la respuesta

Entregá:

1. diagnóstico breve,
2. migración SQL completa,
3. validación post-migración,
4. checklist de impacto en backend/tests,
5. riesgos si se aplica sin backfill previo.

Quiero una solución pragmática, incremental y apta para producción.
