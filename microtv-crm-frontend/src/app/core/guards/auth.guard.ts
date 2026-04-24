import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthSessionService } from '../services/auth-session.service';

export const authGuard: CanActivateFn = (_, state) => {
  const authSessionService = inject(AuthSessionService);
  const router = inject(Router);

  if (authSessionService.isAuthenticatedSnapshot()) {
    return true;
  }

  return router.createUrlTree(['/login'], {
    queryParams: { redirectTo: state.url }
  });
};

export const guestOnlyGuard: CanActivateFn = () => {
  const authSessionService = inject(AuthSessionService);
  const router = inject(Router);

  if (authSessionService.isAuthenticatedSnapshot()) {
    return router.createUrlTree(['/']);
  }

  return true;
};

export const adminOnlyGuard: CanActivateFn = () => {
  const authSessionService = inject(AuthSessionService);
  const router = inject(Router);

  const session = authSessionService.sessionSnapshot();
  if (session?.user.role_keys.includes('admin')) {
    return true;
  }

  return router.createUrlTree(['/tasks']);
};

export const adminOrExecutiveGuard: CanActivateFn = () => {
  const authSessionService = inject(AuthSessionService);
  const router = inject(Router);

  const roles = authSessionService.sessionSnapshot()?.user.role_keys ?? [];
  if (roles.includes('admin') || roles.includes('ejecutivo')) {
    return true;
  }

  return router.createUrlTree(['/tasks']);
};