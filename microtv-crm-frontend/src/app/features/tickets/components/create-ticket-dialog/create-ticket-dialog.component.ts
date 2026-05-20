import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { switchMap, take } from 'rxjs';

import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { AppLocation } from '../../../../core/models/location.model';
import { CrmUserOption } from '../../../../core/models/task-management.model';
import { SettingsCategory } from '../../../../core/models/settings-management.model';
import { CreateTicketRequest, TicketClientOption, TicketDetail, TicketPriority, TicketRoleOption } from '../../../../core/models/ticket-management.model';
import { InventoryService } from '../../../../core/services/inventory.service';
import { TicketManagementService } from '../../../../core/services/ticket-management.service';
import { SettingsManagementService } from '../../../../core/services/settings-management.service';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { LocationPickerService } from '../../../../shared/services/location-picker.service';

type LocationMode = 'client' | 'custom' | 'none';

interface PriorityOption {
  id: TicketPriority;
  label: string;
}

interface RequiredMaterialSelection {
  product_id: string;
  quantity: number;
}

@Component({
  selector: 'app-create-ticket-dialog',
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
    MatSlideToggleModule,
    ReactiveFormsModule
  ],
  templateUrl: './create-ticket-dialog.component.html',
  styleUrl: './create-ticket-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CreateTicketDialogComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly dialogRef = inject(MatDialogRef<CreateTicketDialogComponent, TicketDetail>);
  private readonly formBuilder = inject(FormBuilder);
  private readonly ticketManagementService = inject(TicketManagementService);
  private readonly inventoryService = inject(InventoryService);
  private readonly locationPickerService = inject(LocationPickerService);
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly settingsManagementService = inject(SettingsManagementService);

  readonly isLoading = signal(true);
  readonly isSubmitting = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly roles = signal<TicketRoleOption[]>([]);
  readonly clients = signal<TicketClientOption[]>([]);
  readonly assignees = signal<CrmUserOption[]>([]);
  readonly inventoryProducts = signal<InventoryProduct[]>([]);
  readonly requiredMaterials = signal<RequiredMaterialSelection[]>([]);
  readonly customLocation = signal<AppLocation | null>(null);
  readonly categories = signal<SettingsCategory[]>([]);
  readonly priorities: readonly PriorityOption[] = [
    { id: 'LOW', label: 'Baja' },
    { id: 'MEDIUM', label: 'Media' },
    { id: 'HIGH', label: 'Alta' },
    { id: 'CRITICAL', label: 'Crítica' }
  ];

  readonly form = this.formBuilder.group({
    title: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    client_id: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    }),
    location_mode: this.formBuilder.control<LocationMode>('none', {
      validators: [Validators.required],
      nonNullable: true
    }),
    priority: this.formBuilder.control<TicketPriority>('MEDIUM', {
      validators: [Validators.required],
      nonNullable: true
    }),
    category_id: this.formBuilder.control<string | null>(null),
    requires_arrival_comment: this.formBuilder.control(false, { nonNullable: true }),
    requires_video_evidence: this.formBuilder.control(true, { nonNullable: true }),
    assigned_role_id: this.formBuilder.control<string | null>(null),
    assigned_user_id: this.formBuilder.control<string | null>(null),
    collaborator_user_ids: this.formBuilder.control<string[]>([], { nonNullable: true }),
    description: this.formBuilder.control('', {
      validators: [Validators.required],
      nonNullable: true
    })
  });

  readonly selectedClient = computed(() => {
    const clientId = this.form.controls.client_id.getRawValue();
    return this.clients().find((client) => client.client_id === clientId) ?? null;
  });
  readonly selectedClientLocation = computed<AppLocation | null>(() => {
    const location = this.selectedClient()?.location;
    if (!location) {
      return null;
    }

    return {
      latitude: location.latitude,
      longitude: location.longitude,
      addressLabel: location.address_label?.trim() || location.formatted_address?.trim() || undefined
    };
  });
  readonly selectedLocation = computed<AppLocation | null>(() => {
    const mode = this.form.controls.location_mode.getRawValue();
    if (mode === 'custom') {
      return this.customLocation();
    }

    if (mode === 'client') {
      return this.selectedClientLocation();
    }

    return null;
  });

  constructor() {
    this.loadBootstrapData();

    this.form.controls.client_id.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.syncLocationModeWithClient();
    });

    this.form.controls.location_mode.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((mode) => {
      if (mode !== 'custom') {
        this.customLocation.set(null);
      }
    });

    this.form.controls.assigned_role_id.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((roleId) => {
      this.loadAssigneesForRole(roleId);
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    if (this.form.controls.assigned_user_id.getRawValue() && !this.form.controls.assigned_role_id.getRawValue()) {
      this.errorMessage.set('Debes elegir un rol antes de seleccionar un usuario asignado.');
      return;
    }

    this.errorMessage.set(null);
    this.isSubmitting.set(true);

    const locationMode = this.form.controls.location_mode.getRawValue();
    if (locationMode === 'custom') {
      if (!this.locationLinkService.isValidLocation(this.customLocation())) {
        this.errorMessage.set('Selecciona una ubicación válida para continuar.');
        this.isSubmitting.set(false);
        return;
      }

      this.ticketManagementService
        .createLocation(this.customLocation() as AppLocation)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (location) => this.submitTicket(location.locationId),
          error: (error: Error) => {
            this.errorMessage.set(error.message);
            this.isSubmitting.set(false);
          }
        });
      return;
    }

    const selectedClient = this.selectedClient();
    const locationId = locationMode === 'client' ? selectedClient?.location?.location_id ?? null : null;
    this.submitTicket(locationId);
  }

  openLocationPicker(): void {
    this.locationPickerService
      .open({
        title: 'Seleccionar ubicación del ticket',
        initialLocation: this.customLocation()
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result) => {
        if (!result) {
          return;
        }

        this.customLocation.set(result.location);
      });
  }

  clearCustomLocation(): void {
    this.customLocation.set(null);
  }

  addMaterial(): void {
    const products = this.inventoryProducts();
    if (!products.length) {
      return;
    }

    const selectedIds = new Set(this.requiredMaterials().map((item) => item.product_id));
    const firstAvailable = products.find((product) => !selectedIds.has(product.productId));
    if (!firstAvailable) {
      return;
    }

    this.requiredMaterials.update((current) => [
      ...current,
      {
        product_id: firstAvailable.productId,
        quantity: 1
      }
    ]);
  }

  removeMaterial(index: number): void {
    this.requiredMaterials.update((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  updateMaterialProduct(index: number, productId: string): void {
    this.requiredMaterials.update((current) =>
      current.map((item, currentIndex) => (currentIndex === index ? { ...item, product_id: productId } : item))
    );
  }

  updateMaterialQuantity(index: number, quantity: number): void {
    const normalizedQuantity = Math.max(1, Number.isFinite(quantity) ? Math.trunc(quantity) : 1);
    this.requiredMaterials.update((current) =>
      current.map((item, currentIndex) => (currentIndex === index ? { ...item, quantity: normalizedQuantity } : item))
    );
  }

  availableProductsForMaterial(index: number): InventoryProduct[] {
    const selectedByOthers = new Set(
      this.requiredMaterials()
        .map((item, currentIndex) => (currentIndex === index ? '' : item.product_id))
        .filter((productId) => Boolean(productId))
    );
    return this.inventoryProducts().filter((product) => !selectedByOthers.has(product.productId));
  }

  selectedLocationLabel(): string {
    const location = this.selectedLocation();
    if (!location) {
      return 'Sin ubicación definida';
    }

    return location.addressLabel?.trim() || `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  }

  canOpenInMaps(): boolean {
    return this.locationLinkService.isValidLocation(this.selectedLocation());
  }

  openInMaps(): void {
    this.locationLinkService.openInGoogleMaps(this.selectedLocation());
  }

  private loadBootstrapData(): void {
    this.isLoading.set(true);
    let pendingRequests = 4;
    const onRequestCompleted = () => {
      pendingRequests -= 1;
      if (pendingRequests <= 0) {
        this.isLoading.set(false);
      }
    };

    this.ticketManagementService
      .listAssignableRoles()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (roles) => {
          this.roles.set(roles);
          onRequestCompleted();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          onRequestCompleted();
        }
      });

    this.ticketManagementService
      .listClients()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (clients) => {
          this.clients.set(clients.filter((client) => client.is_active));
          onRequestCompleted();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          onRequestCompleted();
        }
      });

    this.inventoryService
      .refresh()
      .pipe(
        switchMap(() => this.inventoryService.products$.pipe(take(1))),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (products) => {
          this.inventoryProducts.set(products.filter((product) => product.isActive));
          onRequestCompleted();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          onRequestCompleted();
        }
      });

    this.settingsManagementService
      .listCategories('operational')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (cats) => {
          this.categories.set(cats.filter((c) => c.is_active));
          onRequestCompleted();
        },
        error: () => {
          onRequestCompleted();
        }
      });
  }

  private syncLocationModeWithClient(): void {
    const client = this.selectedClient();
    const hasClientLocation = Boolean(client?.location?.location_id);
    this.form.controls.location_mode.setValue(hasClientLocation ? 'client' : 'none');
  }

  private loadAssigneesForRole(roleId: string | null): void {
    if (!roleId) {
      this.assignees.set([]);
      this.form.controls.assigned_user_id.setValue(null);
      this.form.controls.collaborator_user_ids.setValue([]);
      return;
    }

    const role = this.roles().find((item) => item.crm_role_id === roleId);
    if (!role) {
      this.assignees.set([]);
      this.form.controls.assigned_user_id.setValue(null);
      this.form.controls.collaborator_user_ids.setValue([]);
      return;
    }

    this.ticketManagementService
      .listCrmUsersByRole(role.role_key)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (users) => {
          this.assignees.set(users);
          const selectedUserId = this.form.controls.assigned_user_id.getRawValue();
          if (selectedUserId && !users.some((user) => user.crm_user_id === selectedUserId)) {
            this.form.controls.assigned_user_id.setValue(null);
          }
          const validUserIds = new Set(users.map((user) => user.crm_user_id));
          this.form.controls.collaborator_user_ids.setValue(
            this.form.controls.collaborator_user_ids.getRawValue().filter((userId) => validUserIds.has(userId)),
            { emitEvent: false }
          );
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.assignees.set([]);
          this.form.controls.assigned_user_id.setValue(null);
          this.form.controls.collaborator_user_ids.setValue([]);
        }
      });
  }

  private submitTicket(locationId: string | null): void {
    const payload: CreateTicketRequest = {
      title: this.form.controls.title.getRawValue().trim(),
      description: this.form.controls.description.getRawValue().trim(),
      client_id: this.form.controls.client_id.getRawValue(),
      location_id: locationId,
      priority: this.form.controls.priority.getRawValue(),
      category_id: this.form.controls.category_id.getRawValue() || null,
      requires_arrival_comment: this.form.controls.requires_arrival_comment.getRawValue(),
      requires_video_evidence: this.form.controls.requires_video_evidence.getRawValue(),
      assigned_role_id: this.form.controls.assigned_role_id.getRawValue(),
      assigned_user_id: this.form.controls.assigned_user_id.getRawValue(),
      collaborator_user_ids: this.form.controls.collaborator_user_ids.getRawValue(),
      required_materials: this.buildRequiredMaterialsPayload()
    };

    this.ticketManagementService
      .createTicket(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (ticket) => {
          this.isSubmitting.set(false);
          this.dialogRef.close(ticket);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSubmitting.set(false);
        }
      });
  }

  private buildRequiredMaterialsPayload(): { product_id: string; quantity: number }[] {
    const seen = new Set<string>();
    const payload: { product_id: string; quantity: number }[] = [];
    for (const material of this.requiredMaterials()) {
      const productId = material.product_id?.trim();
      if (!productId || seen.has(productId)) {
        continue;
      }
      const quantity = Math.max(1, Math.trunc(material.quantity || 1));
      seen.add(productId);
      payload.push({ product_id: productId, quantity });
    }
    return payload;
  }
}
