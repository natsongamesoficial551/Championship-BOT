import discord
from discord.ext import commands
from discord import app_commands
import database
import asyncio

CATEGORIAS_TICKET = {
    "denuncia":  ("🚨", "Denúncia",          "Denúncia contra jogador ou staff"),
    "resultado": ("📸", "Resultado",          "Contestação de resultado de partida"),
    "pagamento": ("💰", "Pagamento",          "Problemas com pagamento ou PIX"),
    "duvida":    ("❓", "Dúvida",             "Dúvidas gerais sobre o servidor"),
    "tecnico":   ("🔧", "Problema Técnico",   "Problemas técnicos com o bot"),
}

# ─────────────────────────────────────────────────────────────────
# VIEW — Seletor de categoria do ticket
# ─────────────────────────────────────────────────────────────────
class CategoriaTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Denúncia",        style=discord.ButtonStyle.danger,
                       emoji="🚨", custom_id="ticket_denuncia")
    async def denuncia(self, interaction: discord.Interaction, _):
        await abrir_ticket(interaction, "denuncia")

    @discord.ui.button(label="Resultado",       style=discord.ButtonStyle.primary,
                       emoji="📸", custom_id="ticket_resultado")
    async def resultado(self, interaction: discord.Interaction, _):
        await abrir_ticket(interaction, "resultado")

    @discord.ui.button(label="Pagamento",       style=discord.ButtonStyle.success,
                       emoji="💰", custom_id="ticket_pagamento")
    async def pagamento(self, interaction: discord.Interaction, _):
        await abrir_ticket(interaction, "pagamento")

    @discord.ui.button(label="Dúvida",          style=discord.ButtonStyle.secondary,
                       emoji="❓", custom_id="ticket_duvida")
    async def duvida(self, interaction: discord.Interaction, _):
        await abrir_ticket(interaction, "duvida")

    @discord.ui.button(label="Prob. Técnico",   style=discord.ButtonStyle.secondary,
                       emoji="🔧", custom_id="ticket_tecnico")
    async def tecnico(self, interaction: discord.Interaction, _):
        await abrir_ticket(interaction, "tecnico")

# ─────────────────────────────────────────────────────────────────
# VIEW — Dentro do ticket (fechar)
# ─────────────────────────────────────────────────────────────────
class TicketAbertoView(discord.ui.View):
    def __init__(self, ticket_id: int):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        for item in self.children:
            item.custom_id = f"{item.custom_id}_{ticket_id}"

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger,
                       emoji="🔒", custom_id="btn_fechar_ticket")
    async def fechar(self, interaction: discord.Interaction, _):
        # Staff ou o próprio dono pode fechar
        ticket = await database.get_ticket(self.ticket_id)
        if not ticket:
            return await interaction.response.send_message(embed=embed_erro(
                "Ticket não encontrado", "Este ticket não existe no banco."
            ), ephemeral=True)

        eh_dono  = str(interaction.user.id) == ticket[1]
        eh_staff = interaction.user.guild_permissions.manage_roles

        if not eh_dono and not eh_staff:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem permissão", "Apenas o autor ou a staff podem fechar este ticket."
            ), ephemeral=True)

        await database.atualizar_ticket(self.ticket_id, "fechado")

        embed = discord.Embed(
            title="🔒 Ticket Fechado",
            description=(
                f"Ticket fechado por {interaction.user.mention}.\n"
                "Este canal será deletado em **5 segundos**."
            ),
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)

        try:
            await interaction.channel.delete(reason="Ticket fechado")
        except Exception:
            pass

        await enviar_log(interaction.guild, discord.Embed(
            title="🔒 Ticket Fechado", color=0xE74C3C
        ).add_field(name="Ticket ID",   value=str(self.ticket_id),    inline=True
        ).add_field(name="Fechado por", value=str(interaction.user),  inline=True))

    @discord.ui.button(label="Marcar como Resolvido", style=discord.ButtonStyle.success,
                       emoji="✅", custom_id="btn_resolver_ticket")
    async def resolver(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem permissão", "Apenas a staff pode marcar como resolvido."
            ), ephemeral=True)

        await database.atualizar_ticket(self.ticket_id, "resolvido")
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Ticket Resolvido",
            description="Este ticket foi marcado como resolvido pela staff.",
            color=0x2ECC71
        ))

        await enviar_log(interaction.guild, discord.Embed(
            title="✅ Ticket Resolvido", color=0x2ECC71
        ).add_field(name="Ticket ID",    value=str(self.ticket_id),   inline=True
        ).add_field(name="Resolvido por", value=str(interaction.user), inline=True))

# ─────────────────────────────────────────────────────────────────
# COG — Suporte
# ─────────────────────────────────────────────────────────────────
class SuporteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def postar_embed_suporte(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="🎫suporte")
        if not canal:
            print(f"  ⚠️   Canal #suporte não encontrado em {guild.name}")
            return

        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = discord.Embed(
            title="🎫 Central de Suporte — FFC",
            description=(
                "Precisa de ajuda? Abra um ticket clicando no botão da categoria correta.\n\n"
                "🚨 **Denúncia** — jogador usando hack, comportamento inadequado\n"
                "📸 **Resultado** — contestação de resultado de partida\n"
                "💰 **Pagamento** — problema com PIX ou taxa de inscrição\n"
                "❓ **Dúvida** — qualquer dúvida sobre o servidor\n"
                "🔧 **Prob. Técnico** — bug no bot ou erro de sistema\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ Tickets sem resposta por mais de 24h serão fechados automaticamente.\n"
                "⚠️ Abrir tickets falsos resultará em punição."
            ),
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Suporte")
        await canal.send(embed=embed, view=CategoriaTicketView())
        print(f"  📨  Embed de suporte postada em {guild.name}")

    # ── Auto-fechar tickets inativos após 24h ─────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self._verificar_tickets_inativos())

    async def _verificar_tickets_inativos(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            tickets = await database.get_tickets_abertos()
            for ticket in tickets:
                canal = discord.utils.get(
                    self.bot.get_all_channels(), name=f"ticket-{ticket[0]}"
                )
                if canal:
                    ultima_msg = None
                    async for msg in canal.history(limit=1):
                        ultima_msg = msg
                    if ultima_msg:
                        inativo = (discord.utils.utcnow() - ultima_msg.created_at).total_seconds()
                        if inativo > 86400:  # 24h
                            await database.atualizar_ticket(ticket[0], "fechado")
                            embed = discord.Embed(
                                title="⏰ Ticket Fechado por Inatividade",
                                description="Este ticket foi fechado automaticamente após 24h sem resposta.",
                                color=0xF39C12
                            )
                            await canal.send(embed=embed)
                            await asyncio.sleep(5)
                            try:
                                await canal.delete(reason="Ticket inativo 24h")
                            except Exception:
                                pass
            await asyncio.sleep(3600)  # verifica a cada 1h

async def setup(bot):
    bot.add_view(CategoriaTicketView())
    await bot.add_cog(SuporteCog(bot))

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def embed_erro(titulo, descricao):
    return discord.Embed(title=f"❌ {titulo}", description=descricao, color=0xE74C3C)

def embed_aviso(titulo, descricao):
    return discord.Embed(title=f"⚠️ {titulo}", description=descricao, color=0xF39C12)

async def abrir_ticket(interaction: discord.Interaction, categoria: str):
    guild  = interaction.guild
    member = interaction.user

    # Verificar se já tem ticket aberto
    ticket_existente = await database.get_ticket_aberto_membro(str(member.id))
    if ticket_existente:
        canal_existente = discord.utils.get(guild.text_channels, name=f"ticket-{ticket_existente[0]}")
        if canal_existente:
            return await interaction.response.send_message(embed=discord.Embed(
                title="⚠️ Ticket já aberto",
                description=f"Você já tem um ticket aberto: {canal_existente.mention}\nFeche o atual antes de abrir outro.",
                color=0xF39C12
            ), ephemeral=True)

    emoji, nome, descricao = CATEGORIAS_TICKET[categoria]

    # Salvar no banco
    ticket_id = await database.criar_ticket(str(member.id), str(member), categoria)

    # Buscar categoria Staff no Discord
    cat_staff = discord.utils.get(guild.categories, name="🔒 STAFF")

    # Permissões do canal do ticket
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member:             discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    # Adiciona permissão para cada cargo staff
    for nome_cargo in ["👑 CEO", "⚙ DEV", "🛡 ADM", "📢 MRKT"]:
        cargo = discord.utils.get(guild.roles, name=nome_cargo)
        if cargo:
            overwrites[cargo] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_messages=True
            )

    canal_ticket = await guild.create_text_channel(
        name=f"ticket-{ticket_id}",
        category=cat_staff,
        overwrites=overwrites,
        topic=f"Ticket #{ticket_id} | {nome} | {member}",
        reason=f"Ticket aberto por {member}"
    )

    embed = discord.Embed(
        title=f"{emoji} Ticket #{ticket_id} — {nome}",
        description=(
            f"Olá {member.mention}, seu ticket foi aberto!\n\n"
            f"**Categoria:** {descricao}\n\n"
            "Descreva seu problema com o máximo de detalhes possível.\n"
            "A staff entrará em contato em breve.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 Clique em **Fechar Ticket** quando resolver.\n"
            "✅ A staff pode marcar como **Resolvido**."
        ),
        color=0xE8A020
    )
    embed.set_footer(text=f"FFC • Ticket #{ticket_id}")
    await canal_ticket.send(content=member.mention, embed=embed, view=TicketAbertoView(ticket_id))

    await interaction.response.send_message(embed=discord.Embed(
        title="✅ Ticket aberto!",
        description=f"Seu ticket foi criado: {canal_ticket.mention}",
        color=0x2ECC71
    ), ephemeral=True)

    await enviar_log(guild, discord.Embed(
        title=f"{emoji} Ticket Aberto — {nome}", color=0xE8A020
    ).add_field(name="Membro",    value=f"{member} (`{member.id}`)", inline=False
    ).add_field(name="Categoria", value=nome,                        inline=True
    ).add_field(name="Canal",     value=canal_ticket.mention,        inline=True))

async def enviar_log(guild, embed):
    embed.set_footer(text="Free Fire Championships • Log")
    log_ch = discord.utils.get(guild.text_channels, name="📋logs")
    if log_ch:
        await log_ch.send(embed=embed)
