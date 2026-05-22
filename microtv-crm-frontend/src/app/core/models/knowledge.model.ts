export type KnowledgeArticleStatus = 'draft' | 'published';
export type KnowledgeAttachmentType = 'image' | 'video';

export interface KnowledgeCategory {
  article_category_id: string;
  name: string;
  slug: string;
  description: string | null;
}

export interface KnowledgeAttachment {
  attachment_id: string;
  file_type: KnowledgeAttachmentType;
  mime_type: string;
  original_filename: string;
  file_url: string;
  size_bytes: number | null;
  created_at: string;
}

export interface KnowledgeArticleListItem {
  article_id: string;
  title: string;
  slug: string;
  category: KnowledgeCategory | null;
  status: KnowledgeArticleStatus;
  excerpt: string | null;
  created_by_display_name: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeArticleDetail extends KnowledgeArticleListItem {
  content_md: string;
  attachments: KnowledgeAttachment[];
}

export interface CreateKnowledgeArticleRequest {
  title: string;
  category_id?: string | null;
  content_md: string;
  status: KnowledgeArticleStatus;
  is_auto_draft?: boolean;
}

export interface UpdateKnowledgeArticleRequest {
  title?: string;
  category_id?: string | null;
  content_md?: string;
  status?: KnowledgeArticleStatus;
}
