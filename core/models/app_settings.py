from dataclasses import MISSING, dataclass, fields
from typing import Any

from ..utils.constants import (
    DETECTION_TYPE,
    WATERMARK_FULLPAGE_BLOCK_STRATEGY,
    WATERMARK_FULLPAGE_FREQUENCY,
    WATERMARK_FULLPAGE_POSITION,
    WATERMARK_OVERLAY_POSITION,
    WIDTH_ENFORCEMENT,
)


@dataclass
class AppSettings:
    """Model for holding Application Settings."""

    # Core Settings
    split_height: int = 5000
    output_type: str = ".jpg"
    lossy_quality: int = 100
    detector_type: int = DETECTION_TYPE.PIXEL_COMPARISON
    sensitivity: int = 100
    ignorable_pixels: int = 0
    scan_step: int = 10
    enforce_type: int = WIDTH_ENFORCEMENT.MANUAL
    enforce_width: int = 800
    run_postprocess: bool = False
    postprocess_app: str = ""
    postprocess_args: str = ""
    run_comiczip: bool = False
    waifu_only: bool = False
    waifu_hardware_index: int = 0
    parallel_processing: bool = True
    last_browse_location: str = ""
    download_dir: str = "C:/Manhwa/Downloads"
    piccoma_email: str = ""
    piccoma_password: str = ""
    verdinha_email: str = ""
    verdinha_password: str = ""
    empreguetes_email: str = ""
    empreguetes_password: str = ""
    mediocre_email: str = ""
    mediocre_password: str = ""
    tiraninha_email: str = ""
    tiraninha_password: str = ""
    comikey_email: str = ""
    comikey_password: str = ""
    last_login_site: str = "Piccoma"

    gemini_api_key: str = ""

    # Watermark Settings - Fullpage
    watermark_fullpage_enabled: bool = False
    watermark_fullpage_paths: str = ""
    watermark_fullpage_position: int = WATERMARK_FULLPAGE_POSITION.CENTER
    watermark_fullpage_frequency: int = WATERMARK_FULLPAGE_FREQUENCY.ONCE_PER_PAGE
    watermark_fullpage_threshold: int = 200
    watermark_fullpage_alternate_interval: int = 2
    watermark_fullpage_max_per_page: int = 1
    watermark_fullpage_block_strategy: int = WATERMARK_FULLPAGE_BLOCK_STRATEGY.FIRST
    watermark_fullpage_min_spacing_top: int = 50
    watermark_fullpage_min_spacing_bottom: int = 50
    watermark_fullpage_min_spacing_sides: int = 10
    watermark_fullpage_require_centered_space: bool = True
    watermark_fullpage_min_area_height: int = 400
    watermark_fullpage_insert_mode: bool = True

    # Watermark Settings - Overlay
    watermark_overlay_enabled: bool = False
    watermark_overlay_paths: str = ""
    watermark_overlay_position: int = WATERMARK_OVERLAY_POSITION.AUTO
    watermark_overlay_opacity: int = 80
    watermark_overlay_scale_pct: int = 50
    watermark_overlay_max_per_page: int = 1
    watermark_overlay_margin: int = 10
    watermark_overlay_min_space_around: int = 30

    # Watermark Settings - Header/Footer
    watermark_header_enabled: bool = False
    watermark_header_paths: str = ""
    watermark_footer_enabled: bool = False
    watermark_footer_paths: str = ""

    # Watermark quick-toggle restore snapshot (used by context menu on/off)
    watermark_restore_saved: bool = False
    watermark_restore_watermark_fullpage_enabled: bool = False
    watermark_restore_watermark_overlay_enabled: bool = False
    watermark_restore_watermark_header_enabled: bool = False
    watermark_restore_watermark_footer_enabled: bool = False

    def __init__(self, json_dict: dict[str, Any] | None = None) -> None:
        """Initialize with defaults, then override from json_dict if provided."""
        # Set all defaults from field definitions
        for f in fields(self):
            if f.default is not MISSING:
                value = f.default
            elif f.default_factory is not MISSING:
                value = f.default_factory()
            else:
                continue
            setattr(self, f.name, value)
        
        # Override with values from json_dict
        if json_dict is not None:
            valid_fields = {f.name for f in fields(self)}
            for key, value in json_dict.items():
                if key in valid_fields:
                    setattr(self, key, value)
