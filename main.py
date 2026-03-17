import discord
from discord.ext import commands
import asyncio
import os

# ─────────────────────────────────────────────────────────────────
# AMBIENTE
# ─────────────────────────────────────────────────────────────────
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
    import aiohttp
    ping_url = os.getenv("BOT_PING", "http://localhost:8080")
    print(f"🏓  Autoping configurado para: {ping_url}")
    await asyncio.sleep(60)
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ping_url) as resp:
                    print(f"🏓  Autoping OK — status {resp.status}")
        except Exception as e:
            print(f"  ⚠️  Autoping falhou: {e}")
        await asyncio.sleep(300)

# ─────────────────────────────────────────────────────────────────
# BOT
# ─────────────────────────────────────────────────────────────────
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
    print(f"📡  Servidores: {[g.name for g in bot.guilds]}")
    print(f"  ℹ️   Use /setup-embeds no Discord para postar as embeds\n")

    if IS_RENDER:
        asyncio.create_task(autoping())

    # Sincroniza slash commands — única requisição no startup
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"  🔄  {len(synced)} comandos sincronizados em: {guild.name}")
        except Exception as e:
            print(f"  ❌  Erro ao sincronizar {guild.name}: {e}")

asyncio.run(main())
