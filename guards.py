import discord
import time
from functools import wraps

# ─────────────────────────────────────────────────────────────────
# HIERARQUIA DE CARGOS (quanto maior = mais poder)
# ─────────────────────────────────────────────────────────────────
HIERARQUIA = {
    "👑 CEO":      5,
    "⚙ DEV":       4,
    "📢 MRKT":     3,
    "🛡 ADM":      2,
    "⚔ Capitão":  1,
    "🎮 Membro":   0,
    "✅ Verificado": 0,
    "👁 Visitante": -1,
}

def get_nivel(member: discord.Member) -> int:
    nivel = -1
    for role in member.roles:
        nivel = max(nivel, HIERARQUIA.get(role.name, -1))
    if member.guild_permissions.administrator:
        nivel = max(nivel, 5)
    return nivel

def pode_punir(aplicador: discord.Member, alvo: discord.Member) -> tuple[bool, str]:
    """Retorna (pode, motivo)"""
    if aplicador.id == alvo.id:
        return False, "Você não pode punir a si mesmo."
    if alvo.bot:
        return False, "Você não pode punir um bot."
    nivel_aplicador = get_nivel(aplicador)
    nivel_alvo      = get_nivel(alvo)
    if nivel_aplicador <= nivel_alvo:
        return False, f"Você não pode punir alguém com cargo igual ou superior ao seu."
    return True, ""

# ─────────────────────────────────────────────────────────────────
# RATE LIMITER — cooldown por usuário por ação
# ─────────────────────────────────────────────────────────────────
_cooldowns: dict[str, float] = {}

def check_cooldown(user_id: int, acao: str, segundos: float = 3.0) -> tuple[bool, float]:
    """
    Retorna (pode_usar, segundos_restantes).
    Se pode_usar=True, registra o uso.
    """
    chave = f"{user_id}:{acao}"
    agora = time.monotonic()
    ultimo = _cooldowns.get(chave, 0)
    restante = segundos - (agora - ultimo)
    if restante > 0:
        return False, round(restante, 1)
    _cooldowns[chave] = agora
    return True, 0.0

def limpar_cooldowns_antigos():
    """Remove entradas com mais de 5 minutos para não acumular memória."""
    agora = time.monotonic()
    chaves_velhas = [k for k, v in _cooldowns.items() if agora - v > 300]
    for k in chaves_velhas:
        del _cooldowns[k]

# ─────────────────────────────────────────────────────────────────
# HELPER — embed de erro padrão
# ─────────────────────────────────────────────────────────────────
def embed_sem_permissao(motivo: str = "Você não tem permissão para isso."):
    return discord.Embed(title="🚫 Sem Permissão", description=motivo, color=0xE74C3C)

def embed_cooldown(segundos: float):
    return discord.Embed(
        title="⏳ Devagar!",
        description=f"Aguarde **{segundos}s** antes de usar isso novamente.",
        color=0xF39C12
    )
