import sys


def main() -> None:
    # El mismo ejecutable hace de agente cuando se lanza con --agent
    # (así el .exe no necesita Python instalado para hospedar servidores).
    if "--agent" in sys.argv[1:]:
        from ownhost.agent.__main__ import main as agent_main

        agent_main([a for a in sys.argv[1:] if a != "--agent"])
        return

    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from ownhost.app import ASSETS, theme
    from ownhost.app.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Ownhost")
    app.setDesktopFileName("ownhost")  # enlaza la ventana con su .desktop en Linux
    app.setWindowIcon(QIcon(str(ASSETS / "icon.png")))
    # Botones estándar (Aceptar, Cancelar, Cerrar...) en español: la app está escrita en español.
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
