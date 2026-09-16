import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService, Perfil } from '../../services/auth.service';

@Component({
  selector: 'app-topbar',
  templateUrl: './topbar.component.html',
  styleUrls: ['./topbar.component.css']
})
export class TopbarComponent {
  menuAbierto = false;
  cambiando = false;
  constructor(public auth: AuthService, private router: Router) {}
  cambiarPerfil(perfil: Perfil): void {
    if (perfil === this.auth.usuario?.perfil_activo) { this.menuAbierto = false; return; }
    this.cambiando = true;
    this.auth.cambiarPerfil(perfil).subscribe({
      next: () => { this.menuAbierto = false; this.cambiando = false; this.router.navigate([this.auth.rutaInicial()]); },
      error: () => { this.cambiando = false; }
    });
  }
}
