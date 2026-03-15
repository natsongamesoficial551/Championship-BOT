import discord
from discord.ext import commands
from discord import app_commands
import database
import guards

# ─────────────────────────────────────────────────────────────────
# MODAL — Criar Time
# ─────────────────────────────────────────────────────────────────
class CriarTimeModal(discord.ui.Modal, title="⚔️ Criar Time — Free Fire Championships"):

    nome_time = discord.ui.TextInput(
        label="Nome do Time",
        placeholder="Ex: Team Alpha",
        min_length=3,
        max_length=30,
        required=True
    )
    modo = discord.ui.TextInput(
        label="Modo de Jogo",
        placeholder="Digite: 4v4 ou 2v2",
        min_length=3,
        max_length=3,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        member = interaction.user
        nome   = self.nome_time.value.strip()
        modo   = self.modo.value.strip().lower()

        if modo not in ["4v4", "2v2"]:
            return await interaction.response.send_message(embed=embed_erro(
                "Modo inválido", "Digite exatamente **4v4** ou **2v2**."
            ), ephemeral=True)

        jogador = await database.get_jogador(str(member.id))
        if not jogador:
            return await interaction.response.send_message(embed=embed_erro(
                "Não registrado", "Registre-se primeiro no canal **#verificação**."
            ), ephemeral=True)

        if await database.get_time_do_jogador(str(member.id)):
            time_atual = await database.get_time_do_jogador(str(member.id))
            return await interaction.response.send_message(embed=embed_aviso(
                "Já está em um time",
                f"Você já faz parte do time **{time_atual[1]}**.\nSaia antes de criar um novo."
            ), ephemeral=True)

        if await database.get_time_por_nome(nome):
            return await interaction.response.send_message(embed=embed_erro(
                "Nome já existe", f"Já existe um time com o nome **{nome}**."
            ), ephemeral=True)

        limite = 4 if modo == "4v4" else 2
        await database.criar_time(nome, str(member.id), jogador[2], modo, limite)

        embed = discord.Embed(
            title="✅ Time criado com sucesso!",
            description=(
                f"**Time:** `{nome}`\n"
                f"**Modo:** `{modo}`\n"
                f"**Capitão:** {member.mention}\n"
                f"**Vagas:** 1/{limite}\n\n"
                "Compartilhe o nome do time para seus membros entrarem."
            ),
            color=0x2ECC71
        )
        embed.set_footer(text="Free Fire Championships • Times")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        cargo = discord.utils.get(interaction.guild.roles, name="⚔ Capitão")
        if cargo:
            await member.add_roles(cargo)

        await postar_card_time(interaction.guild, nome, jogador[2], modo, limite, [jogador[2]])
        await enviar_log(interaction.guild, discord.Embed(
            title="⚔️ Time Criado", color=0x2ECC71
        ).add_field(name="Time",    value=nome,        inline=True
        ).add_field(name="Modo",    value=modo,        inline=True
        ).add_field(name="Capitão", value=str(member), inline=True))

    async def on_error(self, interaction, error):
        await interaction.response.send_message(embed=embed_erro(
            "Erro interno", "Algo deu errado. Tente novamente ou abra um ticket."
        ), ephemeral=True)
        raise error

# ─────────────────────────────────────────────────────────────────
# MODAL — Entrar em Time
# ─────────────────────────────────────────────────────────────────
class EntrarTimeModal(discord.ui.Modal, title="🎮 Entrar em Time — FFC"):

    nome_time = discord.ui.TextInput(
        label="Nome do Time",
        placeholder="Digite o nome exato do time",
        min_length=3,
        max_length=30,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        member = interaction.user
        nome   = self.nome_time.value.strip()

        jogador = await database.get_jogador(str(member.id))
        if not jogador:
            return await interaction.response.send_message(embed=embed_erro(
                "Não registrado", "Registre-se primeiro no canal **#verificação**."
            ), ephemeral=True)

        if await database.get_time_do_jogador(str(member.id)):
            time_atual = await database.get_time_do_jogador(str(member.id))
            return await interaction.response.send_message(embed=embed_aviso(
                "Já está em um time", f"Você já faz parte do time **{time_atual[1]}**."
            ), ephemeral=True)

        time = await database.get_time_por_nome(nome)
        if not time:
            return await interaction.response.send_message(embed=embed_erro(
                "Time não encontrado", f"Nenhum time com o nome **{nome}** foi encontrado."
            ), ephemeral=True)

        if time[6] == "locked":
            return await interaction.response.send_message(embed=embed_erro(
                "Time bloqueado", "Este time está em campeonato ativo. Entradas não permitidas."
            ), ephemeral=True)

        membros = await database.get_membros_time(time[0])
        if len(membros) >= time[5]:
            return await interaction.response.send_message(embed=embed_erro(
                "Time cheio", f"O time **{nome}** já atingiu o limite de **{time[5]}** jogadores."
            ), ephemeral=True)

        await database.entrar_time(time[0], str(member.id), jogador[2])
        membros_att = await database.get_membros_time(time[0])
        nicks = [m[2] for m in membros_att]

        embed = discord.Embed(
            title="✅ Entrou no time!",
            description=(
                f"**Time:** `{nome}`\n"
                f"**Modo:** `{time[4]}`\n"
                f"**Vagas:** {len(membros_att)}/{time[5]}\n"
                f"**Membros:** {', '.join(nicks)}"
            ),
            color=0x2ECC71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await postar_card_time(interaction.guild, nome, time[3], time[4], time[5], nicks)
        await enviar_log(interaction.guild, discord.Embed(
            title="➕ Jogador Entrou no Time", color=0x3498DB
        ).add_field(name="Time",    value=nome,        inline=True
        ).add_field(name="Jogador", value=str(member), inline=True
        ).add_field(name="Vagas",   value=f"{len(membros_att)}/{time[5]}", inline=True))

# ─────────────────────────────────────────────────────────────────
# VIEW — Confirmação de saída (SEM timeout para ser persistente)
# ─────────────────────────────────────────────────────────────────
class SairTimeConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # obrigatório para persistência

    @discord.ui.button(label="Confirmar saída", style=discord.ButtonStyle.danger,
                       emoji="🚪", custom_id="btn_confirmar_saida")
    async def confirmar(self, interaction: discord.Interaction, _):
        member = interaction.user
        time   = await database.get_time_do_jogador(str(member.id))
        if not time:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem time", "Você não está em nenhum time."
            ), ephemeral=True)

        if time[6] == "locked":
            return await interaction.response.send_message(embed=embed_erro(
                "Time bloqueado", "Não é possível sair durante um campeonato ativo."
            ), ephemeral=True)

        membros = await database.get_membros_time(time[0])
        if time[2] == str(member.id) and len(membros) == 1:
            await database.deletar_time(time[0])
            cargo = discord.utils.get(interaction.guild.roles, name="⚔ Capitão")
            if cargo and cargo in member.roles:
                await member.remove_roles(cargo)
            return await interaction.response.send_message(embed=discord.Embed(
                title="🗑️ Time dissolvido",
                description=f"O time **{time[1]}** foi dissolvido pois você era o único membro.",
                color=0xE74C3C
            ), ephemeral=True)

        await database.sair_time(time[0], str(member.id))
        if time[2] == str(member.id):
            cargo = discord.utils.get(interaction.guild.roles, name="⚔ Capitão")
            if cargo and cargo in member.roles:
                await member.remove_roles(cargo)

        await interaction.response.send_message(embed=discord.Embed(
            title="🚪 Saiu do time",
            description=f"Você saiu do time **{time[1]}**.",
            color=0xF39C12
        ), ephemeral=True)

        await enviar_log(interaction.guild, discord.Embed(
            title="➖ Jogador Saiu do Time", color=0xF39C12
        ).add_field(name="Time",    value=time[1],     inline=True
        ).add_field(name="Jogador", value=str(member), inline=True))

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary,
                       emoji="✖️", custom_id="btn_cancelar_saida")
    async def cancelar(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("Operação cancelada.", ephemeral=True)

# ─────────────────────────────────────────────────────────────────
# VIEW — Botões do painel de times (persistente)
# ─────────────────────────────────────────────────────────────────
class TimesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Criar Time", style=discord.ButtonStyle.success,
                       emoji="⚔️", custom_id="btn_criar_time")
    async def btn_criar(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(CriarTimeModal())

    @discord.ui.button(label="Entrar em Time", style=discord.ButtonStyle.primary,
                       emoji="🎮", custom_id="btn_entrar_time")
    async def btn_entrar(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(EntrarTimeModal())

    @discord.ui.button(label="Ver meu Time", style=discord.ButtonStyle.secondary,
                       emoji="👥", custom_id="btn_ver_time")
    async def btn_ver(self, interaction: discord.Interaction, _):
        time = await database.get_time_do_jogador(str(interaction.user.id))
        if not time:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem time", "Você não está em nenhum time.\nUse **Criar Time** ou **Entrar em Time**."
            ), ephemeral=True)

        membros = await database.get_membros_time(time[0])
        nicks   = [m[2] for m in membros]
        status  = "🔒 Bloqueado (campeonato ativo)" if time[6] == "locked" else "🟢 Aberto"

        embed = discord.Embed(title=f"👥 Time — {time[1]}", color=0xE8A020)
        embed.add_field(name="Modo",    value=time[4],                    inline=True)
        embed.add_field(name="Vagas",   value=f"{len(membros)}/{time[5]}", inline=True)
        embed.add_field(name="Status",  value=status,                     inline=True)
        embed.add_field(name="Capitão", value=time[3],                    inline=True)
        embed.add_field(name="Membros", value="\n".join(f"• {n}" for n in nicks), inline=False)
        embed.set_footer(text="Free Fire Championships • Times")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Sair do Time", style=discord.ButtonStyle.danger,
                       emoji="🚪", custom_id="btn_sair_time")
    async def btn_sair(self, interaction: discord.Interaction, _):
        time = await database.get_time_do_jogador(str(interaction.user.id))
        if not time:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem time", "Você não está em nenhum time."
            ), ephemeral=True)

        embed = discord.Embed(
            title="⚠️ Confirmar saída",
            description=f"Tem certeza que quer sair do time **{time[1]}**?",
            color=0xF39C12
        )
        await interaction.response.send_message(embed=embed, view=SairTimeConfirmView(), ephemeral=True)

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────
class TimesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def postar_embed_times(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="📝inscrição")
        if not canal:
            print(f"  ⚠️   Canal #inscrição não encontrado em {guild.name}")
            return

        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = discord.Embed(
            title="⚔️ Gerenciamento de Times",
            description=(
                "Gerencie seu time para os campeonatos!\n\n"
                "**Como funciona:**\n"
                "🆕 **Criar Time** — crie um novo time e vire capitão\n"
                "🎮 **Entrar em Time** — entre em um time existente pelo nome\n"
                "👥 **Ver meu Time** — veja membros, vagas e status\n"
                "🚪 **Sair do Time** — saia do time atual\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ Após o campeonato iniciar, **não é possível trocar membros**."
            ),
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Times")
        await canal.send(embed=embed, view=TimesView())
        print(f"  📨  Embed de times postada em {guild.name}")

    @app_commands.command(name="listar-times", description="[ADMIN] Lista todos os times cadastrados.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def listar_times(self, interaction: discord.Interaction):
        times = await database.get_todos_times()
        if not times:
            return await interaction.response.send_message(embed=embed_aviso(
                "Sem times", "Nenhum time cadastrado ainda."
            ), ephemeral=True)

        embed = discord.Embed(title="📋 Times Cadastrados", color=0xE8A020)
        for t in times:
            membros = await database.get_membros_time(t[0])
            status  = "🔒" if t[6] == "locked" else "🟢"
            embed.add_field(
                name=f"{status} {t[1]} ({t[4]})",
                value=f"Capitão: {t[3]} | {len(membros)}/{t[5]} membros",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="travar-time", description="[ADMIN] Trava/destrava roster de um time.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(nome="Nome do time")
    async def travar_time(self, interaction: discord.Interaction, nome: str):
        time = await database.get_time_por_nome(nome)
        if not time:
            return await interaction.response.send_message(embed=embed_erro(
                "Time não encontrado", f"Nenhum time com o nome **{nome}**."
            ), ephemeral=True)

        novo_status = "open" if time[6] == "locked" else "locked"
        await database.atualizar_status_time(time[0], novo_status)
        emoji = "🔒" if novo_status == "locked" else "🟢"
        acao  = "bloqueado" if novo_status == "locked" else "desbloqueado"
        await interaction.response.send_message(embed=discord.Embed(
            title=f"{emoji} Time {acao}",
            description=f"O time **{nome}** foi **{acao}** com sucesso.",
            color=0xE8A020
        ), ephemeral=True)

async def setup(bot):
    bot.add_view(TimesView())
    bot.add_view(SairTimeConfirmView())
    await bot.add_cog(TimesCog(bot))

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def embed_erro(titulo, descricao):
    return discord.Embed(title=f"❌ {titulo}", description=descricao, color=0xE74C3C)

def embed_aviso(titulo, descricao):
    return discord.Embed(title=f"⚠️ {titulo}", description=descricao, color=0xF39C12)

async def postar_card_time(guild, nome, capitao_nick, modo, limite, nicks):
    canal = discord.utils.get(guild.text_channels, name="👥times-inscritos")
    if not canal:
        return
    async for msg in canal.history(limit=100):
        if msg.author.bot and msg.embeds:
            if msg.embeds[0].title and nome in msg.embeds[0].title:
                try:
                    await msg.delete()
                except Exception:
                    pass
                break

    embed = discord.Embed(title=f"⚔️ {nome}", color=0xE8A020)
    embed.add_field(name="Modo",    value=modo,                               inline=True)
    embed.add_field(name="Capitão", value=capitao_nick,                       inline=True)
    embed.add_field(name="Vagas",   value=f"{len(nicks)}/{limite}",           inline=True)
    embed.add_field(name="Membros", value="\n".join(f"• {n}" for n in nicks), inline=False)
    embed.set_footer(text="Free Fire Championships • Times Inscritos")
    await canal.send(embed=embed)

async def enviar_log(guild, embed):
    embed.set_footer(text="Free Fire Championships • Log")
    log_ch = discord.utils.get(guild.text_channels, name="📋logs")
    if log_ch:
        await log_ch.send(embed=embed)
