import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CatalogComponent } from './pages/catalog/catalog.component';
import { DocentesComponent } from './pages/docentes/docentes.component';
import { MantenimientoComponent } from './pages/mantenimiento/mantenimiento.component';

const routes: Routes = [
  { path: 'catalog', component: CatalogComponent },
  { path: 'docentes', component: DocentesComponent },
  { path: 'mantenimiento', component: MantenimientoComponent },
  { path: '', redirectTo: '/catalog', pathMatch: 'full' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {
    anchorScrolling: 'enabled',
    scrollPositionRestoration: 'enabled'
  })],
  exports: [RouterModule]
})
export class AppRoutingModule { }
