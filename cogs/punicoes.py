import discord
from discord.ext import commands
from discord import app_commands
import database
import asyncio
import guards
import json
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────────────────────────
# HELPER — Criar/garantir cargo 🔇 Mutado com bloqueio total
# ─────────────────────────────────────────────────────────────────
async def garantir_cargo_mutado(guild: discord.Guild) -> discord.Role:
    cargo = discord.utils.get(guild.roles, name="🔇 Mutado")
    if not cargo:
        cargo = await guild.create_role(
            name="🔇 Mutado",
            color=discord.Color.from_str("#2C2F33"),
            hoist=False,
            mentionable=False,
            reason="Cargo de mute FFC"
        )

    for channel in guild.channels:
        try:
            if isinstance(channel, discord.TextChannel):
                await channel.set_permissions(cargo,
                    send_messages=False,
                    add_reactions=False,
                    create_public_threads=False,
                    create_private_threads=False,
                    send_messages_in_threads=False,
                    read_messages=True,
                )
            elif isinstance(channel, discord.VoiceChannel):
                await channel.set_permissions(cargo,
                    speak=False,
                    send_messages=False,
                )
        except discord.Forbidden:
            pass
        await asyncio.sleep(0.1)

    return cargo

# ─────────────────────────────────────────────────────────────────
# SALVAR / RESTAURAR cargos — "recortar e colar"
# ─────────────────────────────────────────────────────────────────
def _cargos_para_salvar(membro: discord.Member) -> list[int]:
    """
    Retorna IDs dos cargos do membro que devem ser salvos.
    Exclui: @everyone, 🔇 Mutado, cargos gerenciados por bots.
    Mantém: cargo de identificação (Nick | ID), e qualquer outro cargo normal.
    """
    ignorar = {"@everyone", "🔇 Mutado"}
    return [
        r.id for r in membro.roles
        if r.name not in ignorar and not r.managed
    ]

async def salvar_cargos_membro(discord_id: str, cargos: list[int]):
    await database.salvar_cargos_snapshot(discord_id, json.dumps(cargos))

async def restaurar_cargos_membro(membro: discord.Member):
    snapshot_json = await database.get_cargos_snapshot(str(membro.id))
    if not snapshot_json:
        return

    ids_salvos = json.loads(snapshot_json)
    guild      = membro.guild

    # Monta lista de cargos válidos (podem ter sido deletados enquanto estava mutado)
    cargos_restaurar = [
        guild.get_role(rid) for rid in ids_salvos
        if guild.get_role(rid) is not None
    ]

    # Remove cargo de mute e adiciona os salvos de volta
    cargo_muted = discord.utils.get(guild.roles, name="🔇 Mutado")
    try:
        if cargo_muted and cargo_muted in membro.roles:
            await membro.remove_roles(cargo_muted, reason="Mute expirado — FFC")
        if cargos_restaurar:
            await membro.add_roles(*cargos_restaurar, reason="Restauração pós-mute — FFC")
    except discord.Forbidden:
        pass

    # Limpa o snapshot do banco
    await database.deletar_cargos_snapshot(str(membro.id))

# ─────────────────────────────────────────────────────────────────
# TIMER — DM com timestamp nativo do Discord
# ─────────────────────────────────────────────────────────────────
async def enviar_timer_dm(membro: discord.Member, motivo: str, segundos_total: int):
    expira_em = datetime.now(timezone.utc) + timedelta(seconds=segundos_total)
    timestamp = int(expira_em.timestamp())

    embed = discord.Embed(
        title="🔇 Você foi mutado",
        description=(
            f"**Motivo:** {motivo}\n\n"
            f"**Expira em:** <t:{timestamp}:R>\n"
            f"**Data/hora de fim:** <t:{timestamp}:F>\n\n"
            "Você pode ver os canais mas não pode enviar mensagens nem falar em voz.\n"
            "Seus cargos serão **devolvidos automaticamente** quando o mute expirar.\n\n"
            "Se acredita que é um erro, aguarde o fim do mute e abra um ticket em **#suporte**."
        ),
        color=0xE74C3C
    )
    embed.set_footer(text="Free Fire Championships • Punições")
    try:
        await membro.send(embed=embed)
    except discord.Forbidden:
        pass

# ─────────────────────────────────────────────────────────────────
# REMOÇÃO AUTOMÁTICA + RESTAURAÇÃO de cargos
# ─────────────────────────────────────────────────────────────────
async def remover_mute_automatico(membro: discord.Member, segundos: int):
    await asyncio.sleep(segundos)
    try:
        membro_atual = membro.guild.get_member(membro.id)
        if not membro_atual:
            return

        # Restaura todos os cargos salvos (inclui remoção do mute)
        await restaurar_cargos_membro(membro_atual)

        try:
            await membro_atual.send(embed=discord.Embed(
                title="🔊 Mute removido!",
                description=(
                    "Seu mute expirou e seus cargos foram **restaurados automaticamente**.\n\n"
                    "Você pode falar novamente no servidor.\n"
                    "Lembre-se de seguir as regras para evitar novas punições."
                ),
                color=0x2ECC71
            ))
        except discord.Forbidden:
            pass

        # Log
        log_ch = discord.utils.get(membro.guild.text_channels, name="📋logs")
        if log_ch:
            await log_ch.send(embed=discord.Embed(
                title="🔊 Mute Expirado — Cargos Restaurados", color=0x2ECC71
            ).add_field(name="Membro", value=f"{membro_atual} (`{membro_atual.id}`)", inline=False)
            .set_footer(text="Free Fire Championships • Log"))

    except Exception as e:
        print(f"  ⚠️  Erro ao remover mute de {membro}: {e}")

# ─────────────────────────────────────────────────────────────────
# MODAL — Punir jogador
# ─────────────────────────────────────────────────────────────────
class PunirModal(discord.ui.Modal):
    def __init__(self, tipo: str, membro: discord.Member, aplicador: discord.Member):
        super().__init__(title=f"⚠️ Aplicar Punição — {tipo.upper()}")
        self.tipo      = tipo
        self.membro    = membro
        self.aplicador = aplicador

    motivo = discord.ui.TextInput(
        label="Motivo",
        placeholder="Descreva o motivo da punição...",
        style=discord.TextStyle.paragraph,
        min_length=5, max_length=300, required=True
    )
    duracao = discord.ui.TextInput(
        label="Duração em horas (0 = permanente) — só para MUTE",
        placeholder="Ex: 24 | 168 | 0",
        min_length=1, max_length=5, required=True,
        default="24"
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild  = interaction.guild
        membro = self.membro
        tipo   = self.tipo

        pode, motivo_h = guards.pode_punir(self.aplicador, membro)
        if not pode:
            return await interaction.response.send_message(
                embed=guards.embed_sem_permissao(motivo_h), ephemeral=True
            )

        motivo = self.motivo.value.strip()
        try:
            horas = int(self.duracao.value.strip())
        except ValueError:
            return await interaction.response.send_message(embed=embed_erro(
                "Duração inválida", "Digite um número inteiro. Ex: `24`"
            ), ephemeral=True)

        permanente  = horas == 0
        segundos    = horas * 3600

        ultima      = await database.get_ultima_punicao(str(membro.id), tipo)
        reincidente = ultima is not None
        if reincidente and not permanente:
            horas    = horas * 2
            segundos = horas * 3600

        punicao_id = await database.salvar_punicao(
            discord_id   = str(membro.id),
            discord_tag  = str(membro),
            tipo         = tipo,
            motivo       = motivo,
            horas        = 0 if permanente else horas,
            permanente   = permanente,
            aplicado_por = str(interaction.user.id)
        )

        duracao_texto = "Permanente" if permanente else f"{horas}h"
        if reincidente and not permanente:
            duracao_texto += " *(dobrado — reincidente)*"

        # ── MUTE — recortar cargos, aplicar mute, agendar restauração ──
        if tipo == "mute":
            await interaction.response.defer(ephemeral=True)

            # 1. Salva snapshot dos cargos atuais
            cargos_ids = _cargos_para_salvar(membro)
            await salvar_cargos_membro(str(membro.id), cargos_ids)

            # 2. Garante cargo mutado e suas permissões
            cargo_muted = await garantir_cargo_mutado(guild)

            # 3. Remove TODOS os cargos (exceto @everyone, ID FF e gerenciados)
            cargos_remover = [
                r for r in membro.roles
                if r.name not in {"@everyone", "🔇 Mutado"}
                and not r.managed
                and not ("|" in r.name)  # mantém o cargo Nick | ID
            ]
            if cargos_remover:
                try:
                    await membro.remove_roles(*cargos_remover, reason=f"[FFC] Mute — {motivo}")
                except discord.Forbidden:
                    pass

            # 4. Aplica o cargo 🔇 Mutado
            await membro.add_roles(cargo_muted, reason=f"[FFC] Mute — {motivo}")

            # 5. Envia DM com timer
            if not permanente:
                await enviar_timer_dm(membro, motivo, segundos)
                asyncio.create_task(remover_mute_automatico(membro, segundos))
            else:
                try:
                    await membro.send(embed=discord.Embed(
                        title="🔇 Você foi mutado permanentemente",
                        description=(
                            f"**Motivo:** {motivo}\n\n"
                            "Seus cargos foram removidos temporariamente.\n"
                            "Entre em contato com a staff via **#suporte** para contestar."
                        ),
                        color=0xE74C3C
                    ))
                except discord.Forbidden:
                    pass

            expira_txt = "nunca (permanente)" if permanente else f"<t:{int((datetime.now(timezone.utc) + timedelta(seconds=segundos)).timestamp())}:R>"

            embed_ok = discord.Embed(
                title="🔇 Mute aplicado!",
                description=(
                    f"**Membro:** {membro.mention}\n"
                    f"**Duração:** `{duracao_texto}`\n"
                    f"**Expira:** {expira_txt}\n"
                    f"**Motivo:** {motivo}\n"
                    f"**Cargos salvos:** {len(cargos_ids)} cargo(s) serão restaurados ao final\n"
                    + ("⚠️ **Reincidente** — punição dobrada." if reincidente and not permanente else "")
                ),
                color=0xE8A020
            )
            embed_ok.set_footer(text=f"FFC • ID: {punicao_id}")

            await enviar_log(guild, discord.Embed(
                title="🔇 Mute Aplicado", color=0xE74C3C
            ).add_field(name="Membro",        value=f"{membro} (`{membro.id}`)", inline=False
            ).add_field(name="Duração",        value=duracao_texto,              inline=True
            ).add_field(name="Cargos salvos",  value=str(len(cargos_ids)),       inline=True
            ).add_field(name="Motivo",         value=motivo,                     inline=False
            ).add_field(name="Aplicado por",   value=str(interaction.user),      inline=True
            ).add_field(name="Reincidente",    value="Sim" if reincidente else "Não", inline=True))

            return await interaction.followup.send(embed=embed_ok, ephemeral=True)

        # ── BAN ──────────────────────────────────────────────────
        elif tipo == "ban":
            try:
                await membro.ban(reason=f"[FFC] {motivo} — por {interaction.user}")
            except discord.Forbidden:
                return await interaction.response.send_message(embed=embed_erro(
                    "Sem permissão", "Não foi possível banir este membro."
                ), ephemeral=True)

        # ── KICK ─────────────────────────────────────────────────
        elif tipo == "kick":
            try:
                await membro.kick(reason=f"[FFC] {motivo} — por {interaction.user}")
            except discord.Forbidden:
                return await interaction.response.send_message(embed=embed_erro(
                    "Sem permissão", "Não foi possível expulsar este membro."
                ), ephemeral=True)

        # ── ADVERTÊNCIA ──────────────────────────────────────────
        elif tipo == "advertencia":
            try:
                await membro.send(embed=discord.Embed(
                    title="⚠️ Advertência Recebida",
                    description=(
                        f"**Servidor:** {guild.name}\n"
                        f"**Motivo:** {motivo}\n\n"
                        "Esta é uma advertência formal. Reincidência resultará em punição mais severa."
                    ),
                    color=0xF39C12
                ))
            except discord.Forbidden:
                pass

        embed_ok = discord.Embed(
            title=f"✅ Punição aplicada — {tipo.upper()}",
            description=(
                f"**Membro:** {membro.mention}\n"
                f"**Duração:** `{duracao_texto}`\n"
                f"**Motivo:** {motivo}\n"
                + ("⚠️ **Reincidente** — punição dobrada." if reincidente and not permanente else "")
            ),
            color=0xE8A020
        )
        embed_ok.set_footer(text=f"FFC • ID: {punicao_id}")
        await interaction.response.send_message(embed=embed_ok, ephemeral=True)

        await enviar_log(guild, discord.Embed(
            title=f"⚠️ Punição — {tipo.upper()}", color=0xE74C3C
        ).add_field(name="Membro",       value=f"{membro} (`{membro.id}`)", inline=False
        ).add_field(name="Tipo",         value=tipo,            inline=True
        ).add_field(name="Duração",      value=duracao_texto,   inline=True
        ).add_field(name="Motivo",       value=motivo,          inline=False
        ).add_field(name="Aplicado por", value=str(interaction.user), inline=True
        ).add_field(name="Reincidente",  value="Sim" if reincidente else "Não", inline=True))

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────
class PunicoesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            cargo = discord.utils.get(guild.roles, name="🔇 Mutado")
            if cargo:
                for channel in guild.text_channels:
                    overwrite = channel.overwrites_for(cargo)
                    if overwrite.send_messages is not False:
                        try:
                            await channel.set_permissions(cargo,
                                send_messages=False,
                                add_reactions=False,
                                read_messages=True,
                            )
                        except discord.Forbidden:
                            pass

    @app_commands.command(name="advertir", description="[ADMIN] Aplica advertência a um membro.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(membro="Membro a ser advertido")
    async def advertir(self, interaction: discord.Interaction, membro: discord.Member):
        pode, motivo = guards.pode_punir(interaction.user, membro)
        if not pode:
            return await interaction.response.send_message(embed=guards.embed_sem_permissao(motivo), ephemeral=True)
        await interaction.response.send_modal(PunirModal("advertencia", membro, interaction.user))

    @app_commands.command(name="mutar", description="[ADMIN] Muta — remove cargos, aplica mute e restaura ao final.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(membro="Membro a ser mutado")
    async def mutar(self, interaction: discord.Interaction, membro: discord.Member):
        pode, motivo = guards.pode_punir(interaction.user, membro)
        if not pode:
            return await interaction.response.send_message(embed=guards.embed_sem_permissao(motivo), ephemeral=True)
        await interaction.response.send_modal(PunirModal("mute", membro, interaction.user))

    @app_commands.command(name="banir", description="[ADMIN] Bane um membro.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(membro="Membro a ser banido")
    async def banir(self, interaction: discord.Interaction, membro: discord.Member):
        pode, motivo = guards.pode_punir(interaction.user, membro)
        if not pode:
            return await interaction.response.send_message(embed=guards.embed_sem_permissao(motivo), ephemeral=True)
        await interaction.response.send_modal(PunirModal("ban", membro, interaction.user))

    @app_commands.command(name="kickar", description="[ADMIN] Expulsa um membro.")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(membro="Membro a ser expulso")
    async def kickar(self, interaction: discord.Interaction, membro: discord.Member):
        pode, motivo = guards.pode_punir(interaction.user, membro)
        if not pode:
            return await interaction.response.send_message(embed=guards.embed_sem_permissao(motivo), ephemeral=True)
        await interaction.response.send_modal(PunirModal("kick", membro, interaction.user))

    @app_commands.command(name="desmutar", description="[ADMIN] Remove o mute e restaura os cargos do membro.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(membro="Membro a ser desmutado")
    async def desmutar(self, interaction: discord.Interaction, membro: discord.Member):
        cargo_muted = discord.utils.get(interaction.guild.roles, name="🔇 Mutado")
        if not cargo_muted or cargo_muted not in membro.roles:
            return await interaction.response.send_message(embed=embed_aviso(
                "Sem mute", f"{membro.mention} não está mutado."
            ), ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # Restaura cargos salvos (inclui remoção do mute)
        await restaurar_cargos_membro(membro)

        try:
            await membro.send(embed=discord.Embed(
                title="🔊 Mute removido!",
                description="Seu mute foi removido pela staff e seus cargos foram **restaurados**.",
                color=0x2ECC71
            ))
        except discord.Forbidden:
            pass

        await interaction.followup.send(embed=discord.Embed(
            title="🔊 Membro desmutado",
            description=f"{membro.mention} foi desmutado e os cargos foram restaurados.",
            color=0x2ECC71
        ), ephemeral=True)

        await enviar_log(interaction.guild, discord.Embed(
            title="🔊 Membro Desmutado — Cargos Restaurados", color=0x2ECC71
        ).add_field(name="Membro",        value=str(membro),           inline=True
        ).add_field(name="Desmutado por", value=str(interaction.user), inline=True))

    @app_commands.command(name="historico-punicoes", description="[ADMIN] Histórico de punições de um membro.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(membro="Membro a consultar")
    async def historico_punicoes(self, interaction: discord.Interaction, membro: discord.Member):
        punicoes = await database.get_punicoes_membro(str(membro.id))
        if not punicoes:
            return await interaction.response.send_message(embed=embed_aviso(
                "Sem punições", f"{membro.mention} não possui punições registradas."
            ), ephemeral=True)
        embed = discord.Embed(title=f"📋 Histórico — {membro.display_name}", color=0xE8A020)
        for p in punicoes[:10]:
            duracao = "Permanente" if p[6] else f"{p[5]}h"
            embed.add_field(
                name=f"#{p[0]} — {p[3].upper()} ({duracao})",
                value=f"**Motivo:** {p[4]}\n**Data:** {p[8]}",
                inline=False
            )
        embed.set_footer(text=f"FFC • {len(punicoes)} punição(ões) total")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PunicoesCog(bot))

def embed_erro(t, d):  return discord.Embed(title=f"❌ {t}", description=d, color=0xE74C3C)
def embed_aviso(t, d): return discord.Embed(title=f"⚠️ {t}", description=d, color=0xF39C12)

async def enviar_log(guild, embed):
    embed.set_footer(text="Free Fire Championships • Log")
    log_ch = discord.utils.get(guild.text_channels, name="📋logs")
    if log_ch:
        await log_ch.send(embed=embed)
