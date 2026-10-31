import sys


def main() -> None:
    # The same executable acts as the agent when launched with --agent
    # (so the .exe does not need Python installed to host servers).
    if "--agent" in sys.argv[1:]:
        from ownhost.agent.__main__ import main as agent_main

        agent_main([a for a in sys.argv[1:] if a != "--agent"])
        return

    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from ownhost import i18n
    from ownhost.app.settings import load_settings

    # The language is chosen before the windows are built (Settings → Language; first time: the system's).
    i18n.set_language(load_settings().get("language"))

    from ownhost.app import ASSETS, theme
    from ownhost.app.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Ownhost")
    app.setDesktopFileName("ownhost")  # links the window to its .desktop file on Linux
    app.setWindowIcon(QIcon(str(ASSETS / "icon.png")))
    # Standard buttons (OK, Cancel, Close...) in the app's language: Qt's own texts are English.
    if i18n.language() == "es":
        QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Country.Spain))
        translator = QTranslator(app)
        if translator.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            app.installTranslator(translator)
    theme.apply(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
