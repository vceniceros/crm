"""
AFIP public padron A4 client.
Endpoint: GET {base_url}/persona/{cuit}
No authentication required — public API.
"""
import httpx

from src.config import settings

# Maps AFIP regimen codes/descriptions to our fiscal_type values
_FISCAL_TYPE_MAP: dict[str, str] = {
    "RESPONSABLE INSCRIPTO": "responsable_inscripto",
    "MONOTRIBUTO": "monotributo",
    "EXENTO": "exento",
    "SOCIEDADES": "sociedad",
}


def _extract_fiscal_type(afip_data: dict) -> str | None:
    """Best-effort extraction of fiscal category from AFIP padron response."""
    data = afip_data.get("data", {})

    # Check for simplified monotributo regime
    simplificado = data.get("regimenes", {}).get("simplificado")
    if simplificado:
        return "monotributo"

    # Check actividad regimes for IVA category
    for regimen in data.get("regimenes", {}).get("actividad", []):
        descripcion = str(regimen.get("descripcionActividad", "")).upper()
        for keyword, fiscal_type in _FISCAL_TYPE_MAP.items():
            if keyword in descripcion:
                return fiscal_type

    # Fallback: check tipoPersona — juridica implies sociedad
    tipo_persona = str(data.get("datosGenerales", {}).get("tipoPersona", "")).upper()
    if tipo_persona == "JURIDICA":
        return "sociedad"

    return None


async def verify_cuit(cuit: str) -> dict:
    """
    Query AFIP padron A4 for the given CUIT.

    Returns the raw afip_data dict (to be stored as-is) enriched with
    a 'fiscal_type' key extracted from the response.

    Raises ValueError if:
    - The CUIT is not found
    - The CUIT is not ACTIVO
    - The AFIP service is unreachable (wraps as ValueError so callers handle it uniformly)
    """
    url = f"{settings.afip_base_url}/persona/{cuit}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
    except httpx.TimeoutException as exc:
        raise ValueError("AFIP service timed out. Intentá nuevamente en unos minutos.") from exc
    except httpx.RequestError as exc:
        raise ValueError("No se pudo conectar al servicio de AFIP. Intentá nuevamente.") from exc

    if response.status_code == 404:
        raise ValueError(f"CUIT {cuit} no encontrado en AFIP.")

    if response.status_code != 200:
        raise ValueError(f"AFIP respondió con código {response.status_code}. Intentá nuevamente.")

    try:
        body = response.json()
    except Exception as exc:
        raise ValueError("Respuesta inesperada de AFIP.") from exc

    data = body.get("data", {})
    estado = str(data.get("estadoClave", "")).upper()
    if estado != "ACTIVO":
        raise ValueError(
            f"El CUIT {cuit} figura como '{estado}' en AFIP. "
            "Verificá que esté activo antes de continuar."
        )

    fiscal_type = _extract_fiscal_type(body)
    return {**body, "fiscal_type": fiscal_type}
