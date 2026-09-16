import { Component } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../services/auth.service';

@Component({ selector: 'app-login', templateUrl: './login.component.html', styleUrls: ['./login.component.css'] })
export class LoginComponent {
  nombreUsuario = '';
  clave = '';
  cargando = false;
  error = '';
  mostrarClave = false;

  constructor(private auth: AuthService, private router: Router, private route: ActivatedRoute) {
    if (auth.autenticado) this.router.navigate([auth.rutaInicial()]);
  }

  ingresar(): void {
    this.error = '';
    this.cargando = true;
    this.auth.login(this.nombreUsuario, this.clave).subscribe({
      next: () => {
        const requested = this.route.snapshot.queryParamMap.get('returnUrl');
        this.router.navigateByUrl(requested || this.auth.rutaInicial());
      },
      error: (error: HttpErrorResponse) => {
        this.cargando = false;
        this.error = error.error?.detail || 'No se pudo iniciar sesión.';
      }
    });
  }
}
