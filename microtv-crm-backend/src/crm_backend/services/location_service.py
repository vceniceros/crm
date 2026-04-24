"""Application service for reusable real locations."""

from dataclasses import dataclass

from crm_backend.core.exceptions import ClientAccessDeniedError
from crm_backend.models import Location
from crm_backend.repositories import LocationRepository
from crm_backend.services.auth_service import ResolvedCrmSession


@dataclass(slots=True)
class CreateLocationCommand:
    latitude: float
    longitude: float
    address_label: str | None
    formatted_address: str | None


class LocationApplicationService:
    """Persist reusable locations for clients and tasks."""

    OPERATIONAL_ROLE_KEYS = {"admin", "ejecutivo", "tecnico", "deposito"}

    def __init__(self, repository: LocationRepository) -> None:
        self._repository = repository

    def create_location(self, actor: ResolvedCrmSession, command: CreateLocationCommand) -> Location:
        if not self.OPERATIONAL_ROLE_KEYS.intersection(actor.role_keys):
            raise ClientAccessDeniedError("El usuario no puede crear ubicaciones operativas.")

        normalized_address = command.address_label.strip() if command.address_label else None
        normalized_formatted = command.formatted_address.strip() if command.formatted_address else normalized_address
        return self._repository.create(
            latitude=command.latitude,
            longitude=command.longitude,
            address_label=normalized_address,
            formatted_address=normalized_formatted,
        )
