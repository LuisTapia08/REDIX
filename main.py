import pymupdf
from src.shared.llm import gerar

pdf = pymupdf.open("assets/redacoes/teste.pdf")
imagens = [pagina.get_pixmap(dpi=200).tobytes("png") for pagina in pdf]

prompt = (
    "Transcreva fielmente o texto manuscrito desta redação, mantendo "
    "os erros de ortografia do aluno. Marque palavras duvidosas como [?palavra] "
    "e trechos ilegíveis como [ilegível]. Responda apenas com a transcrição."
)
partes = [gerar(prompt, imagens=[img], temperatura=0) for img in imagens]
print("\n\n".join(partes))