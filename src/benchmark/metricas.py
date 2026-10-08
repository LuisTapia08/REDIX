"""Métricas de fidelidade de transcrição (sem dependências externas).

Pontuação é tratada como token próprio, porque trocar a vírgula do aluno
por ponto e vírgula é exatamente o tipo de "correção silenciosa" que
queremos flagrar.
"""
import re
import unicodedata
from dataclasses import dataclass, field

TOKEN = re.compile(r"\w+(?:[-']\w+)*|[^\w\s]", re.UNICODE)
MARCA_DUVIDA = re.compile(r"\[\?([^\]]*)\]")
MARCA_ILEGIVEL = re.compile(r"\[ileg[íi]vel\]", re.IGNORECASE)


def normalizar(texto: str) -> str:
    """Unifica Unicode e espaços; NÃO mexe em acentos, caixa ou pontuação."""
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("“", '"').replace("”", '"')
    texto = texto.replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", texto).strip()


QUEBRA_HIFEN = re.compile(r"(\w+)-[ \t]*\r?\n\s*(\w+)")


def juntar_hifens(texto: str, guia: str) -> str:
    """Resolve palavras partidas no fim da linha ("nega-\\ntivo").

    Sem dicionário não dá para saber se o hífen é da palavra
    ("baixa-autoestima", "espera-se") ou só da translineação ("negativo").
    Usamos o outro texto como guia: se ele traz "a-b", mantém o hífen;
    senão, junta "ab". Assim a quebra de linha nunca conta como erro.
    """
    guia = re.sub(r"\s+", " ", guia)

    def _resolver(m: re.Match) -> str:
        a, b = m.group(1), m.group(2)
        return f"{a}-{b}" if f"{a}-{b}" in guia else f"{a}{b}"

    return QUEBRA_HIFEN.sub(_resolver, texto)


def contar_linhas(texto: str) -> int:
    return sum(1 for linha in texto.splitlines() if linha.strip())


def limpar_marcas(texto: str) -> str:
    """Remove as marcas do transcritor para comparar só o conteúdo."""
    texto = MARCA_DUVIDA.sub(r"\1", texto)
    return MARCA_ILEGIVEL.sub(" ", texto)


def tokens(texto: str) -> list[str]:
    return TOKEN.findall(normalizar(texto))


def tokens_com_duvida(texto: str) -> tuple[list[str], set[int]]:
    """Tokeniza a transcrição e devolve os índices que vieram de [?...]."""
    texto = MARCA_ILEGIVEL.sub(" ", normalizar(texto))
    toks: list[str] = []
    duvidosos: set[int] = set()
    pos = 0
    for m in MARCA_DUVIDA.finditer(texto):
        toks += TOKEN.findall(texto[pos:m.start()])
        novos = TOKEN.findall(m.group(1))
        duvidosos.update(range(len(toks), len(toks) + len(novos)))
        toks += novos
        pos = m.end()
    toks += TOKEN.findall(texto[pos:])
    return toks, duvidosos


def _distancia(a, b) -> int:
    anterior = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        atual = [i]
        for j, y in enumerate(b, 1):
            atual.append(min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (x != y)))
        anterior = atual
    return anterior[-1]


def _alinhar(ref: list[str], hip: list[str]) -> list[tuple[str, int, int, int, int]]:
    """Alinhamento de Levenshtein com backtrace.

    Devolve operações (tipo, i1, i2, j1, j2) já agrupadas em blocos
    contíguos, onde tipo é 'igual', 'troca', 'omissao' ou 'insercao'.
    """
    n, m = len(ref), len(hip)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + (ref[i - 1] != hip[j - 1]),
            )
    passos = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (ref[i - 1] != hip[j - 1]):
            passos.append("igual" if ref[i - 1] == hip[j - 1] else "troca")
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            passos.append("omissao")
            i -= 1
        else:
            passos.append("insercao")
            j -= 1
    passos.reverse()

    blocos, i, j = [], 0, 0
    for passo in passos:
        di, dj = {"igual": (1, 1), "troca": (1, 1), "omissao": (1, 0), "insercao": (0, 1)}[passo]
        tipo = passo
        # trocas ficam token a token; omissões/inserções seguidas viram um bloco
        if blocos and blocos[-1][0] == tipo and tipo != "troca":
            t, i1, _, j1, _ = blocos[-1]
            blocos[-1] = (t, i1, i + di, j1, j + dj)
        else:
            blocos.append((tipo, i, i + di, j, j + dj))
        i, j = i + di, j + dj
    return blocos


@dataclass
class Diferenca:
    referencia: str
    transcricao: str
    contexto: str
    categoria: str
    sinalizada: bool = False  # o modelo marcou [?...] nesse trecho


@dataclass
class Relatorio:
    cer: float
    wer: float
    tokens_referencia: int
    erros_tokens: int
    marcas_duvida: int
    marcas_ilegivel: int
    linhas_referencia: int = 0
    linhas_transcricao: int = 0
    diferencas: list[Diferenca] = field(default_factory=list)

    @property
    def silenciosas(self) -> int:
        """Divergências que o modelo NÃO sinalizou — as mais perigosas."""
        return sum(not d.sinalizada for d in self.diferencas)

    def por_categoria(self) -> dict[str, int]:
        contagem: dict[str, int] = {}
        for d in self.diferencas:
            contagem[d.categoria] = contagem.get(d.categoria, 0) + 1
        return contagem


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def _categorizar(ref: list[str], hip: list[str]) -> str:
    r, h = " ".join(ref), " ".join(hip)
    pont = lambda ts: all(not t[0].isalnum() for t in ts)  # noqa: E731
    if ref and hip and pont(ref) and pont(hip):
        return "pontuação trocada"
    if (not ref and hip and pont(hip)) or (not hip and ref and pont(ref)):
        return "pontuação inserida/omitida"
    if r.lower() == h.lower():
        return "maiúscula/minúscula"
    if _sem_acento(r).lower() == _sem_acento(h).lower():
        return "acentuação"
    if not ref:
        return "palavra inserida"
    if not hip:
        return "palavra omitida"
    return "palavra trocada"


def avaliar(referencia: str, transcricao: str, janela: int = 4) -> Relatorio:
    marcas_duvida = len(MARCA_DUVIDA.findall(transcricao))
    marcas_ilegivel = len(MARCA_ILEGIVEL.findall(transcricao))
    linhas_ref, linhas_hip = contar_linhas(referencia), contar_linhas(transcricao)
    referencia = juntar_hifens(referencia, guia=transcricao)
    transcricao = juntar_hifens(transcricao, guia=referencia)
    hip_limpa = limpar_marcas(transcricao)

    ref_t = tokens(referencia)
    hip_t, duvidosos = tokens_com_duvida(transcricao)
    ref_c, hip_c = normalizar(referencia), normalizar(hip_limpa)

    diferencas = []
    erros = 0
    for tipo, i1, i2, j1, j2 in _alinhar(ref_t, hip_t):
        if tipo == "igual":
            continue
        erros += max(i2 - i1, j2 - j1)
        ctx = " ".join(ref_t[max(0, i1 - janela):i1]) + " ⟦…⟧ " + " ".join(ref_t[i2:i2 + janela])
        diferencas.append(
            Diferenca(
                referencia=" ".join(ref_t[i1:i2]),
                transcricao=" ".join(hip_t[j1:j2]),
                contexto=ctx.strip(),
                categoria=_categorizar(ref_t[i1:i2], hip_t[j1:j2]),
                sinalizada=any(j in duvidosos for j in range(j1, j2)),
            )
        )

    return Relatorio(
        cer=_distancia(ref_c, hip_c) / max(len(ref_c), 1),
        wer=_distancia(ref_t, hip_t) / max(len(ref_t), 1),
        tokens_referencia=len(ref_t),
        erros_tokens=erros,
        marcas_duvida=marcas_duvida,
        marcas_ilegivel=marcas_ilegivel,
        linhas_referencia=linhas_ref,
        linhas_transcricao=linhas_hip,
        diferencas=diferencas,
    )
