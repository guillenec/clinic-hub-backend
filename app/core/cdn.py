import cloudinary
import cloudinary.uploader
from cloudinary import CloudinaryImage
from app.core.config import settings

def setup_cloudinary():
    if not (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET):
        raise RuntimeError("Faltan CLOUDINARY_* en .env")
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )

setup_cloudinary()

def upload_png(file_bytes: bytes, folder: str) -> tuple[str, str]:
    res = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type="image",
        format="png",
        overwrite=True,
        unique_filename=True,
        use_filename=False,
        tags=["clinichub"],
        type="upload",
        transformation=[{"quality": "auto:best"}],
    )
    return res["secure_url"], res["public_id"]

def destroy(public_id: str) -> None:
    if public_id:
        cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)

def upload_png_bg_removed(file_bytes: bytes, folder: str) -> tuple[str, str]:
    res = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type="image",
        format="png",
        transformation=[
            {"effect": "background_removal"},  # requiere add-on habilitado
            {"quality": "auto:best"}
        ]
    )
    return res["secure_url"], res["public_id"]

def build_url_with_bg_removal(public_id: str) -> str:
    return CloudinaryImage(public_id).build_url(effect="background_removal", format="png", secure=True)

def upload_image_avatar(file_bytes: bytes, folder: str) -> tuple[str, str]:
    """
    Sube imagen (png/jpg) optimizada y cuadrada (1:1).
    Si la cuenta tiene 'gravity:face' disponible, centra en el rostro.
    """
    res = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type="image",
        overwrite=True,
        unique_filename=True,
        use_filename=False,
        tags=["clinichub", "avatar"],
        type="upload",
        transformation=[
            {"width": 512, "height": 512, "crop": "fill", "gravity": "auto"},
            {"quality": "auto:good"},
            {"fetch_format": "auto"}
        ],
    )
    return res["secure_url"], res["public_id"]
