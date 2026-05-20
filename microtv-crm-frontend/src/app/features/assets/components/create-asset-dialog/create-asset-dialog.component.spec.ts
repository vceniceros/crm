import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { CreateAssetDialogComponent } from './create-asset-dialog.component';

describe('CreateAssetDialogComponent', () => {
  let component: CreateAssetDialogComponent;
  let fixture: ComponentFixture<CreateAssetDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CreateAssetDialogComponent],
      providers: [provideHttpClient(), { provide: MAT_DIALOG_DATA, useValue: {} }, { provide: MatDialogRef, useValue: { close: () => undefined } }]
    }).compileComponents();

    fixture = TestBed.createComponent(CreateAssetDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
