import { HttpErrorResponse } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';

import { ClientItem } from '../../../../core/models/client.model';
import { CreateClientFormValue } from '../../../../core/models/create-client.model';
import { ClientsService } from '../../../../core/services/clients.service';
import { ClientLocation } from '../../../../core/models/client.model';
import { LocationPickerService } from '../../../../shared/services/location-picker.service';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationMapComponent } from '../../../../shared/ui/location-map/location-map.component';
import { CreateClientFormGroup, CreateClientFormModel } from './create-client-form.types';

export interface ClientDialogData {
  mode: 'create' | 'edit';
  client?: ClientItem;
}

@Component({
  selector: 'app-create-client-dialog',
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
    ReactiveFormsModule,
    LocationMapComponent
  ],
  templateUrl: './create-client-dialog.component.html',
  styleUrl: './create-client-dialog.component.scss'
})
export class CreateClientDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<CreateClientDialogComponent, ClientItem>);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly clientsService = inject(ClientsService);
  private readonly locationPickerService = inject(LocationPickerService);
  private readonly locationLinkService = inject(LocationLinkService);
  readonly data = inject<ClientDialogData | null>(MAT_DIALOG_DATA, { optional: true }) ?? { mode: 'create' as const };

  readonly isSubmitting = signal(false);
  readonly isLoading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly selectedLocation = signal<ClientLocation | null>(this.data.client?.location ?? null);

  readonly form: CreateClientFormGroup = this.formBuilder.group<CreateClientFormModel>({
    razonSocial: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    cuit: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    email: this.formBuilder.control('', {
      validators: [Validators.email],
      nonNullable: true
    }),
    telefono: this.formBuilder.control('', {
      nonNullable: true
    }),
    isActive: this.formBuilder.control(true, {
      nonNullable: true
    })
  });

  constructor() {
    if (this.data.client) {
      this.patchForm(this.data.client);
    }

    if (this.isEditMode() && this.data.client?.id) {
      this.isLoading.set(true);
      this.clientsService
        .getClientById(String(this.data.client.id))
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (client) => {
            this.patchForm(client);
            this.isLoading.set(false);
          },
          error: (error: unknown) => {
            this.errorMessage.set(this.resolveErrorMessage(error));
            this.isLoading.set(false);
          }
        });
    }
  }

  isEditMode(): boolean {
    return this.data.mode === 'edit';
  }

  dialogTitle(): string {
    return this.isEditMode() ? 'Editar cliente' : 'Crear cliente';
  }

  submitLabel(): string {
    if (this.isSubmitting()) {
      return this.isEditMode() ? 'Guardando...' : 'Creando...';
    }

    return this.isEditMode() ? 'Guardar cambios' : 'Crear cliente';
  }

  locationLabel(): string {
    const location = this.selectedLocation();
    if (!location) {
      return 'Sin ubicación cargada';
    }

    return location.addressLabel?.trim() || `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  }

  hasValidLocation(): boolean {
    return this.locationLinkService.isValidLocation(this.selectedLocation());
  }

  openLocationPicker(): void {
    this.locationPickerService
      .open({
        title: this.isEditMode() ? 'Editar ubicación del cliente' : 'Seleccionar ubicación del cliente',
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

  clearLocation(): void {
    this.selectedLocation.set(null);
  }

  openLocationInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.selectedLocation());
  }

  submit(): void {
    if (this.form.invalid || this.isLoading()) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    const payload: CreateClientFormValue = {
      razonSocial: this.form.controls.razonSocial.getRawValue(),
      cuit: this.form.controls.cuit.getRawValue(),
      email: this.form.controls.email.getRawValue(),
      telefono: this.form.controls.telefono.getRawValue(),
      isActive: this.form.controls.isActive.getRawValue(),
      location: this.selectedLocation()
    };

    const request$ = this.isEditMode() && this.data.client?.id
      ? this.clientsService.updateClient(String(this.data.client.id), payload)
      : this.clientsService.createClient(payload);

    request$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (client) => {
        this.isSubmitting.set(false);
        this.dialogRef.close(client);
      },
      error: (error: unknown) => {
        this.isSubmitting.set(false);
        this.errorMessage.set(this.resolveErrorMessage(error));
      }
    });
  }

  private patchForm(client: ClientItem): void {
    this.form.patchValue({
      razonSocial: client.razonSocial,
      cuit: client.cuit,
      email: client.email ?? '',
      telefono: client.telefono ?? '',
      isActive: client.isActive
    });
    this.selectedLocation.set(client.location);
  }

  private resolveErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const apiMessage = error.error?.error?.message;
      if (typeof apiMessage === 'string' && apiMessage.trim()) {
        return apiMessage;
      }
    }

    if (error instanceof Error && error.message.trim()) {
      return error.message;
    }

    return 'No se pudo crear el cliente.';
  }
}