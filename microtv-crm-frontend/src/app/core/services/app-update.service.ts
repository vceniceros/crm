import { ApplicationRef, Injectable, inject } from '@angular/core';
import { SwUpdate, VersionEvent } from '@angular/service-worker';
import { concat, interval } from 'rxjs';
import { filter, first } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class AppUpdateService {
  private readonly appRef = inject(ApplicationRef);
  private readonly updates = inject(SwUpdate);

  start(): void {
    if (!this.updates.isEnabled) {
      return;
    }

    this.updates.versionUpdates.subscribe((event: VersionEvent) => {
      if (event.type !== 'VERSION_READY') {
        return;
      }

      const shouldReload = window.confirm('Hay una nueva versión disponible. ¿Querés actualizar ahora?');
      if (!shouldReload) {
        return;
      }

      this.updates.activateUpdate().then(() => window.location.reload());
    });

    const appIsStable$ = this.appRef.isStable.pipe(
      first((isStable) => isStable)
    );

    concat(appIsStable$, interval(6 * 60 * 60 * 1000)).subscribe(() => {
      this.updates.checkForUpdate();
    });
  }
}
