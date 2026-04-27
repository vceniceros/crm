import { Injectable } from '@angular/core';

export type ListingViewMode = 'table' | 'cards';

@Injectable({ providedIn: 'root' })
export class ListingViewPreferenceService {
  private readonly storagePrefix = 'microtv.crm.listing.view';

  getView(key: string, fallback: ListingViewMode = 'table'): ListingViewMode {
    if (typeof window === 'undefined' || !window.localStorage) {
      return fallback;
    }

    const value = window.localStorage.getItem(`${this.storagePrefix}.${key}`);
    return value === 'cards' || value === 'table' ? value : fallback;
  }

  setView(key: string, mode: ListingViewMode): void {
    if (typeof window === 'undefined' || !window.localStorage) {
      return;
    }

    window.localStorage.setItem(`${this.storagePrefix}.${key}`, mode);
  }
}
