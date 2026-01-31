__all__ = ["run_app"]

def run_app():
    """Run the native GTK3 GUI app."""
    from . import gtk_gui
    gtk_gui.run_app()
