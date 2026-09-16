import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, RouterStateSnapshot } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}
  canActivate(_: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
    if (this.auth.autenticado) return true;
    this.router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
    return false;
  }
}

@Injectable({ providedIn: 'root' })
export class AdminGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}
  canActivate(route: ActivatedRouteSnapshot): boolean {
    const permiso = route.data['permiso'] as string;
    const permisos = (route.data['permisos'] as string[] | undefined) || [];
    if ((!permiso && !permisos.length) || (permiso && this.auth.puede(permiso)) || this.auth.puedeAlguno(...permisos)) return true;
    this.router.navigate([this.auth.rutaInicial()]);
    return false;
  }
}

@Injectable({ providedIn: 'root' })
export class StudentGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}
  canActivate(): boolean {
    if (this.auth.puede('MATRICULA_PROPIA')) return true;
    this.router.navigate([this.auth.rutaInicial()]);
    return false;
  }
}
