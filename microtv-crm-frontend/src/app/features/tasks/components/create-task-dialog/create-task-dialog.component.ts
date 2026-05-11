import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';

import { AppLocation } from '../../../../core/models/location.model';
import { ClientSummary, TaskDetail, TaskTemplate } from '../../../../core/models/task-management.model';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationPickerService } from '../../../../shared/services/location-picker.service';
import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';

@Component({
  selector: 'app-create-task-dialog',
  standalone: true,
  imports: [
    MatButtonModule,
    MatCheckboxModule,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogModule,
    MatDialogTitle,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    LocationMapComponent,
    ReactiveFormsModule
  ],
  templateUrl: './create-task-dialog.component.html',
  styleUrl: './create-task-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CreateTaskDialogComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly dialogData = inject<{ templateId?: string } | null>(MAT_DIALOG_DATA, { optional: true });
  private readonly dialogRef = inject(MatDialogRef<CreateTaskDialogComponent, TaskDetail>);
  private readonly formBuilder = inject(FormBuilder);
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly locationPickerService = inject(LocationPickerService);
  private readonly locationLinkService = inject(LocationLinkService);

  readonly isLoading = signal(true);
  readonly isSubmitting = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly templates = signal<TaskTemplate[]>([]);
  readonly clients = signal<ClientSummary[]>([]);
  readonly selectedLocation = signal<AppLocation | null>(null);

  readonly form = this.formBuilder.group({
    template_id: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true }),
    client_id: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true }),
    task_title: this.formBuilder.control<string | null>(null),
    task_description: this.formBuilder.control<string | null>(null),
    requires_arrival_comment: this.formBuilder.control(false, { nonNullable: true }),
    requires_video_evidence: this.formBuilder.control(false, { nonNullable: true })
  });

  readonly selectedTemplate = computed(
    () => this.templates().find((template) => template.template_id === this.form.controls.template_id.getRawValue()) ?? null
  );

  constructor() {
    const preselectedTemplateId = this.dialogData?.templateId?.trim();
    if (preselectedTemplateId) {
      this.form.controls.template_id.setValue(preselectedTemplateId);
    }

    this.loadBootstrapData();
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.errorMessage.set('Completá template y cliente para crear el pedido.');
      return;
    }

    this.errorMessage.set(null);
    this.isSubmitting.set(true);

    if (this.hasValidSelectedLocation()) {
      this.taskManagementService
        .createLocation(this.selectedLocation() as AppLocation)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (location) => this.submitTaskCreation(location.locationId),
          error: (error: Error) => {
            this.errorMessage.set(error.message);
            this.isSubmitting.set(false);
          }
        });
      return;
    }

    this.submitTaskCreation(null);
  }

  openLocationPicker(): void {
    this.locationPickerService
      .open({
        title: 'Seleccionar ubicación operativa del pedido',
        initialLocation: this.selectedLocation()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result) => {
        if (!result) {
          return;
        }

        this.selectedLocation.set(result.location);
      });
  }

  clearSelectedLocation(): void {
    this.selectedLocation.set(null);
  }

  openSelectedLocationInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.selectedLocation());
  }

  hasValidSelectedLocation(): boolean {
    return this.locationLinkService.isValidLocation(this.selectedLocation());
  }

  selectedLocationLabel(): string {
    const location = this.selectedLocation();
    if (!location) {
      return 'Sin ubicación cargada';
    }

    return location.addressLabel?.trim() || `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  }

  private loadBootstrapData(): void {
    this.isLoading.set(true);

    let pendingRequests = 2;
    const onRequestCompleted = () => {
      pendingRequests -= 1;
      if (pendingRequests <= 0) {
        this.isLoading.set(false);
      }
    };

    this.taskManagementService
      .listTemplates()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (templates) => {
          this.templates.set(templates);
          onRequestCompleted();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          onRequestCompleted();
        }
      });

    this.taskManagementService
      .listClients()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (clients) => {
          this.clients.set(clients);
          onRequestCompleted();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          onRequestCompleted();
        }
      });
  }

  private submitTaskCreation(locationId: string | null): void {
    this.taskManagementService
      .createTaskFromTemplate({
        template_id: this.form.controls.template_id.getRawValue(),
        client_id: this.form.controls.client_id.getRawValue(),
        location_id: locationId,
        task_title: this.form.controls.task_title.getRawValue()?.trim() || null,
        task_description: this.form.controls.task_description.getRawValue()?.trim() || null,
        requires_arrival_comment: this.form.controls.requires_arrival_comment.getRawValue(),
        requires_video_evidence: this.form.controls.requires_video_evidence.getRawValue()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (task) => {
          this.isSubmitting.set(false);
          this.dialogRef.close(task);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSubmitting.set(false);
        }
      });
  }
}