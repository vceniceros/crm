import { ClientLocation } from './client.model';

export interface CreateClientFormValue {
  razonSocial: string;
  cuit: string;
  email: string;
  telefono: string;
  location: ClientLocation | null;
}