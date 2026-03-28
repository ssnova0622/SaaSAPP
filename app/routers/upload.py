import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response
from .deps import get_current_user, ensure_tenant_active
from app.services.s3.storage_upload import StorageUpload
from app.services.s3.storage_media import MediaStorage

router = APIRouter()


@router.post("/tenants/{tenant}/upload", dependencies=[Depends(get_current_user)])
async def upload_file(tenant: str, file: UploadFile = File(...), _active_ok: bool = Depends(ensure_tenant_active)):
    try:
        data = await file.read()
        url = StorageUpload.upload_file(tenant, file.filename, data, file.content_type)
        return {"url": url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenants/{tenant}/media/upload", dependencies=[Depends(get_current_user)])
async def upload_media(
        tenant: str,
        file: UploadFile = File(..., description="Image file for product/variant"),
        _active_ok: bool = Depends(ensure_tenant_active),
):
    """Upload a product image. Saved to media_storage/{tenant}/ (local) or S3 when enabled. Returns URL to store in image_url."""
    try:
        data = await file.read()
        url = MediaStorage.upload_media(tenant, file.filename or "image.jpg", data, file.content_type)
        return {"url": url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uploads/{tenant}/{filename}")
async def get_upload(tenant: str, filename: str):
    # Serve local files for development
    path = os.path.join(os.getcwd(), "uploads", tenant, filename)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/media/{tenant}/{filename}")
async def get_media(tenant: str, filename: str):
    """Serve product media from media_storage/{tenant}/ or S3. Used for image_url like /v1/media/tenant/filename."""
    url_path = f"/v1/media/{tenant}/{filename}"
    data = MediaStorage.get_bytes(url_path)
    if data is None:
        raise HTTPException(status_code=404, detail="File not found")
    # Guess media type from extension
    ext = (os.path.splitext(filename)[1] or "").lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif",
                   ".webp": "image/webp"}
    media_type = media_types.get(ext, "image/jpeg")
    return Response(content=data, media_type=media_type)
