export interface LoginRequest {
  email: string;
  password: string;
}

export interface MembershipOptionResponse {
  membership_id: string;
  tenant_type: string;
  tenant_id: string;
  roles: string[];
}

export interface ActiveMembershipResponse {
  membership_id: string;
  tenant_type: string;
  tenant_id: string;
  auth_roles: string[];
}

export interface AuthenticatedUserResponse {
  crm_user_id: string;
  auth_user_id: string;
  email: string | null;
  display_name: string | null;
  primary_role: string;
  role_keys: string[];
  active_membership: ActiveMembershipResponse;
}

export interface TokenBundleResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number | null;
}

export interface LoginSuccessResponse {
  status: 'authenticated';
  tokens: TokenBundleResponse;
  user: AuthenticatedUserResponse;
}

export interface ContextSelectionRequiredResponse {
  status: 'context_selection_required';
  login_ticket: string;
  memberships: MembershipOptionResponse[];
}

export interface AccessPendingResponse {
  status: 'access_pending';
  user_type: string | null;
}

export type CrmLoginResponse =
  | LoginSuccessResponse
  | ContextSelectionRequiredResponse
  | AccessPendingResponse;