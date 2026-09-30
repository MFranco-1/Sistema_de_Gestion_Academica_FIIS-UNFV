import { of } from 'rxjs';
import { MatriculaComponent } from './matricula.component';
import { ApiService, Estudiante, MatriculaResumen, OfertaCurso } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

describe('MatriculaComponent', () => {
  let component: MatriculaComponent;
  let api: jasmine.SpyObj<ApiService>;

  const oferta = (id: number, curso: string, seccion: string, creditos = 3): OfertaCurso => ({
    id_oferta: id,
    cod_periodo: '2027-I',
    corr_pe: 1,
    cod_curso: curso,
    den_curso: `Curso ${curso}`,
    semestre: 5,
    cred: creditos,
    cod_seccion: seccion,
    vacantes: 35,
    matriculados: 0,
    vacantes_disponibles: 35,
    disponible: true,
    motivo: 'Disponible',
    horario_resumen: '',
    horarios: [],
    docente_nombre: 'Docente de prueba'
  });

  beforeEach(() => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['guardarPrematricula']);
    component = new MatriculaComponent(api, {} as AuthService);
    component.estudiante = {
      cod_estudiante: '2024035774',
      dni: '12345678',
      apellidos_nombres: 'Estudiante de Prueba',
      correo: '2024035774@unfv.edu.pe',
      cod_fac: 1,
      cod_esc: 1,
      corr_pe: 1,
      ciclo_actual: 5,
      estado: 'ACTIVO',
      den_plan: 'Plan de Estudios 2019',
      anio_ingreso: 2024,
      creditos_aprobados: 88,
      creditos_matriculados: 0
    } as Estudiante;
    component.periodoSeleccionado = '2027-I';
  });

  it('mantiene una sola sección seleccionada por curso', () => {
    component.ofertas = [oferta(1, 'P19-31', 'A'), oferta(2, 'P19-31', 'B')];

    component.alternarOferta(1, true);
    component.alternarOferta(2, true);

    expect([...component.seleccionadas]).toEqual([2]);
  });

  it('ubica a un alumno sin historial en el periodo correspondiente a su ingreso', () => {
    component.estudiante!.ciclo_actual = 1;
    (component as any).periodosBase = [
      { cod_periodo: '2024-I', den_periodo: 'Semestre académico 2024-I', anio: 2024, tipo_periodo: 'I', fecha_inicio: '2024-03-18', fecha_fin: '2024-07-19', activo: false },
      { cod_periodo: '2026-II', den_periodo: 'Semestre académico 2026-II', anio: 2026, tipo_periodo: 'II', fecha_inicio: '2026-08-17', fecha_fin: '2026-12-18', activo: true },
      { cod_periodo: '2027-I', den_periodo: 'Semestre académico 2027-I', anio: 2027, tipo_periodo: 'I', fecha_inicio: '2027-03-15', fecha_fin: '2027-07-16', activo: false }
    ];
    (component as any).historialCargado = true;
    spyOn(component, 'cargarOfertas');

    (component as any).actualizarPeriodosMatricula();

    expect(component.periodoSeleccionado).toBe('2024-I');
    expect(component.periodos.map(periodo => periodo.cod_periodo)).toContain('2024-I');
  });

  it('ofrece el verano siguiente cuando queda un curso desaprobado', () => {
    component.estudiante!.ciclo_actual = 3;
    (component as any).periodosBase = [
      { cod_periodo: '2024-II', den_periodo: 'Semestre académico 2024-II', anio: 2024, tipo_periodo: 'II', fecha_inicio: '2024-08-19', fecha_fin: '2024-12-21', activo: false },
      { cod_periodo: '2025-V', den_periodo: 'Ciclo de verano 2025', anio: 2025, tipo_periodo: 'VERANO', fecha_inicio: '2025-01-06', fecha_fin: '2025-02-28', activo: false },
      { cod_periodo: '2025-I', den_periodo: 'Semestre académico 2025-I', anio: 2025, tipo_periodo: 'I', fecha_inicio: '2025-03-17', fecha_fin: '2025-07-19', activo: false }
    ];
    component.matriculas = [{
      id_matricula: 2, cod_estudiante: '2024035774', cod_periodo: '2024-II', ciclo_matricula: 2,
      fecha_matricula: '2024-08-19', estado: 'CERRADA', total_creditos: 22,
      constancia_disponible: false,
      detalles: [{
        id_matricula: 2, id_oferta: 20, cod_periodo: '2024-II', cod_curso: 'P19-09',
        den_curso: 'Inglés II', semestre: 2, cod_seccion: 'A', docente_nombre: 'Docente',
        cred: 1, nota_final: 8, resultado: 'DESAPROBADO'
      }]
    }];
    (component as any).historialCargado = true;
    spyOn(component, 'cargarOfertas');

    (component as any).actualizarPeriodosMatricula();

    expect(component.periodos.map(periodo => periodo.cod_periodo)).toEqual(['2025-V', '2025-I']);
    expect(component.periodoSeleccionado).toBe('2025-V');
  });

  it('filtra los cursos al presionar una sección', () => {
    component.ofertas = [oferta(1, 'P19-31', 'A'), oferta(2, 'P19-32', 'B')];

    component.seleccionarSeccion('B');

    expect(component.ofertasFiltradas.map(item => item.id_oferta)).toEqual([2]);
  });

  it('guarda la prematrícula seleccionada', () => {
    api.guardarPrematricula.and.returnValue(of({ mensaje: 'Prematrícula guardada.' }));
    component.seleccionadas.add(3);

    component.guardarPrematricula();

    expect(api.guardarPrematricula).toHaveBeenCalledWith('2024035774', {
      cod_periodo: '2027-I',
      ofertas: [3]
    });
    expect(component.mensaje).toBe('Prematrícula guardada.');
  });

  it('solo abre la confirmación cuando la matrícula está habilitada', () => {
    component.seleccionadas.add(1);
    component.accesoMatricula = {
      cod_periodo: '2027-I', ciclo: 5, fase: 'CERRADA', habilitado: false,
      mensaje: '', total_estudiantes: 0, limite_tercio: 0, tercio_superior: false,
      sancion_trica: false, cursos_trica: [], periodos_suspension: []
    };

    component.abrirConfirmacion();
    expect(component.confirmando).toBeFalse();

    component.accesoMatricula.habilitado = true;
    component.abrirConfirmacion();
    expect(component.confirmando).toBeTrue();
  });

  it('genera la constancia cargando jsPDF bajo demanda', async () => {
    const lienzo = document.createElement('canvas');
    lienzo.width = 2;
    lienzo.height = 2;
    const imagen = lienzo.toDataURL('image/png');
    spyOn<any>(component, 'cargarImagen').and.resolveTo(imagen);
    const matricula: MatriculaResumen = {
      id_matricula: 10,
      cod_estudiante: '2024035774',
      cod_periodo: '2027-I',
      ciclo_matricula: 5,
      fecha_matricula: '2027-03-15',
      estado: 'REGISTRADA',
      total_creditos: 3,
      constancia_disponible: false,
      detalles: [{
        id_matricula: 10, id_oferta: 1, cod_periodo: '2027-I', cod_curso: 'P19-31',
        den_curso: 'Programación aplicada II', semestre: 5, cod_seccion: 'A',
        docente_nombre: 'Docente de prueba', cred: 3, resultado: 'MATRICULADO'
      }]
    };

    const pdf = await (component as any).crearDocumentoPdf(matricula, imagen);

    expect((pdf.output('arraybuffer') as ArrayBuffer).byteLength).toBeGreaterThan(1000);
  });
});
