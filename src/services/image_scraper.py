"""Image scraper service for extracting case-related images with attribution."""

import asyncio
import hashlib
import logging
import os
import re
from typing import Any, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CaseImage(BaseModel):
    """Represents an image scraped from a case source."""
    
    image_id: str
    url: str
    local_path: Optional[str] = None
    alt_text: str = ""
    caption: str = ""
    source_url: str
    source_name: str
    attribution: str
    image_type: str = "general"  # general, victim, location, evidence, document


class ImageScraperService:
    """Service for scraping and downloading case-related images."""
    
    def __init__(self, output_dir: str = "frontend/images"):
        """
        Initialize the ImageScraperService.
        
        Args:
            output_dir: Directory to save downloaded images
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Common image extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        
        # Headers to mimic browser request
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
    
    async def scrape_images_from_url(
        self,
        url: str,
        limit: int = 10,
    ) -> List[CaseImage]:
        """
        Scrape images from a URL with attribution.
        
        Args:
            url: URL to scrape images from
            limit: Maximum number of images to return
            
        Returns:
            List of CaseImage objects with attribution
        """
        images: List[CaseImage] = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                html = response.text
                
                # Parse source info
                parsed_url = urlparse(url)
                source_name = parsed_url.netloc.replace("www.", "")
                
                # Extract images using regex (avoiding heavy dependencies)
                img_patterns = [
                    # Standard img tags
                    r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*>',
                    # Figure with figcaption
                    r'<figure[^>]*>.*?<img[^>]+src=["\']([^"\']+)["\'].*?<figcaption[^>]*>([^<]+)</figcaption>',
                    # Open Graph images
                    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                ]
                
                found_urls = set()
                
                for pattern in img_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        if isinstance(match, tuple):
                            img_url = match[0]
                            alt_or_caption = match[1] if len(match) > 1 else ""
                        else:
                            img_url = match
                            alt_or_caption = ""
                        
                        # Skip if already found or invalid
                        if img_url in found_urls:
                            continue
                        
                        # Make absolute URL
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = urljoin(url, img_url)
                        elif not img_url.startswith('http'):
                            img_url = urljoin(url, img_url)
                        
                        # Filter out icons, logos, tracking pixels
                        if self._is_valid_case_image(img_url):
                            found_urls.add(img_url)
                            
                            # Generate image ID
                            image_id = hashlib.md5(img_url.encode()).hexdigest()[:12]
                            
                            # Classify image type
                            image_type = self._classify_image(img_url, alt_or_caption)
                            
                            # Create attribution
                            attribution = f"Image source: {source_name} ({url})"
                            
                            images.append(CaseImage(
                                image_id=image_id,
                                url=img_url,
                                alt_text=alt_or_caption if alt_or_caption else "",
                                caption=alt_or_caption if alt_or_caption else "",
                                source_url=url,
                                source_name=source_name,
                                attribution=attribution,
                                image_type=image_type,
                            ))
                            
                            if len(images) >= limit:
                                break
                    
                    if len(images) >= limit:
                        break
                
        except Exception as e:
            logger.error(f"Failed to scrape images from {url}: {e}")
        
        return images
    
    async def download_image(self, image: CaseImage) -> Optional[str]:
        """
        Download an image and save locally.
        
        Args:
            image: CaseImage to download
            
        Returns:
            Local file path if successful, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(image.url, headers=self.headers)
                response.raise_for_status()
                
                # Determine file extension
                content_type = response.headers.get("content-type", "")
                if "jpeg" in content_type or "jpg" in content_type:
                    ext = ".jpg"
                elif "png" in content_type:
                    ext = ".png"
                elif "gif" in content_type:
                    ext = ".gif"
                elif "webp" in content_type:
                    ext = ".webp"
                else:
                    # Try to get from URL
                    parsed = urlparse(image.url)
                    ext = os.path.splitext(parsed.path)[1] or ".jpg"
                
                # Save file
                filename = f"{image.image_id}{ext}"
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, "wb") as f:
                    f.write(response.content)
                
                image.local_path = f"images/{filename}"
                logger.info(f"Downloaded image: {filepath}")
                return image.local_path
                
        except Exception as e:
            logger.error(f"Failed to download image {image.url}: {e}")
            return None
    
    async def scrape_and_download(
        self,
        urls: List[str],
        limit_per_url: int = 5,
    ) -> List[CaseImage]:
        """
        Scrape and download images from multiple URLs.
        
        Args:
            urls: List of URLs to scrape
            limit_per_url: Max images per URL
            
        Returns:
            List of downloaded CaseImage objects
        """
        all_images: List[CaseImage] = []
        
        for url in urls:
            images = await self.scrape_images_from_url(url, limit=limit_per_url)
            
            # Download each image
            for image in images:
                local_path = await self.download_image(image)
                if local_path:
                    all_images.append(image)
        
        return all_images
    
    def _is_valid_case_image(self, url: str) -> bool:
        """Check if URL is likely a valid case-related image."""
        url_lower = url.lower()
        
        # Skip common non-content images
        skip_patterns = [
            'logo', 'icon', 'favicon', 'sprite', 'button',
            'banner', 'ad', 'tracking', 'pixel', 'spacer',
            'avatar', 'profile', 'thumb', 'social', 'share',
            'facebook', 'twitter', 'instagram', 'pinterest',
            'google', 'analytics', 'widget', 'badge',
            '1x1', '2x2', 'blank', 'transparent',
        ]
        
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        # Check for valid image extension
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1].lower()
        
        # Allow URLs without extension (might be served dynamically)
        if ext and ext not in self.image_extensions:
            return False
        
        # Minimum URL length (skip tiny tracking URLs)
        if len(url) < 30:
            return False
        
        return True
    
    def _classify_image(self, url: str, alt_text: str) -> str:
        """Classify image type based on URL and alt text."""
        combined = (url + " " + alt_text).lower()
        
        if any(word in combined for word in ['victim', 'missing', 'person', 'photo', 'portrait']):
            return "victim"
        elif any(word in combined for word in ['map', 'location', 'scene', 'area', 'site']):
            return "location"
        elif any(word in combined for word in ['evidence', 'forensic', 'weapon', 'clue']):
            return "evidence"
        elif any(word in combined for word in ['document', 'report', 'record', 'file']):
            return "document"
        else:
            return "general"


def create_image_scraper(output_dir: str = "frontend/images") -> ImageScraperService:
    """Create an ImageScraperService instance."""
    return ImageScraperService(output_dir=output_dir)
