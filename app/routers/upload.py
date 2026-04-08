import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response
from .deps import get_current_user, ensure_tenant_active
from app.services.s3.storage import StorageService

router = APIRouter()

_IMAGE_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
}


@router.post("/tenants/{tenant}/upload", dependencies=[Depends(get_current_user)])
async def upload_file(tenant: str, file: UploadFile = File(...), _active_ok: bool = Depends(ensure_tenant_active)):
    """Upload an arbitrary file. Returns a URL/key that can be stored and later resolved."""
    try:
        data = await file.read()
        url = StorageService.upload_file(tenant, file.filename or "file", data, file.content_type)
        return {"url": url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenants/{tenant}/media/upload", dependencies=[Depends(get_current_user)])
async def upload_media(
        tenant: str,
        file: UploadFile = File(..., description="Image file for product/variant"),
        _active_ok: bool = Depends(ensure_tenant_active),
):
    """Upload a product image. Returns /v1/media/{tenant}/{filename} stored as product.image_url."""
    try:
        data = await file.read()
        url = StorageService.upload_media(tenant, file.filename or "image.jpg", data, file.content_type)
        return {"url": url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uploads/{tenant}/{filename}")
async def get_upload(tenant: str, filename: str):
    """
    Serve a previously uploaded file.
    Local mode: stream from ./uploads/{tenant}/{filename}.
    S3 mode: proxy bytes from S3 (avoids CORS / public-bucket requirements).
    """
    key_or_path = f"/v1/uploads/{tenant}/{filename}"
    data = StorageService.get_upload_bytes(key_or_path)
    if data is None:
        raise HTTPException(status_code=404, detail="File not found")
    ext = (os.path.splitext(filename)[1] or "").lower()
    media_type = _IMAGE_TYPES.get(ext, "application/octet-stream")
    return Response(content=data, media_type=media_type)


@router.get("/media/{tenant}/{filename}")
async def get_media(tenant: str, filename: str):
    """
    Serve a product image.
    Local mode: read from ./media_storage/{tenant}/{filename}.
    S3 mode: proxy bytes from S3.
    """
    url_path = f"/v1/media/{tenant}/{filename}"
    data = StorageService.get_media_bytes(url_path)
    if data is None:
        raise HTTPException(status_code=404, detail="File not found")
    ext = (os.path.splitext(filename)[1] or "").lower()
    media_type = _IMAGE_TYPES.get(ext, "image/jpeg")
    return Response(content=data, media_type=media_type)
