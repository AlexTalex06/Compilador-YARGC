from tabulate import tabulate
from typing import Optional, Any, Dict, List

class Simbolo:
    """Representa una entrada en la tabla de símbolos."""
    def __init__(self, nombre: str, categoria: str, tipo: Optional[str], valor: Any = None, ambito_nivel: int = 0):
        self.nombre = nombre
        self.categoria = categoria
        self.tipo = tipo
        self.valor = valor
        self.ambito_nivel = ambito_nivel # Nivel de anidamiento (0 = global)

    def __repr__(self):
        return f"Simbolo({self.nombre}, {self.categoria}, {self.tipo}, {self.valor}, Ambito {self.ambito_nivel})"


class TablaSimbolos:
    """
    Maneja la tabla de símbolos usando una Pila de Ámbitos (Scope Stack)
    y un historial de todos los ámbitos creados para la impresión final.
    """
    
    def __init__(self):
        # 'scope_stack' es la pila activa para búsquedas (se modifica)
        # 'all_scopes' es el historial de todos los ámbitos (solo se añade)
        
        self.global_scope: Dict[str, Simbolo] = {}
        self.scope_stack: List[Dict[str, Simbolo]] = [self.global_scope]
        self.all_scopes: List[Dict[str, Simbolo]] = [self.global_scope]

    def __repr__(self):
        return f"TablaSimbolos(NivelActual={self.get_nivel_actual()}, AmbitosTotales={len(self.all_scopes)})"

    def get_nivel_actual(self) -> int:
        """Devuelve el nivel de anidamiento actual (0 es global)."""
        return len(self.scope_stack) - 1

    # --- MANEJO DE ÁMBITOS ---

    def entrar_ambito(self):
        """
        Inicia un nuevo ámbito (al entrar a una función, 'si', 'mientras').
        """
        nuevo_scope: Dict[str, Simbolo] = {}
        # 1. Añadir a la pila activa (para búsquedas)
        self.scope_stack.append(nuevo_scope)
        # 2. Añadir al historial (para impresión final)
        self.all_scopes.append(nuevo_scope)

    def salir_ambito(self):
        """
        Cierra el ámbito actual (al salir de un bloque).
        Solo lo quita de la pila activa, *no* del historial.
        """
        if self.get_nivel_actual() > 0:
            self.scope_stack.pop()
        else:
            print("Error: Intento de salir del ámbito global")

    # --- OPERACIONES CON SÍMBOLOS ---

    def agregar_simbolo(self, nombre: str, categoria: str, tipo: Optional[str] = None, valor: Any = None) -> Simbolo:
        """
        Agrega un nuevo símbolo *solo* al ámbito actual (el último en la pila activa).
        """
        # Siempre se agrega al ámbito en el tope de la pila activa
        ambito_actual = self.scope_stack[-1]
        nivel = self.get_nivel_actual()
        
        if nombre in ambito_actual:
            # El analizador semántico debería manejar este error
            pass 

        simbolo = Simbolo(nombre, categoria, tipo, valor, nivel)
        ambito_actual[nombre] = simbolo
        return simbolo

    def buscar_simbolo(self, nombre: str) -> Optional[Simbolo]:
        """
        Busca un símbolo desde el ámbito actual hacia arriba (en la pila activa).
        """
        # Itera desde el último scope (local) hasta el primero (global)
        # USANDO LA PILA ACTIVA
        for scope in reversed(self.scope_stack):
            if nombre in scope:
                return scope[nombre]
        
        return None

    def buscar_en_ambito_actual(self, nombre: str) -> Optional[Simbolo]:
        """
        Busca un símbolo *solo* en el ámbito actual (tope de la pila activa).
        """
        ambito_actual = self.scope_stack[-1]
        if nombre in ambito_actual:
            return ambito_actual[nombre]
        return None

    def actualizar_simbolo(self, nombre: str, valor: Any = None, tipo: Optional[str] = None) -> Optional[Simbolo]:
        """
        Actualiza el valor o tipo de un símbolo existente (usando la pila activa).
        """
        simbolo = self.buscar_simbolo(nombre)
        
        if simbolo:
            if valor is not None:
                simbolo.valor = valor
            if tipo is not None:
                simbolo.tipo = tipo
            return simbolo
        else:
            return None

    # --- IMPRESIÓN Y DEPURACIÓN ---

    def obtener_todos(self) -> List[Simbolo]:
        """Devuelve todos los símbolos de todos los ámbitos (del historial)."""
        lista = []
        for scope in self.all_scopes:
            lista.extend(scope.values())
        return lista

    def mostrar_tabla(self):
        """
        Muestra la tabla de símbolos completa en formato tabular,
        usando el HISTORIAL de todos los ámbitos.
        """
        filas = []
        
        # Recopila todos los símbolos de TODOS LOS ÁMBITOS CREADOS
        for nivel, scope in enumerate(self.all_scopes):
            if not scope:
                continue
            
            for simbolo in scope.values():
                filas.append([
                    simbolo.nombre,
                    simbolo.categoria,
                    simbolo.tipo,
                    str(simbolo.valor),
                    simbolo.ambito_nivel
                ])

        print("\n=== TABLA DE SÍMBOLOS (Todos los Ámbitos) ===")
        if not filas:
            print("Tabla vacía.")
            return

        print(tabulate(filas, headers=["Nombre", "Categoría", "Tipo", "Valor", "Ámbito (Nivel)"], tablefmt="grid"))

# --- Instancia Global Única ---
tabla_global = TablaSimbolos()