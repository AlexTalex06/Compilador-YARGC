import tokenize
from io import BytesIO
from dataclasses import dataclass
from typing import List, Optional
from manejador_de_errores import ManejadorDeErrores

@dataclass
class Token:
    tipo: str
    lexema: str
    renglon: int
    columna: int
    valor: Optional[str] = None

PALABRAS_RESERVADAS = {
    "def", "si", "sino", "para", "mientras", "retornar",
    "Verdadero", "Falso", "Nada", "imprimir"
}

OPERADORES_COMPUESTOS = {
    "+=", "-=", "*=", "/=", "==", "!=", ">=", "<=", "+", "-", "*", "/", "=", ">", "<"
}

class Lexer:
    def __init__(self, codigo: str, manejador_errores: ManejadorDeErrores):
        self.codigo = codigo
        self.tokens: List[Token] = []
        self.manejador_errores = manejador_errores

    def tokenizar(self) -> List[Token]:
        codigo_bytes = self.codigo.encode("utf-8")
        try:
            for tok in tokenize.tokenize(BytesIO(codigo_bytes).readline):
                tipo = tokenize.tok_name[tok.type]
                lexema = tok.string
                renglon, columna = tok.start
                columna += 1
                valor = None

                if tipo in ("ENCODING", "NL"):
                    continue

                if tipo == "NAME":
                    if lexema in PALABRAS_RESERVADAS:
                        tipo_norm = "PALABRA_RESERVADA"
                        if lexema in ("Verdadero", "Falso", "Nada"):
                            valor = eval(lexema)
                    else:
                        tipo_norm = "IDENTIFICADOR"

                elif tipo == "NUMBER":
                    tipo_norm = "NUMERO"
                    try:
                        valor = int(lexema)
                    except ValueError:
                        try:
                            valor = float(lexema)
                        except ValueError:
                            self.manejador_errores.agregar_error(
                                "léxico",
                                f"Número inválido '{lexema}'",
                                renglon,
                                columna
                            )
                            valor = lexema

                elif tipo == "STRING":
                    tipo_norm = "CADENA"
                    valor = lexema.strip('"').strip("'")

                elif tipo == "COMMENT":
                    tipo_norm = "COMENTARIO"
                    valor = lexema

                elif tipo in ("INDENT", "DEDENT"):
                    tipo_norm = tipo

                elif tipo == "NEWLINE":
                    tipo_norm = "NUEVA_LINEA"

                elif tipo == "ENDMARKER":
                    tipo_norm = "EOF"

                else:
                    if lexema in OPERADORES_COMPUESTOS:
                        tipo_norm = "OPERADOR"
                    else:
                        tipo_norm = lexema

                self.tokens.append(Token(tipo_norm, lexema, renglon, columna, valor))

        except tokenize.TokenError as e:
            msg, (renglon, columna) = e.args[0], e.args[1]
            self.manejador_errores.agregar_error("léxico", msg, renglon, columna)

        # Asegurar que el archivo termine con un EOF
        if not self.tokens or self.tokens[-1].tipo != "EOF":
            self.tokens.append(Token("EOF", "", 0, 0))

        return self.tokens