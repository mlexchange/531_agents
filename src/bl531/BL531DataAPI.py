"""
BL531 Data Retrieval API - Minimal and General.

Simple interface to retrieve experimental data from BL531 beamline via Tiled.
Returns data in organized format so AI agents know what's available.

Can run in MOCK mode for testing without Tiled connection.
"""
import os
from typing import Dict, Any, List, Optional
import numpy as np
from dataclasses import dataclass, field

try:  
    from configs.logger import get_logger
except ImportError: 
    from logging import getLogger as get_logger

logger = get_logger("bl531_data_api")

# Check if we should use mock mode
MOCK_MODE = os.getenv("BL531_MOCK_MODE", "true").lower() == "true"


@dataclass
class RunData:
    """Organized data from a beamline run."""
    run_uid: str
    metadata: Dict[str, Any]
    detectors: Dict[str, Any] = field(default_factory=dict)
    motors: Dict[str, Any] = field(default_factory=dict)
    images: Dict[str, Any] = field(default_factory=dict)
    other: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        """Pretty print what data is available."""
        lines = [f"RunData(run_uid='{self.run_uid}')"]
        if self.detectors:
            lines.append(f"  Detectors: {list(self.detectors.keys())}")
        if self.motors:
            lines.append(f"  Motors: {list(self.motors.keys())}")
        if self.images:
            lines.append(f"  Images: {list(self.images.keys())}")
        if self.other:
            lines.append(f"  Other: {list(self.other.keys())}")
        return "\n".join(lines)
    
    def to_summary(self) -> Dict[str, Any]:
        """Convert to summary dict for AI agent."""
        return {
            "run_uid": self.run_uid,
            "metadata": self.metadata,
            "available_detectors": list(self.detectors.keys()),
            "available_motors": list(self.motors.keys()),
            "available_images": list(self.images.keys()),
            "available_other": list(self.other.keys()),
        }


class BL531DataAPI:
    """
    Simple client for retrieving BL531 experimental data.
    
    Usage:
        data_api = BL531DataAPI(tiled_uri="http://192.168.10.155:8000", api_key="key")
        run_data = data_api.get_run_data(run_uid)
        
        # Access organized data:
        image = run_data.images['det_image']
        diode = run_data.detectors['diode']
        motor_pos = run_data.motors['hexapod_motor_Tz_mm_readback']
    """
    
    def __init__(self, tiled_uri: str, api_key: str, mock_mode: bool = MOCK_MODE):
        """Initialize connection to Tiled server."""
        self.mock_mode = mock_mode
        
        if self.mock_mode:
            logger.warning("🎭 BL531DataAPI running in MOCK MODE - returning simulated data")
            self.tiled_client = None
            self.catalog = None
        else:
            from tiled.client import from_uri
            self.tiled_client = from_uri(tiled_uri, api_key=api_key)
            self.catalog = self.tiled_client
            logger.info(f"✅ Connected to Tiled at {tiled_uri}")
    
    def get_run_data(self, run_uid: str) -> RunData:
        """
        Get all data from a run in organized format.
        
        Args:
            run_uid: Run identifier
            
        Returns:
            RunData object with organized data in categories
        """
        logger.info(f"📥 Retrieving organized data for {run_uid}")
        
        if self.mock_mode:
            return self._mock_run_data(run_uid)
        
        run_data = RunData(run_uid=run_uid, metadata={})
        
        # Get primary stream data
        primary = self.catalog[run_uid]['primary']
        run_data.metadata = dict(primary.metadata) if hasattr(primary, 'metadata') else {}
        
        for key in primary.keys():
            try:
                # Skip reading large image data
                if key == 'det_image':
                    run_data.images[key] = 'Available (not loaded - use get_image() to load)'
                    logger.info(f"  ✅ {key}: Available (not loaded)")
                    continue
                
                data = primary[key].read()
                self._categorize_data(key, data, run_data)
                logger.info(f"  ✅ {key}: shape {data.shape}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to load {key}: {e}")
        
        logger.info(f"✅ Retrieved organized data:\n{run_data}")
        return run_data
    
    def get_image(self, run_uid: str, image_key: str = 'det_image') -> np.ndarray:
        """
        Load image data on demand (images can be large).
        
        Args:
            run_uid: Run identifier
            image_key: Image key (default: 'det_image')
            
        Returns:
            Image data as numpy array
        """
        logger.info(f"📷 Loading {image_key} for {run_uid}")
        
        if self.mock_mode:
            return self._mock_image_data()
        
        primary = self.catalog[run_uid]['primary']
        image = primary[image_key].read()
        logger.info(f"✅ Loaded {image_key}: shape {image.shape}")
        return image
    
    def _categorize_data(self, key: str, data: np.ndarray, run_data: RunData):
        """Categorize data into detectors, motors, images, or other."""
        key_lower = key.lower()
        
        # Categorize by key name patterns
        if 'image' in key_lower:
            run_data.images[key] = data
        elif any(detector in key_lower for detector in ['diode', 'det', 'counter', 'scaler']):
            run_data.detectors[key] = data
        elif any(motor in key_lower for motor in ['motor', 'hexapod', 'angle', 'mono', '_readback']):
            run_data.motors[key] = data
        else:
            run_data.other[key] = data
    
    def list_runs(self, limit: int = 10) -> List[str]:
        """
        List available run UIDs.
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of run UIDs
        """
        if self.mock_mode:
            return [f"mock-run-{i:04d}" for i in range(limit)]
        
        runs = list(self.catalog.keys())[:limit]
        logger.info(f"📋 Found {len(runs)} runs")
        return runs
    
    def _mock_run_data(self, run_uid: str) -> RunData:
        """Generate mock data for testing."""
        run_data = RunData(
            run_uid=run_uid,
            metadata={
                "plan_name": "scan",
                "sample": "mock_sample",
                "timestamp": "2025-11-05T12:00:00"
            }
        )
        
        # Mock detector data
        run_data.detectors = {
            "diode": np.array([100.5, 102.3, 98.7, 101.2, 99.8]),
        }
        
        # Mock motor data
        run_data.motors = {
            "gi_angle": np.array([0.1, 0.12, 0.14, 0.16, 0.18]),
            "hexapod_motor_Tz_mm_readback": np.array([5.0, 5.0, 5.0, 5.0, 5.0]),
        }
        
        # Mock image availability
        run_data.images = {
            "det_image": "Available (not loaded - use get_image() to load)"
        }
        
        logger.info(f"🎭 MOCK: Generated mock data for {run_uid}")
        return run_data
    
    def _mock_image_data(self) -> np.ndarray:
        """Generate mock image data."""
        # Return a small 100x100 mock image
        mock_image = np.random.randint(0, 1000, size=(100, 100), dtype=np.uint16)
        logger.info(f"🎭 MOCK: Generated mock image: shape {mock_image.shape}")
        return mock_image


# ============================================================================
# Module-level instance
# ============================================================================

if MOCK_MODE:
    logger.info("🎭 Creating BL531DataAPI instance in MOCK MODE")
    bl531_data = BL531DataAPI(
        tiled_uri="http://mock-tiled:8000",
        api_key="mock",
        mock_mode=True
    )
else:
    tiled_uri = os.getenv("TILED_URI", "http://192.168.10.155:8000")
    api_key = os.getenv("TILED_API_KEY", "")
    
    logger.info(f"Creating BL531DataAPI instance with tiled_uri={tiled_uri}")
    bl531_data = BL531DataAPI(
        tiled_uri=tiled_uri,
        api_key=api_key,
        mock_mode=False
    )