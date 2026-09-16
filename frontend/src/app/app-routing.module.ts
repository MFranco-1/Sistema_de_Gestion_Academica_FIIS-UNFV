import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CatalogComponent } from './pages/catalog/catalog.component';
import { DocentesComponent } from './pages/docentes/docentes.component';
import { MantenimientoComponent } from './pages/mantenimiento/mantenimiento.component';
import { MatriculaComponent } from './pages/matricula/matricula.component';
import { LoginComponent } from './pages/login/login.component';
import { AdminGuard, AuthGuard, LoginGuard, StudentGuard } from './services/auth.guard';
import { UsuariosComponent } from './pages/usuarios/usuarios.component';
import { PerfilesComponent } from './pages/perfiles/perfiles.component';
import { GestionMatriculasComponent } from './pages/gestion-matriculas/gestion-matriculas.component';

const routes: Routes = [
  { path: 'login', component: LoginComponent, canActivate: [LoginGuard] },
  { path: 'catalog', component: CatalogComponent, canActivate: [AuthGuard, AdminGuard], data: { permiso: 'GESTION_CURRICULAR' } },
  { path: 'docentes', component: DocentesComponent, canActivate: [AuthGuard, AdminGuard], data: { permiso: 'PLANA_DOCENTE' } },
  { path: 'mantenimiento', component: MantenimientoComponent, canActivate: [AuthGuard, AdminGuard], data: { permisos: ['MANTENIMIENTO_ACADEMICO', 'GESTION_ESTUDIANTES'] } },
  { path: 'admin/usuarios', component: UsuariosComponent, canActivate: [AuthGuard, AdminGuard], data: { permiso: 'GESTION_USUARIOS' } },
  { path: 'admin/perfiles', component: PerfilesComponent, canActivate: [AuthGuard, AdminGuard], data: { permiso: 'GESTION_PERFILES' } },
  { path: 'admin/matriculas', component: GestionMatriculasComponent, canActivate: [AuthGuard, AdminGuard], data: { permiso: 'GESTION_MATRICULAS' } },
  { path: 'matricula', component: MatriculaComponent, canActivate: [AuthGuard, StudentGuard] },
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: '**', redirectTo: '/login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {
    anchorScrolling: 'enabled',
    scrollPositionRestoration: 'enabled'
  })],
  exports: [RouterModule]
})
export class AppRoutingModule { }
