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
  constructor(public auth: AuthService, public router: Router) {}
  get mostrarPanel(): boolean { return this.auth.autenticado && !this.router.url.startsWith('/login'); }
}
