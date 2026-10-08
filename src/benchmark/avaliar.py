"""Benchmark de transcrição.

Estrutura esperada (fica dentro de assets/redacoes/, que não vai pro git):

    assets/redacoes/benchmark/<caso>/
        redacao.pdf       redação original
        referencia.txt    transcrição conferida à mão, COM os erros do aluno
        resultados/       criado automaticamente

Uso:
    python -m src.benchmark.avaliar                 # roda todos os casos
    python -m src.benchmark.avaliar caso01          # roda um caso
    python -m src.benchmark.avaliar caso01 --transcricao saida.txt
        (só pontua um texto já transcrito, sem chamar o modelo)
"""
import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from src.benchmark.metricas import Relatorio, avaliar
from src.shared.config import RAIZ, settings

BENCHMARK = RAIZ / "assets" / "redacoes" / "benchmark"


def _imprimir(caso: str, modelo: str, rel: Relatorio, segundos: float | None) -> None:
    print(f"\n=== {caso} · {modelo} ===")
    print(f"CER: {rel.cer:.2%}   WER: {rel.wer:.2%}   "
          f"({rel.erros_tokens} tokens divergentes de {rel.tokens_referencia})")
    print(f"Divergências: {len(rel.diferencas)} ({rel.silenciosas} SILENCIOSAS, "
          f"{len(rel.diferencas) - rel.silenciosas} sinalizadas com [?])")
    aviso = "" if rel.linhas_transcricao == rel.linhas_referencia else "  ⚠ quebras de linha não preservadas"
    print(f"Linhas: {rel.linhas_transcricao} transcritas / {rel.linhas_referencia} na folha{aviso}")
    print(f"Marcas de dúvida: {rel.marcas_duvida}   Ilegível: {rel.marcas_ilegivel}"
          + (f"   Tempo: {segundos:.1f}s" if segundos is not None else ""))
    if rel.diferencas:
        print("Por categoria: " + ", ".join(f"{k}: {v}" for k, v in sorted(rel.por_categoria().items())))
        print("\nDivergências (referência → transcrição;  !! silenciosa, [?] sinalizada):")
        for d in rel.diferencas:
            flag = "  [?]" if d.sinalizada else "  !!"
            print(f"{flag} [{d.categoria}] «{d.referencia or '∅'}» → «{d.transcricao or '∅'}»")
            print(f"      … {d.contexto} …")


def _registrar(pasta: Path, caso: str, modelo: str, rel: Relatorio, segundos: float | None) -> None:
    historico = BENCHMARK / "historico.csv"
    novo = not historico.exists()
    with historico.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["data", "caso", "modelo", "cer", "wer", "erros_tokens",
                        "tokens_ref", "silenciosas", "duvidas", "ilegivel", "segundos"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), caso, modelo,
                    f"{rel.cer:.4f}", f"{rel.wer:.4f}", rel.erros_tokens,
                    rel.tokens_referencia, rel.silenciosas, rel.marcas_duvida, rel.marcas_ilegivel,
                    f"{segundos:.1f}" if segundos is not None else ""])


def rodar_caso(caso: str, arquivo_transcricao: Path | None = None) -> Relatorio:
    pasta = BENCHMARK / caso
    referencia_txt = pasta / "referencia.txt"
    if not referencia_txt.exists():
        sys.exit(f"Falta {referencia_txt} — escreva a transcrição de referência à mão.")
    referencia = referencia_txt.read_text(encoding="utf-8")

    segundos = None
    if arquivo_transcricao:
        transcricao = arquivo_transcricao.read_text(encoding="utf-8")
        modelo = f"arquivo:{arquivo_transcricao.name}"
    else:
        from src.transcricao.transcrever import transcrever_pdf

        modelo = f"{settings.llm_provider}:{settings.llm_model}"
        inicio = time.perf_counter()
        transcricao = transcrever_pdf(str(pasta / "redacao.pdf"))
        segundos = time.perf_counter() - inicio

        resultados = pasta / "resultados"
        resultados.mkdir(exist_ok=True)
        nome = modelo.replace(":", "_").replace("/", "_")
        carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
        (resultados / f"{carimbo}_{nome}.txt").write_text(transcricao, encoding="utf-8")

    rel = avaliar(referencia, transcricao)
    _imprimir(caso, modelo, rel, segundos)
    _registrar(pasta, caso, modelo, rel, segundos)
    return rel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("casos", nargs="*", help="nomes das pastas em assets/redacoes/benchmark")
    parser.add_argument("--transcricao", type=Path, help="pontua este arquivo em vez de chamar o modelo")
    args = parser.parse_args()

    casos = args.casos
    if not casos and BENCHMARK.exists():
        casos = sorted(p.name for p in BENCHMARK.iterdir() if p.is_dir())
    if not casos:
        sys.exit(f"Nenhum caso encontrado em {BENCHMARK}")
    if args.transcricao and len(casos) != 1:
        sys.exit("--transcricao exige exatamente um caso.")
    for caso in casos:
        rodar_caso(caso, args.transcricao)


if __name__ == "__main__":
    main()
