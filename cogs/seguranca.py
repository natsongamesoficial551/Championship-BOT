import discord
from discord.ext import commands
from discord import app_commands
import database
import guards
import asyncio
import shutil
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "database.db")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "backups")

# ─────────────────────────────────────────────────────────────────
# COG — Segurança, Logs Avançados, Status, Season
# ─────────────────────────────────────────────────────────────────
class SegurancaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────────────────────
    # BACKUP AUTOMÁTICO — a cada 6h
    # ─────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self._backup_automatico())
        self.bot.loop.create_task(self._limpar_cooldowns())

    async def _backup_automatico(self):
        await self.bot.wait_until_ready()
        os.makedirs(BACKUP_DIR, exist_ok=True)
        while not self.bot.is_closed():
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                destino = os.path.join(BACKUP_DIR, f"backup_{ts}.db")
                shutil.copy2(DB_PATH, destino)

                # Manter só os últimos 10 backups
                backups = sorted(
                    [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")],
                    reverse=True
                )
                for antigo in backups[10:]:
                    os.remove(os.path.join(BACKUP_DIR, antigo))

                print(f"  💾  Backup criado: backup_{ts}.db ({len(backups)} total)")

                # Log no Discord
                for guild in self.bot.guilds:
                    await self._log_sistema(guild, discord.Embed(
                        title="💾 Backup Automático",
                        description=f"Banco de dados salvo com sucesso.\n`backup_{ts}.db`",
                        color=0x3498DB
                    ))
            except Exception as e:
                print(f"  ❌  Erro no backup: {e}")

            await asyncio.sleep(21600)  # 6 horas

    async def _limpar_cooldowns(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            guards.limpar_cooldowns_antigos()
            await asyncio.sleep(300)  # a cada 5 min

    # ─────────────────────────────────────────────────────────────
    # LOGS AVANÇADOS — edições e deleções de mensagem
    # ─────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content:
            return
        await self._log_sistema(before.guild, discord.Embed(
            title="✏️ Mensagem Editada",
            color=0xF39C12
        ).add_field(name="Autor",   value=f"{before.author} (`{before.author.id}`)", inline=False
        ).add_field(name="Canal",   value=before.channel.mention, inline=True
        ).add_field(name="Antes",   value=before.content[:400] or "—", inline=False
        ).add_field(name="Depois",  value=after.content[:400]  or "—", inline=False))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        await self._log_sistema(message.guild, discord.Embed(
            title="🗑️ Mensagem Deletada",
            color=0xE74C3C
        ).add_field(name="Autor",    value=f"{message.author} (`{message.author.id}`)", inline=False
        ).add_field(name="Canal",    value=message.channel.mention, inline=True
        ).add_field(name="Conteúdo", value=message.content[:400] or "—", inline=False))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._log_sistema(member.guild, discord.Embed(
            title="🚪 Membro Saiu",
            color=0xE74C3C
        ).add_field(name="Membro", value=f"{member} (`{member.id}`)", inline=False
        ).add_field(name="Cargos", value=", ".join(r.name for r in member.roles[1:]) or "—", inline=False))

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self._log_sistema(guild, discord.Embed(
            title="🔨 Membro Banido",
            color=0xE74C3C
        ).add_field(name="Membro", value=f"{user} (`{user.id}`)", inline=False))

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self._log_sistema(guild, discord.Embed(
            title="✅ Ban Removido",
            color=0x2ECC71
        ).add_field(name="Membro", value=f"{user} (`{user.id}`)", inline=False))

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Loga tentativas suspeitas — interações em canais errados."""
        if not interaction.guild:
            return
        # Detecta uso de comandos slash por não-verificados
        if interaction.type == discord.InteractionType.application_command:
            nivel = guards.get_nivel(interaction.user)
            if nivel < 0:
                await self._log_sistema(interaction.guild, discord.Embed(
                    title="⚠️ Tentativa Suspeita",
                    description="Visitante não verificado tentou usar um comando.",
                    color=0xE74C3C
                ).add_field(name="Usuário",  value=f"{interaction.user} (`{interaction.user.id}`)", inline=False
                ).add_field(name="Comando",  value=str(interaction.data.get("name", "?")), inline=True))

    # ─────────────────────────────────────────────────────────────
    # /status — Painel de status do bot
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(name="status", description="[ADMIN] Painel de status completo do servidor.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def status(self, interaction: discord.Interaction):
        guild = interaction.guild

        camp        = await database.get_campeonato_ativo()
        inscritos   = await database.get_inscritos_campeonato(camp[0]) if camp else []
        times       = await database.get_todos_times()
        tickets     = await database.get_tickets_abertos()
        jogadores   = await database.get_total_jogadores()
        backups     = os.listdir(BACKUP_DIR) if os.path.exists(BACKUP_DIR) else []
        ultimo_bkp  = sorted(backups)[-1] if backups else "Nenhum"

        # Resultados pendentes
        pendentes = 0
        if camp:
            todos_res = await database.get_todos_resultados_campeonato(camp[0])
            pendentes = sum(1 for r in todos_res if r[7] == "pendente")

        embed = discord.Embed(
            title="📊 Status — Free Fire Championships",
            color=0xE8A020
        )
        embed.add_field(name="🎮 Jogadores Registrados", value=str(jogadores),              inline=True)
        embed.add_field(name="⚔️ Times Ativos",          value=str(len(times)),             inline=True)
        embed.add_field(name="🎫 Tickets Abertos",       value=str(len(tickets)),           inline=True)

        if camp:
            embed.add_field(
                name=f"🏆 Campeonato Ativo",
                value=(
                    f"**{camp[1]}**\n"
                    f"Modo: `{camp[2]}` | Status: `{camp[6]}`\n"
                    f"Inscritos: {len(inscritos)}/{camp[4]} (mín)\n"
                    f"Resultados pendentes: {pendentes}"
                ),
                inline=False
            )
        else:
            embed.add_field(name="🏆 Campeonato", value="Nenhum ativo", inline=False)

        embed.add_field(name="💾 Último Backup",  value=ultimo_bkp,            inline=True)
        embed.add_field(name="📦 Backups Salvos", value=str(len(backups)),     inline=True)
        embed.add_field(name="🤖 Latência",       value=f"{round(self.bot.latency*1000)}ms", inline=True)
        embed.set_footer(text=f"FFC • {guild.member_count} membros no servidor")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ─────────────────────────────────────────────────────────────
    # /backup-manual — Força backup agora
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(name="backup", description="[ADMIN] Força um backup manual do banco.")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_manual(self, interaction: discord.Interaction):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(BACKUP_DIR, f"backup_manual_{ts}.db")
        shutil.copy2(DB_PATH, destino)
        await interaction.response.send_message(embed=discord.Embed(
            title="💾 Backup Criado",
            description=f"`backup_manual_{ts}.db` salvo com sucesso.",
            color=0x2ECC71
        ), ephemeral=True)

    # ─────────────────────────────────────────────────────────────
    # /nova-season — Reseta ranking e times para nova temporada
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(name="nova-season", description="[CEO] Inicia nova Season — reseta ranking e times.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(numero="Número da nova season (Ex: 2)")
    async def nova_season(self, interaction: discord.Interaction, numero: int):
        # Só CEO pode resetar
        nivel = guards.get_nivel(interaction.user)
        if nivel < 5:
            return await interaction.response.send_message(
                embed=guards.embed_sem_permissao("Apenas o **CEO** pode iniciar uma nova Season."),
                ephemeral=True
            )

        # Confirmação de segurança
        embed = discord.Embed(
            title=f"⚠️ Iniciar Season {numero}?",
            description=(
                "Esta ação irá:\n\n"
                "🔄 **Zerar** todos os pontos de ranking\n"
                "🗑️ **Deletar** todos os times\n"
                "🏁 **Cancelar** campeonato ativo (se houver)\n\n"
                "**Esta ação é irreversível.**\n"
                "Certifique-se de ter feito backup antes."
            ),
            color=0xE74C3C
        )
        await interaction.response.send_message(
            embed=embed,
            view=ConfirmarSeasonView(numero, interaction.user.id),
            ephemeral=True
        )

    # ─────────────────────────────────────────────────────────────
    # HELPER LOG
    # ─────────────────────────────────────────────────────────────
    async def _log_sistema(self, guild: discord.Guild, embed: discord.Embed):
        if not guild:
            return
        embed.set_footer(text="Free Fire Championships • Log do Sistema")
        log_ch = discord.utils.get(guild.text_channels, name="📋logs")
        if log_ch:
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

# ─────────────────────────────────────────────────────────────────
# VIEW — Confirmação de nova Season
# ─────────────────────────────────────────────────────────────────
class ConfirmarSeasonView(discord.ui.View):
    def __init__(self, numero: int, autor_id: int):
        super().__init__(timeout=30)
        self.numero   = numero
        self.autor_id = autor_id

    @discord.ui.button(label="Confirmar — Iniciar Season", style=discord.ButtonStyle.danger,
                       emoji="🚀", custom_id="btn_confirmar_season")
    async def confirmar(self, interaction: discord.Interaction, _):
        if interaction.user.id != self.autor_id:
            return await interaction.response.send_message(
                embed=guards.embed_sem_permissao("Só quem iniciou pode confirmar."),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # Backup antes de resetar
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(BACKUP_DIR, f"pre_season{self.numero}_{ts}.db")
        shutil.copy2(DB_PATH, destino)

        # Reseta ranking, times e membros
        await database.resetar_season()

        # Anuncia no servidor
        for guild in interaction.client.guilds:
            canal_anuncios = discord.utils.get(guild.text_channels, name="📢anúncios")
            if canal_anuncios:
                embed_anuncio = discord.Embed(
                    title=f"🏁 Season {self.numero} Iniciada!",
                    description=(
                        f"A **Season {self.numero}** do Free Fire Championships começou!\n\n"
                        "🔄 Rankings zerados\n"
                        "⚔️ Times resetados\n"
                        "🏆 Novos campeonatos em breve!\n\n"
                        "Boa sorte a todos! 🎮"
                    ),
                    color=0xE8A020
                )
                await canal_anuncios.send(content="@everyone", embed=embed_anuncio)

            # Log
            log_ch = discord.utils.get(guild.text_channels, name="📋logs")
            if log_ch:
                await log_ch.send(embed=discord.Embed(
                    title=f"🏁 Season {self.numero} Iniciada",
                    color=0xE8A020
                ).add_field(name="Iniciada por", value=str(interaction.user), inline=True
                ).add_field(name="Backup",       value=f"pre_season{self.numero}_{ts}.db", inline=True))

        await interaction.followup.send(embed=discord.Embed(
            title=f"✅ Season {self.numero} iniciada!",
            description=f"Backup salvo antes do reset.\nAnúncio postado no servidor.",
            color=0x2ECC71
        ), ephemeral=True)
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("Operação cancelada.", ephemeral=True)
        self.stop()

async def setup(bot):
    await bot.add_cog(SegurancaCog(bot))
