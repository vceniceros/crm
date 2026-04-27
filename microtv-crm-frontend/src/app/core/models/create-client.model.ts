import { ClientLocation } from './client.model';

export interface CreateClientFormValue {
  razonSocial: string;
  cuit: string;
  email: string;
  telefono: string;
  isActive: boolean;
  location: ClientLocation | null;
}