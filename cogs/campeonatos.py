import discord
from discord.ext import commands
from discord import app_commands
import database
import guards
import asyncio

# ─────────────────────────────────────────────────────────────────
# MODAL — Admin abre campeonato
# ─────────────────────────────────────────────────────────────────
class AbrirCampeonatoModal(discord.ui.Modal, title="🏆 Abrir Campeonato — FFC"):

    nome = discord.ui.TextInput(
        label="Nome do Campeonato",
        placeholder="Ex: Championship Season 1 — 4v4",
        min_length=3, max_length=60, required=True
    )
    modo = discord.ui.TextInput(
        label="Modo",
        placeholder="4v4 | 2v2 | x1 | br_solo | br_duo | br_squad",
        min_length=2, max_length=10, required=True
    )
    taxa = discord.ui.TextInput(
        label="Taxa de Entrada (R$)",
        placeholder="Ex: 10",
        min_length=1, max_length=6, required=True
    )
    minimo = discord.ui.TextInput(
        label="Mínimo de Inscritos (times ou jogadores)",
        placeholder="Ex: 10",
        min_length=1, max_length=3, required=True
    )
    maximo = discord.ui.TextInput(
        label="Máximo de Inscritos (0 = sem limite)",
        placeholder="Ex: 52 para BR, 0 para modos clássicos",
        min_length=1, max_length=3, required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild

        modo_val = self.modo.value.strip().lower()
        MODOS_VALIDOS = ["4v4", "2v2", "x1", "br_solo", "br_duo", "br_squad"]
        if modo_val not in MODOS_VALIDOS:
            return await interaction.response.send_message(embed=embed_erro(
                "Modo inválido",
                f"Modos aceitos: `{'` | `'.join(MODOS_VALIDOS)}`"
            ), ephemeral=True)

        try:
            taxa_val   = float(self.taxa.value.strip().replace(",", "."))
            minimo_val = int(self.minimo.value.strip())
            maximo_val = int(self.maximo.value.strip())
        except ValueError:
            return await interaction.response.send_message(embed=embed_erro(
                "Valores inválidos", "Taxa, mínimo e máximo devem ser números."
            ), ephemeral=True)

        camp_id = await database.criar_campeonato(
            nome      = self.nome.value.strip(),
            modo      = modo_val,
            taxa      = taxa_val,
            minimo    = minimo_val,
            maximo    = maximo_val if maximo_val > 0 else None,
            criado_por= str(interaction.user.id)
        )

        premio = round(taxa_val * minimo_val * 0.7, 2)
        lucro  = round(taxa_val * minimo_val * 0.3, 2)

        embed = discord.Embed(
            title="✅ Campeonato criado!",
            description=(
                f"**Nome:** {self.nome.value.strip()}\n"
                f"**Modo:** `{modo_val}`\n"
                f"**Taxa:** R$ {taxa_val:.2f}\n"
                f"**Mín. inscritos:** {minimo_val}\n"
                f"**Máx. inscritos:** {maximo_val if maximo_val > 0 else 'Sem limite'}\n"
                f"**Prêmio estimado (mín):** R$ {premio:.2f}\n"
                f"**Lucro estimado (mín):** R$ {lucro:.2f}\n\n"
                "Use o botão **Publicar Inscrições** para abrir para os jogadores."
            ),
            color=0x2ECC71
        )
        embed.set_footer(text=f"FFC • ID do campeonato: {camp_id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        await enviar_log(guild, discord.Embed(
            title="🏆 Campeonato Criado", color=0x2ECC71
        ).add_field(name="Nome",  value=self.nome.value.strip(), inline=False
        ).add_field(name="Modo",  value=modo_val,                inline=True
        ).add_field(name="Taxa",  value=f"R$ {taxa_val:.2f}",   inline=True
        ).add_field(name="Criado por", value=str(interaction.user), inline=True))

# ─────────────────────────────────────────────────────────────────
# VIEW — Painel da staff (canal gestão-de-campeonato)
# ─────────────────────────────────────────────────────────────────
class GestaoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Campeonato", style=discord.ButtonStyle.success,
                       emoji="🏆", custom_id="btn_abrir_camp")
    async def btn_abrir(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem permissão", "Apenas staff pode usar este painel."
            ), ephemeral=True)
        await interaction.response.send_modal(AbrirCampeonatoModal())

    @discord.ui.button(label="Publicar Inscrições", style=discord.ButtonStyle.primary,
                       emoji="📢", custom_id="btn_publicar_inscricoes")
    async def btn_publicar(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem permissão", "Apenas staff pode usar este painel."
            ), ephemeral=True)

        camps = await database.get_campeonatos_por_status("criado")
        if not camps:
            return await interaction.response.send_message(embed=embed_aviso(
                "Nenhum campeonato pendente",
                "Crie um campeonato primeiro com **Abrir Campeonato**."
            ), ephemeral=True)

        # Se tiver mais de um, usa o mais recente
        camp = camps[0]
        await database.atualizar_status_campeonato(camp[0], "aberto")

        cog = interaction.client.cogs.get("CampeonatosCog")
        if cog:
            await cog.postar_embed_inscricoes(interaction.guild, camp[0])

        await interaction.response.send_message(embed=discord.Embed(
            title="📢 Inscrições publicadas!",
            description=f"O campeonato **{camp[1]}** está aberto para inscrições.",
            color=0x2ECC71
        ), ephemeral=True)

    @discord.ui.button(label="Fechar Inscrições", style=discord.ButtonStyle.secondary,
                       emoji="🔒", custom_id="btn_fechar_inscricoes")
    async def btn_fechar(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem permissão", "Apenas staff pode usar este painel."
            ), ephemeral=True)

        camps = await database.get_campeonatos_por_status("aberto")
        if not camps:
            return await interaction.response.send_message(embed=embed_aviso(
                "Nenhum campeonato aberto", "Não há campeonatos com inscrições abertas."
            ), ephemeral=True)

        camp    = camps[0]
        inscritos = await database.get_inscritos_campeonato(camp[0])

        if len(inscritos) < camp[4]:  # camp[4] = minimo
            return await interaction.response.send_message(embed=embed_erro(
                "Mínimo não atingido",
                f"O campeonato precisa de **{camp[4]}** inscritos.\n"
                f"Atualmente: **{len(inscritos)}** inscritos.\n\n"
                "Para cancelar e devolver os PIX, use **Cancelar Campeonato**."
            ), ephemeral=True)

        await database.atualizar_status_campeonato(camp[0], "em_andamento")
        # Trava todos os times inscritos
        for i in inscritos:
            if camp[2] not in ["x1", "br_solo"]:  # modos com time
                time = await database.get_time_do_jogador(i[1])
                if time:
                    await database.atualizar_status_time(time[0], "locked")

        premio = round(camp[3] * len(inscritos) * 0.7, 2)
        lucro  = round(camp[3] * len(inscritos) * 0.3, 2)

        embed = discord.Embed(
            title="🔒 Inscrições fechadas!",
            description=(
                f"**Campeonato:** {camp[1]}\n"
                f"**Inscritos:** {len(inscritos)}\n"
                f"**Arrecadado:** R$ {camp[3] * len(inscritos):.2f}\n"
                f"**Prêmio:** R$ {premio:.2f}\n"
                f"**Lucro:** R$ {lucro:.2f}\n\n"
                "O campeonato está em andamento. Agora gerencie os resultados em **#resultados**."
            ),
            color=0xE8A020
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await enviar_log(interaction.guild, discord.Embed(
            title="🔒 Inscrições Fechadas", color=0xE8A020
        ).add_field(name="Campeonato", value=camp[1],          inline=False
        ).add_field(name="Inscritos",  value=len(inscritos),   inline=True
        ).add_field(name="Prêmio",     value=f"R$ {premio:.2f}", inline=True))

    @discord.ui.button(label="Cancelar Campeonato", style=discord.ButtonStyle.danger,
                       emoji="❌", custom_id="btn_cancelar_camp")
    async def btn_cancelar(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=embed_erro(
                "Sem permissão", "Apenas administradores podem cancelar campeonatos."
            ), ephemeral=True)

        camps = await database.get_campeonatos_ativos()
        if not camps:
            return await interaction.response.send_message(embed=embed_aviso(
                "Nenhum campeonato ativo", "Não há campeonatos para cancelar."
            ), ephemeral=True)

        camp = camps[0]
        inscritos = await database.get_inscritos_campeonato(camp[0])
        await database.atualizar_status_campeonato(camp[0], "cancelado")

        embed = discord.Embed(
            title="❌ Campeonato cancelado",
            description=(
                f"**{camp[1]}** foi cancelado.\n\n"
                f"**Inscritos a receber PIX de volta:** {len(inscritos)}\n\n"
                "⚠️ A devolução dos PIX deve ser feita manualmente pela staff."
            ),
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await enviar_log(interaction.guild, discord.Embed(
            title="❌ Campeonato Cancelado", color=0xE74C3C
        ).add_field(name="Campeonato",    value=camp[1],       inline=False
        ).add_field(name="Cancelado por", value=str(interaction.user), inline=True
        ).add_field(name="Inscritos",     value=len(inscritos), inline=True))

# ─────────────────────────────────────────────────────────────────
# VIEW — Inscrição (canal #inscrição, visível para jogadores)
# ─────────────────────────────────────────────────────────────────
class InscricaoView(discord.ui.View):
    def __init__(self, camp_id: int):
        super().__init__(timeout=None)
        self.camp_id = camp_id
        # Atualiza custom_id com camp_id para persistência
        for item in self.children:
            item.custom_id = f"{item.custom_id}_{camp_id}"

    @discord.ui.button(label="Inscrever", style=discord.ButtonStyle.success,
                       emoji="📝", custom_id="btn_inscrever")
    async def btn_inscrever(self, interaction: discord.Interaction, _):
        guild  = interaction.guild
        member = interaction.user

        # Busca campeonato ativo
        camp = await database.get_campeonato_ativo()
        if not camp or camp[6] != "aberto":
            return await interaction.response.send_message(embed=embed_erro(
                "Sem campeonato aberto", "Não há campeonatos com inscrições abertas no momento."
            ), ephemeral=True)

        jogador = await database.get_jogador(str(member.id))
        if not jogador:
            return await interaction.response.send_message(embed=embed_erro(
                "Não registrado", "Registre-se primeiro no canal **#verificação**."
            ), ephemeral=True)

        # Verificar se já está inscrito
        if await database.jogador_inscrito(camp[0], str(member.id)):
            return await interaction.response.send_message(embed=embed_aviso(
                "Já inscrito", f"Você já está inscrito no campeonato **{camp[1]}**."
            ), ephemeral=True)

        modo = camp[2]  # camp[2] = modo

        # Modos com time: exige time completo e capitão
        if modo in ["4v4", "2v2"]:
            time = await database.get_time_do_jogador(str(member.id))
            if not time:
                return await interaction.response.send_message(embed=embed_erro(
                    "Sem time", "Você precisa estar em um time para se inscrever neste modo."
                ), ephemeral=True)
            if time[2] != str(member.id):
                return await interaction.response.send_message(embed=embed_erro(
                    "Apenas o capitão", "Somente o **capitão do time** pode inscrever o time."
                ), ephemeral=True)
            membros  = await database.get_membros_time(time[0])
            limite   = 4 if modo == "4v4" else 2
            if len(membros) < limite:
                return await interaction.response.send_message(embed=embed_erro(
                    "Time incompleto",
                    f"Seu time precisa de **{limite} jogadores** para se inscrever no modo {modo}.\n"
                    f"Atualmente: **{len(membros)}** jogador(es)."
                ), ephemeral=True)
            # Inscreve todos os membros do time
            for m in membros:
                await database.inscrever_jogador(camp[0], m[1], m[2], time[1])
            nome_inscricao = time[1]

        # BR Duo: exige duo completo
        elif modo == "br_duo":
            time = await database.get_time_do_jogador(str(member.id))
            if not time:
                return await interaction.response.send_message(embed=embed_erro(
                    "Sem duo", "Crie um time com modo 2v2 para representar seu duo."
                ), ephemeral=True)
            if time[2] != str(member.id):
                return await interaction.response.send_message(embed=embed_erro(
                    "Apenas o capitão", "Somente o **capitão** pode inscrever o duo."
                ), ephemeral=True)
            membros = await database.get_membros_time(time[0])
            if len(membros) < 2:
                return await interaction.response.send_message(embed=embed_erro(
                    "Duo incompleto", "Seu duo precisa de **2 jogadores**."
                ), ephemeral=True)
            for m in membros:
                await database.inscrever_jogador(camp[0], m[1], m[2], time[1])
            nome_inscricao = time[1]

        # BR Squad: exige squad completo
        elif modo == "br_squad":
            time = await database.get_time_do_jogador(str(member.id))
            if not time:
                return await interaction.response.send_message(embed=embed_erro(
                    "Sem squad", "Crie um time com modo 4v4 para representar seu squad."
                ), ephemeral=True)
            if time[2] != str(member.id):
                return await interaction.response.send_message(embed=embed_erro(
                    "Apenas o capitão", "Somente o **capitão** pode inscrever o squad."
                ), ephemeral=True)
            membros = await database.get_membros_time(time[0])
            if len(membros) < 4:
                return await interaction.response.send_message(embed=embed_erro(
                    "Squad incompleto", "Seu squad precisa de **4 jogadores**."
                ), ephemeral=True)
            for m in membros:
                await database.inscrever_jogador(camp[0], m[1], m[2], time[1])
            nome_inscricao = time[1]

        # X1 e BR Solo: inscrição individual
        else:
            await database.inscrever_jogador(camp[0], str(member.id), jogador[2], None)
            nome_inscricao = jogador[2]

        # Verificar máximo
        inscritos = await database.get_inscritos_campeonato(camp[0])
        if camp[5] and len(inscritos) > camp[5]:
            # Desfaz inscrição
            await database.cancelar_inscricao(camp[0], str(member.id))
            return await interaction.response.send_message(embed=embed_erro(
                "Campeonato cheio",
                f"O campeonato atingiu o limite máximo de **{camp[5]}** inscritos."
            ), ephemeral=True)

        total     = len(await database.get_inscritos_campeonato(camp[0]))
        premio    = round(camp[3] * total * 0.7, 2)

        embed = discord.Embed(
            title="✅ Inscrição confirmada!",
            description=(
                f"**Campeonato:** {camp[1]}\n"
                f"**Modo:** `{modo}`\n"
                f"**Inscrito como:** `{nome_inscricao}`\n\n"
                f"**Taxa:** R$ {camp[3]:.2f} — pague via PIX para a staff confirmar.\n"
                f"**Prêmio atual:** R$ {premio:.2f}\n"
                f"**Inscritos:** {total}/{camp[4]} (mín)"
            ),
            color=0x2ECC71
        )
        embed.set_footer(text="Free Fire Championships • Inscrição")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Atualiza canal de verificação de pagamentos
        await notificar_pagamento_pendente(guild, member, camp, nome_inscricao)
        await enviar_log(guild, discord.Embed(
            title="📝 Nova Inscrição", color=0x2ECC71
        ).add_field(name="Campeonato", value=camp[1],         inline=False
        ).add_field(name="Jogador",    value=str(member),     inline=True
        ).add_field(name="Inscrito como", value=nome_inscricao, inline=True
        ).add_field(name="Total inscritos", value=total,      inline=True))

    @discord.ui.button(label="Ver Inscritos", style=discord.ButtonStyle.secondary,
                       emoji="👥", custom_id="btn_ver_inscritos")
    async def btn_ver_inscritos(self, interaction: discord.Interaction, _):
        camp = await database.get_campeonato_ativo()
        if not camp:
            return await interaction.response.send_message(embed=embed_aviso(
                "Sem campeonato", "Não há campeonatos ativos no momento."
            ), ephemeral=True)

        inscritos = await database.get_inscritos_campeonato(camp[0])
        total     = len(inscritos)
        premio    = round(camp[3] * total * 0.7, 2)

        embed = discord.Embed(
            title=f"👥 Inscritos — {camp[1]}",
            description=f"**Modo:** `{camp[2]}` | **Taxa:** R$ {camp[3]:.2f}",
            color=0xE8A020
        )
        if inscritos:
            nomes = "\n".join(f"• {i[2]}" + (f" ({i[3]})" if i[3] else "") for i in inscritos[:20])
            embed.add_field(name=f"Inscritos ({total})", value=nomes, inline=False)
        else:
            embed.add_field(name="Inscritos", value="Nenhum inscrito ainda.", inline=False)

        embed.add_field(name="Mínimo",  value=str(camp[4]),        inline=True)
        embed.add_field(name="Máximo",  value=str(camp[5] or "—"), inline=True)
        embed.add_field(name="Prêmio estimado", value=f"R$ {premio:.2f}", inline=True)
        embed.set_footer(text="Free Fire Championships • Inscrições")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Cancelar Inscrição", style=discord.ButtonStyle.danger,
                       emoji="🚫", custom_id="btn_cancelar_inscricao")
    async def btn_cancelar_inscricao(self, interaction: discord.Interaction, _):
        camp = await database.get_campeonato_ativo()
        if not camp or camp[6] != "aberto":
            return await interaction.response.send_message(embed=embed_erro(
                "Fora do prazo", "Inscrições não estão abertas ou o campeonato já iniciou."
            ), ephemeral=True)

        if not await database.jogador_inscrito(camp[0], str(interaction.user.id)):
            return await interaction.response.send_message(embed=embed_aviso(
                "Não inscrito", "Você não está inscrito neste campeonato."
            ), ephemeral=True)

        await database.cancelar_inscricao(camp[0], str(interaction.user.id))
        await interaction.response.send_message(embed=discord.Embed(
            title="🚫 Inscrição cancelada",
            description=(
                f"Sua inscrição no campeonato **{camp[1]}** foi cancelada.\n\n"
                "⚠️ Se já realizou o pagamento, entre em contato com a staff via **#suporte**."
            ),
            color=0xF39C12
        ), ephemeral=True)

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────
class CampeonatosCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def postar_embed_gestao(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="⚙gestão-de-campeonato")
        if not canal:
            print(f"  ⚠️   Canal #gestão-de-campeonato não encontrado em {guild.name}")
            return

        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = discord.Embed(
            title="⚙️ Painel de Gestão — Campeonatos",
            description=(
                "Gerencie os campeonatos do servidor por aqui.\n\n"
                "**Fluxo correto:**\n"
                "1️⃣ **Abrir Campeonato** — define nome, modo, taxa e limites\n"
                "2️⃣ **Publicar Inscrições** — libera para os jogadores\n"
                "3️⃣ Aguardar inscrições e confirmar PIX manualmente\n"
                "4️⃣ **Fechar Inscrições** — inicia o campeonato e trava os times\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "❌ **Cancelar Campeonato** — devolve inscrições (PIX manual)"
            ),
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Staff")
        await canal.send(embed=embed, view=GestaoView())
        print(f"  📨  Embed de gestão postada em {guild.name}")

    async def postar_embed_inscricoes(self, guild: discord.Guild, camp_id: int):
        camp = await database.get_campeonato_por_id(camp_id)
        if not camp:
            return

        # Detecta canal correto: BR vai pro #battle-royale-inscrição, clássico pro #campeonatos-inscrições
        is_br    = camp[2].startswith("br_")
        nome_ch  = "🌐battle-royale-inscrição" if is_br else "🏆campeonatos-inscrições"
        canal    = discord.utils.get(guild.text_channels, name=nome_ch)
        if not canal:
            print(f"  ⚠️   Canal #{nome_ch} não encontrado em {guild.name}")
            return

        # Remove embeds antigas do bot neste canal
        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                titulo = msg.embeds[0].title or ""
                if "Campeonato" in titulo or "Inscrições" in titulo or "Battle Royale" in titulo:
                    try:
                        await msg.delete()
                    except Exception:
                        pass

        MODO_LABELS = {
            "4v4":      "4v4 — Time completo (4 jogadores)",
            "2v2":      "2v2 — Time completo (2 jogadores)",
            "x1":       "X1 Solo — Inscrição individual",
            "br_solo":  "Battle Royale Solo — Individual (45–52 jogadores)",
            "br_duo":   "Battle Royale Duo — Time de 2 (44–52 jogadores)",
            "br_squad": "Battle Royale Squad — Time de 4 (44–52 jogadores)",
        }

        TAXA_INFO = {
            "br_solo":  "R$ 5,00/jogador",
            "br_duo":   "R$ 10,00/duo",
            "br_squad": "R$ 15,00/squad",
        }

        VITORIA_INFO = {
            "br_solo":  "Prêmio total para o último jogador vivo",
            "br_duo":   "Dividido entre os 2 do último duo vivo",
            "br_squad": "Dividido entre os 4 do último squad vivo",
        }

        premio_min = round(camp[3] * camp[4] * 0.7, 2)
        emoji_titulo = "🌐" if is_br else "🏆"

        desc = (
            f"**Modo:** {MODO_LABELS.get(camp[2], camp[2])}\n"
            f"**Taxa:** R$ {camp[3]:.2f}\n"
            f"**Prêmio mínimo:** R$ {premio_min:.2f}\n"
            f"**Mínimo de inscritos:** {camp[4]}\n"
            f"**Máximo:** {camp[5] or 'Sem limite'}\n\n"
        )

        if is_br:
            desc += (
                f"🏆 **Critério de vitória:** {VITORIA_INFO.get(camp[2], '—')}\n\n"
            )

        desc += (
            "📌 Clique em **Inscrever** para participar.\n"
            "💰 Após a inscrição, pague a taxa via **PIX** e aguarde confirmação da staff.\n"
            "⚠️ O campeonato só inicia ao atingir o mínimo de inscritos pagos."
        )

        embed = discord.Embed(
            title=f"{emoji_titulo} {camp[1]}",
            description=desc,
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Inscrições Abertas")
        await canal.send(embed=embed, view=InscricaoView(camp_id))
        print(f"  📨  Embed de inscrições postada em #{nome_ch} ({guild.name})")

    @app_commands.command(name="campeonato-atual", description="[ADMIN] Veja o campeonato ativo.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def campeonato_atual(self, interaction: discord.Interaction):
        camp = await database.get_campeonato_ativo()
        if not camp:
            return await interaction.response.send_message(embed=embed_aviso(
                "Nenhum campeonato ativo", "Crie um campeonato no painel de gestão."
            ), ephemeral=True)

        inscritos = await database.get_inscritos_campeonato(camp[0])
        premio    = round(camp[3] * len(inscritos) * 0.7, 2)
        lucro     = round(camp[3] * len(inscritos) * 0.3, 2)

        embed = discord.Embed(title=f"🏆 {camp[1]}", color=0xE8A020)
        embed.add_field(name="Modo",      value=camp[2],               inline=True)
        embed.add_field(name="Status",    value=camp[6],               inline=True)
        embed.add_field(name="Taxa",      value=f"R$ {camp[3]:.2f}",  inline=True)
        embed.add_field(name="Inscritos", value=f"{len(inscritos)}/{camp[4]} (mín)", inline=True)
        embed.add_field(name="Prêmio",    value=f"R$ {premio:.2f}",   inline=True)
        embed.add_field(name="Lucro",     value=f"R$ {lucro:.2f}",    inline=True)
        embed.set_footer(text=f"FFC • ID: {camp[0]}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    bot.add_view(GestaoView())
    await bot.add_cog(CampeonatosCog(bot))

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def embed_erro(titulo, descricao):
    return discord.Embed(title=f"❌ {titulo}", description=descricao, color=0xE74C3C)

def embed_aviso(titulo, descricao):
    return discord.Embed(title=f"⚠️ {titulo}", description=descricao, color=0xF39C12)

async def notificar_pagamento_pendente(guild, member, camp, nome_inscricao):
    canal = discord.utils.get(guild.text_channels, name="✅verificação-de-resultados")
    if not canal:
        return
    embed = discord.Embed(
        title="💰 Pagamento Pendente",
        description=(
            f"**Jogador:** {member.mention} (`{member.id}`)\n"
            f"**Campeonato:** {camp[1]}\n"
            f"**Inscrito como:** `{nome_inscricao}`\n"
            f"**Valor:** R$ {camp[3]:.2f}\n\n"
            "Confirme o recebimento do PIX antes de validar a inscrição."
        ),
        color=0xF39C12
    )
    embed.set_footer(text="FFC • Pagamentos Pendentes")
    await canal.send(embed=embed)

async def enviar_log(guild, embed):
    embed.set_footer(text="Free Fire Championships • Log")
    log_ch = discord.utils.get(guild.text_channels, name="📋logs")
    if log_ch:
        await log_ch.send(embed=embed)
