export interface MeResponse {
  display_name: string | null;
  email: string | null;
  avatar_url: string | null;
  roles: string[];
}

export interface MePatchRequest {
  display_name?: string;
  email?: string;
}
