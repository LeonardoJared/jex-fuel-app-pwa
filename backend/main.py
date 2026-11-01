import hashlib
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from decimal import Decimal
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db

# ===========================================================================
# CONFIGURACIÓN CRIPTOGRÁFICA: ARGON2id (Estándar OWASP)
# ===========================================================================

# Configuración siguiendo las recomendaciones de OWASP:
# - memory_cost: 65536 KiB (64 MiB de RAM por cálculo, neutraliza GPUs y ASICs)
# - time_cost: 3 iteraciones
# - parallelism: 4 hilos
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

def hash_password(password: str) -> str:
    """Genera hash Argon2id seguro."""
    return ph.hash(password)

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verifica contraseñas soportando:
    1. Argon2id (Nuevo estándar)
    2. Bcrypt (Transición)
    3. SHA-256 (Legacy)
    """
    
    if stored_hash.startswith("$argon2id$") or stored_hash.startswith("$argon2i$"):
        try:
            return ph.verify(stored_hash, plain_password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        try:
            pwd_bytes = plain_password.encode('utf-8')[:72]
            return bcrypt.checkpw(pwd_bytes, stored_hash.encode('utf-8'))
        except Exception:
            return False

    legacy_sha256 = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return legacy_sha256 == stored_hash

# ===========================================================================
# INICIALIZACIÓN DE FASTAPI
# ===========================================================================

app = FastAPI(
    title="JEX Technologies - API de Operaciones de Combustible",
    description="Backend transaccional en la nube para el control y despacho de Diesel B5",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================================
# MODELOS DE VALIDACIÓN (PYDANTIC)
# ===========================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class EquipmentDetail(BaseModel):
    item_number: int
    equipment_name: str
    equipment_code: str
    quantity_gln: Decimal = Field(..., gt=0, description="La cantidad en galones debe ser mayor a 0")

class FullLogsheet(BaseModel):
    log_date: str
    shift: str
    fuel_type: Optional[str] = None      
    supervisor_id: str                   
    operator_id: Optional[str] = None    
    truck_id: Optional[str] = None       
    remarks: Optional[str] = None
    supervisor_signature: Optional[str] = None
    operator_signature: Optional[str] = None
    equipments: List[EquipmentDetail] = []

class SupervisorCreate(BaseModel):
    full_name: str
    username: str
    password: str

class OperatorCreate(BaseModel):
    full_name: str

class TruckCreate(BaseModel):
    license_plate: str

# ===========================================================================
# MONITOREO
# ===========================================================================

@app.get("/health", tags=["Monitoreo"])
def health_check(db: Session = Depends(get_db)):
    """Verifica el estado de la API y la conexión activa con Neon PostgreSQL."""
    try:
        db.execute(text("SELECT 1;"))
        return {"status": "ok", "database": "Neon PostgreSQL conectado"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Base de datos Neon no disponible: {str(e)}"
        )

# ===========================================================================
# AUTENTICACIÓN
# ===========================================================================

@app.post("/api/login", tags=["Autenticación"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    query = text("""
        SELECT u.username, u.password_hash, u.role_id, u.supervisor_id, s.full_name, u.user_id 
        FROM users u
        LEFT JOIN supervisors s ON u.supervisor_id = s.supervisor_id
        WHERE LOWER(u.username) = LOWER(:username) AND u.is_active = TRUE
    """)
    result = db.execute(query, {"username": payload.username.strip()}).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo en el sistema JEX."
        )
    
    username = result[0]
    db_password_hash = result[1]
    role_id = result[2]
    supervisor_id = result[3]
    full_name = result[4]
    user_id = result[5]
    
    if not verify_password(payload.password, db_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta. Intente nuevamente."
        )
    
    if not db_password_hash.startswith("$argon2id$"):
        new_argon2_hash = hash_password(payload.password)
        db.execute(
            text("UPDATE users SET password_hash = :new_hash WHERE user_id = :uid"),
            {"new_hash": new_argon2_hash, "uid": user_id}
        )
        db.commit()

    return {
        "status": "success",
        "username": username,
        "role": role_id,
        "supervisor_id": supervisor_id,
        "name": full_name if full_name else "Administrador Central JEX"
    }

# ===========================================================================
# CATÁLOGOS BASE
# ===========================================================================

@app.get("/api/supervisors", tags=["Catálogos"])
def get_supervisors(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT supervisor_id, full_name FROM supervisors ORDER BY supervisor_id"))
    return [{"id": row.supervisor_id, "name": row.full_name} for row in result.fetchall()]

@app.get("/api/fuel-types", tags=["Catálogos"])
def get_fuel_types(db: Session = Depends(get_db)):
    """Obtiene los tipos de combustible registrados en la tabla fuel_types."""
    result = db.execute(text("SELECT fuel_type_id, description FROM fuel_types ORDER BY fuel_type_id"))
    return [{"id": row.fuel_type_id, "name": row.description} for row in result.fetchall()]

@app.get("/api/operators", tags=["Catálogos"])
def get_operators(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT operator_id, full_name FROM operators ORDER BY operator_id"))
    return [{"id": row.operator_id, "name": row.full_name} for row in result.fetchall()]

@app.get("/api/fuel-trucks", tags=["Catálogos"])
def get_fuel_trucks(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT truck_id, license_plate FROM fuel_trucks ORDER BY truck_id"))
    return [{"id": row.truck_id, "name": row.license_plate} for row in result.fetchall()]

# ===========================================================================
# OPERACIONES DE PLANILLA DE COMBUSTIBLE
# ===========================================================================

@app.post("/api/fuel-logsheet-complete", tags=["Operaciones"])
def create_full_logsheet(payload: FullLogsheet, db: Session = Depends(get_db)):
    try:
        query_header = text("""
            INSERT INTO fuel_log (log_date, shift, fuel_type, supervisor_id, operator_id, truck_id, remarks, supervisor_signature, operator_signature) 
            VALUES (CAST(:log_date AS DATE), :shift, :fuel_type, :supervisor_id, :operator_id, :truck_id, :remarks, :supervisor_signature, :operator_signature)
            RETURNING log_id;
        """)
        result = db.execute(query_header, {
            "log_date": payload.log_date, 
            "shift": payload.shift,
            "fuel_type": payload.fuel_type if payload.fuel_type and payload.fuel_type != "-" else None,
            "supervisor_id": payload.supervisor_id,
            "operator_id": payload.operator_id if payload.operator_id and payload.operator_id.strip() != "" else None,
            "truck_id": payload.truck_id if payload.truck_id and payload.truck_id.strip() != "" else None,
            "remarks": payload.remarks if payload.remarks else "Despacho Rutinario",
            "supervisor_signature": payload.supervisor_signature,
            "operator_signature": payload.operator_signature
        })
        log_id = result.fetchone()[0]
        
        if payload.equipments:
            query_detail = text("""
                INSERT INTO fuel_log_details (log_id, item_number, equipment_name, equipment_code, quantity_gln) 
                VALUES (:log_id, :item_number, :equipment_name, :equipment_code, :quantity_gln);
            """)
            for eq in payload.equipments:
                db.execute(query_detail, {
                    "log_id": log_id, 
                    "item_number": eq.item_number,
                    "equipment_name": eq.equipment_name.upper().strip(), 
                    "equipment_code": eq.equipment_code.upper().strip(), 
                    "quantity_gln": eq.quantity_gln
                })
                
        db.commit()
        return {"status": "success", "log_id": log_id, "rows_inserted": len(payload.equipments)}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error transaccional en la BD: {str(e)}"
        )

@app.get("/api/fuel-logs-history", tags=["Operaciones"])
def get_fuel_logs_history(db: Session = Depends(get_db)):
    query = text("""
        SELECT fl.log_id, fl.log_date, fl.shift, fl.fuel_type, s.full_name AS supervisor, 
               COALESCE(o.full_name, 'SIN OPERADOR') AS operator, 
               COALESCE(ft.license_plate, 'SIN CISTERNA') AS truck_plate, 
               fl.remarks
        FROM fuel_log fl
        INNER JOIN supervisors s ON fl.supervisor_id = s.supervisor_id
        LEFT JOIN operators o ON fl.operator_id = o.operator_id
        LEFT JOIN fuel_trucks ft ON fl.truck_id = ft.truck_id
        ORDER BY fl.log_id DESC;
    """)
    result = db.execute(query).fetchall()
    return [{
        "log_id": row.log_id, 
        "log_date": str(row.log_date), 
        "shift": row.shift, 
        "fuel_type": row.fuel_type,
        "supervisor": row.supervisor, 
        "operator": row.operator, 
        "truck_plate": row.truck_plate, 
        "remarks": row.remarks
    } for row in result]

# ===========================================================================
# REGISTRO Y ELIMINACIÓN DE ENTIDADES
# ===========================================================================

@app.post("/api/supervisors", tags=["Gestión"])
def create_supervisor(payload: SupervisorCreate, db: Session = Depends(get_db)):
    try:
        query_max = text("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(supervisor_id FROM 5) AS INTEGER)), 0) 
            FROM supervisors 
            WHERE supervisor_id LIKE 'SUP-%';
        """)
        last_num = db.execute(query_max).scalar()
        generated_id = f"SUP-{(last_num + 1):02d}"
        
        # Encriptación con Bcrypt
        secure_password_hash = hash_password(payload.password)
        
        db.execute(
            text("INSERT INTO supervisors (supervisor_id, full_name) VALUES (:id, :name);"), 
            {"id": generated_id, "name": payload.full_name.strip().upper()}
        )
        db.execute(
            text("""
                INSERT INTO users (username, password_hash, role_id, supervisor_id, is_active) 
                VALUES (:user, :hash, 'SUPERVISOR', :id, TRUE);
            """), 
            {"user": payload.username.strip().lower(), "hash": secure_password_hash, "id": generated_id}
        )
        db.commit()
        return {"status": "success", "message": f"Supervisor creado con código {generated_id}."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error en BD: {str(e)}")

@app.post("/api/operators", tags=["Gestión"])
def create_operator(payload: OperatorCreate, db: Session = Depends(get_db)):
    try:
        query_max = text("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(operator_id FROM 5) AS INTEGER)), 0) 
            FROM operators 
            WHERE operator_id LIKE 'OPE-%';
        """)
        last_num = db.execute(query_max).scalar()
        generated_id = f"OPE-{(last_num + 1):02d}"
        
        db.execute(
            text("INSERT INTO operators (operator_id, full_name) VALUES (:id, :name);"), 
            {"id": generated_id, "name": payload.full_name.strip().upper()}
        )
        db.commit()
        return {"status": "success", "message": f"Operador creado con código {generated_id}."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error: {str(e)}")

@app.post("/api/fuel-trucks", tags=["Gestión"])
def create_fuel_truck(payload: TruckCreate, db: Session = Depends(get_db)):
    try:
        query_max = text("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(truck_id FROM 5) AS INTEGER)), 0) 
            FROM fuel_trucks 
            WHERE truck_id LIKE 'CIS-%';
        """)
        last_num = db.execute(query_max).scalar()
        generated_id = f"CIS-{(last_num + 1):02d}"
        
        db.execute(
            text("INSERT INTO fuel_trucks (truck_id, license_plate) VALUES (:id, :plate);"), 
            {"id": generated_id, "plate": payload.license_plate.strip().upper()}
        )
        db.commit()
        return {"status": "success", "message": f"Cisterna registrada con código {generated_id}."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error: {str(e)}")

# ===========================================================================
# ELIMINACIÓN CON CONTROL DE INTEGRIDAD REFERENCIAL
# ===========================================================================

@app.delete("/api/supervisors/{supervisor_id}", tags=["Gestión"])
def delete_supervisor(supervisor_id: str, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM users WHERE supervisor_id = :id"), {"id": supervisor_id})
        db.execute(text("DELETE FROM supervisors WHERE supervisor_id = :id"), {"id": supervisor_id})
        db.commit()
        return {"status": "success", "message": "Supervisor eliminado correctamente."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el supervisor porque tiene registros históricos de combustible asociados."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al eliminar: {str(e)}")

@app.delete("/api/operators/{operator_id}", tags=["Gestión"])
def delete_operator(operator_id: str, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM operators WHERE operator_id = :id"), {"id": operator_id})
        db.commit()
        return {"status": "success", "message": "Operador eliminado correctamente."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el operador porque está asignado a planillas de combustible históricas."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al eliminar: {str(e)}")

@app.delete("/api/fuel-trucks/{truck_id}", tags=["Gestión"])
def delete_fuel_truck(truck_id: str, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM fuel_trucks WHERE truck_id = :id"), {"id": truck_id})
        db.commit()
        return {"status": "success", "message": "Cisterna eliminada correctamente."}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar la cisterna porque tiene despachos de combustible asociados."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al eliminar: {str(e)}")