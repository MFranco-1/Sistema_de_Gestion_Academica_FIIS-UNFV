import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CatalogComponent } from './pages/catalog/catalog.component';
import { DocentesComponent } from './pages/docentes/docentes.component';
import { MantenimientoComponent } from './pages/mantenimiento/mantenimiento.component';
import { MatriculaComponent } from './pages/matricula/matricula.component';
import { LoginComponent } from './pages/login/login.component';
import { AdminGuard, AuthGuard, StudentGuard } from './services/auth.guard';
import { UsuariosComponent } from './pages/usuarios/usuarios.component';
import { PerfilesComponent } from './pages/perfiles/perfiles.component';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'catalog', component: CatalogComponent, canActivate: [AuthGuard, AdminGuard] },
  { path: 'docentes', component: DocentesComponent, canActivate: [AuthGuard, AdminGuard] },
  { path: 'mantenimiento', component: MantenimientoComponent, canActivate: [AuthGuard, AdminGuard] },
  { path: 'admin/usuarios', component: UsuariosComponent, canActivate: [AuthGuard, AdminGuard] },
  { path: 'admin/perfiles', component: PerfilesComponent, canActivate: [AuthGuard, AdminGuard] },
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
