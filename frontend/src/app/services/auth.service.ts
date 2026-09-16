import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

export type Perfil = 'ADMINISTRADOR' | 'ESTUDIANTE';

export interface UsuarioSesion {
  id_usuario: number;
  nombre_usuario: string;
  nombre_mostrar: string;
  cod_estudiante?: string;
  perfil_activo: Perfil;
  perfiles: Perfil[];
  nombres_perfiles: Record<string, string>;
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
  get esAdministrador(): boolean { return this.usuario?.perfil_activo === 'ADMINISTRADOR'; }
  get esEstudiante(): boolean { return this.usuario?.perfil_activo === 'ESTUDIANTE'; }
  nombrePerfil(perfil?: Perfil): string { return perfil ? (this.usuario?.nombres_perfiles?.[perfil] || (perfil === 'ADMINISTRADOR' ? 'Administrador' : 'Estudiante')) : ''; }

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

  rutaInicial(): string { return this.esEstudiante ? '/matricula' : '/catalog'; }

  private saveSession(response: LoginResponse): void {
    localStorage.setItem(this.storageKey, JSON.stringify(response));
    this.state.next(response.usuario);
  }

  private readSession(): UsuarioSesion | null {
    try { return JSON.parse(localStorage.getItem(this.storageKey) || 'null')?.usuario ?? null; }
    catch { localStorage.removeItem(this.storageKey); return null; }
  }
}
