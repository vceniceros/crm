export interface NavigationItem {
  id: string;
  label: string;
  icon: string;
  route?: string;
  badge?: number;
  active?: boolean;
}

export interface NavigationSection {
  section: string;
  items: NavigationItem[];
}