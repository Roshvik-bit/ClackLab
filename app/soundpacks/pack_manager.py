"""
Sound pack manager handling installation, import, and storage of custom mechanical keyboard packs.
"""

import os
import shutil
import zipfile
import logging
from typing import List, Optional
from .pack_validator import SoundPackValidator, ValidationReport

logger = logging.getLogger(__name__)

class SoundPackManager:
    """Manages custom sound packs stored in user application support directory."""

    def __init__(self, target_dir: Optional[str] = None):
        self.target_dir = target_dir or os.path.expanduser("~/Library/Application Support/ClackLab/soundpacks")
        os.makedirs(self.target_dir, exist_ok=True)

    def list_installed_packs(self) -> List[str]:
        if not os.path.exists(self.target_dir):
            return []
        return [
            d for d in os.listdir(self.target_dir)
            if os.path.isdir(os.path.join(self.target_dir, d))
        ]

    def import_from_folder(self, source_dir: str) -> tuple[bool, str, Optional[ValidationReport]]:
        """Validates and imports a local sound pack directory."""
        if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
            return False, f"Source path is not a directory: {source_dir}", None

        report = SoundPackValidator.validate_directory(source_dir)
        if not report.is_valid:
            err_msg = "; ".join(report.errors)
            return False, f"Validation failed: {err_msg}", report

        pack_folder_name = os.path.basename(os.path.normpath(source_dir))
        dest_dir = os.path.join(self.target_dir, pack_folder_name)

        try:
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(source_dir, dest_dir)
            logger.info(f"Successfully imported sound pack to {dest_dir}")
            return True, f"Successfully imported '{report.pack_name}'", report
        except Exception as e:
            logger.error(f"Failed to copy sound pack: {e}")
            return False, f"Copy error: {e}", report

    def import_from_zip(self, zip_path: str) -> tuple[bool, str, Optional[ValidationReport]]:
        """Extracts, validates, and imports a ZIP archive sound pack."""
        if not os.path.exists(zip_path) or not zip_path.endswith('.zip'):
            return False, f"Invalid ZIP file: {zip_path}", None

        temp_extract = os.path.join(self.target_dir, "_temp_extract")
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
        os.makedirs(temp_extract, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_extract)

            # Check if contents are nested in a single root folder
            entries = os.listdir(temp_extract)
            pack_dir = temp_extract
            if len(entries) == 1 and os.path.isdir(os.path.join(temp_extract, entries[0])):
                pack_dir = os.path.join(temp_extract, entries[0])

            success, msg, report = self.import_from_folder(pack_dir)
            shutil.rmtree(temp_extract)
            return success, msg, report
        except Exception as e:
            if os.path.exists(temp_extract):
                shutil.rmtree(temp_extract)
            return False, f"ZIP extraction failed: {e}", None

    def delete_pack(self, pack_name: str) -> bool:
        dest_dir = os.path.join(self.target_dir, pack_name)
        if os.path.exists(dest_dir):
            try:
                shutil.rmtree(dest_dir)
                return True
            except Exception as e:
                logger.error(f"Failed to delete sound pack {pack_name}: {e}")
                return False
        return False
