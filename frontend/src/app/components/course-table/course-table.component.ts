import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Curso } from '../../services/api.service';

@Component({
  selector: 'app-course-table',
  templateUrl: './course-table.component.html',
  styleUrls: ['./course-table.component.css']
})
export class CourseTableComponent {
  @Input() cursos: Curso[] = [];
  @Output() verDetalle = new EventEmitter<Curso>();

  getRomanSemester(num: number): string {
    const romanMap: { [key: number]: string } = {
      1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
      6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X'
    };
    return romanMap[num] || num.toString();
  }
}
