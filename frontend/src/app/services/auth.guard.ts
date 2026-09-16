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
  canActivate(): boolean {
    if (this.auth.esAdministrador) return true;
    this.router.navigate(['/matricula']);
    return false;
  }
}

@Injectable({ providedIn: 'root' })
export class StudentGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}
  canActivate(): boolean {
    if (this.auth.esEstudiante) return true;
    this.router.navigate(['/catalog']);
    return false;
  }
}
