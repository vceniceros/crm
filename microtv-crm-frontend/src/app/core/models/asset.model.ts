import { TaskSummary } from './task-management.model';
import { TicketSummary } from './ticket-management.model';

export interface AssetCategoryField {
  field_id: string;
  field_name: string;
  field_type: 'string' | 'number';
  is_required: boolean;
  order_index: number;
}

export interface AssetCategory {
  asset_category_id: string;
  category_name: string;
  description: string | null;
  is_active: boolean;
  fields: AssetCategoryField[];
}

export interface AssetFieldValue {
  field_id: string;
  field_name: string;
  field_type: 'string' | 'number';
  raw_value: string;
}

export interface AssetSummary {
  asset_id: string;
  asset_name: string;
  category_name: string;
  client_name: string;
  parent_asset_id: string | null;
  parent_asset_name: string | null;
  created_by_crm_user_id: string;
}

export interface Asset extends AssetSummary {
  category_id: string;
  client_id: string;
  notes: string | null;
  field_values: AssetFieldValue[];
}

export interface CreateAssetCategoryPayload {
  category_name: string;
  description: string | null;
  fields: Array<{
    field_name: string;
    field_type: 'string' | 'number';
    is_required: boolean;
    order_index: number;
  }>;
}

export interface AssetFieldValuePayload {
  field_id: string;
  value: string;
}

export interface CreateAssetPayload {
  category_id: string;
  client_id: string;
  asset_name: string;
  notes: string | null;
  parent_asset_id: string | null;
  field_values: AssetFieldValuePayload[];
}

export interface UpdateAssetPayload {
  asset_name?: string;
  notes?: string | null;
  parent_asset_id?: string | null;
  field_values?: AssetFieldValuePayload[];
}

export type AssetLinkedTicket = TicketSummary;
export type AssetLinkedTask = TaskSummary;
