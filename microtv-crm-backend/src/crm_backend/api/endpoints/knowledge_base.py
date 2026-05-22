"""HTTP endpoints for the knowledge base module."""

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from crm_backend.api.dependencies import get_authenticated_crm_session, get_knowledge_application_service
from crm_backend.schemas import ErrorResponse
from crm_backend.schemas.knowledge import (
    CreateKnowledgeArticleRequest,
    KnowledgeArticleDetail,
    KnowledgeArticleFilterParams,
    KnowledgeArticleListItem,
    KnowledgeAttachmentResponse,
    KnowledgeCategoryResponse,
    UpdateKnowledgeArticleRequest,
)
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.knowledge_service import KnowledgeApplicationService


router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


def _created_by_display_name(article) -> str:
    user = getattr(article, "created_by", None)
    return getattr(user, "display_name", None) or getattr(user, "email", None) or "Usuario CRM"


def _map_article_list_item(article) -> KnowledgeArticleListItem:
    excerpt = (article.content_md or "").strip().replace("\n", " ")
    return KnowledgeArticleListItem(
        article_id=article.article_id,
        title=article.title,
        slug=article.slug,
        category=KnowledgeCategoryResponse.model_validate(article.category) if article.category is not None else None,
        status=article.status,
        excerpt=excerpt[:200] if excerpt else None,
        created_by_display_name=_created_by_display_name(article),
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _map_article_detail(article) -> KnowledgeArticleDetail:
    base = _map_article_list_item(article).model_dump()
    return KnowledgeArticleDetail(
        **base,
        content_md=article.content_md,
        attachments=[KnowledgeAttachmentResponse.model_validate(item) for item in article.attachments],
    )


@router.get("/categories", response_model=list[KnowledgeCategoryResponse], responses={401: {"model": ErrorResponse}})
def list_categories(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: KnowledgeApplicationService = Depends(get_knowledge_application_service),
) -> list[KnowledgeCategoryResponse]:
    return [KnowledgeCategoryResponse.model_validate(item) for item in service.list_categories()]


@router.get("/articles", response_model=list[KnowledgeArticleListItem], responses={401: {"model": ErrorResponse}})
def list_articles(
    search: str | None = None,
    category_id: str | None = None,
    status: str | None = "published",
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: KnowledgeApplicationService = Depends(get_knowledge_application_service),
) -> list[KnowledgeArticleListItem]:
    filters = KnowledgeArticleFilterParams(search=search, category_id=category_id, status=status)
    return [_map_article_list_item(item) for item in service.list_articles(actor, filters)]


@router.get("/articles/{article_id}", response_model=KnowledgeArticleDetail, responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def get_article(
    article_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: KnowledgeApplicationService = Depends(get_knowledge_application_service),
) -> KnowledgeArticleDetail:
    return _map_article_detail(service.get_article(actor, article_id))


@router.post(
    "/articles",
    status_code=status.HTTP_201_CREATED,
    response_model=KnowledgeArticleDetail,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_article(
    payload: CreateKnowledgeArticleRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: KnowledgeApplicationService = Depends(get_knowledge_application_service),
) -> KnowledgeArticleDetail:
    return _map_article_detail(service.create_article(actor, payload))


@router.put(
    "/articles/{article_id}",
    response_model=KnowledgeArticleDetail,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_article(
    article_id: str,
    payload: UpdateKnowledgeArticleRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: KnowledgeApplicationService = Depends(get_knowledge_application_service),
) -> KnowledgeArticleDetail:
    return _map_article_detail(service.update_article(actor, article_id, payload))


@router.delete(
    "/articles/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_article(
    article_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: KnowledgeApplicationService = Depends(get_knowledge_application_service),
) -> Response:
    service.delete_article(actor, article_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/articles/{article_id}/attachments",
    status_code=status.HTTP_201_CREATED,
    response_model=KnowledgeAttachmentResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def upload_attachment(
    article_id: str,
    file: UploadFile = File(...),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: KnowledgeApplicationService = Depends(get_knowledge_application_service),
) -> KnowledgeAttachmentResponse:
    return KnowledgeAttachmentResponse.model_validate(await service.upload_attachment(actor, article_id, file))


@router.delete(
    "/articles/{article_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_attachment(
    article_id: str,
    attachment_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: KnowledgeApplicationService = Depends(get_knowledge_application_service),
) -> Response:
    service.delete_attachment(actor, article_id, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
