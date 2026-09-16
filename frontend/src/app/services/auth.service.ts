import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

export type Perfil = string;

export interface UsuarioSesion {
  id_usuario: number;
  nombre_usuario: string;
  nombre_mostrar: string;
  cod_estudiante?: string;
  perfil_activo: Perfil;
  perfiles: Perfil[];
  nombres_perfiles: Record<string, string>;
  permisos: string[];
}

interface LoginResponse { token: string; usuario: UsuarioSesion; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiUrl = environment.apiUrl;
  private readonly storageKey = 'fiis_sesion';
  private readonly state = new BehaviorSubject<UsuarioSesion | null>(this.readSession());
  usuario$ = this.state.asObservable();

  constructor(private http: HttpClient, private router: Router) {}

  get usuario(): UsuarioSesion | null { return this.state.value; }
  get token(): string | null {
    const stored = localStorage.getItem(this.storageKey);
    return stored ? JSON.parse(stored).token : null;
  }
  get autenticado(): boolean { return !!this.usuario && !!this.token; }
  get esAdministrador(): boolean { return this.puede('GESTION_USUARIOS'); }
  get esEstudiante(): boolean { return this.puede('MATRICULA_PROPIA'); }
  puede(permiso: string): boolean { return !!this.usuario?.permisos?.includes(permiso); }
  puedeAlguno(...permisos: string[]): boolean { return permisos.some(permiso => this.puede(permiso)); }
  nombrePerfil(perfil?: Perfil): string { return perfil ? (this.usuario?.nombres_perfiles?.[perfil] || perfil) : ''; }

  login(nombre_usuario: string, clave: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/login`, { nombre_usuario, clave }).pipe(
      tap(response => this.saveSession(response))
    );
  }

  cambiarPerfil(perfil: Perfil): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/cambiar-perfil`, { perfil }).pipe(
      tap(response => this.saveSession(response))
    );
  }

  logout(): void {
    localStorage.removeItem(this.storageKey);
    this.state.next(null);
    this.router.navigate(['/login']);
  }

  rutaInicial(): string {
    if (this.puede('MATRICULA_PROPIA')) return '/matricula';
    if (this.puede('GESTION_CURRICULAR')) return '/catalog';
    if (this.puede('GESTION_MATRICULAS')) return '/admin/matriculas';
    if (this.puede('GESTION_USUARIOS')) return '/admin/usuarios';
    if (this.puede('GESTION_PERFILES')) return '/admin/perfiles';
    return '/login';
  }

  private saveSession(response: LoginResponse): void {
    localStorage.setItem(this.storageKey, JSON.stringify(response));
    this.state.next(response.usuario);
  }

  private readSession(): UsuarioSesion | null {
    try { return JSON.parse(localStorage.getItem(this.storageKey) || 'null')?.usuario ?? null; }
    catch { localStorage.removeItem(this.storageKey); return null; }
  }
}
