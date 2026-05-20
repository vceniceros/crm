import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { MatDialogRef } from '@angular/material/dialog';

import { CreateAssetCategoryDialogComponent } from './create-asset-category-dialog.component';

describe('CreateAssetCategoryDialogComponent', () => {
  let component: CreateAssetCategoryDialogComponent;
  let fixture: ComponentFixture<CreateAssetCategoryDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CreateAssetCategoryDialogComponent],
      providers: [provideHttpClient(), { provide: MatDialogRef, useValue: { close: () => undefined } }]
    }).compileComponents();

    fixture = TestBed.createComponent(CreateAssetCategoryDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
