from dataclasses import dataclass, field
from typing import List, Optional, Any
from lexico import Token 

@dataclass
class Nodo:
    pass

@dataclass
class NodoPrograma(Nodo):
    declaraciones: List[Nodo] = field(default_factory=list)

@dataclass
class NodoBloque(Nodo):
    sentencias: List[Nodo] = field(default_factory=list)

@dataclass
class NodoComentario(Nodo):
    texto: str

@dataclass
class NodoAsignacion(Nodo):
    identificador: str
    expresion: Nodo
    token: Token 

@dataclass
class NodoBinario(Nodo):
    operador: str
    izquierda: Nodo
    derecha: Nodo

@dataclass
class NodoIdentificador(Nodo):
    nombre: str
    token: Token 

@dataclass
class NodoLiteral(Nodo):
    valor: Any

@dataclass
class NodoIf(Nodo):
    condicion: Nodo
    cuerpo: NodoBloque
    cuerpo_else: Optional[NodoBloque] = None

@dataclass
class NodoWhile(Nodo):
    condicion: Nodo
    cuerpo: NodoBloque

@dataclass
class NodoFor(Nodo):
    variable: str
    iterable: Nodo
    cuerpo: NodoBloque
    token_variable: Token  

@dataclass
class NodoFuncion(Nodo):
    nombre: str
    parametros: List[str] # El parser solo pasa los nombres
    cuerpo: NodoBloque

@dataclass
class NodoReturn(Nodo):
    valor: Optional[Nodo] = None

@dataclass
class NodoLlamadaFuncion(Nodo):
    nombre: str
    token: Token 
    argumentos: List[Nodo] = field(default_factory=list)