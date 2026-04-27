export interface TemplateSubtask {
  id: string;
  title: string;
  children: TemplateSubtask[];
}