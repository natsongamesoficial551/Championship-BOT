import discord
from discord.ext import commands
import asyncio
import os

IS_RENDER = os.getenv("RENDER") is not None

if IS_RENDER:
    print("🌐  Ambiente: RENDER")
else:
    from dotenv import load_dotenv
    load_dotenv()
    print("💻  Ambiente: LOCAL")

if IS_RENDER:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class PingHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Championship BOT - Online!")
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
        def log_message(self, *args):
            pass

    def start_keepalive():
        port = int(os.getenv("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), PingHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"🌐  Servidor web interno iniciado na porta {port}")

    start_keepalive()

async def autoping():
    """Pinga a cada 5 minutos para manter o Render acordado."""
    import aiohttp
    ping_url = os.getenv("BOT_PING", "http://localhost:8080")
    print(f"🏓  Autoping configurado para: {ping_url}")
    await asyncio.sleep(60)  # aguarda 1 min antes do primeiro ping
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ping_url) as resp:
                    print(f"🏓  Autoping OK — status {resp.status}")
        except Exception as e:
            print(f"  ⚠️  Autoping falhou: {e}")
        await asyncio.sleep(300)  # 5 minutos

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.registro",
    "cogs.times",
    "cogs.campeonatos",
    "cogs.resultados",
    "cogs.punicoes",
    "cogs.suporte",
    "cogs.ranking",
    "cogs.utilidades",
    "cogs.seguranca",
    "cogs.painel_staff",
]

async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"  ✅  Cog carregada: {cog}")
            except Exception as e:
                print(f"  ❌  Erro ao carregar {cog}: {e}")

        await bot.start(os.getenv("DISCORD_TOKEN"))

_primeiro_ready = True

@bot.event
async def on_ready():
    global _primeiro_ready
    if not _primeiro_ready:
        return
    _primeiro_ready = False
    print(f"\n🤖  Championship BOT online: {bot.user}")
    print(f"📡  Servidores: {[g.name for g in bot.guilds]}\n")

    # Inicia autoping só no Render
    if IS_RENDER:
        asyncio.create_task(autoping())

    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"  🔄  {len(synced)} comandos sincronizados em: {guild.name}")
        except Exception as e:
            print(f"  ❌  Erro ao sincronizar {guild.name}: {e}")

    await asyncio.sleep(1)

    cog_registro    = bot.cogs.get("RegistroCog")
    cog_times       = bot.cogs.get("TimesCog")
    cog_campeonatos = bot.cogs.get("CampeonatosCog")
    cog_resultados  = bot.cogs.get("ResultadosCog")
    cog_suporte     = bot.cogs.get("SuporteCog")
    cog_ranking     = bot.cogs.get("RankingCog")
    cog_utilidades  = bot.cogs.get("UtilidadesCog")
    cog_staff       = bot.cogs.get("PainelStaffCog")

    for guild in bot.guilds:
        # Delay entre cada postagem para evitar rate limit do Discord
        if cog_registro:
            await cog_registro.postar_embed_registro(guild)
            await asyncio.sleep(2)
        if cog_times:
            await cog_times.postar_embed_times(guild)
            await asyncio.sleep(2)
        if cog_campeonatos:
            await cog_campeonatos.postar_embed_gestao(guild)
            await asyncio.sleep(2)
        if cog_resultados:
            await cog_resultados.postar_embed_provas(guild)
            await asyncio.sleep(2)
        if cog_suporte:
            await cog_suporte.postar_embed_suporte(guild)
            await asyncio.sleep(2)
        # ranking só via comando /ranking — sem auto-post
        if cog_utilidades:
            await cog_utilidades.postar_regras(guild)
            await asyncio.sleep(2)
            await cog_utilidades.postar_como_participar(guild)
            await asyncio.sleep(2)
            await cog_utilidades.postar_premiacoes(guild)
            await asyncio.sleep(2)
            await cog_utilidades.postar_embed_br(guild)
            await asyncio.sleep(2)

    # Painel staff usa ID fixo do canal
    if cog_staff:
        await asyncio.sleep(2)
        await cog_staff.postar_painel_staff()

asyncio.run(main())
