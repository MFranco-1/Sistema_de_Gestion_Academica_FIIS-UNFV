import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ApiService, BloqueHorario, Estudiante, MatriculaResumen, OfertaCurso, PeriodoAcademico } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({ selector: 'app-matricula', templateUrl: './matricula.component.html', styleUrls: ['./matricula.component.css'] })
export class MatriculaComponent implements OnInit {
  estudiante?: Estudiante;
  periodos: PeriodoAcademico[] = [];
  ofertas: OfertaCurso[] = [];
  matriculas: MatriculaResumen[] = [];
  seleccionadas = new Set<number>();
  periodoSeleccionado = '';
  mensaje = '';
  error = '';
  cargando = true;
  fotoPerfil = '';
  readonly diasHorario = ['LUNES','MARTES','MIERCOLES','JUEVES','VIERNES','SABADO'];

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.cargarFicha();
    this.api.getPeriodos().subscribe({
      next: data => {
        this.periodos = data;
        this.periodoSeleccionado = data.find(p => p.activo)?.cod_periodo ?? data[0]?.cod_periodo ?? '';
        this.cargarOfertas();
      },
      error: error => this.mostrarError(error)
    });
  }

  cargarFicha(): void {
    this.api.getMiEstudiante().subscribe({
      next: estudiante => {
        this.estudiante = estudiante;
        this.fotoPerfil = localStorage.getItem(`fiis_foto_${estudiante.cod_estudiante}`) || '';
        this.cargando = false;
        this.cargarOfertas();
      },
      error: error => { this.cargando = false; this.mostrarError(error); }
    });
  }

  cargarOfertas(): void {
    if (!this.estudiante || !this.periodoSeleccionado) return;
    this.seleccionadas.clear();
    this.api.getOfertasEstudiante(this.estudiante.cod_estudiante, this.periodoSeleccionado).subscribe({
      next: data => {
        this.ofertas = data;
        this.api.getPrematricula(this.estudiante!.cod_estudiante).subscribe(guardada => {
          if (guardada.cod_periodo === this.periodoSeleccionado) {
            const validas = new Set(data.map(item => item.id_oferta));
            this.seleccionadas = new Set(guardada.ofertas.filter(id => validas.has(id)));
          }
        });
      },
      error: error => this.mostrarError(error)
    });
  }

  cargarHistorial(): void {
    if (!this.estudiante) return;
    this.api.getMatriculasEstudiante(this.estudiante.cod_estudiante).subscribe({
      next: data => this.matriculas = data,
      error: error => this.mostrarError(error)
    });
  }

  alternarOferta(id: number, seleccionada: boolean): void {
    if (seleccionada) {
      const elegida = this.ofertas.find(item => item.id_oferta === id);
      if (elegida) this.ofertas.filter(item => item.cod_curso === elegida.cod_curso).forEach(item => this.seleccionadas.delete(item.id_oferta));
      this.seleccionadas.add(id);
    } else this.seleccionadas.delete(id);
  }

  guardarPrematricula(): void {
    if (!this.estudiante) return;
    this.mensaje = ''; this.error = '';
    this.api.guardarPrematricula(this.estudiante.cod_estudiante, { cod_periodo: this.periodoSeleccionado, ofertas: [...this.seleccionadas] }).subscribe({
      next: data => this.mensaje = data.mensaje,
      error: error => this.mostrarError(error)
    });
  }

  bloquesDia(dia: string): { oferta: OfertaCurso; bloque: BloqueHorario }[] {
    const resultado: { oferta: OfertaCurso; bloque: BloqueHorario }[] = [];
    this.ofertas.filter(o => this.seleccionadas.has(o.id_oferta)).forEach(oferta => oferta.horarios.filter(b => b.dia_semana === dia).forEach(bloque => resultado.push({ oferta, bloque })));
    return resultado.sort((a,b) => a.bloque.hora_inicio.localeCompare(b.bloque.hora_inicio));
  }

  get crucePrematricula(): string {
    const bloques = this.diasHorario.flatMap(dia => this.bloquesDia(dia));
    const minutos = (v: string) => { const [h,m] = v.slice(0,5).split(':').map(Number); return h*60+m; };
    for (let i=0;i<bloques.length;i++) for (let j=i+1;j<bloques.length;j++) {
      const a=bloques[i], b=bloques[j];
      if (a.bloque.dia_semana === b.bloque.dia_semana && a.oferta.cod_curso !== b.oferta.cod_curso && minutos(a.bloque.hora_inicio)<minutos(b.bloque.hora_fin) && minutos(a.bloque.hora_fin)>minutos(b.bloque.hora_inicio)) return `${a.oferta.cod_curso} se cruza con ${b.oferta.cod_curso} el ${a.bloque.dia_semana.toLowerCase()}.`;
    }
    return '';
  }

  registrarMatricula(): void {
    if (!this.estudiante || !this.seleccionadas.size) return;
    this.mensaje = ''; this.error = '';
    this.api.crearMatricula(this.estudiante.cod_estudiante, this.periodoSeleccionado, [...this.seleccionadas]).subscribe({
      next: () => { this.mensaje = 'Matrícula registrada correctamente.'; this.cargarFicha(); },
      error: error => this.mostrarError(error)
    });
  }

  semestreRomano(numero: number): string { return ['I','II','III','IV','V','VI','VII','VIII','IX','X'][numero - 1]; }
  get iniciales(): string {
    return (this.estudiante?.apellidos_nombres || '').split(/[ ,]+/).filter(Boolean).slice(0, 2).map(parte => parte[0]).join('').toUpperCase();
  }
  seleccionarFoto(event: Event): void {
    const archivo = (event.target as HTMLInputElement).files?.[0];
    if (!archivo || !archivo.type.startsWith('image/')) return;
    if (archivo.size > 1024 * 1024) { this.error = 'La foto debe pesar como máximo 1 MB.'; return; }
    const lector = new FileReader();
    lector.onload = () => {
      this.fotoPerfil = String(lector.result);
      if (this.estudiante) localStorage.setItem(`fiis_foto_${this.estudiante.cod_estudiante}`, this.fotoPerfil);
    };
    lector.readAsDataURL(archivo);
  }
  get creditosSeleccionados(): number {
    return this.ofertas.filter(item => this.seleccionadas.has(item.id_oferta)).reduce((total, item) => total + item.cred, 0);
  }
  private mostrarError(error: HttpErrorResponse): void {
    this.mensaje = '';
    const detalle = error.error?.detail;
    this.error = typeof detalle === 'string' ? detalle : 'No se pudo completar la operación.';
  }
}
