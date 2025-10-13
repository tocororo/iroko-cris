from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .schemas import CaptchaResponse
from .captcha_service import CaptchaService
from iroko.database import get_db_session

router = APIRouter(prefix="/captcha", tags=["captcha"])

@router.get("/", response_model=CaptchaResponse)
async def generate_captcha(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate a new CAPTCHA challenge
    """
    try:
        captcha_service = CaptchaService(db)
        captcha_id, captcha_text, base64_image = await captcha_service.generate_captcha()
        
        print(captcha_id, captcha_text)
        # Get expiry time (10 minutes from now)
        expires_at = datetime.utcnow().replace(microsecond=0)
        
        return CaptchaResponse(
            captcha_id=captcha_id,
            captcha_image=f"data:image/png;base64,{base64_image}",
            expires_at=expires_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate CAPTCHA"
        )

@router.post("/validate")
async def validate_captcha(
    captcha_id: str,
    user_input: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Validate a CAPTCHA challenge
    """
    captcha_service = CaptchaService(db)
    print(captcha_id, user_input)
    is_valid = await captcha_service.validate_captcha(captcha_id, user_input)
    
    return {
        "valid": is_valid,
        "message": "CAPTCHA validated successfully" if is_valid else "Invalid CAPTCHA"
    }

@router.post("/cleanup")
async def cleanup_captchas(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Clean up expired CAPTCHA challenges (admin endpoint)
    """
    captcha_service = CaptchaService(db)
    await captcha_service.cleanup_expired_captchas()
    
    return {"message": "Expired CAPTCHAs cleaned up successfully"}