import random
import string
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Tuple, Optional
import base64

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import CaptchaChallenge
import logging

logger = logging.getLogger('iroko-cris.auth')

class CaptchaService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_captcha(self) -> Tuple[str, str, str]:
        """
        Generate a new CAPTCHA challenge
        Returns: (captcha_id, text, base64_image)
        """
        try:
            # Generate random text (6 characters, alphanumeric)
            captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Generate CAPTCHA image
            from PIL import Image, ImageDraw, ImageFont
            import os
            
            # Create image
            width, height = 200, 80
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # Try to use a font, fallback to default
            try:
                # Try different font paths
                font_paths = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
                    '/System/Library/Fonts/Arial.ttf',
                    'arial.ttf'
                ]
                
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, 36)
                        break
                
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            
            # Add noise - random lines
            for _ in range(8):
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(0, width)
                y2 = random.randint(0, height)
                draw.line([(x1, y1), (x2, y2)], fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)), width=2)
            
            # Add noise - random dots
            for _ in range(400):
                x = random.randint(0, width)
                y = random.randint(0, height)
                draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            
            # Get text bounding box using modern approach
            bbox = draw.textbbox((0, 0), captcha_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) / 2
            y = (height - text_height) / 2
            
            # Draw text with slight distortion
            for i, char in enumerate(captcha_text):
                char_x = x + i * (text_width / len(captcha_text))
                char_y = y + random.randint(-15, 5)
                
                # Draw each character with slight variation
                draw.text(
                    (char_x, char_y), 
                    char, 
                    fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)), 
                    font=font
                )
            
            # Add wave distortion to the entire text
            # self._add_wave_distortion(image)
            
            # Convert to base64
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Generate unique ID
            captcha_id = str(uuid.uuid4())
            
            # Store in database
            expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
            
            captcha_challenge = CaptchaChallenge(
                id=captcha_id,
                text=captcha_text,
                expires_at=expires_at
            )
            
            self.db.add(captcha_challenge)
            await self.db.commit()
            
            return captcha_id, captcha_text, base64_image
            
        except Exception as e:
            logger.error(f"Error generating CAPTCHA: {e}")
            # Fallback: simple text-based CAPTCHA
            return self._generate_fallback_captcha()
    
    def _add_wave_distortion(self, image):
        """Add wave distortion to make CAPTCHA harder to read by bots"""
        import math
        
        width, height = image.size
        pixels = image.load()
        
        for y in range(height):
            # Create a sine wave distortion
            shift = int(3 * math.sin(2 * math.pi * y / 30))
            for x in range(width):
                if 0 <= x + shift < width:
                    pixels[x, y] = pixels[x + shift, y]
    
    def _generate_fallback_captcha(self) -> Tuple[str, str, str]:
        """Generate a fallback CAPTCHA if image generation fails"""
        captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        captcha_id = str(uuid.uuid4())
        
        # Create a simple text-based image
        from PIL import Image, ImageDraw, ImageFont
        
        width, height = 200, 80
        image = Image.new('RGB', (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(image)
        
        # Use default font
        font = ImageFont.load_default()
        
        # Get text bounding box using modern approach
        bbox = draw.textbbox((0, 0), captcha_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        draw.text((x, y), captcha_text, fill=(0, 0, 0), font=font)
        
        # Convert to base64
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return captcha_id, captcha_text, base64_image
    
    async def validate_captcha(self, captcha_id: str, user_input: str) -> bool:
        """
        Validate CAPTCHA challenge
        Returns: True if valid, False otherwise
        """
        try:
            # Find and delete the CAPTCHA challenge
            result = await self.db.execute(
                select(CaptchaChallenge).filter(
                    CaptchaChallenge.id == captcha_id,
                    CaptchaChallenge.expires_at > datetime.utcnow()
                )
            )
            captcha = result.scalar_one_or_none()
            
            if not captcha:
                return False
            
            # Case-insensitive comparison
            is_valid = captcha.text.upper() == user_input.upper()
            
            # Delete the used CAPTCHA
            await self.db.delete(captcha)
            await self.db.commit()
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating CAPTCHA: {e}")
            return False
    
    async def cleanup_expired_captchas(self):
        """Clean up expired CAPTCHA challenges"""
        try:
            from sqlalchemy import delete
            
            result = await self.db.execute(
                delete(CaptchaChallenge).where(
                    CaptchaChallenge.expires_at <= datetime.utcnow()
                )
            )
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Cleaned up {result.rowcount} expired CAPTCHAs")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired CAPTCHAs: {e}")