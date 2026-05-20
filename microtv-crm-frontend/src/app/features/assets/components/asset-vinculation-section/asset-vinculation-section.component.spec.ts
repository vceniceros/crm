import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { AssetVinculationSectionComponent } from './asset-vinculation-section.component';

describe('AssetVinculationSectionComponent', () => {
  let component: AssetVinculationSectionComponent;
  let fixture: ComponentFixture<AssetVinculationSectionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssetVinculationSectionComponent],
      providers: [provideHttpClient()]
    }).compileComponents();

    fixture = TestBed.createComponent(AssetVinculationSectionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
