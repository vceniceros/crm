import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';

import { ClientItem, ClientLocation } from '../../../../core/models/client.model';
import { CreateClientFormValue } from '../../../../core/models/create-client.model';
import { MockClientsService } from '../../../../core/services/mock-clients.service';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationPickerService } from '../../../../shared/services/location-picker.service';
import { CreateClientFormGroup, CreateClientFormModel } from './create-client-form.types';

@Component({
  selector: 'app-create-client-dialog',
  standalone: true,
  imports: [
    MatButtonModule,
    MatDialogActions,
    MatDialogClose,
    MatDialogContent,
    MatDialogModule,
    MatDialogTitle,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    ReactiveFormsModule
  ],
  templateUrl: './create-client-dialog.component.html',
  styleUrl: './create-client-dialog.component.scss'
})
export class CreateClientDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<CreateClientDialogComponent, ClientItem>);
  private readonly formBuilder = inject(FormBuilder);
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly locationPickerService = inject(LocationPickerService);
  private readonly mockClientsService = inject(MockClientsService);

  readonly selectedLocation = signal<ClientLocation | null>(null);
  readonly googleMapsUrl = computed(() => this.locationLinkService.buildGoogleMapsUrl(this.selectedLocation()));

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
      validators: [Validators.required, Validators.email],
      nonNullable: true
    }),
    telefono: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    })
  });

  openLocationPicker(): void {
    this.locationPickerService
      .open({
        title: 'Seleccionar ubicación del cliente',
        initialLocation: this.selectedLocation()
      })
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

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const payload: CreateClientFormValue = {
      razonSocial: this.form.controls.razonSocial.getRawValue(),
      cuit: this.form.controls.cuit.getRawValue(),
      email: this.form.controls.email.getRawValue(),
      telefono: this.form.controls.telefono.getRawValue(),
      location: this.selectedLocation()
    };

    this.mockClientsService
      .createClient(payload)
      .pipe(map((client) => this.dialogRef.close(client)))
      .subscribe();
  }
}