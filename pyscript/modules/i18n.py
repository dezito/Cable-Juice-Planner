from __future__ import annotations

from typing import Dict, Any, List, Optional
import os
import re
from logging import getLogger

from filesystem import add_config_folder_path, load_yaml


class I18nCatalog:
    """
    Internationalization catalog loader/translator.

    Public API:
      - set_lang(lang: Optional[str]) -> str
      - get_lang() -> str
      - load_catalog(path: str) -> None
      - t(key: str, default: Optional[str] = None, **fmt) -> str
      - get_catalog() -> Dict[str, str]                      # effective catalog
      - get_catalog_for_lang(lang: Optional[str]) -> Dict[str, str]
      - get_available_langs() -> List[str]
    """

    _LANG_CODE_RE = re.compile(r'^([A-Za-z]{2})-?([A-Za-z]{2})$')

    def __init__(self, base_lang: Optional[str] = "en-GB", logger_basename: Optional[str] = None) -> None:
        basename = logger_basename or f"pyscript.modules.{__name__}.I18nCatalog"
        self._logger = getLogger(basename)

        # state
        self._base_lang: str = self._norm_lang(base_lang)
        self._language: str = self._base_lang
        self._catalog_by_lang: Dict[str, Dict[str, str]] = {}
        self._effective_catalog: Dict[str, str] = {}

    # --------- Helper instance methods (no descriptors) ---------

    def _norm_lang(self, lang: Optional[str]) -> str:
        """
        Normalize language code:
          - None -> 'en-GB'
          - 'en_US' -> 'en-US'
          - 'en-gb' -> 'en-GB'
          - 'da' or invalid -> 'en-GB' (can be extended as needed)
        """
        token = (lang or "en-GB").replace("_", "-")
        m = self._LANG_CODE_RE.match(token)
        if m:
            l = m.group(1).lower()
            r = m.group(2).upper()
            return f"{l}-{r}"
        return "en-GB"

    def _flatten(self, prefix: str, obj: Any) -> Dict[str, str]:
        """Flatten nested dicts into dot-keys."""
        out: Dict[str, str] = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else str(k)
                out.update(self._flatten(key, v))
        else:
            out[prefix] = obj
        return out

    def _detect_lang_from_path(self, path: str) -> str:
        """
        Filename → language:
          da-DK.yaml -> da-DK
          en-GB.yaml -> en-GB
          en_US.yaml -> en-US (underscore is tolerated)
        Default: en-GB
        """
        base = os.path.basename(path)
        name, _ext = os.path.splitext(base)
        token = name.replace("_", "-")
        m = self._LANG_CODE_RE.match(token)
        if m:
            l = m.group(1).lower()
            r = m.group(2).upper()
            return f"{l}-{r}"
        return "en-GB"

    def _rebuild_effective_catalog(self) -> None:
        """Effective catalog = base ⊕ active language."""
        base_cat = self._catalog_by_lang.get(self._base_lang, {})
        cur_cat  = self._catalog_by_lang.get(self._language, {})
        eff = dict(base_cat)
        eff.update(cur_cat)
        self._effective_catalog = eff

    # --------- Public API ---------

    def set_lang(self, lang: Optional[str]) -> str:
        """Set active language and rebuild."""
        self._language = self._norm_lang(lang)
        self._rebuild_effective_catalog()
        return self._language

    def get_lang(self) -> str:
        """Return the active language code."""
        return self._language

    def load_catalog(self, path: str) -> None:
        """
        Load YAML catalogs from a folder with *.yaml.
        - Base (default en-GB) is the fallback.
        - Other languages overlay the base.
        - Invalid files are skipped.
        """
        self._catalog_by_lang = {}

        path = add_config_folder_path(path)
        if not os.path.isdir(path):
            self._logger.error(f"Path '{path}' is not a directory")
            return

        base_files = []
        other_files = []

        for fname in os.listdir(path):
            if not fname.endswith(".yaml"):
                continue
            full_path = os.path.join(path, fname)
            try:
                lang = self._detect_lang_from_path(full_path)
                (base_files if lang == self._base_lang else other_files).append((full_path, lang))
            except Exception as e:
                self._logger.warning(f"Skipping file '{full_path}', lang detect failed: {e}")

        # load base first, then overlays
        for p, lang in base_files + other_files:
            try:
                data = load_yaml(filename=p) or {}
                flat = self._flatten("", data)
                self._catalog_by_lang.setdefault(lang, {}).update(flat)
            except Exception as e:
                self._logger.warning(f"Skipping invalid catalog file '{p}': {e}")

        self._catalog_by_lang.setdefault(self._base_lang, {})
        self._rebuild_effective_catalog()

    def t(self, key: str, default: Optional[str] = None, **fmt) -> str:
        """
        Lookup in the effective catalog: active language → base → default → key.
        Supports .format(**fmt) placeholders.
        """
        try:
            s = self._effective_catalog.get(key, default if default is not None else key)
            try:
                return s.format(**fmt) if fmt else s
            except Exception:
                return s
        except Exception as e:
            self._logger.getChild("t").error(f"Error translating key '{key}': {e}")
            return key

    # --------- Inspectors ---------

    def get_catalog(self) -> Dict[str, str]:
        """Effective catalog (copy)."""
        return dict(self._effective_catalog)

    def get_available_langs(self) -> List[str]:
        """Sorted language codes that are loaded."""
        return sorted(self._catalog_by_lang.keys())
