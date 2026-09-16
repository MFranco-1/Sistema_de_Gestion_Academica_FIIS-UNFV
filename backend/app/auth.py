import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.database import get_db


PERFIL_ADMIN = "ADMINISTRADOR"
PERFIL_ESTUDIANTE = "ESTUDIANTE"
PERMISOS_VALIDOS = {
    "GESTION_CURRICULAR", "PLANA_DOCENTE", "MANTENIMIENTO_ACADEMICO",
    "GESTION_ESTUDIANTES", "GESTION_USUARIOS", "GESTION_PERFILES",
    "MATRICULA_PROPIA", "GESTION_MATRICULAS",
}
PERMISOS_ADMIN = sorted(PERMISOS_VALIDOS - {"MATRICULA_PROPIA"})
PERMISOS_ESTUDIANTE = ["MATRICULA_PROPIA"]
security = HTTPBearer(auto_error=False)


@dataclass
class UsuarioActual:
    id_usuario: int
    nombre_usuario: str
    nombre_mostrar: str
    cod_estudiante: str | None
    perfil_activo: str
    perfiles: list[str]
    nombres_perfiles: dict[str, str]
    permisos: list[str]


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _secret() -> bytes:
    return os.getenv("AUTH_SECRET", "fiis-unfv-cambiar-en-produccion").encode()


def create_token(user: models.Usuario, perfil_activo: str) -> str:
    payload = {"sub": user.id_usuario, "perfil": perfil_activo, "exp": int(time.time()) + 28800}
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64encode(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def _decode_token(token: str) -> dict:
    try:
        body, signature = token.split(".", 1)
        expected = _b64encode(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(_b64decode(body))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="La sesión no es válida o ha expirado.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> UsuarioActual:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Debe iniciar sesión.")
    payload = _decode_token(credentials.credentials)
    user = db.query(models.Usuario).filter_by(id_usuario=payload["sub"], activo=True).first()
    if not user:
        raise HTTPException(status_code=401, detail="El usuario no está disponible.")
    perfiles = sorted(perfil.codigo for perfil in user.perfiles)
    perfil_activo = payload.get("perfil")
    if perfil_activo not in perfiles:
        raise HTTPException(status_code=403, detail="El perfil activo ya no está asignado.")
    perfil_obj = next(perfil for perfil in user.perfiles if perfil.codigo == perfil_activo)
    permisos = sorted({item for item in perfil_obj.permisos.split(",") if item})
    return UsuarioActual(
        user.id_usuario, user.nombre_usuario, user.nombre_mostrar,
        user.cod_estudiante, perfil_activo, perfiles,
        {perfil.codigo: perfil.nombre for perfil in user.perfiles},
        permisos,
    )


def require_admin(user: UsuarioActual = Depends(get_current_user)) -> UsuarioActual:
    if "GESTION_USUARIOS" not in user.permisos:
        raise HTTPException(status_code=403, detail="El perfil activo no tiene permiso para esta operación.")
    return user


def require_student(user: UsuarioActual = Depends(get_current_user)) -> UsuarioActual:
    if "MATRICULA_PROPIA" not in user.permisos:
        raise HTTPException(status_code=403, detail="El perfil activo no permite matrícula personal.")
    if not user.cod_estudiante:
        raise HTTPException(status_code=403, detail="El usuario no está vinculado con un estudiante.")
    return user


def require_permission(permission: str):
    def dependency(user: UsuarioActual = Depends(get_current_user)) -> UsuarioActual:
        if permission not in user.permisos:
            raise HTTPException(
                status_code=403,
                detail=f"El perfil activo no tiene el permiso {permission}.",
            )
        return user
    return dependency


def require_any_permission(*permissions: str):
    def dependency(user: UsuarioActual = Depends(get_current_user)) -> UsuarioActual:
        if not set(permissions).intersection(user.permisos):
            raise HTTPException(
                status_code=403,
                detail="El perfil activo no tiene permisos para esta operación.",
            )
        return user
    return dependency


def ensure_security_data(db: Session) -> None:
    perfiles = {}
    defaults = (
        (PERFIL_ADMIN, "Administrador", PERMISOS_ADMIN),
        (PERFIL_ESTUDIANTE, "Estudiante", PERMISOS_ESTUDIANTE),
    )
    for codigo, nombre, permisos_default in defaults:
        perfil = db.query(models.Perfil).filter_by(codigo=codigo).first()
        if not perfil:
            perfil = models.Perfil(
                codigo=codigo, nombre=nombre, permisos=",".join(permisos_default),
            )
            db.add(perfil)
            db.flush()
        elif not perfil.permisos:
            perfil.permisos = ",".join(permisos_default)
        perfiles[codigo] = perfil
    admin_name = os.getenv("ADMIN_USERNAME", "admin").strip().lower()
    configured_password = os.getenv("ADMIN_PASSWORD")
    admin = db.query(models.Usuario).filter_by(nombre_usuario=admin_name).first()
    if not admin:
        admin = models.Usuario(
            nombre_usuario=admin_name,
            clave_hash=hash_password(configured_password or "Admin123*"),
            nombre_mostrar="Administrador FIIS",
            activo=True,
        )
        admin.perfiles = [perfiles[PERFIL_ADMIN]]
        db.add(admin)
    elif configured_password:
        admin.clave_hash = hash_password(configured_password)
    db.commit()


def ensure_student_user(db: Session, student: models.Estudiante) -> None:
    user = db.query(models.Usuario).filter_by(cod_estudiante=student.cod_estudiante).first()
    if user:
        user.nombre_mostrar = student.apellidos_nombres
        return
    perfil = db.query(models.Perfil).filter_by(codigo=PERFIL_ESTUDIANTE).one()
    username = student.cod_estudiante.lower()
    if db.query(models.Usuario).filter_by(nombre_usuario=username).first():
        username = student.correo.lower()
    user = models.Usuario(
        nombre_usuario=username,
        clave_hash=hash_password(student.dni),
        nombre_mostrar=student.apellidos_nombres,
        cod_estudiante=student.cod_estudiante,
        activo=True,
    )
    user.perfiles = [perfil]
    db.add(user)
