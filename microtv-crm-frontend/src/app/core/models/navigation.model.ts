import { MockModuleKey } from './permission.model';

export interface NavigationItem {
  id: string;
  label: string;
  icon: string;
  moduleKey?: MockModuleKey;
  route?: string;
  badge?: number;
  active?: boolean;
}

export interface NavigationSection {
  section: string;
  items: NavigationItem[];
}