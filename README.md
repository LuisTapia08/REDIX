# Redix

Correção automática de redações no modelo ENEM para professores de Língua Portuguesa.

O professor envia o PDF de uma redação manuscrita. A IA transcreve o texto e avalia nas 5 competências do ENEM. O professor revisa e aprova a correção, e o aluno recebe o resultado por e-mail com videoaulas sobre os pontos fracos.

> **Status:** protótipo. Por enquanto existe só a etapa de **transcrição**, com um benchmark para medir a fidelidade dela.

## Por que a transcrição é "diplomática"

Modelos de visão tendem a corrigir o aluno sem avisar: trocam vírgula por ponto e vírgula, acertam a concordância, ajeitam a ortografia. Para corrigir uma redação isso é fatal, porque a Competência 1 avalia justamente esses desvios.

Por isso a transcrição precisa copiar o texto **exatamente como o aluno escreveu**, com todos os erros. Quando o modelo não tem certeza de uma palavra, ele escreve `[?palavra]` e não troca nada em silêncio.

## Estrutura

```
src/
├── shared/
│   ├── config.py        # lê o .env
│   └── llm.py           # gerar(): interface única para Anthropic, OpenAI e Ollama
├── transcricao/
│   └── transcrever.py   # PDF → imagens → transcrição fiel
└── benchmark/
    ├── metricas.py      # CER, WER e divergências silenciosas × sinalizadas
    └── avaliar.py       # roda os casos de teste e registra o histórico
main.py                  # transcreve um PDF e imprime o texto
```

## Instalação (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz:

```env
# Provedor ativo: anthropic, openai ou ollama
LLM_PROVIDER=ollama
LLM_MODEL=qwen3.5:9b
OLLAMA_HOST=http://localhost:11434
# OLLAMA_NUM_CTX=16384
# LLM_MAX_TOKENS=4096
# ANTHROPIC_API_KEY=...
# OPENAI_API_KEY=...
```

Para usar o Ollama: `ollama pull qwen3.5:9b`.

> Ao gerar o `requirements.txt` no PowerShell 5.1, use `pip freeze | Out-File -Encoding utf8 requirements.txt`. O `>` salva em UTF-16, e depois o `pip install -r` quebra.

## Uso

Transcrever uma redação:

```powershell
python main.py caminho\da\redacao.pdf
```

## Benchmark de transcrição

Cada caso de teste fica em `assets/redacoes/benchmark/<caso>/`. Essa pasta não vai para o git, para proteger os dados dos alunos.

```
assets/redacoes/benchmark/caso01/
├── redacao.pdf
├── referencia.txt   # transcrição feita à mão, COM os erros do aluno, uma linha por linha da folha
└── resultados/      # saídas do modelo (criada automaticamente)
```

```powershell
python -m src.benchmark.avaliar                # todos os casos
python -m src.benchmark.avaliar caso01         # um caso
python -m src.benchmark.avaliar caso01 --transcricao saida.txt   # só pontua, sem chamar o modelo
```

O relatório mostra:

- **CER / WER**: taxa de erro por caractere e por palavra. A pontuação conta como token, então trocar `,` por `;` conta como erro.
- **Silenciosas**: divergências que o modelo **não** marcou com `[?]`. É a métrica mais importante.
- **Linhas**: avisa se as quebras de linha da folha se perderam.

Cada execução é registrada em `assets/redacoes/benchmark/historico.csv`, para comparar modelos.

### Resultados até agora

| Modelo | Casos | WER | Silenciosas | Tempo/página | Observação |
|---|---|---|---|---|---|
| qwen3.5:4b (prompt antigo) | 1 | — | várias | — | "corrigia" o aluno e inventou erro de concordância |
| qwen3.5:9b (prompt atual) | 1 | 0% | 0 | ~180 s | não preserva as quebras de linha |

## Próximos passos

- [ ] Mais casos no benchmark (letra difícil, rasuras, nomes próprios)
- [ ] Preservar as quebras de linha (no ENEM: mínimo de 7 linhas, máximo de 30)
- [ ] Reduzir o tempo de transcrição
- [ ] Avaliação nas 5 competências com saída em JSON (trecho, tipo de erro, sugestão)
- [ ] Marcação dos erros no PDF (PyMuPDF)
- [ ] API (FastAPI), Postgres + S3, fila assíncrona (Redis)
- [ ] Tela de revisão do professor antes do envio
- [ ] Envio por e-mail (Resend, SendGrid ou SES)
