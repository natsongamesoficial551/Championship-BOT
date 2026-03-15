import discord
from discord.ext import commands
from discord import app_commands
import database
import guards
import asyncio
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────
# MODAL — Envio de Resultado
# ─────────────────────────────────────────────────────────────────
class ResultadoModal(discord.ui.Modal, title="📸 Enviar Resultado — FFC"):

    time_adversario = discord.ui.TextInput(
        label="Nome do Time Adversário",
        placeholder="Ex: Team Beta (nome exato)",
        min_length=2, max_length=30, required=True
    )
    placar = discord.ui.TextInput(
        label="Placar",
        placeholder="Ex: 3x1 | Ex BR: 1° lugar",
        min_length=2, max_length=20, required=True
    )
    link_video = discord.ui.TextInput(
        label="Link do Vídeo (opcional)",
        placeholder="Ex: https://youtube.com/...",
        min_length=0, max_length=200, required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild  = interaction.guild
        member = interaction.user

        # Verifica se tem campeonato ativo
        camp = await database.get_campeonato_ativo()
        if not camp or camp[6] != "em_andamento":
            return await interaction.response.send_message(embed=embed_erro(
                "Sem campeonato ativo",
                "Não há campeonatos em andamento no momento."
            ), ephemeral=True)

        # Verifica se é capitão de um time inscrito
        time = await database.get_time_do_jogador(str(member.id))
        if not time:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem time", "Você não está em nenhum time."
            ), ephemeral=True)

        if time[2] != str(member.id):
            return await interaction.response.send_message(embed=embed_erro(
                "Apenas o capitão",
                "Somente o **capitão do time** pode enviar o resultado."
            ), ephemeral=True)

        if not await database.jogador_inscrito(camp[0], str(member.id)):
            return await interaction.response.send_message(embed=embed_erro(
                "Time não inscrito",
                "Seu time não está inscrito neste campeonato."
            ), ephemeral=True)

        # Verifica se já enviou resultado recentemente (evita duplicata)
        ultimo = await database.get_ultimo_resultado_time(camp[0], time[1])
        if ultimo and ultimo[7] == "pendente":
            return await interaction.response.send_message(embed=embed_aviso(
                "Resultado pendente",
                "Você já enviou um resultado que está aguardando aprovação da staff.\n"
                "Aguarde antes de enviar novamente."
            ), ephemeral=True)

        # Verifica prazo (30 min desde o fechamento das inscrições)
        # Registra horário do envio
        adversario = self.time_adversario.value.strip()
        placar     = self.placar.value.strip()
        link       = self.link_video.value.strip() if self.link_video.value else None

        # Valida se adversário existe no campeonato (modo com times)
        if camp[2] in ["4v4", "2v2", "br_duo", "br_squad"]:
            adversario_existe = await database.get_time_inscrito_campeonato(camp[0], adversario)
            if not adversario_existe:
                return await interaction.response.send_message(embed=embed_erro(
                    "Adversário não encontrado",
                    f"O time **{adversario}** não está inscrito neste campeonato.\n"
                    "Verifique o nome exato e tente novamente."
                ), ephemeral=True)

        # Verifica se há print anexado
        # O print é solicitado via mensagem de acompanhamento — instruímos o usuário
        resultado_id = await database.salvar_resultado(
            camp_id        = camp[0],
            time_nome      = time[1],
            time_id        = time[0],
            adversario     = adversario,
            placar         = placar,
            link_video     = link,
            enviado_por    = str(member.id)
        )

        embed_ok = discord.Embed(
            title="✅ Resultado enviado!",
            description=(
                f"**Campeonato:** {camp[1]}\n"
                f"**Seu time:** `{time[1]}`\n"
                f"**Adversário:** `{adversario}`\n"
                f"**Placar:** `{placar}`\n"
                f"**Vídeo:** {link or '—'}\n\n"
                "⏳ Aguardando aprovação da staff.\n"
                "⚠️ **Não se esqueça:** envie o print no canal **#📸provas-de-partida** agora!"
            ),
            color=0xF39C12
        )
        embed_ok.set_footer(text=f"FFC • ID do resultado: {resultado_id}")
        await interaction.response.send_message(embed=embed_ok, ephemeral=True)

        # Envia para verificação da staff
        await notificar_staff_resultado(guild, member, time[1], adversario, placar, link, resultado_id, camp[1])

        await enviar_log(guild, discord.Embed(
            title="📸 Resultado Enviado", color=0xF39C12
        ).add_field(name="Campeonato",  value=camp[1],     inline=False
        ).add_field(name="Time",        value=time[1],     inline=True
        ).add_field(name="Adversário",  value=adversario,  inline=True
        ).add_field(name="Placar",      value=placar,      inline=True
        ).add_field(name="Enviado por", value=str(member), inline=True))

    async def on_error(self, interaction, error):
        await interaction.response.send_message(embed=embed_erro(
            "Erro interno", "Algo deu errado. Tente novamente ou abra um ticket."
        ), ephemeral=True)
        raise error

# ─────────────────────────────────────────────────────────────────
# VIEW — Botão no canal #provas-de-partida
# ─────────────────────────────────────────────────────────────────
class ProvasView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar Resultado", style=discord.ButtonStyle.success,
                       emoji="📸", custom_id="btn_enviar_resultado")
    async def btn_resultado(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(ResultadoModal())

    @discord.ui.button(label="Ver meus Resultados", style=discord.ButtonStyle.secondary,
                       emoji="📊", custom_id="btn_ver_resultados")
    async def btn_ver(self, interaction: discord.Interaction, _):
        time = await database.get_time_do_jogador(str(interaction.user.id))
        camp = await database.get_campeonato_ativo()

        if not camp or not time:
            return await interaction.response.send_message(embed=embed_aviso(
                "Sem dados", "Você não está em um time ou não há campeonato ativo."
            ), ephemeral=True)

        resultados = await database.get_resultados_time(camp[0], time[1])
        if not resultados:
            return await interaction.response.send_message(embed=embed_aviso(
                "Sem resultados", "Seu time ainda não enviou nenhum resultado neste campeonato."
            ), ephemeral=True)

        embed = discord.Embed(title=f"📊 Resultados — {time[1]}", color=0xE8A020)
        for r in resultados:
            status_emoji = {"pendente": "⏳", "aprovado": "✅", "contestado": "❌"}.get(r[7], "❓")
            embed.add_field(
                name=f"{status_emoji} vs {r[4]} — {r[5]}",
                value=f"Status: **{r[7]}**" + (f"\nMotivo: {r[8]}" if r[8] else ""),
                inline=False
            )
        embed.set_footer(text="FFC • Resultados")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ─────────────────────────────────────────────────────────────────
# VIEW — Staff aprova/contesta (canal #verificação-de-resultados)
# ─────────────────────────────────────────────────────────────────
class AprovarResultadoView(discord.ui.View):
    def __init__(self, resultado_id: int):
        super().__init__(timeout=None)
        self.resultado_id = resultado_id
        for item in self.children:
            item.custom_id = f"{item.custom_id}_{resultado_id}"

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success,
                       emoji="✅", custom_id="btn_aprovar_resultado")
    async def btn_aprovar(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem permissão", "Apenas staff pode aprovar resultados."
            ), ephemeral=True)

        resultado = await database.get_resultado_por_id(self.resultado_id)
        if not resultado:
            return await interaction.response.send_message(embed=embed_erro(
                "Resultado não encontrado", "Este resultado não existe mais no banco."
            ), ephemeral=True)

        if resultado[7] != "pendente":
            return await interaction.response.send_message(embed=embed_aviso(
                "Já processado", f"Este resultado já foi **{resultado[7]}**."
            ), ephemeral=True)

        await database.atualizar_resultado(self.resultado_id, "aprovado", None)

        # Atualiza ranking do time
        await database.incrementar_ranking(resultado[3], resultado[2], "vitoria")

        # Posta no canal #resultados
        await postar_resultado_oficial(interaction.guild, resultado)

        # Notifica o capitão
        await notificar_capitao(interaction.guild, resultado, aprovado=True, motivo=None)

        await interaction.message.edit(
            embed=interaction.message.embeds[0].set_field_at(
                -1, name="Status", value="✅ Aprovado por " + str(interaction.user)
            ),
            view=None
        )
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Resultado aprovado!",
            description=f"**{resultado[3]}** vs **{resultado[4]}** — `{resultado[5]}`",
            color=0x2ECC71
        ), ephemeral=True)

        await enviar_log(interaction.guild, discord.Embed(
            title="✅ Resultado Aprovado", color=0x2ECC71
        ).add_field(name="Time",         value=resultado[3],        inline=True
        ).add_field(name="Adversário",   value=resultado[4],        inline=True
        ).add_field(name="Placar",       value=resultado[5],        inline=True
        ).add_field(name="Aprovado por", value=str(interaction.user), inline=False))

    @discord.ui.button(label="Contestar", style=discord.ButtonStyle.danger,
                       emoji="❌", custom_id="btn_contestar_resultado")
    async def btn_contestar(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem permissão", "Apenas staff pode contestar resultados."
            ), ephemeral=True)
        await interaction.response.send_modal(ContestarModal(self.resultado_id))

# ─────────────────────────────────────────────────────────────────
# MODAL — Contestar resultado
# ─────────────────────────────────────────────────────────────────
class ContestarModal(discord.ui.Modal, title="❌ Contestar Resultado — FFC"):
    def __init__(self, resultado_id: int):
        super().__init__()
        self.resultado_id = resultado_id

    motivo = discord.ui.TextInput(
        label="Motivo da Contestação",
        placeholder="Ex: Print inválido, resultado não confere com o jogo...",
        style=discord.TextStyle.paragraph,
        min_length=10, max_length=300, required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        resultado = await database.get_resultado_por_id(self.resultado_id)
        if not resultado:
            return await interaction.response.send_message(embed=embed_erro(
                "Não encontrado", "Resultado não existe mais."
            ), ephemeral=True)

        motivo_val = self.motivo.value.strip()
        await database.atualizar_resultado(self.resultado_id, "contestado", motivo_val)

        # Notifica o capitão
        await notificar_capitao(interaction.guild, resultado, aprovado=False, motivo=motivo_val)

        await interaction.message.edit(
            embed=interaction.message.embeds[0].set_field_at(
                -1, name="Status", value="❌ Contestado por " + str(interaction.user)
            ),
            view=None
        )
        await interaction.response.send_message(embed=discord.Embed(
            title="❌ Resultado contestado",
            description=f"Motivo registrado e capitão notificado.",
            color=0xE74C3C
        ), ephemeral=True)

        await enviar_log(interaction.guild, discord.Embed(
            title="❌ Resultado Contestado", color=0xE74C3C
        ).add_field(name="Time",          value=resultado[3],          inline=True
        ).add_field(name="Adversário",    value=resultado[4],          inline=True
        ).add_field(name="Motivo",        value=motivo_val,            inline=False
        ).add_field(name="Contestado por", value=str(interaction.user), inline=False))

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────
class ResultadosCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def postar_embed_provas(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="📸provas-de-partida")
        if not canal:
            print(f"  ⚠️   Canal #provas-de-partida não encontrado em {guild.name}")
            return

        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = discord.Embed(
            title="📸 Envio de Resultados",
            description=(
                "Aqui o capitão do time vencedor registra o resultado da partida.\n\n"
                "**Regras de envio:**\n"
                "📸 **Print obrigatório** — envie a imagem no chat após clicar no botão\n"
                "🔗 **Vídeo** — opcional mas recomendado\n"
                "⏱️ **Prazo** — 30 minutos após o fim da partida\n"
                "👤 **Quem envia** — apenas o **capitão** do time vencedor\n"
                "🎯 **Informe o adversário** — nome exato do time adversário\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ Resultado falso = **Ban 7 dias + eliminação do campeonato**\n"
                "⚠️ W.O sem aviso = **Advertência + 24h mutado**"
            ),
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Resultados")
        await canal.send(embed=embed, view=ProvasView())
        print(f"  📨  Embed de provas postada em {guild.name}")

    # ── Comando admin: /aprovar-resultado ─────────────────────────
    @app_commands.command(name="aprovar-resultado", description="[ADMIN] Aprova um resultado pelo ID.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(resultado_id="ID do resultado (visível na embed de verificação)")
    async def aprovar_resultado(self, interaction: discord.Interaction, resultado_id: int):
        resultado = await database.get_resultado_por_id(resultado_id)
        if not resultado:
            return await interaction.response.send_message(embed=embed_erro(
                "Não encontrado", f"Nenhum resultado com ID `{resultado_id}`."
            ), ephemeral=True)

        if resultado[7] != "pendente":
            return await interaction.response.send_message(embed=embed_aviso(
                "Já processado", f"Este resultado já foi **{resultado[7]}**."
            ), ephemeral=True)

        await database.atualizar_resultado(resultado_id, "aprovado", None)
        await database.incrementar_ranking(resultado[3], resultado[2], "vitoria")
        await postar_resultado_oficial(interaction.guild, resultado)
        await notificar_capitao(interaction.guild, resultado, aprovado=True, motivo=None)

        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Resultado aprovado!",
            description=f"**{resultado[3]}** vs **{resultado[4]}** — `{resultado[5]}`",
            color=0x2ECC71
        ), ephemeral=True)

    # ── Comando admin: /contestar-resultado ───────────────────────
    @app_commands.command(name="contestar-resultado", description="[ADMIN] Contesta um resultado pelo ID.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(resultado_id="ID do resultado", motivo="Motivo da contestação")
    async def contestar_resultado(self, interaction: discord.Interaction, resultado_id: int, motivo: str):
        resultado = await database.get_resultado_por_id(resultado_id)
        if not resultado:
            return await interaction.response.send_message(embed=embed_erro(
                "Não encontrado", f"Nenhum resultado com ID `{resultado_id}`."
            ), ephemeral=True)

        await database.atualizar_resultado(resultado_id, "contestado", motivo)
        await notificar_capitao(interaction.guild, resultado, aprovado=False, motivo=motivo)

        await interaction.response.send_message(embed=discord.Embed(
            title="❌ Resultado contestado",
            description=f"Motivo: {motivo}",
            color=0xE74C3C
        ), ephemeral=True)

async def setup(bot):
    bot.add_view(ProvasView())
    await bot.add_cog(ResultadosCog(bot))

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def embed_erro(titulo, descricao):
    return discord.Embed(title=f"❌ {titulo}", description=descricao, color=0xE74C3C)

def embed_aviso(titulo, descricao):
    return discord.Embed(title=f"⚠️ {titulo}", description=descricao, color=0xF39C12)

async def notificar_staff_resultado(guild, member, time_nome, adversario, placar, link, resultado_id, camp_nome):
    canal = discord.utils.get(guild.text_channels, name="✅verificação-de-resultados")
    if not canal:
        return

    embed = discord.Embed(
        title="📸 Resultado Aguardando Aprovação",
        color=0xF39C12
    )
    embed.add_field(name="Campeonato",  value=camp_nome,           inline=False)
    embed.add_field(name="Time",        value=time_nome,           inline=True)
    embed.add_field(name="Adversário",  value=adversario,          inline=True)
    embed.add_field(name="Placar",      value=placar,              inline=True)
    embed.add_field(name="Vídeo",       value=link or "—",         inline=False)
    embed.add_field(name="Capitão",     value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Status",      value="⏳ Pendente",       inline=True)
    embed.set_footer(text=f"FFC • ID do resultado: {resultado_id}")

    await canal.send(embed=embed, view=AprovarResultadoView(resultado_id))

async def postar_resultado_oficial(guild, resultado):
    # Detecta se é BR pelo campeonato associado
    camp = await database.get_campeonato_por_id(resultado[1])
    is_br = camp and camp[2].startswith("br_")

    # Posta no canal correto
    nome_ch = "🌐battle-royale-resultados" if is_br else "🎯resultados"
    canal   = discord.utils.get(guild.text_channels, name=nome_ch)
    if not canal:
        return

    emoji_titulo = "🌐" if is_br else "🏆"
    embed = discord.Embed(
        title=f"{emoji_titulo} Resultado Oficial",
        color=0x2ECC71
    )
    embed.add_field(name="🥇 Vencedor",   value=resultado[3], inline=True)
    embed.add_field(name="⚔️ Adversário", value=resultado[4], inline=True)
    embed.add_field(name="📊 Placar",     value=resultado[5], inline=True)
    if is_br and camp:
        MODO_LABEL = {"br_solo": "Solo", "br_duo": "Duo", "br_squad": "Squad"}
        embed.add_field(name="🌐 Modo BR", value=MODO_LABEL.get(camp[2], camp[2]), inline=True)
    if resultado[6]:
        embed.add_field(name="🎥 Vídeo", value=resultado[6], inline=False)
    embed.set_footer(text="Free Fire Championships • Resultado Oficial")
    await canal.send(embed=embed)

async def notificar_capitao(guild, resultado, aprovado: bool, motivo: str):
    # Busca o membro pelo discord_id do enviado_por
    member = guild.get_member(int(resultado[9]))
    if not member:
        return

    if aprovado:
        embed = discord.Embed(
            title="✅ Resultado aprovado!",
            description=(
                f"Seu resultado foi **aprovado** pela staff!\n\n"
                f"**Time:** {resultado[3]}\n"
                f"**Adversário:** {resultado[4]}\n"
                f"**Placar:** {resultado[5]}\n\n"
                "O ranking foi atualizado. 🏆"
            ),
            color=0x2ECC71
        )
    else:
        embed = discord.Embed(
            title="❌ Resultado contestado",
            description=(
                f"Seu resultado foi **contestado** pela staff.\n\n"
                f"**Time:** {resultado[3]}\n"
                f"**Adversário:** {resultado[4]}\n"
                f"**Placar:** {resultado[5]}\n\n"
                f"**Motivo:** {motivo}\n\n"
                "Se acredita que é um erro, abra um ticket em **#suporte**."
            ),
            color=0xE74C3C
        )

    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        # DM fechada — notifica no canal de suporte
        canal = discord.utils.get(guild.text_channels, name="🎫suporte")
        if canal:
            await canal.send(f"{member.mention}", embed=embed)

async def enviar_log(guild, embed):
    embed.set_footer(text="Free Fire Championships • Log")
    log_ch = discord.utils.get(guild.text_channels, name="📋logs")
    if log_ch:
        await log_ch.send(embed=embed)
