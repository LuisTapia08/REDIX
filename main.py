import sys

from src.transcricao.transcrever import transcrever_pdf

caminho = sys.argv[1] if len(sys.argv) > 1 else "assets/redacoes/teste.pdf"
print(transcrever_pdf(caminho))
