import { isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, OnInit, PLATFORM_ID, computed, inject, input, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { UiHelpModuleId, UiHelpModuleTexts } from '../../../core/config/ui-help-texts.config';
import { ContextHelpService } from '../../../core/services/context-help.service';

@Component({
  selector: 'app-context-help-card',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatTooltipModule],
  templateUrl: './context-help-card.component.html',
  styleUrl: './context-help-card.component.scss'
})
export class ContextHelpCardComponent implements OnInit {
  readonly storageId = input.required<UiHelpModuleId>();
  readonly content = input.required<UiHelpModuleTexts>();
  readonly showOnlyFirstVisit = input(true);

  private readonly platformId = inject(PLATFORM_ID);
  private readonly destroyRef = inject(DestroyRef);
  private readonly contextHelpService = inject(ContextHelpService);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  readonly visible = signal(true);
  readonly mobileMode = signal(false);
  readonly mobileExpanded = signal(true);

  readonly mobileToggleLabel = computed(() => (this.mobileExpanded() ? 'Ocultar detalles' : 'Ver detalles'));

  ngOnInit(): void {
    this.initializeState();
    this.initializeViewportMode();

    this.contextHelpService.requests$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((action) => {
      if (action === 'hide') {
        this.visible.set(false);
        return;
      }

      this.showHelp();
      if (this.mobileMode()) {
        this.mobileExpanded.set(true);
      }
    });
  }

  showHelp(): void {
    this.visible.set(true);
    this.writeFlag(this.hiddenKey(), false);
  }

  hideHelp(): void {
    this.visible.set(false);
    this.writeFlag(this.hiddenKey(), true);
  }

  toggleMobileDetails(): void {
    this.mobileExpanded.update((expanded) => !expanded);
  }

  private initializeState(): void {
    if (!this.isBrowser) {
      this.visible.set(true);
      return;
    }

    const seen = this.readFlag(this.seenKey());
    const hidden = this.readFlag(this.hiddenKey());
    const shouldAutoHide = this.showOnlyFirstVisit() && seen;

    this.visible.set(!hidden && !shouldAutoHide);

    if (!seen) {
      this.writeFlag(this.seenKey(), true);
    }
  }

  private initializeViewportMode(): void {
    if (!this.isBrowser) {
      this.mobileMode.set(false);
      this.mobileExpanded.set(true);
      return;
    }

    const mediaQuery = globalThis.matchMedia('(max-width: 720px)');
    const syncWithViewport = () => {
      const isMobile = mediaQuery.matches;
      this.mobileMode.set(isMobile);
      this.mobileExpanded.set(!isMobile);
    };

    syncWithViewport();
    mediaQuery.addEventListener('change', syncWithViewport);
    this.destroyRef.onDestroy(() => {
      mediaQuery.removeEventListener('change', syncWithViewport);
    });
  }

  private seenKey(): string {
    return `crm.context-help.${this.storageId()}.seen`;
  }

  private hiddenKey(): string {
    return `crm.context-help.${this.storageId()}.hidden`;
  }

  private readFlag(key: string): boolean {
    if (!this.isBrowser) {
      return false;
    }

    try {
      return globalThis.localStorage.getItem(key) === '1';
    } catch {
      return false;
    }
  }

  private writeFlag(key: string, value: boolean): void {
    if (!this.isBrowser) {
      return;
    }

    try {
      globalThis.localStorage.setItem(key, value ? '1' : '0');
    } catch {
      // Ignore persistence errors and keep the in-memory behavior.
    }
  }
}