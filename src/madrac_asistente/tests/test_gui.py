"""Tests for MADRAC GUI (tkinter)."""
import tkinter as tk
import pytest


def test_gui_creation():
    """Test that the GUI can be created without errors."""
    from gui import InterfazJarvis

    root = tk.Tk()
    root.withdraw()
    gui = InterfazJarvis(root)
    assert gui.root.title() == "Asistente Jarvis"
    root.destroy()


def test_gui_crear_gui():
    """Test that crear_gui returns a valid GUI and root window."""
    from gui import crear_gui

    gui, root = crear_gui()
    assert gui is not None
    assert root is not None
    assert gui.root.title() == "Asistente Jarvis"
    root.destroy()


def test_config_mostrar_gui_false_means_no_window():
    """When mostrar_gui is false, the assistant runs headless (no GUI window)."""
    from core.config import cargar_config

    config = cargar_config()
    assert "interfaz" in config
    assert "mostrar_gui" in config["interfaz"]


def test_config_mostrar_gui_true_enables_window():
    """When mostrar_gui is true, the GUI window is shown."""
    from core.config import cargar_config, guardar_config

    config = cargar_config()
    config["interfaz"]["mostrar_gui"] = True
    guardar_config(config)

    config2 = cargar_config()
    assert config2["interfaz"]["mostrar_gui"] is True

    # Restore
    config["interfaz"]["mostrar_gui"] = False
    guardar_config(config)