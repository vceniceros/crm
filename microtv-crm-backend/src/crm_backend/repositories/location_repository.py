"""Repository for reusable locations."""

from crm_backend.models import Location


class LocationRepository:
    """Persist and query standalone task/client locations."""

    def __init__(self, session) -> None:
        self._session = session

    def create(
        self,
        *,
        latitude: float,
        longitude: float,
        address_label: str | None,
        formatted_address: str | None,
    ) -> Location:
        location = Location(
            latitude=latitude,
            longitude=longitude,
            address_label=address_label,
            formatted_address=formatted_address,
        )
        self._session.add(location)
        self._session.commit()
        self._session.refresh(location)
        return location

    def get_by_id(self, location_id: str) -> Location | None:
        return self._session.get(Location, location_id)
