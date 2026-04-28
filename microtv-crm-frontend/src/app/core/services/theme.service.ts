import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, computed, inject, signal } from '@angular/core';

export type ThemeMode = 'light' | 'dark';

const THEME_STORAGE_KEY = 'crm-theme-preference';
const THEME_TRANSITION_CLASS = 'theme-transition';
const THEME_TRANSITION_MS = 500;

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly platformId = inject(PLATFORM_ID);

  private readonly manualTheme = signal<ThemeMode | null>(null);
  private readonly systemTheme = signal<ThemeMode>('light');

  private mediaQueryList: MediaQueryList | null = null;
  private transitionTimeoutId: number | null = null;
  private initialized = false;

  readonly theme = computed(() => this.manualTheme() ?? this.systemTheme());

  initialize(): void {
    if (this.initialized || !isPlatformBrowser(this.platformId)) {
      return;
    }

    this.initialized = true;
    this.mediaQueryList = window.matchMedia('(prefers-color-scheme: dark)');
    this.systemTheme.set(this.mediaQueryList.matches ? 'dark' : 'light');

    const storedTheme = this.readStoredTheme();
    if (storedTheme) {
      this.manualTheme.set(storedTheme);
    }

    this.applyTheme(this.theme());
    this.mediaQueryList.addEventListener('change', this.handleSystemThemeChange);
  }

  toggleTheme(): void {
    const nextTheme: ThemeMode = this.theme() === 'dark' ? 'light' : 'dark';
    this.setManualTheme(nextTheme);
  }

  private setManualTheme(theme: ThemeMode): void {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    this.enableThemeTransition();
    this.manualTheme.set(theme);
    this.writeStoredTheme(theme);
    this.applyTheme(theme);
  }

  private enableThemeTransition(): void {
    const root = this.document.documentElement;

    root.classList.add(THEME_TRANSITION_CLASS);

    if (this.transitionTimeoutId !== null) {
      window.clearTimeout(this.transitionTimeoutId);
    }

    this.transitionTimeoutId = window.setTimeout(() => {
      root.classList.remove(THEME_TRANSITION_CLASS);
      this.transitionTimeoutId = null;
    }, THEME_TRANSITION_MS);
  }

  private readonly handleSystemThemeChange = (event: MediaQueryListEvent): void => {
    this.systemTheme.set(event.matches ? 'dark' : 'light');

    // Respect system changes only while there is no manual user preference saved.
    if (!this.manualTheme()) {
      this.applyTheme(this.theme());
    }
  };

  private applyTheme(theme: ThemeMode): void {
    const root = this.document.documentElement;
    const body = this.document.body;

    root.classList.remove('theme-light', 'theme-dark');
    root.classList.add(`theme-${theme}`);

    if (body) {
      body.classList.remove('theme-light', 'theme-dark');
      body.classList.add(`theme-${theme}`);
    }

    this.updateThemeColorMeta(theme);
  }

  private updateThemeColorMeta(theme: ThemeMode): void {
    const metaThemeColor = this.document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', theme === 'dark' ? '#10141d' : '#ffffff');
    }
  }

  private readStoredTheme(): ThemeMode | null {
    try {
      const value = localStorage.getItem(THEME_STORAGE_KEY);
      return value === 'dark' || value === 'light' ? value : null;
    } catch {
      return null;
    }
  }

  private writeStoredTheme(theme: ThemeMode): void {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Ignore storage errors in private browsing or restricted environments.
    }
  }
}