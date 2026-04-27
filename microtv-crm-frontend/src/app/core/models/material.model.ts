export interface MaterialOption {
  id: number | string;
  name: string;
  unit?: string;
}

export interface TemplateRequiredMaterial {
  materialId: number | string;
  name: string;
  quantity: number;
  unit?: string;
}

export interface MaterialsMockData {
  materials: MaterialOption[];
}