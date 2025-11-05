from tabla_simbolos import tabla_global, Simbolo
from arbol_AST import *
from manejador_de_errores import ManejadorDeErrores
from typing import List, Dict, Any


class AnalizadorSemantico:
    def __init__(self, manejador_errores: ManejadorDeErrores):
        self.tabla = tabla_global
        self.manejador_errores = manejador_errores
        self._current_function = None
        self._collected_returns: List[str] = []

        # Registrar función builtin "imprimir"
        self.tabla.agregar_simbolo(
            "imprimir",
            categoria="función",
            tipo="función",
            valor={"params": ["any"], "returns": "None", "builtin": True},
        )

    # ===================== PUNTO DE ENTRADA =====================
    def analizar(self, nodo_raiz):
        self._analizar(nodo_raiz)

    # ===================== DESPACHADOR =====================
    def _analizar(self, nodo) -> Optional[Dict[str, Any]]:
        if nodo is None:
            return None

        cls = type(nodo)
        if cls is NodoPrograma:
            for d in nodo.declaraciones:
                self._analizar(d)
        elif cls is NodoBloque:
            # Simplemente visita las sentencias. El ámbito lo maneja
            # la función que llamó a este bloque (if, for, def, etc.)
            for s in nodo.sentencias:
                self._analizar(s)
        elif cls is NodoComentario:
            return None
        elif cls is NodoAsignacion:
            return self._analizar_asignacion(nodo)
        elif cls is NodoIdentificador:
            return self._analizar_identificador(nodo)
        elif cls is NodoLiteral:
            return self._analizar_literal(nodo)
        elif cls is NodoBinario:
            return self._analizar_binario(nodo)
        elif cls is NodoIf:
            return self._analizar_if(nodo)
        elif cls is NodoWhile:
            return self._analizar_while(nodo)
        elif cls is NodoFor:
            return self._analizar_for(nodo)
        elif cls is NodoFuncion:
            return self._analizar_funcion(nodo)
        elif cls is NodoLlamadaFuncion:
            return self._analizar_llamada(nodo)
        elif cls is NodoReturn:
            return self._analizar_return(nodo)
        else:
            return None

    # ===================== LITERALES =====================
    def _analizar_literal(self, nodo: NodoLiteral) -> Dict[str, Any]:
        v = nodo.valor
        t = self._tipo_de_valor(v)
        return {"tipo": t, "valor": v}

    def _tipo_de_valor(self, v):
        if v is None:
            return "None"
        if isinstance(v, bool):
            return "bool"
        if isinstance(v, int):
            return "int"
        if isinstance(v, float):
            return "float"
        if isinstance(v, str):
            return "str"
        return "desconocido"

    # ===================== IDENTIFICADOR =====================
    def _analizar_identificador(self, nodo: NodoIdentificador) -> Dict[str, Any]:
        # Busca de local a global
        simbolo = self.tabla.buscar_simbolo(nodo.nombre)
        
        if simbolo is None:
            # Usa el token del AST para el reporte de error
            self.manejador_errores.agregar_error(
                "semántico",
                f"Variable '{nodo.nombre}' usada sin declarar.",
                nodo.token.renglon,
                nodo.token.columna
            )
            return {"tipo": "desconocido", "valor": None}

        return {"tipo": simbolo.tipo or "desconocido", "valor": simbolo.valor}

    # ===================== ASIGNACIÓN =====================
    def _analizar_asignacion(self, nodo: NodoAsignacion) -> Dict[str, Any]:
        nombre = nodo.identificador
        info = self._analizar(nodo.expresion)
        tipo_expr = info.get("tipo", "desconocido") if isinstance(info, dict) else "desconocido"
        valor = info.get("valor", None) if isinstance(info, dict) else None

        # 1. Buscamos si el símbolo ya existe (en cualquier ámbito visible)
        simbolo = self.tabla.buscar_simbolo(nombre)
        
        if simbolo:
            # 2. Si existe, es una re-asignación. Actualizamos su valor/tipo.
            self.tabla.actualizar_simbolo(nombre, valor=valor, tipo=tipo_expr)
        else:
            # 3. Si no existe, es una nueva declaración. La agregamos al ámbito ACTUAL.
            self.tabla.agregar_simbolo(nombre, categoria="variable", tipo=tipo_expr, valor=valor)
            
        return {"tipo": tipo_expr, "valor": valor}

    # ===================== OPERACIONES BINARIAS =====================
    def _analizar_binario(self, nodo: NodoBinario) -> Dict[str, Any]:
        iz = self._analizar(nodo.izquierda)
        dr = self._analizar(nodo.derecha)
        tipo_iz = iz.get("tipo", "desconocido") if isinstance(iz, dict) else "desconocido"
        tipo_dr = dr.get("tipo", "desconocido") if isinstance(dr, dict) else "desconocido"
        op = nodo.operador

        # Si alguno es 'desconocido' (como los parámetros 'a' y 'b'), 
        # no podemos estar seguros. Asumimos que es válido por ahora.
        if tipo_iz == "desconocido" or tipo_dr == "desconocido":
            if op in ("==", "!=", "<", "<=", ">", ">=", "and", "or"):
                return {"tipo": "bool", "valor": None}
            # Para aritmética, el resultado es 'desconocido'
            return {"tipo": "desconocido", "valor": None}

        if op in ("+", "-", "*", "/", "%"):
            if tipo_iz in ("int", "float") and tipo_dr in ("int", "float"):
                tipo_res = "float" if "float" in (tipo_iz, tipo_dr) or op == "/" else "int"
                return {"tipo": tipo_res, "valor": None}
            if op == "+" and tipo_iz == "str" and tipo_dr == "str":
                return {"tipo": "str", "valor": None}

            self.manejador_errores.agregar_error(
                "semántico",
                f"Operación '{op}' no compatible entre '{tipo_iz}' y '{tipo_dr}'."
                # (Se necesitaría token del operador en NodoBinario para mejor error)
            )
            return {"tipo": "desconocido", "valor": None}

        if op in ("==", "!=", "<", "<=", ">", ">="):
            return {"tipo": "bool", "valor": None}

        if op in ("and", "or"):
            if tipo_iz == "bool" and tipo_dr == "bool":
                return {"tipo": "bool", "valor": None}
            
            self.manejador_errores.agregar_error(
                "semántico",
                f"Operador lógico '{op}' requiere operandos booleanos."
            )
        return {"tipo": "desconocido", "valor": None}

    # ===================== IF / WHILE / FOR =====================
    def _analizar_if(self, nodo: NodoIf):
        self._analizar(nodo.condicion)
        
        # --- AÑADIDO: El Semántico maneja el ámbito ---
        self.tabla.entrar_ambito()
        self._analizar(nodo.cuerpo)
        self.tabla.salir_ambito()
        
        if nodo.cuerpo_else:
            # --- AÑADIDO: El Semántico maneja el ámbito ---
            self.tabla.entrar_ambito()
            self._analizar(nodo.cuerpo_else)
            self.tabla.salir_ambito()
        return None

    def _analizar_while(self, nodo: NodoWhile):
        self._analizar(nodo.condicion)
        
        # --- AÑADIDO: El Semántico maneja el ámbito ---
        self.tabla.entrar_ambito()
        self._analizar(nodo.cuerpo)
        self.tabla.salir_ambito()
        return None

    def _analizar_for(self, nodo: NodoFor):
        self._analizar(nodo.iterable)
        
        # --- AÑADIDO: El Semántico maneja el ámbito ---
        self.tabla.entrar_ambito()
        
        # Agregamos la variable del bucle al nuevo ámbito
        self.tabla.agregar_simbolo(nodo.variable, 'variable_loop', tipo=None)
        
        self._analizar(nodo.cuerpo)
        self.tabla.salir_ambito()
        return None

    # ===================== FUNCIONES =====================
    def _analizar_funcion(self, nodo: NodoFuncion):
        # 1. Verificar si ya existe en el ámbito ACTUAL
        if self.tabla.buscar_en_ambito_actual(nodo.nombre):
            self.manejador_errores.agregar_error(
                "semántico", 
                f"Función '{nodo.nombre}' ya declarada en este ámbito."
                # (Falta token en NodoFuncion para mejor error)
            )
            return

        # 2. Registrar la función en el ámbito actual (exterior)
        self.tabla.agregar_simbolo(
            nodo.nombre,
            categoria="función",
            tipo="función",
            valor={"params": nodo.parametros[:], "returns": "desconocido"},
        )
        
        self._current_function = nodo.nombre
        self._collected_returns = []

        # --- AÑADIDO: El Semántico maneja el ámbito ---
        # 3. Entrar a un nuevo ámbito para el cuerpo de la función
        self.tabla.entrar_ambito()

        # 4. Registrar los parámetros en este nuevo ámbito (Nivel 1)
        for p in nodo.parametros:
            self.tabla.agregar_simbolo(p, categoria="parametro", tipo=None)

        # 5. Analizar el cuerpo (ahora sí encontrará 'a' y 'b')
        self._analizar(nodo.cuerpo)
        
        # 6. Salir del ámbito de la función
        self.tabla.salir_ambito()

        # 7. Unificar tipo de retorno y actualizar el símbolo de la función
        ret_tipo = self._unificar_tipos_returns(self._collected_returns)
        
        simbolo_func = self.tabla.buscar_simbolo(nodo.nombre) 
        if simbolo_func and isinstance(simbolo_func.valor, dict):
            simbolo_func.valor["returns"] = ret_tipo

        self._current_function = None
        self._collected_returns = []
        return None

    def _unificar_tipos_returns(self, tipos: List[str]):
        if not tipos:
            return "None"
        tipos_filtrados = [t for t in tipos if t]
        if not tipos_filtrados:
            return "None"
        first = tipos_filtrados[0]
        if all(t == first for t in tipos_filtrados):
            return first
        if all(t in ("int", "float") for t in tipos_filtrados):
            return "float"
        return "desconocido"

    # ===================== LLAMADAS =====================
    def _analizar_llamada(self, nodo: NodoLlamadaFuncion) -> Dict[str, Any]:
        simbolo = self.tabla.buscar_simbolo(nodo.nombre)
        
        if simbolo is None or simbolo.categoria != "función":
            self.manejador_errores.agregar_error(
                "semántico",
                f"Llamada a función no declarada '{nodo.nombre}'.",
                nodo.token.renglon,
                nodo.token.columna
            )
            return {"tipo": "desconocido", "valor": None}

        # (Faltaría verificar número y tipo de argumentos)
        for a in nodo.argumentos:
            self._analizar(a)

        ret = simbolo.valor.get("returns", "desconocido") if isinstance(simbolo.valor, dict) else "desconocido"
        return {"tipo": ret, "valor": None}

    # ===================== RETURN =====================
    def _analizar_return(self, nodo: NodoReturn) -> Dict[str, Any]:
        if nodo.valor:
            info = self._analizar(nodo.valor)
            tipo = info.get("tipo", "desconocido") if isinstance(info, dict) else "desconocido"
        else:
            tipo = "None"

        if self._current_function:
            self._collected_returns.append(tipo)
        # (Faltaría error si 'return' está fuera de una función)
        return {"tipo": tipo, "valor": None}