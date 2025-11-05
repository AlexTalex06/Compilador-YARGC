from arbol_AST import *
from manejador_de_errores import ManejadorDeErrores
from lexico import Token
# !!! ELIMINADO: Ya no importa 'tabla_global'

class Sintactico:
    def __init__(self, tokens, manejador_errores: ManejadorDeErrores):
        self.tokens = tokens
        self.pos = 0
        self.manejador_errores = manejador_errores
        # !!! ELIMINADO: Ya no necesita acceso a 'tabla_simbolos'

    # ---------------- utilidades ----------------
    def current_token(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else Token("EOF", "", 0, 0)

    def advance(self):
        self.pos += 1

    def lookahead(self, n):
        if self.pos + n < len(self.tokens):
            return self.tokens[self.pos + n]
        return Token("EOF", "", 0, 0)

    def _is(self, token, tipo=None, lexema=None):
        if token is None:
            return False
        ok_tipo = True
        if tipo is not None:
            ok_tipo = (token.tipo == tipo) or (token.lexema == tipo)
        ok_lex = True
        if lexema is not None:
            ok_lex = (token.lexema == lexema)
        return ok_tipo and ok_lex

    def match(self, tipo=None, lexema=None):
        t = self.current_token()
        if self._is(t, tipo, lexema):
            self.advance()
            return t
        return None

    def expect(self, tipo=None, lexema=None):
        token = self.current_token()
        if self._is(token, tipo, lexema):
            self.advance()
            return token

        esperado = []
        if tipo:
            esperado.append(f"tipo '{tipo}'")
        if lexema:
            esperado.append(f"lexema '{lexema}'")
        esperado_txt = " y ".join(esperado) if esperado else "token específico"

        self.manejador_errores.agregar_error(
            "sintáctico",
            f"Se esperaba {esperado_txt} y se encontró '{token.lexema}'",
            token.renglon,
            token.columna
        )
        self.advance()
        return token

    # ---------------- parser principal ----------------
    def parsear(self):
        programa = NodoPrograma()
        while self.current_token().tipo != "EOF":
            if self.current_token().tipo == "NUEVA_LINEA":
                self.advance()
                continue
            decl = self.declaracion()
            if decl:
                programa.declaraciones.append(decl)
            else:
                self.advance()
        return programa

    # ---------------- declaración ----------------
    def declaracion(self):
        tok = self.current_token()

        if tok.tipo == "COMENTARIO":
            self.advance()
            return NodoComentario(tok.valor)
        if tok.lexema == "def":
            return self.funcion()
        if tok.lexema == "si":
            return self.condicional()
        if tok.lexema == "mientras":
            return self.while_loop()
        if tok.lexema == "para":
            return self.for_loop()
        if tok.lexema == "retornar":
            return self.retornar()

        if tok.tipo in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            nxt = self.lookahead(1)
            if nxt.lexema == "=":
                return self.asignacion()
            if nxt.lexema == "(":
                return self.llamada_funcion()
            return self.expression()

        return self.expression()

    # ---------------- función ----------------
    def funcion(self):
        self.expect(lexema="def")
        nombre_tok = self.current_token()
        nombre = nombre_tok.lexema
        if nombre_tok.tipo in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            self.advance()
        else:
            self.manejador_errores.agregar_error(
                "sintáctico",
                f"Nombre de función inválido: {nombre_tok.lexema}",
                nombre_tok.renglon,
                nombre_tok.columna
            )
            self.advance()

        self.expect(lexema="(")
        parametros = []
        while self.current_token().tipo != "EOF" and self.current_token().lexema != ")":
            if self.current_token().tipo == "IDENTIFICADOR":
                parametros.append(self.current_token().lexema)
                self.advance()
                if self.current_token().lexema == ",":
                    self.advance()
                    continue
                else:
                    break
            else:
                bad = self.current_token()
                self.manejador_errores.agregar_error(
                    "sintáctico",
                    f"Parámetro inválido: {bad.lexema}",
                    bad.renglon,
                    bad.columna
                )
                self.advance()
                if self.current_token().lexema == ",":
                    self.advance()

        self.expect(lexema=")")
        self.expect(lexema=":")
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        
        # !!! ELIMINADO: 'entrar_ambito' y 'agregar_simbolo' para params

        cuerpo = self.bloque()

        # !!! ELIMINADO: 'salir_ambito'
        
        return NodoFuncion(nombre, parametros, cuerpo)

    # ---------------- bloque ----------------
    def bloque(self):
        sentencias = []
        while self.current_token().tipo == "NUEVA_LINEA":
            self.advance()

        if self.current_token().tipo == "INDENT":
            self.advance()
            while self.current_token().tipo not in ("DEDENT", "EOF"):
                if self.current_token().tipo == "NUEVA_LINEA":
                    self.advance()
                    continue
                s = self.declaracion()
                if s:
                    sentencias.append(s)
                else:
                    self.advance()
            
            if self.current_token().tipo == "DEDENT":
                self.advance()
            else:
                t = self.current_token()
                self.manejador_errores.agregar_error(
                    "sintáctico", "Se esperaba DEDENT al terminar el bloque", t.renglon, t.columna
                )
        else:
            s = self.declaracion()
            if s:
                sentencias.append(s)

        return NodoBloque(sentencias)

    # ---------------- asignación ----------------
    def asignacion(self):
        nombre_tok = self.expect("IDENTIFICADOR")
        if not nombre_tok: return None
        
        nombre = nombre_tok.lexema
        self.expect(lexema="=")
        expr = self.expression()

        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        
        # Pasa el token al Nodo
        return NodoAsignacion(nombre, expr, nombre_tok)

    # ---------------- retornar ----------------
    def retornar(self):
        self.expect(lexema="retornar")
        valor = self.expression()
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        return NodoReturn(valor)

    # ---------------- llamada a función ----------------
    def llamada_funcion(self):
        nombre_tok = self.current_token()
        nombre = nombre_tok.lexema
        self.advance()

        self.expect(lexema="(")
        args = []
        while self.current_token().tipo != "EOF" and self.current_token().lexema != ")":
            if self.current_token().tipo == "NUEVA_LINEA":
                self.advance()
                continue
            arg = self.expression()
            args.append(arg)
            if self.current_token().lexema == ",":
                self.advance()
                continue
            else:
                break
        self.expect(lexema=")")
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        
        # Pasa (nombre, token, argumentos) en el orden correcto
        return NodoLlamadaFuncion(nombre, nombre_tok, args)

    # ---------------- expresiones (precedencia) ----------------
    def expression(self):
        while self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        return self.logical_or()

    def logical_or(self):
        left = self.logical_and()
        while self.current_token().lexema == "or":
            op = self.current_token().lexema
            self.advance()
            right = self.logical_and()
            left = NodoBinario(op, left, right)
        return left

    def logical_and(self):
        left = self.comparison()
        while self.current_token().lexema == "and":
            op = self.current_token().lexema
            self.advance()
            right = self.comparison()
            left = NodoBinario(op, left, right)
        return left

    def comparison(self):
        left = self.arithmetic()
        while self.current_token().lexema in ("==", "!=", "<", "<=", ">", ">="):
            op = self.current_token().lexema
            self.advance()
            right = self.arithmetic()
            left = NodoBinario(op, left, right)
        return left

    def arithmetic(self):
        left = self.term()
        while self.current_token().lexema in ("+", "-"):
            op = self.current_token().lexema
            self.advance()
            right = self.term()
            left = NodoBinario(op, left, right)
        return left

    def term(self):
        left = self.factor()
        while self.current_token().lexema in ("*", "/"):
            op = self.current_token().lexema
            self.advance()
            right = self.factor()
            left = NodoBinario(op, left, right)
        return left

    def factor(self):
        tok = self.current_token()

        if tok.tipo == "NUMERO":
            self.advance()
            return NodoLiteral(tok.valor)
        if tok.tipo == "CADENA":
            self.advance()
            return NodoLiteral(tok.valor)
        if tok.lexema in ("Verdadero", "Falso", "Nada"):
            val = tok.valor
            self.advance()
            return NodoLiteral(val)

        if tok.tipo in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            if self.lookahead(1).lexema == "(":
                return self.llamada_funcion()
            self.advance()
            return NodoIdentificador(tok.lexema, tok) # Pasa el token

        if tok.lexema == "(":
            self.advance()
            expr = self.expression()
            self.expect(lexema=")")
            return expr

        self.manejador_errores.agregar_error(
            "sintáctico",
            f"Expresión no válida: {tok.lexema}",
            tok.renglon,
            tok.columna
        )
        self.advance()
        return NodoLiteral(None)

    # ---------------- condicionales y bucles ----------------
    def condicional(self):
        self.expect(lexema="si")
        condicion = self.expression()
        self.expect(lexema=":")
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()

        # !!! ELIMINADO: 'entrar_ambito'
        cuerpo = self.bloque()
        # !!! ELIMINADO: 'salir_ambito'
        
        cuerpo_else = None
        if self.current_token().lexema == "sino":
            self.advance()
            self.expect(lexema=":")
            if self.current_token().tipo == "NUEVA_LINEA":
                self.advance()
            
            # !!! ELIMINADO: 'entrar_ambito'
            cuerpo_else = self.bloque()
            # !!! ELIMINADO: 'salir_ambito'
            
        return NodoIf(condicion, cuerpo, cuerpo_else)

    def while_loop(self):
        self.expect(lexema="mientras")
        condicion = self.expression()
        self.expect(lexema=":")
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()

        # !!! ELIMINADO: 'entrar_ambito'
        cuerpo = self.bloque()
        # !!! ELIMINADO: 'salir_ambito'
        
        return NodoWhile(condicion, cuerpo)

    def for_loop(self):
        self.expect(lexema="para")
        var_tok = self.expect("IDENTIFICADOR")
        var = var_tok.lexema
        self.expect(lexema="en")
        iterable = self.expression()
        self.expect(lexema=":")
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()

        # !!! ELIMINADO: 'entrar_ambito' y 'agregar_simbolo'
        cuerpo = self.bloque()
        # !!! ELIMINADO: 'salir_ambito'
        
        return NodoFor(var, iterable, cuerpo, var_tok)