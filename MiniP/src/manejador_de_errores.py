class ManejadorDeErrores:
    def __init__(self):
        # Lista que guarda todos los errores detectados en cualquier fase
        self.errores = []

    def agregar_error(self, tipo: str, mensaje: str, linea: int = None, columna: int = None):
        """
        Registra un nuevo error en la lista.
        tipo: tipo de error (léxico, sintáctico, semántico, etc.)
        mensaje: descripción del error
        linea / columna: ubicación opcional del error
        """
        ubicacion = ""
        if linea is not None:
            ubicacion += f" (línea {linea}"
            if columna is not None:
                ubicacion += f", columna {columna}"
            ubicacion += ")"

        error = f"[{tipo.upper()}]{ubicacion}: {mensaje}"
        self.errores.append(error)

    def hay_errores(self) -> bool:
        """Indica si hay errores registrados."""
        return len(self.errores) > 0

    def imprimir_errores(self):
        """Muestra todos los errores almacenados."""
        if not self.errores:
            print("Sin errores detectados.")
        else:
            print("Errores encontrados:")
            for e in self.errores:
                print("  ", e)

    def limpiar(self):
        """Limpia la lista de errores (por si se reusa el manejador)."""
        self.errores.clear()
