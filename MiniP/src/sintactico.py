from arbol_AST import *
from manejador_de_errores import ManejadorDeErrores
from lexico import Token

class Sintactico:
    def __init__(self, tokens, manejador_errores: ManejadorDeErrores):
        self.tokens = tokens
        self.pos = 0
        self.manejador_errores = manejador_errores

    def current_token(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else Token("EOF", "", 0, 0)

    def advance(self):
        self.pos += 1

    def match(self, tipo=None, lexema=None):
        t = self.current_token()
        if tipo is not None:
            ok_tipo = (t.tipo == tipo) or (t.lexema == tipo)
        else:
            ok_tipo = True
        ok_lex = (lexema is None) or (t.lexema == lexema)
        if ok_tipo and ok_lex:
            self.advance()
            return t
        return None

    def expect(self, tipo=None, lexema=None):
        """
        Expect acepta:
          - tipo: si token.tipo == tipo  OR token.lexema == tipo (por compatibilidad con tu lexer)
          - lexema: compara token.lexema == lexema
        Si no coincide, registra error y avanza para recuperación.
        """
        token = self.current_token()

        ok_tipo = True
        if tipo is not None:
            ok_tipo = (token.tipo == tipo) or (token.lexema == tipo)

        ok_lex = True
        if lexema is not None:
            ok_lex = (token.lexema == lexema)

        if ok_tipo and ok_lex:
            self.advance()
            return token

        # Preparar texto esperado para mensaje claro
        esperado = []
        if tipo is not None:
            esperado.append(f"tipo '{tipo}'")
        if lexema is not None:
            esperado.append(f"lexema '{lexema}'")
        esperado_txt = " y ".join(esperado) if esperado else "token específico"

        self.manejador_errores.agregar_error(
            "sintáctico",
            f"Se esperaba {esperado_txt} y se encontró '{token.lexema}'",
            token.renglon,
            token.columna
        )

        # Avanzar para intentar recuperación
        self.advance()
        return token

    def lookahead(self, n):
        if self.pos + n < len(self.tokens):
            return self.tokens[self.pos + n]
        return Token("EOF", "", 0, 0)

    # ------------------- Parser -------------------
    def parsear(self):
        programa = NodoPrograma()
        while self.current_token().tipo != "EOF":
            # saltar líneas en blanco sueltas
            if self.current_token().tipo == "NUEVA_LINEA":
                self.advance()
                continue
            decl = self.declaracion()
            if decl:
                programa.declaraciones.append(decl)
            else:
                # recuperación
                self.advance()
        return programa

    def declaracion(self):
        tok = self.current_token()

        if tok.tipo == "COMENTARIO":
            self.advance()
            return NodoComentario(tok.valor)

        if tok.lexema == "def" or (tok.tipo == "PALABRA_RESERVADA" and tok.lexema == "def"):
            return self.funcion()

        if tok.lexema == "si":
            return self.condicional()
        if tok.lexema == "mientras":
            return self.while_loop()
        if tok.lexema == "para":
            return self.for_loop()

        if tok.lexema == "retornar":
            return self.retornar()

        # Identificador: asignación o llamada o expresión
        if tok.tipo in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            nxt = self.lookahead(1)
            if nxt.lexema == "=":
                return self.asignacion()
            if nxt.lexema == "(":
                return self.llamada_funcion()
            # intentar expresión
            return self.expression()

        # intentar expresión para otros casos
        return self.expression()

    # ----------------- Funciones -----------------
    def funcion(self):
        self.expect("PALABRA_RESERVADA", "def")

        # nombre
        nombre_tok = self.current_token()
        if nombre_tok.tipo in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            nombre = nombre_tok.lexema
            self.advance()
        else:
            nombre = nombre_tok.lexema
            self.advance()

        # parámetros: aceptar '(' por tipo o lexema
        self.expect("(", None)

        parametros = []
        while self.current_token().tipo != "EOF" and self.current_token().lexema != ")":
            if self.current_token().tipo == "IDENTIFICADOR":
                parametros.append(self.current_token().lexema)
                self.advance()
                if self.current_token().lexema == ",":
                    self.advance()
                else:
                    break
            else:
                # recuperación
                self.manejador_errores.agregar_error(
                    "sintáctico",
                    f"Parámetro inválido: {self.current_token().lexema}",
                    self.current_token().renglon,
                    self.current_token().columna
                )
                self.advance()
                if self.current_token().lexema == ",":
                    self.advance()

        self.expect(")", None)
        self.expect(":", None)

        # consumir newline opcional antes del INDENT
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()

        cuerpo = self.bloque()
        return NodoFuncion(nombre, parametros, cuerpo)

    def bloque(self):
        sentencias = []
        # saltar NEWLINEs
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
            # consumir DEDENT si existe
            if self.current_token().tipo == "DEDENT":
                self.advance()
            else:
                tok = self.current_token()
                self.manejador_errores.agregar_error(
                    "sintáctico",
                    "Se esperaba DEDENT al terminar el bloque",
                    tok.renglon,
                    tok.columna
                )
        else:
            # bloque de una sola línea
            s = self.declaracion()
            if s:
                sentencias.append(s)

        return NodoBloque(sentencias)

    def asignacion(self):
        nombre = self.expect("IDENTIFICADOR").lexema
        # aceptar '=' por lexema aunque el tipo sea OPERADOR
        self.expect(None, "=")
        expr = self.expression()
        # consumir NEWLINE opcional
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        return NodoAsignacion(nombre, expr)

    def retornar(self):
        self.expect("PALABRA_RESERVADA", "retornar")
        valor = self.expression()
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        return NodoReturn(valor)

    def llamada_funcion(self):
        # nombre puede ser IDENTIFICADOR o PALABRA_RESERVADA
        nombre_tok = self.current_token()
        nombre = nombre_tok.lexema
        self.advance()

        # aceptar '('
        self.expect(None, "(")
        args = []
        while self.current_token().tipo != "EOF" and self.current_token().lexema != ")":
            if self.current_token().tipo == "NUEVA_LINEA":
                self.advance()
                continue
            arg = self.expression()
            args.append(arg)
            if self.current_token().lexema == ",":
                self.advance()
            else:
                break
        self.expect(None, ")")
        # consume newline opcional
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        return NodoLlamadaFuncion(nombre, args)

    # ---------------- Expresiones ----------------
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
            # llamada si sigue '('
            if self.lookahead(1).lexema == "(":
                return self.llamada_funcion()
            self.advance()
            return NodoIdentificador(tok.lexema)

        if tok.lexema == "(":
            self.advance()
            expr = self.expression()
            self.expect(None, ")")
            return expr

        # error
        self.manejador_errores.agregar_error(
            "sintáctico",
            f"Expresión no válida: {tok.lexema}",
            tok.renglon,
            tok.columna
        )
        self.advance()
        return NodoLiteral(None)

    # ---------------- Condicionales / bucles ----------------
    def condicional(self):
        self.expect("PALABRA_RESERVADA", "si")
        condicion = self.expression()
        self.expect(None, ":")
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        cuerpo = self.bloque()
        cuerpo_else = None
        if self.current_token().lexema == "sino":
            self.advance()
            self.expect(None, ":")
            if self.current_token().tipo == "NUEVA_LINEA":
                self.advance()
            cuerpo_else = self.bloque()
        return NodoIf(condicion, cuerpo, cuerpo_else)

    def while_loop(self):
        self.expect("PALABRA_RESERVADA", "mientras")
        condicion = self.expression()
        self.expect(None, ":")
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        cuerpo = self.bloque()
        return NodoWhile(condicion, cuerpo)

    def for_loop(self):
        self.expect("PALABRA_RESERVADA", "para")
        var = self.expect("IDENTIFICADOR").lexema
        # 'en' puede venir como PALABRA_RESERVADA
        self.expect("PALABRA_RESERVADA", "en")
        iterable = self.expression()
        self.expect(None, ":")
        if self.current_token().tipo == "NUEVA_LINEA":
            self.advance()
        cuerpo = self.bloque()
        return NodoFor(var, iterable, cuerpo)
