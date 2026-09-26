import { Component } from '@angular/core';
import { AuthService } from './services/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'frontend';
  sidebarContraida = localStorage.getItem('fiis_sidebar_contraida') === '1';
  constructor(public auth: AuthService, public router: Router) {}
  get mostrarPanel(): boolean { return this.auth.autenticado && !this.router.url.startsWith('/login'); }
  alternarSidebar(): void {
    this.sidebarContraida = !this.sidebarContraida;
    localStorage.setItem('fiis_sidebar_contraida', this.sidebarContraida ? '1' : '0');
  }
}
