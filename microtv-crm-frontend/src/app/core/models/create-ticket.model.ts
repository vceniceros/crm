import { RequiredInventoryItem } from './inventory-item.model';

export interface CreateTicketFormValue {
  title: string;
  description: string;
  categoryId: number | string | null;
  affectedDeviceId: number | string | null;
  priority: string | null;
  requiredItems: RequiredInventoryItem[];
}