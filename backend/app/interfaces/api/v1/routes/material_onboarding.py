from __future__ import annotations
import json
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from backend.app.application.inventory.services.material_onboarding_service import MaterialOnboardingService
from backend.app.infrastructure.persistence.models.material_onboarding_model import MaterialOnboardingSessionModel
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id,get_current_user_id
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.interfaces.api.v1.schemas.material_onboarding_schemas import MappingRequest,ProfileRequest,ExecuteRequest
router=APIRouter(prefix="/inventory/material-onboarding",tags=["Material Onboarding"])
async def db(request:Request):
    async with request.app.state.container.session_factory() as s: yield s

def bad_request(exc: ValueError):
    message = str(exc) or "Invalid material onboarding request"
    status_code = 404 if "not found" in message.lower() else 400
    raise HTTPException(status_code, message)

@router.get("/template")
async def template(format:str="csv"):
    if format not in {"csv","xlsx"}:
        raise HTTPException(400,"Template format must be csv or xlsx")
    filename=f"raw_material_onboarding_template.{format}"
    return Response(
        MaterialOnboardingService.template_xlsx() if format=="xlsx" else MaterialOnboardingService.template_csv(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if format=="xlsx" else "text/csv",
        headers={"Content-Disposition":f'attachment; filename="{filename}"'},
    )
@router.post("/sessions",dependencies=[Depends(require_permission("inventory:write"))])
async def upload(
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session = Depends(db)
):
    """Upload and process raw material data for onboarding."""
    try:
        s = await MaterialOnboardingService(session).create_session(
            tenant_id, user_id, file.filename, await file.read()
        )
        return {
            "session_id": str(s.id),
            "headers": json.loads(s.original_headers_json or "[]"),
            "mapping": s.mapping_json
        }
    except ValueError as e:
        bad_request(e)
@router.get("/mappings")
async def mappings(tenant_id:uuid.UUID=Depends(get_current_tenant_id),session=Depends(db)):
    return [{"id":str(x.id),"name":x.name,"mapping":x.mapping_json} for x in await MaterialOnboardingService(session).list_mappings(tenant_id)]
@router.post("/mappings",dependencies=[Depends(require_permission("inventory:write"))])
async def save_mapping(body:MappingRequest,tenant_id:uuid.UUID=Depends(get_current_tenant_id),session=Depends(db)):
    x=await MaterialOnboardingService(session).save_mapping(tenant_id,body.name or "Saved Mapping",body.mapping); return {"id":str(x.id)}
@router.get("/profiles")
async def profiles(tenant_id:uuid.UUID=Depends(get_current_tenant_id),session=Depends(db)):
    return [{"id":str(x.id),"name":x.name,"defaults":x.defaults_json} for x in await MaterialOnboardingService(session).list_profiles(tenant_id)]
@router.post("/profiles",dependencies=[Depends(require_permission("inventory:write"))])
async def save_profile(body:ProfileRequest,tenant_id:uuid.UUID=Depends(get_current_tenant_id),session=Depends(db)):
    x=await MaterialOnboardingService(session).save_profile(tenant_id,body.name,body.defaults); return {"id":str(x.id)}
@router.post("/sessions/{session_id}/validate",dependencies=[Depends(require_permission("inventory:write"))])
async def validate(session_id:uuid.UUID,body:MappingRequest,tenant_id:uuid.UUID=Depends(get_current_tenant_id),session=Depends(db)):
    try: return await MaterialOnboardingService(session).validate(session_id,tenant_id,body.mapping)
    except ValueError as e: bad_request(e)
@router.get("/sessions/{session_id}/preview")
async def preview(session_id:uuid.UUID,tenant_id:uuid.UUID=Depends(get_current_tenant_id),session=Depends(db)):
    try: return await MaterialOnboardingService(session).preview(session_id,tenant_id)
    except ValueError as e: bad_request(e)
@router.get("/sessions/{session_id}/status")
async def status(session_id:uuid.UUID,tenant_id:uuid.UUID=Depends(get_current_tenant_id),session=Depends(db)):
    s=await session.get(MaterialOnboardingSessionModel,session_id)
    if s is None or s.tenant_id != tenant_id: raise HTTPException(404,"Import session not found")
    return {"status":s.status,"summary":s.summary_json}
@router.post("/sessions/{session_id}/confirm-protected",dependencies=[Depends(require_permission("inventory:write"))])
async def confirm(session_id:uuid.UUID,tenant_id:uuid.UUID=Depends(get_current_tenant_id),session=Depends(db)):
    try:
        await MaterialOnboardingService(session).confirm_protected(session_id,tenant_id); return {"status":"confirmed"}
    except ValueError as e: bad_request(e)
@router.post("/sessions/{session_id}/execute",dependencies=[Depends(require_permission("inventory:write"))])
async def execute(session_id:uuid.UUID,body:ExecuteRequest,tenant_id:uuid.UUID=Depends(get_current_tenant_id),user_id:uuid.UUID=Depends(get_current_user_id),session=Depends(db)):
    try: return await MaterialOnboardingService(session).execute(session_id,tenant_id,user_id,body.dry_run)
    except ValueError as e: raise HTTPException(400,str(e))
@router.patch("/rows/{row_id}",dependencies=[Depends(require_permission("inventory:write"))])
async def correct_row(row_id:uuid.UUID, body:dict, tenant_id:uuid.UUID=Depends(get_current_tenant_id), session=Depends(db)):
    try: return await MaterialOnboardingService(session).update_row(row_id, tenant_id, body)
    except ValueError as e: bad_request(e)
@router.get("/sessions/{session_id}/validation-report")
async def validation_report(session_id:uuid.UUID, tenant_id:uuid.UUID=Depends(get_current_tenant_id), session=Depends(db)):
    try:
        return Response(
            await MaterialOnboardingService(session).report_csv(session_id, tenant_id),
            media_type="text/csv",
            headers={"Content-Disposition":f'attachment; filename="material-onboarding-validation-{session_id}.csv"'},
        )
    except ValueError as e:
        bad_request(e)
