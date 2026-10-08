"""Transcrição de redações manuscritas via modelo de visão.

Regra central: a transcrição é DIPLOMÁTICA. O texto do aluno deve sair
exatamente como foi escrito, com todos os erros, porque é sobre esses
erros que a Competência 1 do ENEM será avaliada depois.
"""
import pymupdf

from src.shared.llm import gerar

SISTEMA = """Você é um transcritor paleográfico. Sua única tarefa é copiar, \
caractere por caractere, o texto manuscrito da imagem. Você NÃO é revisor, \
NÃO é professor e NÃO deve melhorar o texto.

REGRAS OBRIGATÓRIAS:
1. Preserve TODOS os erros do aluno: ortografia, acentuação, crase, \
concordância, regência, pontuação, maiúsculas/minúsculas e repetições.
2. NUNCA troque vírgula por ponto e vírgula, ponto ou qualquer outro sinal. \
Se o aluno juntou duas orações só com vírgula, mantenha a vírgula.
3. NUNCA acrescente palavras, acentos ou sinais que não estão na imagem, \
nem remova os que estão.
4. Mantenha as quebras de linha do original: uma linha da folha = uma linha \
na saída.
5. Palavras riscadas pelo aluno devem ser omitidas.
6. Se não tiver certeza de uma palavra, escreva a sua melhor leitura no \
formato [?palavra]. Na dúvida, MARQUE — é melhor marcar demais do que \
substituir uma palavra em silêncio. Isso vale especialmente para nomes \
próprios, citações e referências (autores, obras, leis).
7. Trecho impossível de ler: [ilegível].
8. Ignore cabeçalhos impressos da folha, numeração de linhas e o título \
impresso do formulário; transcreva apenas o que o aluno escreveu \
(incluindo o título dele, se houver).

Exemplo: se a imagem diz "os jovens ultilizam as rede social, isso prejudica \
eles" a saída correta é exatamente "os jovens ultilizam as rede social, isso \
prejudica eles" — e NÃO "os jovens utilizam as redes sociais; isso os \
prejudica".

Responda somente com a transcrição, sem comentários."""

PROMPT = "Transcreva esta página seguindo rigorosamente as regras."


def paginas_png(caminho_pdf: str, dpi: int = 200) -> list[bytes]:
    with pymupdf.open(caminho_pdf) as pdf:
        return [pagina.get_pixmap(dpi=dpi).tobytes("png") for pagina in pdf]


def transcrever_pdf(caminho_pdf: str, dpi: int = 200) -> str:
    """Transcreve todas as páginas do PDF e devolve o texto unido."""
    partes = [
        gerar(PROMPT, imagens=[img], sistema=SISTEMA, temperatura=0).strip()
        for img in paginas_png(caminho_pdf, dpi)
    ]
    return "\n".join(partes)
