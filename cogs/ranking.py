import discord
from discord.ext import commands
from discord import app_commands
import database

class RankingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def postar_embed_ranking(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="💬chat-geral")
        if not canal:
            print(f"  ⚠️   Canal #chat-geral não encontrado em {guild.name}")
            return

        # ── Apaga mensagens antigas do bot antes de postar ────────
        async for msg in canal.history(limit=30):
            if msg.author == self.bot.user and msg.embeds:
                titulo = msg.embeds[0].title or ""
                if "Ranking" in titulo:
                    try:
                        await msg.delete()
                    except Exception:
                        pass

        ranking = await database.get_ranking(10)

        embed = discord.Embed(
            title="🏆 Ranking — Free Fire Championships",
            description="Top 10 times do servidor. Atualizado automaticamente após cada resultado aprovado.",
            color=0xE8A020
        )

        if not ranking:
            embed.add_field(name="Sem dados ainda", value="Nenhum campeonato finalizado ainda.", inline=False)
        else:
            medalhas = ["🥇", "🥈", "🥉"]
            for i, r in enumerate(ranking):
                pos = medalhas[i] if i < 3 else f"`#{i+1}`"
                embed.add_field(
                    name=f"{pos} {r[1]}",
                    value=(
                        f"**Pontos:** {r[6]} pts\n"
                        f"✅ {r[3]}V  ❌ {r[4]}D  🏆 {r[5]} camp."
                    ),
                    inline=True
                )

        embed.set_footer(text="Free Fire Championships • Ranking Geral")
        await canal.send(embed=embed)
        print(f"  📨  Embed de ranking postada em {guild.name}")

    @app_commands.command(name="ranking", description="Veja o ranking dos top 10 times.")
    async def ranking(self, interaction: discord.Interaction):
        times = await database.get_ranking(10)
        embed = discord.Embed(title="🏆 Ranking — Top 10 Times", color=0xE8A020)
        if not times:
            embed.description = "Nenhum campeonato finalizado ainda."
        else:
            medalhas = ["🥇", "🥈", "🥉"]
            for i, r in enumerate(times):
                pos = medalhas[i] if i < 3 else f"#{i+1}"
                embed.add_field(
                    name=f"{pos} {r[1]}",
                    value=f"**{r[6]} pts** | {r[3]}V {r[4]}D | {r[5]} 🏆",
                    inline=False
                )
        embed.set_footer(text="FFC • /ranking")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="meu-ranking", description="Veja a posição do seu time no ranking.")
    async def meu_ranking(self, interaction: discord.Interaction):
        time = await database.get_time_do_jogador(str(interaction.user.id))
        if not time:
            return await interaction.response.send_message(embed=discord.Embed(
                title="❌ Sem time", description="Você não está em nenhum time.", color=0xE74C3C
            ), ephemeral=True)
        r = await database.get_ranking_time(time[1])
        if not r:
            return await interaction.response.send_message(embed=discord.Embed(
                title="📊 Sem dados",
                description=f"O time **{time[1]}** ainda não possui dados no ranking.\nParticipe de um campeonato!",
                color=0xF39C12
            ), ephemeral=True)
        todos   = await database.get_ranking(999)
        posicao = next((i+1 for i, t in enumerate(todos) if t[1] == time[1]), "—")
        embed   = discord.Embed(title=f"📊 Ranking — {time[1]}", color=0xE8A020)
        embed.add_field(name="Posição",       value=f"#{posicao}", inline=True)
        embed.add_field(name="Pontos",        value=str(r[6]),     inline=True)
        embed.add_field(name="Vitórias",      value=str(r[3]),     inline=True)
        embed.add_field(name="Derrotas",      value=str(r[4]),     inline=True)
        embed.add_field(name="Camps. Ganhos", value=str(r[5]),     inline=True)
        embed.set_footer(text="FFC • /meu-ranking")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RankingCog(bot))
