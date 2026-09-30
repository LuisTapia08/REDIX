"""Ponto único de chamada aos modelos de IA.

O resto do projeto só usa a função `gerar`. Para trocar de provedor,
basta mudar LLM_PROVIDER e LLM_MODEL no .env.
"""
import base64

from src.shared.config import settings


def gerar(
    prompt: str,
    imagens: list[bytes] | None = None,
    sistema: str | None = None,
    temperatura: float | None = None,
) -> str:
    """Envia um prompt (e imagens PNG opcionais) e devolve o texto da resposta."""
    imagens = imagens or []
    provedor = settings.llm_provider.lower()

    if provedor == "anthropic":
        return _anthropic(prompt, imagens, sistema, temperatura)
    if provedor == "openai":
        return _openai(prompt, imagens, sistema, temperatura)
    if provedor == "ollama":
        return _ollama(prompt, imagens, sistema, temperatura)
    raise ValueError(f"Provedor desconhecido: {settings.llm_provider}")


def _b64(imagem: bytes) -> str:
    return base64.b64encode(imagem).decode("utf-8")


def _anthropic(prompt, imagens, sistema, temperatura) -> str:
    import anthropic  # importado aqui para só exigir a lib de quem usa

    cliente = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    conteudo = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": _b64(img)},
        }
        for img in imagens
    ]
    conteudo.append({"type": "text", "text": prompt})

    parametros = {
        "model": settings.llm_model,
        "max_tokens": settings.llm_max_tokens,
        "messages": [{"role": "user", "content": conteudo}],
    }
    if sistema:
        parametros["system"] = sistema

    resposta = cliente.messages.create(**parametros)
    return "".join(bloco.text for bloco in resposta.content if bloco.type == "text")


def _openai(prompt, imagens, sistema, temperatura) -> str:
    from openai import OpenAI

    cliente = OpenAI(api_key=settings.openai_api_key)
    conteudo = [{"type": "text", "text": prompt}] + [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_b64(img)}"}}
        for img in imagens
    ]
    mensagens = []
    if sistema:
        mensagens.append({"role": "system", "content": sistema})
    mensagens.append({"role": "user", "content": conteudo})

    parametros = {
        "model": settings.llm_model,
        "messages": mensagens,
        "max_completion_tokens": settings.llm_max_tokens,
    }
    if temperatura is not None:
        parametros["temperature"] = temperatura

    resposta = cliente.chat.completions.create(**parametros)
    return resposta.choices[0].message.content or ""


def _ollama(prompt, imagens, sistema, temperatura) -> str:
    from ollama import Client

    cliente = Client(host=settings.ollama_host)
    mensagens = []
    if sistema:
        mensagens.append({"role": "system", "content": sistema})
    mensagem = {"role": "user", "content": prompt}
    if imagens:
        mensagem["images"] = imagens
    mensagens.append(mensagem)

    opcoes = {"num_ctx": settings.ollama_num_ctx, "num_predict": settings.llm_max_tokens}
    if temperatura is not None:
        opcoes["temperature"] = temperatura
    resposta = cliente.chat(
        model=settings.llm_model, messages=mensagens, options=opcoes, think=False
    )
    return resposta["message"]["content"]
