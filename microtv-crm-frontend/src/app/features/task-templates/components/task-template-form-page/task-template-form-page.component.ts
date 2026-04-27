import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import {
  CrmUserOption,
  CreateTaskTemplateRequest,
  TASK_ASSIGNMENT_POLICY_OPTIONS,
  TASK_ROLE_OPTIONS,
  TaskAssignmentPolicy,
  TaskItemType,
  TaskTemplate,
  TaskTemplateSubtaskWriteRequest,
  UpdateTaskTemplateRequest
} from '../../../../core/models/task-management.model';
import { InventoryProduct } from '../../../../core/models/inventory-product.model';
import { InventoryService } from '../../../../core/services/inventory.service';
import { TaskManagementService } from '../../../../core/services/task-management.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';

@Component({
  selector: 'app-task-template-form-page',
  standalone: true,
  imports: [
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    PageTitleComponent,
    ReactiveFormsModule,
    RouterLink
  ],
  templateUrl: './task-template-form-page.component.html',
  styleUrl: './task-template-form-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TaskTemplateFormPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder);
  private readonly inventoryService = inject(InventoryService);
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly destroyRef = inject(DestroyRef);

  readonly isSaving = signal(false);
  readonly isLoading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly inventoryProducts = signal<InventoryProduct[]>([]);
  readonly userOptionsByRole = signal<Record<string, CrmUserOption[]>>({});
  readonly loadingRoles = signal<string[]>([]);
  readonly isEditMode = computed(() => !!this.route.snapshot.paramMap.get('templateId'));
  readonly templateId = this.route.snapshot.paramMap.get('templateId');

  readonly form = this.formBuilder.group({
    template_name: this.formBuilder.control('', { validators: [Validators.required], nonNullable: true }),
    description: this.formBuilder.control<string | null>(null),
    is_active: this.formBuilder.control(true, { nonNullable: true }),
    required_materials: this.formBuilder.array([]),
    subtasks: this.formBuilder.array([] as Array<ReturnType<TaskTemplateFormPageComponent['createSubtaskGroup']>>)
  });

  readonly roleOptions = TASK_ROLE_OPTIONS;
  readonly assignmentPolicyOptions = TASK_ASSIGNMENT_POLICY_OPTIONS;

  constructor() {
    this.inventoryService.products$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((products) => {
      this.inventoryProducts.set(products);
    });
    this.inventoryService
      .refresh()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ error: () => undefined });

    if (this.isEditMode() && this.templateId) {
      this.isLoading.set(true);
      this.taskManagementService
        .getTemplate(this.templateId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (template) => {
            this.hydrateForm(template);
            this.isLoading.set(false);
          },
          error: (error: Error) => {
            this.errorMessage.set(error.message);
            this.isLoading.set(false);
          }
        });
    } else {
      this.addSubtask();
    }
  }

  get subtasks(): FormArray {
    return this.form.controls.subtasks;
  }

  get requiredMaterials(): FormArray {
    return this.form.controls.required_materials;
  }

  items(index: number): FormArray {
    return this.subtasks.at(index).get('items') as FormArray;
  }

  addRequiredMaterial(): void {
    this.requiredMaterials.push(this.createRequiredMaterialGroup());
  }

  removeRequiredMaterial(index: number): void {
    this.requiredMaterials.removeAt(index);
  }

  availableProductsFor(index: number): InventoryProduct[] {
    const selectedProductId = String(this.requiredMaterials.at(index)?.get('product_id')?.value ?? '');
    const selectedByOthers = new Set(
      this.requiredMaterials.controls
        .filter((_, currentIndex) => currentIndex !== index)
        .map((control) => String(control.get('product_id')?.value ?? ''))
        .filter(Boolean)
    );
    return this.inventoryProducts().filter((product) => product.productId === selectedProductId || !selectedByOthers.has(product.productId));
  }

  selectedProduct(productId: string | null | undefined): InventoryProduct | null {
    return this.inventoryProducts().find((product) => product.productId === productId) ?? null;
  }

  addSubtask(): void {
    const group = this.createSubtaskGroup();
    this.subtasks.push(group);
    this.resequenceSubtasks();
    this.loadUsersForSubtask(this.subtasks.length - 1);
  }

  duplicateSubtask(index: number): void {
    const snapshot = this.subtasks.at(index).getRawValue() as TaskTemplateSubtaskWriteRequest;
    this.subtasks.insert(index + 1, this.createSubtaskGroup(snapshot));
    this.resequenceSubtasks();
    this.loadUsersForSubtask(index + 1);
  }

  removeSubtask(index: number): void {
    if (!window.confirm('¿Eliminar esta subtarea del template?')) {
      return;
    }

    this.subtasks.removeAt(index);
    if (!this.subtasks.length) {
      this.addSubtask();
    }
    this.resequenceSubtasks();
  }

  moveSubtask(index: number, direction: -1 | 1): void {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= this.subtasks.length) {
      return;
    }

    const current = this.subtasks.at(index);
    this.subtasks.removeAt(index);
    this.subtasks.insert(targetIndex, current);
    this.resequenceSubtasks();
  }

  onResponsibleRoleChange(subtaskIndex: number): void {
    const subtask = this.subtasks.at(subtaskIndex);
    subtask.get('default_responsible_crm_user_id')?.setValue(null);
    this.loadUsersForSubtask(subtaskIndex);
  }

  getAvailableUsers(subtaskIndex: number): CrmUserOption[] {
    const roleKey = String(this.subtasks.at(subtaskIndex).get('responsible_role_key')?.value ?? '');
    return this.userOptionsByRole()[roleKey] ?? [];
  }

  isLoadingUsers(subtaskIndex: number): boolean {
    const roleKey = String(this.subtasks.at(subtaskIndex).get('responsible_role_key')?.value ?? '');
    return this.loadingRoles().includes(roleKey);
  }

  formatUserLabel(user: CrmUserOption): string {
    const name = user.display_name?.trim();
    const email = user.email?.trim();
    if (name && email) {
      return `${name} · ${email}`;
    }
    return name || email || user.crm_user_id;
  }

  addItem(subtaskIndex: number, itemType: TaskItemType = 'checkbox'): void {
    this.items(subtaskIndex).push(this.createItemGroup({ item_type: itemType }));
    this.resequenceItems(subtaskIndex);
  }

  removeItem(subtaskIndex: number, itemIndex: number): void {
    if (!window.confirm('¿Eliminar este ítem?')) {
      return;
    }

    this.items(subtaskIndex).removeAt(itemIndex);
    if (!this.items(subtaskIndex).length) {
      this.addItem(subtaskIndex);
    }
    this.resequenceItems(subtaskIndex);
  }

  moveItem(subtaskIndex: number, itemIndex: number, direction: -1 | 1): void {
    const list = this.items(subtaskIndex);
    const targetIndex = itemIndex + direction;
    if (targetIndex < 0 || targetIndex >= list.length) {
      return;
    }

    const current = list.at(itemIndex);
    list.removeAt(itemIndex);
    list.insert(targetIndex, current);
    this.resequenceItems(subtaskIndex);
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.errorMessage.set('Revisá el formulario: hay campos obligatorios incompletos.');
      return;
    }

    const payload = this.serializeForm();
    this.isSaving.set(true);
    this.errorMessage.set(null);

    const request$ = this.isEditMode() && this.templateId
      ? this.taskManagementService.updateTemplate(this.templateId, payload as UpdateTaskTemplateRequest)
      : this.taskManagementService.createTemplate(payload);

    request$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (template) => {
          const activation$ = this.isEditMode() && this.templateId
            ? this.taskManagementService.setTemplateActivation(template.template_id, { is_active: this.form.controls.is_active.getRawValue() })
            : null;

          if (!activation$) {
            this.isSaving.set(false);
            void this.router.navigate(['/tasks/templates', template.template_id]);
            return;
          }

          activation$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: (updatedTemplate) => {
              this.isSaving.set(false);
              void this.router.navigate(['/tasks/templates', updatedTemplate.template_id]);
            },
            error: (error: Error) => {
              this.errorMessage.set(error.message);
              this.isSaving.set(false);
            }
          });
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isSaving.set(false);
        }
      });
  }

  private hydrateForm(template: TaskTemplate): void {
    this.form.patchValue({
      template_name: template.template_name,
      description: template.description,
      is_active: template.is_active
    });
    this.requiredMaterials.clear();
    template.required_materials.forEach((material) => {
      this.requiredMaterials.push(
        this.createRequiredMaterialGroup({
          product_id: material.product_id,
          quantity_required: material.quantity_required,
          notes: material.notes
        })
      );
    });
    this.subtasks.clear();
    template.subtasks
      .sort((left, right) => left.order_index - right.order_index)
      .forEach((subtask) => {
        this.subtasks.push(
          this.createSubtaskGroup({
            subtask_title: subtask.subtask_title,
            subtask_description: subtask.subtask_description,
            order_index: subtask.order_index,
            responsible_role_key: subtask.responsible_role_key,
            default_responsible_crm_user_id: subtask.default_responsible_crm_user_id,
            close_comment_required: subtask.close_comment_required,
            next_assignment_policy: subtask.next_assignment_policy,
            items: subtask.items.map((item) => ({
              item_label: item.item_label,
              item_order: item.item_order,
              item_type: item.item_type,
              is_required: item.is_required
            }))
          })
        );
      });
    this.resequenceSubtasks();
    this.subtasks.controls.forEach((_, index) => this.loadUsersForSubtask(index));
  }

  private createSubtaskGroup(subtask?: Partial<TaskTemplateSubtaskWriteRequest>) {
    const items = (subtask?.items?.length ? subtask.items : [undefined]).map((item, itemIndex) =>
      this.createItemGroup(item ? item : { item_order: itemIndex })
    );

    return this.formBuilder.group({
      subtask_title: this.formBuilder.control(subtask?.subtask_title ?? '', { validators: [Validators.required], nonNullable: true }),
      subtask_description: this.formBuilder.control<string | null>(subtask?.subtask_description ?? null),
      order_index: this.formBuilder.control(subtask?.order_index ?? this.subtasks.length, { nonNullable: true }),
      responsible_role_key: this.formBuilder.control(subtask?.responsible_role_key ?? 'tecnico', { validators: [Validators.required], nonNullable: true }),
      default_responsible_crm_user_id: this.formBuilder.control<string | null>(subtask?.default_responsible_crm_user_id ?? null),
      close_comment_required: this.formBuilder.control(subtask?.close_comment_required ?? true, { nonNullable: true }),
      next_assignment_policy: this.formBuilder.control<TaskAssignmentPolicy>(subtask?.next_assignment_policy ?? 'role_queue_auto', { nonNullable: true }),
      items: this.formBuilder.array(items)
    });
  }

  private createRequiredMaterialGroup(material?: Partial<{ product_id: string; quantity_required: number; notes: string | null }>) {
    return this.formBuilder.group({
      product_id: this.formBuilder.control(material?.product_id ?? '', { validators: [Validators.required], nonNullable: true }),
      quantity_required: this.formBuilder.control(material?.quantity_required ?? 1, { validators: [Validators.required, Validators.min(1)], nonNullable: true }),
      notes: this.formBuilder.control<string | null>(material?.notes ?? null)
    });
  }

  private createItemGroup(item?: Partial<{ item_label: string; item_order: number; item_type: TaskItemType; is_required: boolean }>) {
    return this.formBuilder.group({
      item_label: this.formBuilder.control(item?.item_label ?? '', { validators: [Validators.required], nonNullable: true }),
      item_order: this.formBuilder.control(item?.item_order ?? 0, { nonNullable: true }),
      item_type: this.formBuilder.control<TaskItemType>(item?.item_type ?? 'checkbox', { nonNullable: true }),
      is_required: this.formBuilder.control(item?.is_required ?? true, { nonNullable: true })
    });
  }

  private resequenceSubtasks(): void {
    this.subtasks.controls.forEach((control, index) => {
      control.get('order_index')?.setValue(index, { emitEvent: false });
      this.resequenceItems(index);
    });
  }

  private resequenceItems(subtaskIndex: number): void {
    this.items(subtaskIndex).controls.forEach((control, index) => {
      control.get('item_order')?.setValue(index, { emitEvent: false });
    });
  }

  private loadUsersForSubtask(subtaskIndex: number): void {
    const subtask = this.subtasks.at(subtaskIndex);
    const roleKey = String(subtask.get('responsible_role_key')?.value ?? '');
    if (!roleKey || this.userOptionsByRole()[roleKey] || this.loadingRoles().includes(roleKey)) {
      return;
    }

    this.loadingRoles.update((roles) => [...roles, roleKey]);
    this.taskManagementService
      .listCrmUsersByRole(roleKey)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loadingRoles.update((roles) => roles.filter((item) => item !== roleKey)))
      )
      .subscribe({
        next: (users) => {
          this.userOptionsByRole.update((current) => ({ ...current, [roleKey]: users }));
          const selectedUserId = String(subtask.get('default_responsible_crm_user_id')?.value ?? '').trim();
          if (selectedUserId && !users.some((user) => user.crm_user_id === selectedUserId)) {
            subtask.get('default_responsible_crm_user_id')?.setValue(null);
          }
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
        }
      });
  }

  private serializeForm(): CreateTaskTemplateRequest {
    return {
      template_name: this.form.controls.template_name.getRawValue().trim(),
      description: this.form.controls.description.getRawValue()?.trim() || null,
      required_materials: this.requiredMaterials.controls
        .map((control) => ({
          product_id: String(control.get('product_id')?.value ?? '').trim(),
          quantity_required: Math.max(1, Number(control.get('quantity_required')?.value ?? 1)),
          notes: String(control.get('notes')?.value ?? '').trim() || null
        }))
        .filter((material) => material.product_id),
      subtasks: this.subtasks.controls.map((subtaskControl, subtaskIndex) => ({
        subtask_title: String(subtaskControl.get('subtask_title')?.value ?? '').trim(),
        subtask_description: String(subtaskControl.get('subtask_description')?.value ?? '').trim() || null,
        order_index: subtaskIndex,
        responsible_role_key: String(subtaskControl.get('responsible_role_key')?.value ?? ''),
        default_responsible_crm_user_id: String(subtaskControl.get('default_responsible_crm_user_id')?.value ?? '').trim() || null,
        close_comment_required: Boolean(subtaskControl.get('close_comment_required')?.value),
        next_assignment_policy: subtaskControl.get('next_assignment_policy')?.value as TaskAssignmentPolicy,
        items: (subtaskControl.get('items') as FormArray).controls.map((itemControl, itemIndex) => ({
          item_label: String(itemControl.get('item_label')?.value ?? '').trim(),
          item_order: itemIndex,
          item_type: itemControl.get('item_type')?.value as TaskItemType,
          is_required: Boolean(itemControl.get('is_required')?.value)
        }))
      }))
    };
  }
}