import { AppLocation } from './location.model';

export interface ClientOption {
  id: number | string;
  name: string;
}

export type ClientLocation = AppLocation;

export interface ClientItem {
  id: number | string;
  razonSocial: string;
  cuit: string;
  email: string | null;
  telefono: string | null;
  isActive: boolean;
  location: ClientLocation | null;
}

export interface ClientsPageData {
  pageTitle: string;
  pageSubtitle: string;
  items: ClientItem[];
}