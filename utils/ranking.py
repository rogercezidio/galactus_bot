from config import RANK_FILE
import json, logging, asyncio
from pathlib import Path
from collections import defaultdict
from typing import Dict

logger = logging.getLogger(__name__)

_LOCK = asyncio.Lock()                

_EMOJI_TOP = {1: "🥇", 2: "🥈", 3: "🥉"}
_EMOJI_BOT = {1: "💀", 2: "🗑️", 3: "👎"}

def _format_line(pos: int, name: str, media: float, votos: int, flop=False) -> str:
    medal = (_EMOJI_BOT if flop else _EMOJI_TOP).get(pos, "•")
    nota  = f"{media:+.2f}"
    return f"`{pos:>2}` {medal} *{name}*  _{nota}_  ({votos} votos)"


def _default_row() -> Dict[str, int]:
    return {"sum": 0, "count": 0}


def _load() -> Dict[str, Dict[str, int]]:
    if RANK_FILE.exists():
        try:
            with RANK_FILE.open(encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as exc:
            logger.error("Falha ao ler %s: %s – arquivo será recriado.", RANK_FILE, exc)
    return {}                         

def _save(data: Dict[str, Dict[str, int]]) -> None:
    with RANK_FILE.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


async def registrar_voto(carta: str, score: int) -> None:
    """
    Adiciona um voto para `carta`.
    `score` é um inteiro de +2 (🏆 Meta) a -2 (🚫 Injogável).
    """
    async with _LOCK:
        data = _load()
        row = data.setdefault(carta, _default_row())
        row["sum"]   += score
        row["count"] += 1
        _save(data)
    logger.info("Registrado voto %s (%+d).  Total: %s", carta, score, row)


def vote_stats() -> tuple[dict[str, dict], int]:
    """Retorna (dict_dados, total_votos)."""
    data = _load()
    total = sum(row["count"] for row in data.values())
    return data, total


def calcular_top_bottom(n: int = 5, minimo_votos: int = 3):
    """
    Retorna (top, flop, total_cartas_votadas)
    • top  : lista ordenada desc, máx n itens
    • flop : lista ordenada asc,  máx n itens
    """
    data = _load()
    total_cartas = len(data)

    filtrado = [
        (name, row["sum"] / row["count"], row["count"])
        for name, row in data.items()
        if row["count"] >= minimo_votos
    ]
    if not filtrado:
        return [], [], total_cartas

    filtrado.sort(key=lambda x: x[1], reverse=True)
    top  = filtrado[:n]
    flop = filtrado[-n:][::-1]  
    return top, flop, total_cartas

