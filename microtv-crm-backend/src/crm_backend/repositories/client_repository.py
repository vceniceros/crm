"""Repository for CRM client persistence operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crm_backend.models.task_reference import Client, ClientLocation, Location


@dataclass(slots=True)
class ClientLocationUpsert:
    """Normalized location payload used by the clients repository."""

    latitude: float
    longitude: float
    address_label: str | None
    formatted_address: str | None


class ClientRepository:
    """Persist and query CRM clients."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active(self) -> list[Client]:
        statement = (
            select(Client)
            .where(Client.deleted_at.is_(None), Client.is_active.is_(True))
            .order_by(Client.business_name.asc())
        )
        return list(self._session.scalars(statement).all())

    def get_active_by_tax_id(self, tax_id: str, *, exclude_client_id: str | None = None) -> Client | None:
        statement = select(Client).where(Client.tax_id == tax_id, Client.deleted_at.is_(None))
        if exclude_client_id is not None:
            statement = statement.where(Client.client_id != exclude_client_id)
        return self._session.scalar(statement)

    def get_by_id(self, client_id: str) -> Client | None:
        statement = select(Client).where(Client.client_id == client_id, Client.deleted_at.is_(None))
        return self._session.scalar(statement)

    def get_active_by_id(self, client_id: str) -> Client | None:
        return self.get_by_id(client_id)

    def create(
        self,
        *,
        business_name: str,
        tax_id: str,
        email: str | None,
        phone: str | None,
        location: ClientLocationUpsert | None,
    ) -> Client:
        client = Client(
            business_name=business_name,
            tax_id=tax_id,
            email=email,
            phone=phone,
            is_active=True,
        )
        self._session.add(client)
        self._session.flush()
        self._replace_primary_location(client.client_id, location)
        self._session.commit()
        self._session.refresh(client)
        return client

    def update(
        self,
        client: Client,
        *,
        business_name: str,
        tax_id: str,
        email: str | None,
        phone: str | None,
        is_active: bool,
        location: ClientLocationUpsert | None,
    ) -> Client:
        client.business_name = business_name
        client.tax_id = tax_id
        client.email = email
        client.phone = phone
        client.is_active = is_active
        client.deleted_at = None if is_active else datetime.now(UTC)

        self._session.add(client)
        self._replace_primary_location(client.client_id, location)
        self._session.commit()
        self._session.refresh(client)
        return client

    def soft_delete(self, client: Client) -> Client:
        client.is_active = False
        client.deleted_at = datetime.now(UTC)
        self._session.add(client)
        self._session.commit()
        self._session.refresh(client)
        return client

    def get_primary_location(self, client_id: str) -> Location | None:
        statement = (
            select(Location)
            .join(ClientLocation, ClientLocation.location_id == Location.location_id)
            .where(ClientLocation.client_id == client_id, ClientLocation.is_primary.is_(True))
            .order_by(ClientLocation.created_at.desc())
        )
        return self._session.scalar(statement)

    def _get_primary_client_location(self, client_id: str) -> ClientLocation | None:
        statement = (
            select(ClientLocation)
            .where(ClientLocation.client_id == client_id, ClientLocation.is_primary.is_(True))
            .order_by(ClientLocation.created_at.desc())
        )
        return self._session.scalar(statement)

    def _replace_primary_location(self, client_id: str, location: ClientLocationUpsert | None) -> None:
        existing_link = self._get_primary_client_location(client_id)

        if location is None:
            if existing_link is not None:
                self._delete_primary_location(existing_link)
            return

        if existing_link is not None:
            persisted_location = self._session.get(Location, existing_link.location_id)
            if persisted_location is None:
                persisted_location = Location()
                self._session.add(persisted_location)
                self._session.flush()
                existing_link.location_id = persisted_location.location_id

            persisted_location.latitude = location.latitude
            persisted_location.longitude = location.longitude
            persisted_location.address_label = location.address_label
            persisted_location.formatted_address = location.formatted_address
            existing_link.location_label = location.address_label
            existing_link.is_primary = True

            self._session.add(persisted_location)
            self._session.add(existing_link)
            return

        persisted_location = Location(
            latitude=location.latitude,
            longitude=location.longitude,
            address_label=location.address_label,
            formatted_address=location.formatted_address,
        )
        self._session.add(persisted_location)
        self._session.flush()
        self._session.add(
            ClientLocation(
                client_id=client_id,
                location_id=persisted_location.location_id,
                location_label=location.address_label,
                is_primary=True,
            )
        )

    def _delete_primary_location(self, client_location: ClientLocation) -> None:
        location_id = client_location.location_id
        self._session.delete(client_location)
        self._session.flush()

        remaining_links = self._session.scalar(
            select(func.count())
            .select_from(ClientLocation)
            .where(ClientLocation.location_id == location_id)
        )
        if remaining_links == 0:
            persisted_location = self._session.get(Location, location_id)
            if persisted_location is not None:
                self._session.delete(persisted_location)