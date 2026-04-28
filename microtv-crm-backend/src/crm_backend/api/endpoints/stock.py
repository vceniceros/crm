"""Endpoints HTTP del flujo real inicial de depósito."""

from fastapi import APIRouter, Depends, Request, Response, UploadFile, status

from crm_backend.api.dependencies import get_authenticated_crm_session, get_product_image_storage, get_stock_application_service
from crm_backend.infrastructure.product_image_storage import ProductImageStorage
from crm_backend.schemas import (
    CreateStockProductRequest,
    ErrorResponse,
    StockAdjustmentRequest,
    StockCategoryResponse,
    StockProductResponse,
)
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.stock_service import CreateStockProductCommand, StockApplicationService


router = APIRouter(prefix="/stock", tags=["stock"])


def _build_category_response(category) -> StockCategoryResponse:
    """Mapea una entidad de categoría al contrato HTTP.

    Args:
        category: Entidad ORM de categoría.

    Returns:
        StockCategoryResponse: Respuesta serializable.
    """

    return StockCategoryResponse(
        id=category.stock_category_id,
        code=category.code,
        name=category.name,
        is_active=category.is_active,
    )


def _build_product_response(product) -> StockProductResponse:
    """Mapea una entidad de producto al contrato HTTP.

    Args:
        product: Entidad ORM de producto.

    Returns:
        StockProductResponse: Respuesta serializable.
    """

    return StockProductResponse(
        id=product.stock_product_id,
        product_id=product.stock_product_id,
        product_code=product.visible_product_code,
        name=product.name,
        product_name=product.name,
        category_id=product.stock_category_id or "",
        category_name=product.category.name,
        current_stock=product.current_stock,
        image_url=product.image_url,
        requires_tracking=product.requires_tracking,
        created_at=product.created_at,
        updated_at=product.updated_at,
        is_active=product.is_active,
    )


@router.get(
    "/categories",
    response_model=list[StockCategoryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_categories(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    stock_service: StockApplicationService = Depends(get_stock_application_service),
) -> list[StockCategoryResponse]:
    """Lista categorías reales de depósito.

    Args:
        actor: Sesión CRM autenticada.
        stock_service: Servicio de aplicación de depósito.

    Returns:
        list[StockCategoryResponse]: Categorías activas.
    """

    return [_build_category_response(category) for category in stock_service.list_categories(actor)]


@router.get(
    "/products",
    response_model=list[StockProductResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_products(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    stock_service: StockApplicationService = Depends(get_stock_application_service),
) -> list[StockProductResponse]:
    """Lista productos reales de depósito.

    Args:
        actor: Sesión CRM autenticada.
        stock_service: Servicio de aplicación de depósito.

    Returns:
        list[StockProductResponse]: Productos activos.
    """

    return [_build_product_response(product) for product in stock_service.list_products(actor)]


@router.post(
    "/products",
    response_model=StockProductResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def create_product(
    request: Request,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    stock_service: StockApplicationService = Depends(get_stock_application_service),
    image_storage: ProductImageStorage = Depends(get_product_image_storage),
) -> StockProductResponse:
    """Crea un producto real de depósito.

    Args:
        request: Request HTTP entrante.
        actor: Sesión CRM autenticada.
        stock_service: Servicio de aplicación de depósito.
        image_storage: Storage local de imágenes.

    Returns:
        StockProductResponse: Producto persistido.
    """

    payload, upload = await _parse_create_product_request(request)

    image_url = payload.image_url
    stored_image_url: str | None = None
    if upload is not None:
        stored_image_url = await image_storage.store(upload)
        image_url = stored_image_url

    try:
        product = stock_service.create_product(
            actor,
            CreateStockProductCommand(
                name=payload.name,
                product_code=payload.product_code,
                category_id=payload.category_id,
                initial_stock=payload.initial_stock,
                image_url=image_url,
                requires_tracking=payload.requires_tracking,
            ),
        )
    except Exception:
        image_storage.delete(stored_image_url)
        raise

    return _build_product_response(product)


async def _parse_create_product_request(request: Request) -> tuple[CreateStockProductRequest, UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        raw_upload = form.get("image")
        upload = raw_upload if getattr(raw_upload, "filename", "") else None
        payload = CreateStockProductRequest.model_validate(
            {
                "product_name": form.get("product_name") or form.get("name"),
                "product_code": form.get("product_code"),
                "category_id": form.get("category_id"),
                "stock_initial": form.get("stock_initial") or form.get("initial_stock") or 0,
                "requires_tracking": str(form.get("requires_tracking") or "false").lower() in {"1", "true", "on", "yes"},
                "image_url": None,
            }
        )
        return payload, upload

    payload = CreateStockProductRequest.model_validate(await request.json())
    return payload, None


@router.post(
    "/products/{product_id}/increase-stock",
    response_model=StockProductResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def increase_stock(
    product_id: str,
    payload: StockAdjustmentRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    stock_service: StockApplicationService = Depends(get_stock_application_service),
) -> StockProductResponse:
    """Aumenta stock real sobre un producto.

    Args:
        product_id: Producto afectado.
        payload: Cantidad a sumar.
        actor: Sesión CRM autenticada.
        stock_service: Servicio de aplicación de depósito.

    Returns:
        StockProductResponse: Producto actualizado.
    """

    product = stock_service.increase_stock(actor, product_id=product_id, quantity=payload.quantity)
    return _build_product_response(product)


@router.post(
    "/products/{product_id}/decrease-stock",
    response_model=StockProductResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def decrease_stock(
    product_id: str,
    payload: StockAdjustmentRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    stock_service: StockApplicationService = Depends(get_stock_application_service),
) -> StockProductResponse:
    """Disminuye stock real sobre un producto.

    Args:
        product_id: Producto afectado.
        payload: Cantidad a restar.
        actor: Sesión CRM autenticada.
        stock_service: Servicio de aplicación de depósito.

    Returns:
        StockProductResponse: Producto actualizado.
    """

    product = stock_service.decrease_stock(actor, product_id=product_id, quantity=payload.quantity)
    return _build_product_response(product)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def delete_product(
    product_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    stock_service: StockApplicationService = Depends(get_stock_application_service),
    image_storage: ProductImageStorage = Depends(get_product_image_storage),
) -> Response:
    """Da de baja lógica un producto del depósito.

    Args:
        product_id: Producto afectado.
        actor: Sesión CRM autenticada.
        stock_service: Servicio de aplicación de depósito.
        image_storage: Storage local de imágenes.

    Returns:
        Response: Respuesta vacía con estado 204.
    """

    product = stock_service.delete_product(actor, product_id=product_id)
    image_storage.delete(product.image_url)
    return Response(status_code=status.HTTP_204_NO_CONTENT)