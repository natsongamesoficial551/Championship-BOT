import discord
from discord.ext import commands
from discord import app_commands
import database
import guards

# ─────────────────────────────────────────────────────────────────
# MODAL — Registrar
# ─────────────────────────────────────────────────────────────────
class RegistroModal(discord.ui.Modal, title="📋 Registro — Free Fire Championships"):

    nick_ff = discord.ui.TextInput(
        label="Nick no Free Fire",
        placeholder="Ex: NatanFF123",
        min_length=3,
        max_length=30,
        required=True
    )
    id_ff = discord.ui.TextInput(
        label="ID do Free Fire",
        placeholder="Ex: 123456789",
        min_length=5,
        max_length=15,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild  = interaction.guild
        member = interaction.user
        nick   = self.nick_ff.value.strip()
        id_ff  = self.id_ff.value.strip()

        if not id_ff.isdigit():
            return await interaction.response.send_message(embed=embed_erro(
                "ID inválido", "O ID do Free Fire deve conter apenas números.\nEx: `123456789`"
            ), ephemeral=True)

        if (discord.utils.utcnow() - member.created_at).days < 7:
            dias = (discord.utils.utcnow() - member.created_at).days
            return await interaction.response.send_message(embed=embed_erro(
                "Conta muito nova",
                f"Sua conta tem apenas **{dias} dia(s)**.\nExigimos no mínimo **7 dias**."
            ), ephemeral=True)

        if await database.get_jogador(str(member.id)):
            return await interaction.response.send_message(embed=embed_aviso(
                "Já registrado",
                "Você já possui registro!\nUse o botão **🔄 Atualizar Registro** para alterar seus dados."
            ), ephemeral=True)

        if await database.get_jogador_por_id_ff(id_ff):
            return await interaction.response.send_message(embed=embed_erro(
                "ID já cadastrado",
                "Este ID já está em uso.\nSe acredita que é um erro, abra um ticket em **#suporte**."
            ), ephemeral=True)

        # Salvar no banco
        await database.registrar_jogador(str(member.id), str(member), nick, id_ff)

        # Cargos de acesso (Verificado + Membro, remove Visitante)
        await gerenciar_cargos(member, guild, registrando=True)

        # Apelido = Nick FF
        await aplicar_apelido(member, nick)

        # Cargo de identificação: Nick FF | ID FF
        await criar_cargo_identificacao(guild, member, nick, id_ff)

        embed = discord.Embed(
            title="✅ Registro concluído!",
            description=(
                f"Bem-vindo ao **Free Fire Championships**, {member.mention}!\n\n"
                f"**Nick FF:** `{nick}`\n"
                f"**ID FF:** `{id_ff}`\n\n"
                "Você agora tem acesso completo ao servidor. Boa sorte! 🏆"
            ),
            color=0x2ECC71
        )
        embed.set_footer(text="Free Fire Championships • Registro")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        await enviar_log(guild, discord.Embed(
            title="📋 Novo Registro", color=0x2ECC71
        ).add_field(name="Discord", value=f"{member} (`{member.id}`)", inline=False
        ).add_field(name="Nick FF", value=nick,  inline=True
        ).add_field(name="ID FF",   value=id_ff, inline=True))

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(embed=embed_erro(
            "Erro interno", "Algo deu errado. Tente novamente ou abra um ticket em **#suporte**."
        ), ephemeral=True)
        raise error

# ─────────────────────────────────────────────────────────────────
# MODAL — Atualizar
# ─────────────────────────────────────────────────────────────────
class AtualizarModal(discord.ui.Modal, title="🔄 Atualizar Registro — FFC"):

    nick_ff = discord.ui.TextInput(
        label="Novo Nick no Free Fire",
        placeholder="Ex: NatanFF456",
        min_length=3,
        max_length=30,
        required=True
    )
    id_ff = discord.ui.TextInput(
        label="Novo ID do Free Fire",
        placeholder="Ex: 987654321",
        min_length=5,
        max_length=15,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild  = interaction.guild
        member = interaction.user
        nick   = self.nick_ff.value.strip()
        id_ff  = self.id_ff.value.strip()

        if not id_ff.isdigit():
            return await interaction.response.send_message(embed=embed_erro(
                "ID inválido", "O ID deve conter apenas números."
            ), ephemeral=True)

        jogador = await database.get_jogador(str(member.id))
        if not jogador:
            return await interaction.response.send_message(embed=embed_erro(
                "Não registrado", "Use o botão **✅ Registrar** primeiro."
            ), ephemeral=True)

        em_uso = await database.get_jogador_por_id_ff(id_ff)
        if em_uso and em_uso[0] != str(member.id):
            return await interaction.response.send_message(embed=embed_erro(
                "ID já cadastrado", "Este ID já está em uso por outra conta."
            ), ephemeral=True)

        # Atualizar banco
        await database.atualizar_jogador(str(member.id), nick, id_ff)

        # Apelido atualizado
        await aplicar_apelido(member, nick)

        # Remove cargo antigo e cria novo
        await remover_cargo_identificacao(guild, member, jogador[2], jogador[3])
        await criar_cargo_identificacao(guild, member, nick, id_ff)

        embed = discord.Embed(
            title="✅ Registro atualizado!",
            description=(
                f"**Novo Nick FF:** `{nick}`\n"
                f"**Novo ID FF:** `{id_ff}`"
            ),
            color=0x2ECC71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        await enviar_log(guild, discord.Embed(
            title="🔄 Registro Atualizado", color=0x3498DB
        ).add_field(name="Discord",    value=f"{member} (`{member.id}`)", inline=False
        ).add_field(name="Nick antigo", value=jogador[2], inline=True
        ).add_field(name="Nick novo",   value=nick,       inline=True
        ).add_field(name="ID antigo",   value=jogador[3], inline=True
        ).add_field(name="ID novo",     value=id_ff,      inline=True))

# ─────────────────────────────────────────────────────────────────
# VIEW — Botões
# ─────────────────────────────────────────────────────────────────
class RegistroView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Registrar", style=discord.ButtonStyle.success,
                       emoji="✅", custom_id="btn_registrar")
    async def btn_registrar(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(RegistroModal())

    @discord.ui.button(label="Atualizar Registro", style=discord.ButtonStyle.secondary,
                       emoji="🔄", custom_id="btn_atualizar")
    async def btn_atualizar(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(AtualizarModal())

    @discord.ui.button(label="Ver meu Perfil", style=discord.ButtonStyle.primary,
                       emoji="👤", custom_id="btn_perfil")
    async def btn_perfil(self, interaction: discord.Interaction, _):
        jogador = await database.get_jogador(str(interaction.user.id))
        if not jogador:
            return await interaction.response.send_message(embed=embed_erro(
                "Não registrado", "Clique em **✅ Registrar** para começar."
            ), ephemeral=True)

        embed = discord.Embed(title="👤 Seu Perfil", color=0xE8A020)
        embed.add_field(name="Discord",       value=str(interaction.user), inline=False)
        embed.add_field(name="Nick FF",       value=f"`{jogador[2]}`",     inline=True)
        embed.add_field(name="ID FF",         value=f"`{jogador[3]}`",     inline=True)
        embed.add_field(name="Registrado em", value=jogador[4],            inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Free Fire Championships • Perfil")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────
class RegistroCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def postar_embed_registro(self, guild: discord.Guild):
        canal = discord.utils.get(guild.text_channels, name="✅verificação")
        if not canal:
            print(f"  ⚠️   Canal #verificação não encontrado em {guild.name}")
            return

        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = discord.Embed(
            title="🎮 Bem-vindo ao Free Fire Championships!",
            description=(
                "Para ter acesso completo ao servidor, você precisa se registrar.\n\n"
                "**Como funciona:**\n"
                "1️⃣ Clique em **Registrar**\n"
                "2️⃣ Preencha seu **Nick** e **ID** do Free Fire\n"
                "3️⃣ Confirme — acesso liberado automaticamente!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔄 Mudou de nick ou ID? Use **Atualizar Registro**\n"
                "👤 Quer ver seus dados? Use **Ver meu Perfil**"
            ),
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Sistema de Registro")
        await canal.send(embed=embed, view=RegistroView())
        print(f"  📨  Embed de registro postada em {guild.name}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        visitante = discord.utils.get(member.guild.roles, name="👁 Visitante")
        if visitante:
            await member.add_roles(visitante)

        # Restaura tudo se já tinha registro (saiu e voltou)
        jogador = await database.get_jogador(str(member.id))
        if jogador:
            await gerenciar_cargos(member, member.guild, registrando=True)
            await aplicar_apelido(member, jogador[2])
            await criar_cargo_identificacao(member.guild, member, jogador[2], jogador[3])

    @app_commands.command(name="postar-registro", description="[ADMIN] Posta a embed de registro no canal atual.")
    @app_commands.checks.has_permissions(administrator=True)
    async def postar_registro(self, interaction: discord.Interaction):
        await self.postar_embed_registro(interaction.guild)
        await interaction.response.send_message("✅ Embed postada!", ephemeral=True)

    @app_commands.command(name="perfil", description="[ADMIN] Ver perfil de um membro.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(membro="Membro que deseja consultar")
    async def perfil(self, interaction: discord.Interaction, membro: discord.Member):
        jogador = await database.get_jogador(str(membro.id))
        if not jogador:
            return await interaction.response.send_message(embed=embed_erro(
                "Não registrado", f"{membro.mention} não possui registro."
            ), ephemeral=True)

        embed = discord.Embed(title=f"👤 Perfil — {membro.display_name}", color=0xE8A020)
        embed.add_field(name="Discord",       value=f"{membro} (`{membro.id}`)", inline=False)
        embed.add_field(name="Nick FF",       value=f"`{jogador[2]}`",            inline=True)
        embed.add_field(name="ID FF",         value=f"`{jogador[3]}`",            inline=True)
        embed.add_field(name="Registrado em", value=jogador[4],                   inline=False)
        embed.add_field(name="Status",        value=jogador[5],                   inline=True)
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.set_footer(text="Free Fire Championships • Admin")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await database.init_db()
    bot.add_view(RegistroView())
    await bot.add_cog(RegistroCog(bot))

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def embed_erro(titulo, descricao):
    return discord.Embed(title=f"❌ {titulo}", description=descricao, color=0xE74C3C)

def embed_aviso(titulo, descricao):
    return discord.Embed(title=f"⚠️ {titulo}", description=descricao, color=0xF39C12)

async def aplicar_apelido(member: discord.Member, nick: str):
    """Muda o apelido do membro no servidor para o nick do FF."""
    try:
        await member.edit(nick=nick)
    except discord.Forbidden:
        # Bot não pode mudar apelido de quem tem cargo superior (ex: dono do servidor)
        pass

async def criar_cargo_identificacao(guild: discord.Guild, member: discord.Member, nick: str, id_ff: str):
    """Cria um cargo único com Nick FF | ID FF e atribui ao membro."""
    nome_cargo = f"{nick} | {id_ff}"

    # Verifica se o cargo já existe (caso já tenha sido criado antes)
    cargo_existente = discord.utils.get(guild.roles, name=nome_cargo)
    if not cargo_existente:
        cargo_existente = await guild.create_role(
            name=nome_cargo,
            color=discord.Color.from_str("#95A5A6"),
            hoist=False,
            mentionable=False,
            reason="Identificação FFC"
        )

    await member.add_roles(cargo_existente, reason="Identificação FFC")

async def remover_cargo_identificacao(guild: discord.Guild, member: discord.Member, nick_antigo: str, id_antigo: str):
    """Remove o cargo de identificação antigo do membro e apaga o cargo do servidor."""
    nome_cargo = f"{nick_antigo} | {id_antigo}"
    cargo = discord.utils.get(guild.roles, name=nome_cargo)
    if cargo:
        try:
            await member.remove_roles(cargo, reason="Atualização de identificação FFC")
            # Apaga o cargo do servidor se ninguém mais o usa
            if len(cargo.members) == 0:
                await cargo.delete(reason="Cargo de identificação não utilizado")
        except discord.Forbidden:
            pass

async def gerenciar_cargos(member: discord.Member, guild: discord.Guild, registrando: bool):
    verificado = discord.utils.get(guild.roles, name="✅ Verificado")
    membro     = discord.utils.get(guild.roles, name="🎮 Membro")
    visitante  = discord.utils.get(guild.roles, name="👁 Visitante")

    if registrando:
        roles_add = [r for r in [verificado, membro] if r]
        roles_rem = [r for r in [visitante] if r]
        if roles_add: await member.add_roles(*roles_add, reason="Registro FFC")
        if roles_rem: await member.remove_roles(*roles_rem, reason="Registro FFC")

async def enviar_log(guild: discord.Guild, embed: discord.Embed):
    embed.set_footer(text="Free Fire Championships • Log")
    log_ch = discord.utils.get(guild.text_channels, name="📋logs")
    if log_ch:
        await log_ch.send(embed=embed)
