/**
 * @deprecated Legacy mock-only category shape. Use SettingsCategory from
 * settings-management.model.ts for persisted CRM categories.
 */
export interface TicketCategory {
  id: number | string;
  name: string;
}

/**
 * @deprecated Legacy mock-only envelope. Use SettingsManagementService.listCategories().
 */
export interface TicketCategoriesMockData {
  categories: TicketCategory[];
}
