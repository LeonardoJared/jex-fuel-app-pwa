from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text
import hashlib

# Importamos la dependencia de conexión de tu database.py local
from database import get_db

app = FastAPI(
    title="JEX Technologies - API de Operaciones de Combustible",
    description="Backend transaccional en la nube para el control de Diesel B5",
    version="1.0.0"
)

# Configuración de CORS para permitir enlaces con PWA y Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================================
# MODELOS DE PETICIÓN Y VALIDACIÓN (PYDANTIC)
# ===========================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class EquipmentDetail(BaseModel):
    item_number: int
    equipment_name: str
    equipment_code: str
    quantity_gln: Decimal  # Garantiza precisión exacta sin errores flotantes

class FullLogsheet(BaseModel):
    log_date: str
    shift: str
    fuel_type: Optional[str] = None      
    supervisor_id: str                   
    operator_id: Optional[str] = None    
    truck_id: Optional[str] = None       
    remarks: Optional[str] = None
    equipments: List[EquipmentDetail]

class SupervisorCreate(BaseModel):
    full_name: str
    username: str
    password: str

class OperatorCreate(BaseModel):
    full_name: str

class TruckCreate(BaseModel):
    license_plate: str

# ===========================================================================
# ENDPOINTS DE AUTENTICACIÓN Y CATÁLOGOS
# ===========================================================================

@app.post("/api/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    query = text("""
        SELECT u.username, u.password_hash, u.role_id, u.supervisor_id, s.full_name 
        FROM users u
        LEFT JOIN supervisors s ON u.supervisor_id = s.supervisor_id
        WHERE u.username = :username AND u.is_active = TRUE
    """)
    result = db.execute(query, {"username": payload.username}).fetchone()
    
    if not result:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo en el sistema JEX.")
    
    # Desempaquetado explícito con el orden exacto del SELECT SQL
    username = result[0]
    db_password_hash = result[1]
    role_id = result[2]
    supervisor_id = result[3]  # Mapea correctamente con u.supervisor_id
    full_name = result[4]      # Mapea correctamente con s.full_name
    
    input_password_hash = hashlib.sha256(payload.password.encode('utf-8')).hexdigest()
    
    if input_password_hash != db_password_hash:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta. Intente nuevamente.")
    
    return {
        "status": "success",
        "username": username,
        "role": role_id,
        "supervisor_id": supervisor_id,
        "name": full_name if full_name else "Administrador Central JEX"
    }


@app.get("/api/supervisors")
def get_supervisors(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT supervisor_id, full_name FROM supervisors ORDER BY supervisor_id"))
    return [{"id": row.supervisor_id, "name": row.full_name} for row in result.fetchall()]

@app.get("/api/operators")
def get_operators(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT operator_id, full_name FROM operators ORDER BY operator_id"))
    return [{"id": row.operator_id, "name": row.full_name} for row in result.fetchall()]

@app.get("/api/fuel-trucks")
def get_fuel_trucks(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT truck_id, license_plate FROM fuel_trucks ORDER BY truck_id"))
    return [{"id": row.truck_id, "name": row.license_plate} for row in result.fetchall()]

@app.post("/api/fuel-logsheet-complete")
def create_full_logsheet(payload: FullLogsheet, db: Session = Depends(get_db)):
    try:
        query_header = text("""
            INSERT INTO fuel_log (log_date, shift, fuel_type, supervisor_id, operator_id, truck_id, remarks) 
            VALUES (CAST(:log_date AS DATE), :shift, :fuel_type, :supervisor_id, :operator_id, :truck_id, :remarks)
            RETURNING log_id;
        """)
        result = db.execute(query_header, {
            "log_date": payload.log_date, "shift": payload.shift,
            "fuel_type": payload.fuel_type if payload.fuel_type and payload.fuel_type != "-" else None,
            "supervisor_id": payload.supervisor_id,
            "operator_id": payload.operator_id if payload.operator_id and payload.operator_id != "" else None,
            "truck_id": payload.truck_id if payload.truck_id and payload.truck_id != "" else None,
            "remarks": payload.remarks if payload.remarks else "Despacho Rutinario"
        })
        log_id = result.fetchone()[0]
        
        if payload.equipments:
            query_detail = text("""
                INSERT INTO fuel_log_details (log_id, item_number, equipment_name, equipment_code, quantity_gln) 
                VALUES (:log_id, :item_number, :equipment_name, :equipment_code, :quantity_gln);
            """)
            for eq in payload.equipments:
                db.execute(query_detail, {
                    "log_id": log_id, "item_number": eq.item_number,
                    "equipment_name": eq.equipment_name.upper().strip(), 
                    "equipment_code": eq.equipment_code.upper().strip(), "quantity_gln": eq.quantity_gln
                })
        db.commit()
        return {"status": "success", "log_id": log_id, "rows_inserted": len(payload.equipments)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error transaccional en la BD: {str(e)}")

@app.get("/api/fuel-logs-history")
def get_fuel_logs_history(db: Session = Depends(get_db)):
    query = text("""
        SELECT fl.log_id, fl.log_date, fl.shift, fl.fuel_type, s.full_name AS supervisor, 
               coalesce(o.full_name, 'SIN OPERADOR') AS operator, coalesce(ft.license_plate, 'SIN CISTERNA') AS truck_plate, fl.remarks
        FROM fuel_log fl
        INNER JOIN supervisors s ON fl.supervisor_id = s.supervisor_id
        LEFT JOIN operators o ON fl.operator_id = o.operator_id
        LEFT JOIN fuel_trucks ft ON fl.truck_id = ft.truck_id
        ORDER BY fl.log_id DESC;
    """)
    result = db.execute(query).fetchall()
    return [{
        "log_id": row.log_id, "log_date": str(row.log_date), "shift": row.shift, "fuel_type": row.fuel_type,
        "supervisor": row.supervisor, "operator": row.operator, "truck_plate": row.truck_plate, "remarks": row.remarks
    } for row in result]

@app.post("/api/supervisors")
def create_supervisor(payload: SupervisorCreate, db: Session = Depends(get_db)):
    try:
        query_max = text("SELECT COALESCE(MAX(CAST(SUBSTRING(supervisor_id FROM 5) AS INTEGER)), 0) FROM supervisors WHERE supervisor_id LIKE 'SUP-%';")
        last_num = db.execute(query_max).scalar()
        generated_id = f"SUP-{(last_num + 1):02d}"
        password_hash = hashlib.sha256(payload.password.encode('utf-8')).hexdigest()
        
        db.execute(text("INSERT INTO supervisors (supervisor_id, full_name) VALUES (:id, :name);"), {"id": generated_id, "name": payload.full_name.strip().upper()})
        db.execute(text("INSERT INTO users (username, password_hash, role_id, supervisor_id, is_active) VALUES (:user, :hash, 'SUPERVISOR', :id, TRUE);"), {"user": payload.username.strip().lower(), "hash": password_hash, "id": generated_id})
        db.commit()
        return {"status": "success", "message": f"Creado con código {generated_id}."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error en BD: {str(e)}")

@app.post("/api/operators")
def create_operator(payload: OperatorCreate, db: Session = Depends(get_db)):
    try:
        query_max = text("SELECT COALESCE(MAX(CAST(SUBSTRING(operator_id FROM 5) AS INTEGER)), 0) FROM operators WHERE operator_id LIKE 'OPE-%';")
        last_num = db.execute(query_max).scalar()
        generated_id = f"OPE-{(last_num + 1):02d}"
        db.execute(text("INSERT INTO operators (operator_id, full_name) VALUES (:id, :name);"), {"id": generated_id, "name": payload.full_name.strip().upper()})
        db.commit()
        return {"status": "success", "message": f"Operador creado con código {generated_id}."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.post("/api/fuel-trucks")
def create_fuel_truck(payload: TruckCreate, db: Session = Depends(get_db)):
    try:
        query_max = text("SELECT COALESCE(MAX(CAST(SUBSTRING(truck_id FROM 5) AS INTEGER)), 0) FROM fuel_trucks WHERE truck_id LIKE 'CIS-%';")
        last_num = db.execute(query_max).scalar()
        generated_id = f"CIS-{(last_num + 1):02d}"
        db.execute(text("INSERT INTO fuel_trucks (truck_id, license_plate) VALUES (:id, :plate);"), {"id": generated_id, "plate": payload.license_plate.strip().upper()})
        db.commit()
        return {"status": "success", "message": f"Cisterna registrada con código {generated_id}."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.delete("/api/supervisors/{supervisor_id}")
def delete_supervisor(supervisor_id: str, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM users WHERE supervisor_id = :id"), {"id": supervisor_id})
        db.execute(text("DELETE FROM supervisors WHERE supervisor_id = :id"), {"id": supervisor_id})
        db.commit()
        return {"status": "success", "message": "Eliminado correctamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al eliminar: {str(e)}")

@app.delete("/api/operators/{operator_id}")
def delete_operator(operator_id: str, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM operators WHERE operator_id = :id"), {"id": operator_id})
        db.commit()
        return {"status": "success", "message": "Operador eliminado."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al eliminar: {str(e)}")

@app.delete("/api/fuel-trucks/{truck_id}")
def delete_fuel_truck(truck_id: str, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM fuel_trucks WHERE truck_id = :id"), {"id": truck_id})
        db.commit()
        return {"status": "success", "message": "Cisterna eliminada."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al eliminar: {str(e)}")
