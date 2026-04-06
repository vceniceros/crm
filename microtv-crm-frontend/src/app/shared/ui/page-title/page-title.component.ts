import { Component, input } from '@angular/core';

@Component({
  selector: 'app-page-title',
  standalone: true,
  templateUrl: './page-title.component.html',
  styleUrl: './page-title.component.scss'
})
export class PageTitleComponent {
  readonly eyebrow = input('Estado general');
  readonly title = input.required<string>();
  readonly subtitle = input.required<string>();
}