import tokenize
from io import BytesIO
from dataclasses import dataclass
from typing import List, Optional, Any 
from manejador_de_errores import ManejadorDeErrores

@dataclass
class Token:
    tipo: str
    lexema: str
    renglon: int
    columna: int
    valor: Optional[Any] = None


PALABRAS_RESERVADAS = {
    "def", "si", "sino", "para", "mientras", "retornar",
    "Verdadero", "Falso", "Nada", "imprimir"
}

OPERADORES = {
    "+", "-", "*", "/", "=", "==", "!=", ">=", "<=", ">", "<", "+=", "-=", "*=", "/="
}

SIMBOLOS = {"(", ")", ":", ",", "{", "}", "[", "]"}


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

                # Ignorar tokens no útiles (Añadido COMMENT aquí)
                if tipo in ("ENCODING", "NL", "COMMENT"):
                    continue

                # Palabras reservadas e identificadores
                if tipo == "NAME":
                    if lexema in PALABRAS_RESERVADAS:
                        tipo_norm = "PALABRA_RESERVADA"

                        # Asignar valor semántico (esto está bien)
                        if lexema == "Verdadero":
                            valor = True
                        elif lexema == "Falso":
                            valor = False
                        elif lexema == "Nada":
                            valor = None

                    else:
                        tipo_norm = "IDENTIFICADOR"
                        valor = None

                # Números
                elif tipo == "NUMBER":
                    tipo_norm = "NUMERO"
                    try:
                        valor = int(lexema)
                    except ValueError:
                        try:
                            valor = float(lexema)
                        except ValueError:
                            self.manejador_errores.agregar_error(
                                "léxico", f"Número inválido '{lexema}'", renglon, columna
                            )
                            valor = None

                # Cadenas
                elif tipo == "STRING":
                    tipo_norm = "CADENA"
                    valor = lexema.strip('"').strip("'")

                # Sangrías
                elif tipo in ("INDENT", "DEDENT"):
                    tipo_norm = tipo

                # Fin de línea
                elif tipo == "NEWLINE":
                    tipo_norm = "NUEVA_LINEA"

                # Fin de archivo
                elif tipo == "ENDMARKER":
                    tipo_norm = "EOF"

                # Operadores y símbolos
                elif lexema in OPERADORES:
                    tipo_norm = "OPERADOR"

                elif lexema in SIMBOLOS:
                    tipo_norm = "SIMBOLO"

                # Cualquier otro carácter desconocido
                else:
                    tipo_norm = "DESCONOCIDO"
                    self.manejador_errores.agregar_error(
                        "léxico",
                        f"Símbolo no reconocido: {lexema}",
                        renglon,
                        columna,
                    )

                # Añadir el token a la lista (¡Importante!)
                self.tokens.append(Token(tipo_norm, lexema, renglon, columna, valor))

        except tokenize.TokenError as e:
            msg, (renglon, columna) = e.args[0], e.args[1]
            self.manejador_errores.agregar_error("léxico", msg, renglon, columna)

        # Asegurar que el archivo termina con EOF
        if not self.tokens or self.tokens[-1].tipo != "EOF":
            renglon_final = self.tokens[-1].renglon if self.tokens else 0
            columna_final = self.tokens[-1].columna if self.tokens else 0
            self.tokens.append(Token("EOF", "", renglon_final, columna_final))

        return self.tokens