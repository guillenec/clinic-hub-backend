import cloudinary
import cloudinary.uploader
from app.core.config import settings

def setup_cloudinary():
    if not settings.CLOUDINARY_URL:
        raise RuntimeError("Falta CLOUDINARY_URL en variables de entorno")
    cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL, secure=True)

setup_cloudinary()

def upload_png(file_bytes: bytes, folder: str) -> tuple[str, str]:
    """
    Sube PNG a Cloudinary. Devuelve (secure_url, public_id)
    """
    res = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type="image",
        format="png",      # forzamos png
        overwrite=True,
        unique_filename=True,
        use_filename=False,
        tags=["clinichub"],
        type="upload",
        transformation=[{"quality": "auto:best"}],  # optimiza
    )
    return res["secure_url"], res["public_id"]

def destroy(public_id: str) -> None:
    if not public_id:
        return
    cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)
