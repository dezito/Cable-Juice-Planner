import logging
import os
import queue
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener


class DualLogger:
    """
    Dual logger facade for Home Assistant / PyScript.

    - Optional file logging via QueueHandler -> QueueListener (non-blocking)
    - Optional forwarding to HA log based on ha_forward_min_level
    - Reload-safe: shared sink per absolute file path
    - Child loggers inherit file-enabled state
    """

    # abs_path -> {"queue": q, "file_handler": fh, "listener": listener}
    _FILE_SINKS: dict[str, dict] = {}

    def __init__(
        self,
        module_name: str,
        config_folder: str,
        level_file=logging.INFO,
        level_ha=logging.INFO,
        max_bytes=2_000_000,
        backup_count=3,
        filename_override: str | None = None,
        ha_forward_min_level=logging.WARNING,
        cache_children: bool = True,
        file_logging_enabled: bool = False,
    ):
        # Logger names
        self._module_name = module_name
        self._basename = module_name if module_name.startswith("pyscript.") else f"pyscript.{module_name}"

        # Log file path (absolute)
        safe_name = self._basename.replace(".", "_")
        filename = filename_override or f"{safe_name}.log"
        self._log_path = os.path.abspath(os.path.join(config_folder, filename))

        # Levels
        self._level_file = self._to_level(level_file)
        self._level_ha = self._to_level(level_ha)
        self._ha_forward_min_level = self._to_level(ha_forward_min_level)

        # Rotation
        self._max_bytes = int(max_bytes)
        self._backup_count = int(backup_count)

        # Children
        self._cache_children = bool(cache_children)
        self._children = {} if self._cache_children else None

        # HA logger (always active)
        self._ha_logger = self._make_ha_logger()

        # File logging state
        self._file_enabled = bool(file_logging_enabled)
        self._file_logger = None

        if self._file_enabled:
            self._file_logger = self._make_file_logger()

    # ----------------------------
    # Helpers
    # ----------------------------
    @staticmethod
    def _to_level(level):
        if isinstance(level, int):
            return level
        if isinstance(level, str):
            lvl = logging._nameToLevel.get(level.upper())
            if lvl is None:
                raise ValueError(f"Unknown log level: {level!r}")
            return lvl
        raise TypeError(f"level must be int or str, got {type(level)}")

    def _send_to_ha(self, levelno: int) -> bool:
        return levelno >= self._ha_forward_min_level

    # ----------------------------
    # Internals
    # ----------------------------
    def _make_ha_logger(self):
        logger = logging.getLogger(self._basename)
        logger.setLevel(self._level_ha)
        logger.propagate = True
        return logger

    @staticmethod
    def _remove_our_queuehandlers(logger: logging.Logger):
        for h in list(logger.handlers):
            if isinstance(h, QueueHandler) and getattr(h, "_dual_logger_tag", False):
                logger.removeHandler(h)
                try:
                    h.close()
                except Exception:
                    pass

    def _get_or_create_sink(self) -> dict:
        sink = self._FILE_SINKS.get(self._log_path)
        if sink:
            sink["file_handler"].setLevel(self._level_file)
            return sink

        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)

        q = queue.Queue(-1)

        fh = RotatingFileHandler(
            self._log_path,
            maxBytes=self._max_bytes,
            backupCount=self._backup_count,
            encoding="utf-8",
        )
        fh.setLevel(self._level_file)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        ))

        listener = QueueListener(q, fh, respect_handler_level=True)
        listener.start()

        sink = {"queue": q, "file_handler": fh, "listener": listener}
        self._FILE_SINKS[self._log_path] = sink
        return sink

    def _make_file_logger(self):
        logger = logging.getLogger(self._basename + ".file")
        logger.setLevel(self._level_file)
        logger.propagate = False

        self._remove_our_queuehandlers(logger)
        sink = self._get_or_create_sink()

        qh = QueueHandler(sink["queue"])
        qh.setLevel(logging.NOTSET)  # IMPORTANT: transparent
        qh._dual_logger_tag = True
        logger.addHandler(qh)

        return logger

    # ----------------------------
    # Runtime controls
    # ----------------------------
    def enable_file_logging(self):
        if self._file_enabled:
            return
        self._file_logger = self._make_file_logger()
        self._file_enabled = True

        if self._cache_children:
            for child in self._children.values():
                child.enable_file_logging()

    def disable_file_logging(self):
        self._file_enabled = False
        self._file_logger = None

        if self._cache_children:
            for child in self._children.values():
                child.disable_file_logging()

    def set_file_level(self, level):
        lvl = self._to_level(level)
        self._level_file = lvl

        sink = self._FILE_SINKS.get(self._log_path)
        if sink:
            sink["file_handler"].setLevel(lvl)

        if self._file_logger:
            self._file_logger.setLevel(lvl)

    def set_ha_level(self, level):
        self._level_ha = self._to_level(level)
        self._ha_logger.setLevel(self._level_ha)

    # ----------------------------
    # Logging API
    # ----------------------------
    def debug(self, msg, *args, **kwargs):
        if self._file_enabled and self._file_logger:
            self._file_logger.debug(msg, *args, **kwargs)
        if self._send_to_ha(logging.DEBUG):
            self._ha_logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if self._file_enabled and self._file_logger:
            self._file_logger.info(msg, *args, **kwargs)
        if self._send_to_ha(logging.INFO):
            self._ha_logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if self._file_enabled and self._file_logger:
            self._file_logger.warning(msg, *args, **kwargs)
        if self._send_to_ha(logging.WARNING):
            self._ha_logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if self._file_enabled and self._file_logger:
            self._file_logger.error(msg, *args, **kwargs)
        if self._send_to_ha(logging.ERROR):
            self._ha_logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        if self._file_enabled and self._file_logger:
            self._file_logger.exception(msg, *args, **kwargs)
        if self._send_to_ha(logging.ERROR):
            self._ha_logger.exception(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        if self._file_enabled and self._file_logger:
            self._file_logger.critical(msg, *args, **kwargs)
        if self._send_to_ha(logging.CRITICAL):
            self._ha_logger.critical(msg, *args, **kwargs)

    # ----------------------------
    # Child support
    # ----------------------------
    def getChild(self, suffix: str):
        if self._cache_children and suffix in self._children:
            return self._children[suffix]

        child_name = f"{self._module_name}.{suffix}"
        child = DualLogger(
            module_name=child_name,
            config_folder=os.path.dirname(self._log_path),
            level_file=self._level_file,
            level_ha=self._level_ha,
            max_bytes=self._max_bytes,
            backup_count=self._backup_count,
            filename_override=os.path.basename(self._log_path),
            ha_forward_min_level=self._ha_forward_min_level,
            cache_children=self._cache_children,
            file_logging_enabled=self._file_enabled,
        )

        if self._cache_children:
            self._children[suffix] = child
        return child
