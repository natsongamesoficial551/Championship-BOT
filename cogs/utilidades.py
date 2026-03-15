import discord
from discord.ext import commands
from discord import app_commands

# ─────────────────────────────────────────────────────────────────
# COG — Utilidades (Dia 7)
# ─────────────────────────────────────────────────────────────────
class UtilidadesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────────────────────
    # AUTO-POST ao ligar
    # ─────────────────────────────────────────────────────────────
    async def postar_regras(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="📜regras")
        if not canal:
            return
        async for msg in canal.history(limit=20):
            if msg.author == self.bot.user:
                try: await msg.delete()
                except: pass

        # ── Regras do Servidor ────────────────────────────────────
        embed_dc = discord.Embed(
            title="📜 Regras do Servidor",
            color=0xE8A020
        )
        embed_dc.add_field(
            name="💬 Conduta Geral",
            value=(
                "• Respeite todos os membros e a staff\n"
                "• Proibido xingamentos, ofensas e discriminação\n"
                "• Proibido spam, flood e mensagens repetidas\n"
                "• Proibido divulgar outros servidores sem autorização\n"
                "• Proibido compartilhar conteúdo impróprio ou ilegal"
            ),
            inline=False
        )
        embed_dc.add_field(
            name="⚠️ Punições — Servidor",
            value=(
                "🔴 Aplicar golpe no prêmio → **Ban permanente**\n"
                "🔴 Ameaça a membro ou staff → **Ban permanente**\n"
                "🔴 Conta falsa comprovada → **Ban permanente**\n"
                "🟠 Xingamento / palavrão → **Advertência + 24h mutado**\n"
                "🟠 Spam → **Advertência + 1 semana mutado**\n"
                "🟡 Divulgar servidor concorrente → **Kick imediato**\n"
                "🔁 Reincidência → **Punição dobrada automaticamente**"
            ),
            inline=False
        )
        embed_dc.set_footer(text="Free Fire Championships • Regras do Servidor")
        await canal.send(embed=embed_dc)

        # ── Regras do Jogo ────────────────────────────────────────
        embed_ff = discord.Embed(
            title="🎮 Regras do Jogo",
            color=0xE8A020
        )
        embed_ff.add_field(
            name="🕹️ Durante as Partidas",
            value=(
                "• Proibido uso de qualquer tipo de hack ou cheat\n"
                "• Proibido manipular resultados ou enviar provas falsas\n"
                "• Trocar jogadores após início do campeonato é proibido\n"
                "• Resultado deve ser enviado em até **30 minutos** após a partida\n"
                "• Apenas o **capitão do time vencedor** envia o resultado"
            ),
            inline=False
        )
        embed_ff.add_field(
            name="⚠️ Punições — Jogo",
            value=(
                "🔴 Uso de hack em partida → **Ban 30 dias**\n"
                "🔴 Resultado falso comprovado → **Ban 7 dias + eliminação do time**\n"
                "🟠 W.O sem aviso prévio → **Advertência + 24h mutado**\n"
                "🟡 W.O com aviso (30min antes) → Eliminação sem punição adicional\n"
                "🟡 Não aparecer sem justificativa → **Advertência + eliminação**"
            ),
            inline=False
        )
        embed_ff.add_field(
            name="💰 Pagamentos",
            value=(
                "• Pagamento via **PIX** antes da confirmação da vaga\n"
                "• Sem pagamento confirmado = sem vaga garantida\n"
                "• Campeonato só inicia ao atingir o mínimo de inscritos pagos\n"
                "• Se o mínimo não for atingido, **PIX devolvido integralmente**"
            ),
            inline=False
        )
        embed_ff.set_footer(text="Free Fire Championships • Regras do Jogo")
        await canal.send(embed=embed_ff)
        print(f"  📨  Regras postadas em {guild.name}")

    async def postar_como_participar(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="📖como-participar")
        if not canal:
            return
        async for msg in canal.history(limit=20):
            if msg.author == self.bot.user:
                try: await msg.delete()
                except: pass

        embed = discord.Embed(
            title="📖 Como Participar — Free Fire Championships",
            description="Siga os passos abaixo e comece a competir!",
            color=0xE8A020
        )
        embed.add_field(
            name="1️⃣  Registre-se",
            value=(
                "Vá ao canal **#✅verificação** e clique em **Registrar**.\n"
                "Preencha seu **Nick** e **ID** do Free Fire.\n"
                "Pronto — acesso liberado automaticamente!"
            ),
            inline=False
        )
        embed.add_field(
            name="2️⃣  Monte seu Time",
            value=(
                "Vá ao canal **#📝inscrição** e clique em **Criar Time**.\n"
                "Escolha o nome e o modo (**4v4** ou **2v2**).\n"
                "Compartilhe o nome do time para seus amigos entrarem."
            ),
            inline=False
        )
        embed.add_field(
            name="3️⃣  Inscreva-se no Campeonato",
            value=(
                "Quando um campeonato estiver aberto, vá ao canal **#🏆campeonatos-inscrições**.\n"
                "O capitão clica em **Inscrever** e confirma o time.\n"
                "Pague a taxa via **PIX** e aguarde a confirmação da staff."
            ),
            inline=False
        )
        embed.add_field(
            name="4️⃣  Jogue e Envie o Resultado",
            value=(
                "Realize sua partida no horário marcado.\n"
                "O capitão vencedor vai ao canal **#📸provas-de-partida**.\n"
                "Clica em **Enviar Resultado**, preenche o formulário e manda o print."
            ),
            inline=False
        )
        embed.add_field(
            name="5️⃣  Acompanhe o Ranking",
            value=(
                "Use `/ranking` para ver o top 10 times.\n"
                "Use `/meu-ranking` para ver a posição do seu time.\n"
                "Acumule pontos e conquiste o campeonato! 🏆"
            ),
            inline=False
        )
        embed.add_field(
            name="❓ Precisa de Ajuda?",
            value="Abra um ticket em **#🎫suporte** a qualquer momento.",
            inline=False
        )
        embed.set_footer(text="Free Fire Championships • Como Participar")
        await canal.send(embed=embed)
        print(f"  📨  Como participar postado em {guild.name}")

    async def postar_premiacoes(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="🏆premiações")
        if not canal:
            return
        async for msg in canal.history(limit=20):
            if msg.author == self.bot.user:
                try: await msg.delete()
                except: pass

        embed = discord.Embed(
            title="💰 Tabela de Taxas e Premiações",
            description=(
                "Todas as premiações são pagas via **PIX**.\n"
                "**70%** da arrecadação vai para o prêmio — **30%** fica com o servidor.\n"
                "O campeonato **só abre** ao atingir o mínimo de inscritos pagos."
            ),
            color=0xE8A020
        )
        embed.add_field(
            name="🎮 Modos Clássicos",
            value=(
                "```\n"
                "Modo      Taxa       Mín.   Arrecad.  Prêmio\n"
                "4v4       R$10/time  10t    R$100     R$70\n"
                "2v2       R$6/time   10t    R$60      R$42\n"
                "X1 Solo   R$4/jog    10j    R$40      R$28\n"
                "```"
            ),
            inline=False
        )
        embed.add_field(
            name="🌐 Battle Royale",
            value=(
                "```\n"
                "Modo       Taxa        Jog.      Mín.Arr.  Prêmio\n"
                "BR Solo    R$5/jog     45–52     R$225     R$157\n"
                "BR Duo     R$10/duo    44–52     R$220     R$154\n"
                "BR Squad   R$15/squad  44–52     R$165     R$115\n"
                "```"
            ),
            inline=False
        )
        embed.add_field(
            name="🏆 Critério de Vitória — BR",
            value=(
                "• **BR Solo** — prêmio total para o último vivo\n"
                "• **BR Duo** — dividido entre os 2 do último duo\n"
                "• **BR Squad** — dividido entre os 4 do último squad"
            ),
            inline=False
        )
        embed.add_field(
            name="⚠️ Importante",
            value=(
                "• Mínimo não atingido → PIX devolvido a todos\n"
                "• Pagamento via PIX antes da confirmação da vaga\n"
                "• Prêmio pago em até 24h após o término do campeonato"
            ),
            inline=False
        )
        embed.set_footer(text="Free Fire Championships • Premiações")
        await canal.send(embed=embed)
        print(f"  📨  Premiações postadas em {guild.name}")

    # ─────────────────────────────────────────────────────────────
    # COMANDOS STAFF
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(name="anunciar", description="[ADMIN] Posta um anúncio oficial no canal #anúncios.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(titulo="Título do anúncio", mensagem="Conteúdo do anúncio", mencionar="Mencionar @everyone?")
    async def anunciar(self, interaction: discord.Interaction,
                       titulo: str, mensagem: str, mencionar: bool = False):
        canal = discord.utils.get(interaction.guild.text_channels, name="📢anúncios")
        if not canal:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Canal não encontrado",
                description="Canal **#📢anúncios** não encontrado.",
                color=0xE74C3C
            ), ephemeral=True)

        embed = discord.Embed(title=f"📢 {titulo}", description=mensagem, color=0xE8A020)
        embed.set_footer(text=f"Free Fire Championships • Anúncio por {interaction.user.display_name}")

        content = "@everyone" if mencionar else ""
        await canal.send(content=content, embed=embed)
        await interaction.response.send_message("✅ Anúncio postado!", ephemeral=True)

    @app_commands.command(name="cronograma", description="[ADMIN] Posta o cronograma de eventos.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(conteudo="Conteúdo do cronograma (use \\n para quebrar linha)")
    async def cronograma(self, interaction: discord.Interaction, conteudo: str):
        canal = discord.utils.get(interaction.guild.text_channels, name="🗓cronograma")
        if not canal:
            return await interaction.response.send_message("❌ Canal #cronograma não encontrado.", ephemeral=True)

        async for msg in canal.history(limit=20):
            if msg.author == self.bot.user:
                try: await msg.delete()
                except: pass

        embed = discord.Embed(
            title="🗓️ Cronograma de Campeonatos",
            description=conteudo.replace("\\n", "\n"),
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Cronograma")
        await canal.send(embed=embed)
        await interaction.response.send_message("✅ Cronograma atualizado!", ephemeral=True)

    # ─────────────────────────────────────────────────────────────
    # AJUDA — slash commands nativos do Discord
    # ─────────────────────────────────────────────────────────────
    @app_commands.command(name="ajuda", description="Lista todos os comandos disponíveis.")
    async def ajuda(self, interaction: discord.Interaction):
        eh_staff = interaction.user.guild_permissions.manage_roles

        embed = discord.Embed(
            title="📋 Comandos — Free Fire Championships",
            description="Todos os comandos disponíveis para você.",
            color=0xE8A020
        )

        # Comandos para todos
        embed.add_field(
            name="👤 Jogador",
            value=(
                "`/ranking` — Top 10 times\n"
                "`/meu-ranking` — Posição do seu time\n"
                "`/perfil` — Ver seu perfil registrado"
            ),
            inline=False
        )

        if eh_staff:
            embed.add_field(
                name="🛡️ Staff — Registro",
                value=(
                    "`/perfil @membro` — Ver perfil de qualquer membro\n"
                    "`/postar-registro` — Repostar embed de registro"
                ),
                inline=False
            )
            embed.add_field(
                name="🛡️ Staff — Times",
                value=(
                    "`/listar-times` — Ver todos os times\n"
                    "`/travar-time [nome]` — Travar/destravar roster"
                ),
                inline=False
            )
            embed.add_field(
                name="🛡️ Staff — Campeonatos",
                value=(
                    "`/campeonato-atual` — Ver campeonato ativo\n"
                    "`/aprovar-resultado [id]` — Aprovar resultado\n"
                    "`/contestar-resultado [id] [motivo]` — Contestar"
                ),
                inline=False
            )
            embed.add_field(
                name="🛡️ Staff — Punições",
                value=(
                    "`/advertir @membro` — Aplicar advertência\n"
                    "`/mutar @membro` — Mutar membro\n"
                    "`/desmutar @membro` — Desmutar membro\n"
                    "`/banir @membro` — Banir membro\n"
                    "`/kickar @membro` — Expulsar membro\n"
                    "`/historico-punicoes @membro` — Ver histórico"
                ),
                inline=False
            )
            embed.add_field(
                name="🛡️ Staff — Utilidades",
                value=(
                    "`/anunciar [titulo] [msg]` — Postar anúncio\n"
                    "`/cronograma [conteudo]` — Atualizar cronograma"
                ),
                inline=False
            )

        embed.set_footer(text="FFC • Use /ajuda a qualquer momento")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    async def postar_embed_br(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="🌐battle-royale-inscrição")
        if not canal:
            return
        async for msg in canal.history(limit=10):
            if msg.author == guild.me:
                return
        desc = (
            "Bem-vindo ao modo **Battle Royale** do FFC!\n\n"
            "**Modos disponíveis:**\n"
            "🎯 **BR Solo** — R$ 5/jogador | 45–52 jogadores | Último vivo leva tudo\n"
            "👥 **BR Duo** — R$ 10/duo | 44–52 jogadores | Prêmio dividido entre o duo vencedor\n"
            "⚔️ **BR Squad** — R$ 15/squad | 44–52 jogadores | Prêmio dividido entre o squad\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📢 Quando um campeonato BR for aberto, o botão de inscrição aparecerá aqui.\n"
            "🔔 Fique de olho nos **#📢anúncios** para não perder!"
        )
        embed = discord.Embed(
            title="🌐 Battle Royale — Free Fire Championships",
            description=desc,
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Battle Royale")
        await canal.send(embed=embed)
        print(f"  📨  Embed BR informativa postada em {guild.name}")

async def setup(bot):
    await bot.add_cog(UtilidadesCog(bot))
