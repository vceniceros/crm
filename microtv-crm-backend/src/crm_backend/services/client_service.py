"""Application service for real CRM client management."""

from __future__ import annotations

from dataclasses import dataclass

from crm_backend.core.exceptions import ClientAccessDeniedError, ClientNotFoundError, DuplicateClientTaxIdError
from crm_backend.models import Client, Location
from crm_backend.repositories import ClientRepository
from crm_backend.repositories.client_repository import ClientLocationUpsert
from crm_backend.services.auth_service import ResolvedCrmSession


@dataclass(slots=True)
class ClientLocationCommand:
    """Normalized location payload used by the clients application service."""

    latitude: float
    longitude: float
    address_label: str | None
    formatted_address: str | None


@dataclass(slots=True)
class CreateClientCommand:
    """Input payload required to persist a client."""

    business_name: str
    tax_id: str
    email: str | None
    phone: str | None
    location: ClientLocationCommand | None


@dataclass(slots=True)
class UpdateClientCommand:
    """Input payload required to update a client."""

    business_name: str
    tax_id: str
    email: str | None
    phone: str | None
    is_active: bool
    location: ClientLocationCommand | None


@dataclass(slots=True)
class ClientLocationView:
    """Serializable client location snapshot returned by the API."""

    latitude: float
    longitude: float
    address_label: str | None
    formatted_address: str | None


@dataclass(slots=True)
class ClientView:
    """Serializable client snapshot returned by the API."""

    client_id: str
    business_name: str
    tax_id: str
    email: str | None
    phone: str | None
    is_active: bool
    created_at: object
    location: ClientLocationView | None


class ClientApplicationService:
    """Orchestrates client listing and mutations."""

    def __init__(self, repository: ClientRepository) -> None:
        self._repository = repository

    def list_clients(self, actor: ResolvedCrmSession) -> list[ClientView]:
        self._ensure_read_access(actor)
        return [self._build_client_view(client) for client in self._repository.list_active()]

    def get_client(self, actor: ResolvedCrmSession, client_id: str) -> ClientView:
        self._ensure_read_access(actor)
        client = self._repository.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundError()
        return self._build_client_view(client)

    def create_client(self, actor: ResolvedCrmSession, command: CreateClientCommand) -> ClientView:
        self._ensure_write_access(actor)
        normalized_tax_id = command.tax_id.strip()
        if self._repository.get_active_by_tax_id(normalized_tax_id) is not None:
            raise DuplicateClientTaxIdError()

        client = self._repository.create(
            business_name=command.business_name.strip(),
            tax_id=normalized_tax_id,
            email=command.email.strip() if command.email else None,
            phone=command.phone.strip() if command.phone else None,
            location=self._normalize_location(command.location),
        )
        return self._build_client_view(client)

    def update_client(self, actor: ResolvedCrmSession, client_id: str, command: UpdateClientCommand) -> ClientView:
        self._ensure_write_access(actor)
        client = self._repository.get_active_by_id(client_id)
        if client is None:
            raise ClientNotFoundError()

        normalized_tax_id = command.tax_id.strip()
        if self._repository.get_active_by_tax_id(normalized_tax_id, exclude_client_id=client_id) is not None:
            raise DuplicateClientTaxIdError()

        persisted_client = self._repository.update(
            client,
            business_name=command.business_name.strip(),
            tax_id=normalized_tax_id,
            email=command.email.strip() if command.email else None,
            phone=command.phone.strip() if command.phone else None,
            is_active=command.is_active,
            location=self._normalize_location(command.location),
        )
        return self._build_client_view(persisted_client)

    def delete_client(self, actor: ResolvedCrmSession, client_id: str) -> Client:
        self._ensure_write_access(actor)
        client = self._repository.get_active_by_id(client_id)
        if client is None:
            raise ClientNotFoundError()
        return self._repository.soft_delete(client)

    def _ensure_read_access(self, actor: ResolvedCrmSession) -> None:
        if {"admin", "ejecutivo", "deposito", "tecnico"}.intersection(actor.role_keys):
            return
        raise ClientAccessDeniedError("El usuario no tiene acceso al módulo de clientes.")

    def _ensure_write_access(self, actor: ResolvedCrmSession) -> None:
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return
        raise ClientAccessDeniedError()

    def _build_client_view(self, client: Client) -> ClientView:
        location = self._repository.get_primary_location(client.client_id)
        return ClientView(
            client_id=client.client_id,
            business_name=client.business_name,
            tax_id=client.tax_id,
            email=client.email,
            phone=client.phone,
            is_active=client.is_active,
            created_at=client.created_at,
            location=self._build_location_view(location),
        )

    def _build_location_view(self, location: Location | None) -> ClientLocationView | None:
        if location is None:
            return None
        return ClientLocationView(
            latitude=float(location.latitude),
            longitude=float(location.longitude),
            address_label=location.address_label,
            formatted_address=location.formatted_address,
        )

    def _normalize_location(self, location: ClientLocationCommand | None) -> ClientLocationUpsert | None:
        if location is None:
            return None

        normalized_address = location.address_label.strip() if location.address_label else None
        normalized_formatted = location.formatted_address.strip() if location.formatted_address else normalized_address
        return ClientLocationUpsert(
            latitude=location.latitude,
            longitude=location.longitude,
            address_label=normalized_address,
            formatted_address=normalized_formatted,
        )