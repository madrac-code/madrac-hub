"""
Application entry point for MADRAC-SUBS v3.

Orchestrates startup sequence:
1. Ensure directories exist
2. Initialize logging
3. Load configuration
4. Configure threading
5. Initialize plugins
6. Launch UI
"""

import sys

from .core import (
    ensure_dirs,
    setup_logging,
    set_qt_message_handler,
    log_startup_info,
    get_logger,
    configure_threading,
)
from .config import get_config_manager

logger = None


def initialize() -> None:
    """Initialize all subsystems. Safe to call once."""
    global logger

    # 1. Ensure directories exist
    ensure_dirs()

    # 2. Initialize logging first
    setup_logging()
    logger = get_logger("app")
    log_startup_info()

    # 3. Load configuration (triggers migration if needed)
    cfg_mgr = get_config_manager()
    cfg_mgr.load()
    logger.info("Config loaded (version=%d)", cfg_mgr.get("version", 0))

    # 4. Configure threading (ML frameworks)
    thread_count = cfg_mgr.get("whisper.thread_count", 0)
    chosen = configure_threading(thread_count)
    logger.info("Threading configured: %d threads", chosen)

    # 5. Initialize UI internationalization (detect system language)
    from .ui.i18n import detect_system_language, setup as i18n_setup
    lang_code = cfg_mgr.get("idioma", "") or detect_system_language()
    i18n_setup(lang_code)
    cfg_mgr.set("idioma", lang_code)
    logger.info("UI language set to '%s'", lang_code)


def run_ui() -> None:
    """Start the Qt application."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        logger.error("PySide6 not available")
        sys.exit(1)

    set_qt_message_handler()

    app = QApplication(sys.argv)
    app.setApplicationName("MADRAC-SUBS")
    app.setOrganizationName("MadracSoft")

    # Wire infrastructure
    from .core import get_bus
    from .config import get_config_manager
    from .pipeline.queue import QueueManager
    from .pipeline.worker import PipelineWorker
    from .pipeline.stages.audio import AudioExtractionStage
    from .pipeline.stages.transcribe import TranscribeStage
    from .pipeline.stages.translate import TranslateStage
    from .pipeline.stages.format import FormatStage
    from .pipeline.stages.community import CommunityStage

    event_bus = get_bus()
    config_mgr = get_config_manager()
    queue_mgr = QueueManager()

    worker = PipelineWorker()
    worker.set_queue(queue_mgr)
    worker.set_stages([
        AudioExtractionStage(),
        TranscribeStage(),
        TranslateStage(),
        FormatStage(),
        CommunityStage(),
    ])

    from .ui.dialogs import SetupWizard
    if not config_mgr.get("setup_completed", False):
        wizard = SetupWizard()
        wizard.exec()

    from .ui.main_window import MainWindow
    window = MainWindow(
        worker=worker,
        queue_mgr=queue_mgr,
        config_mgr=config_mgr,
        event_bus=event_bus,
    )
    window.show()

    sys.exit(app.exec())


def main() -> None:
    """Application entry point."""
    from .core.exception_hook import install_exception_hooks
    install_exception_hooks()

    try:
        initialize()
    except Exception:
        import traceback
        msg = f"Fatal error during initialization: {traceback.format_exc()}"
        if logger:
            logger.critical(msg)
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    run_ui()


if __name__ == "__main__":
    main()
