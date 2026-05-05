import { DashboardData } from './dashboard.model';
import { NavigationSection } from './navigation.model';

export interface BrandInfo {
  name: string;
  subtitle: string;
}

export interface CurrentUser {
  initials: string;
  name: string;
  role: string;
  avatarUrl?: string | null;
}

export interface TopbarInfo {
  title: string;
  searchPlaceholder: string;
}

export interface LayoutMockData {
  brand: BrandInfo;
  currentUser: CurrentUser;
  topbar: TopbarInfo;
  navigation: NavigationSection[];
  dashboard: DashboardData;
}