import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HTTP_INTERCEPTORS, HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { SidebarComponent } from './components/sidebar/sidebar.component';
import { TopbarComponent } from './components/topbar/topbar.component';
import { CatalogComponent } from './pages/catalog/catalog.component';
import { CourseTableComponent } from './components/course-table/course-table.component';
import { DocentesComponent } from './pages/docentes/docentes.component';
import { MantenimientoComponent } from './pages/mantenimiento/mantenimiento.component';
import { MatriculaComponent } from './pages/matricula/matricula.component';
import { LoginComponent } from './pages/login/login.component';
import { AuthInterceptor } from './services/auth.interceptor';
import { UsuariosComponent } from './pages/usuarios/usuarios.component';
import { PerfilesComponent } from './pages/perfiles/perfiles.component';
import { GestionMatriculasComponent } from './pages/gestion-matriculas/gestion-matriculas.component';

@NgModule({
  declarations: [
    AppComponent,
    SidebarComponent,
    TopbarComponent,
    CatalogComponent,
    CourseTableComponent,
    DocentesComponent,
    MantenimientoComponent,
    MatriculaComponent,
    LoginComponent,
    UsuariosComponent,
    PerfilesComponent,
    GestionMatriculasComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    FormsModule
  ],
  providers: [{ provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }],
  bootstrap: [AppComponent]
})
export class AppModule { }
