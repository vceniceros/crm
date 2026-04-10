import { AppLocation } from './location.model';

export interface ClientOption {
  id: number | string;
  name: string;
}

export type ClientLocation = AppLocation;

export interface ClientItem {
  id: number;
  razonSocial: string;
  cuit: string;
  email: string;
  telefono: string;
  location: ClientLocation | null;
}

export interface ClientsPageData {
  pageTitle: string;
  pageSubtitle: string;
  items: ClientItem[];
}