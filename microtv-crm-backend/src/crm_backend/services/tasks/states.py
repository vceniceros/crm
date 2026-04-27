"""State objects for subtask lifecycle transitions."""

from __future__ import annotations

from dataclasses import dataclass

from crm_backend.core.exceptions import TaskConflictError
from crm_backend.models.task_execution import SubtaskStatus, TransitionAction


@dataclass(slots=True)
class SubtaskState:
    status: str
    allowed_actions: set[str]

    def ensure_action_allowed(self, action: str) -> None:
        if action not in self.allowed_actions:
            raise TaskConflictError(
                f"La acción '{action}' no está permitida para una subtarea en estado '{self.status}'."
            )


STATE_MAP: dict[str, SubtaskState] = {
    SubtaskStatus.LOCKED.value: SubtaskState(SubtaskStatus.LOCKED.value, set()),
    SubtaskStatus.PENDING_ASSIGNMENT.value: SubtaskState(
        SubtaskStatus.PENDING_ASSIGNMENT.value,
        {TransitionAction.CLAIM_SUBTASK.value},
    ),
    SubtaskStatus.ASSIGNED.value: SubtaskState(
        SubtaskStatus.ASSIGNED.value,
        {
            TransitionAction.START_SUBTASK.value,
            TransitionAction.CLOSE_SUBTASK.value,
            TransitionAction.REJECT_SUBTASK.value,
            TransitionAction.PUT_ON_HOLD.value,
            "update_items",
        },
    ),
    SubtaskStatus.IN_PROGRESS.value: SubtaskState(
        SubtaskStatus.IN_PROGRESS.value,
        {
            TransitionAction.CLOSE_SUBTASK.value,
            TransitionAction.REJECT_SUBTASK.value,
            TransitionAction.PUT_ON_HOLD.value,
            "update_items",
        },
    ),
    SubtaskStatus.COMPLETED.value: SubtaskState(SubtaskStatus.COMPLETED.value, set()),
    SubtaskStatus.REJECTED.value: SubtaskState(SubtaskStatus.REJECTED.value, set()),
    SubtaskStatus.ON_HOLD.value: SubtaskState(SubtaskStatus.ON_HOLD.value, set()),
}


def get_subtask_state(status: str) -> SubtaskState:
    state = STATE_MAP.get(status)
    if state is None:
        raise TaskConflictError(f"Estado de subtarea no soportado: '{status}'.")
    return state