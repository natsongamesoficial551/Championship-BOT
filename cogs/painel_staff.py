import discord
from discord.ext import commands
from discord import app_commands
import database
import guards
import asyncio
from datetime import datetime, timezone, timedelta

CANAL_STAFF_ID = 1482815101554790563

# ─────────────────────────────────────────────────────────────────
# HELPER — busca membro por nick, display name ou ID
# ─────────────────────────────────────────────────────────────────
def buscar_membro(guild: discord.Guild, texto: str):
    texto = texto.strip()
    if texto.isdigit():
        return guild.get_member(int(texto))
    m = guild.get_member_named(texto)
    if m:
        return m
    texto_lower = texto.lower()
    for member in guild.members:
        if texto_lower in member.display_name.lower() or texto_lower in member.name.lower():
            return member
    return None

# ─────────────────────────────────────────────────────────────────
# MODAIS COM BUSCA DE MEMBRO
# ─────────────────────────────────────────────────────────────────
class PerfilBuscaModal(discord.ui.Modal, title="👤 Ver Perfil"):
    busca = discord.ui.TextInput(
        label="Nick FF, nome no Discord ou ID",
        placeholder="Ex: NatanFF | Natan | 123456789",
        min_length=2, max_length=40, required=True
    )
    async def on_submit(self, interaction: discord.Interaction):
        member = buscar_membro(interaction.guild, self.busca.value)
        if not member:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Nenhum membro encontrado com `{self.busca.value}`."), ephemeral=True)
        jogador = await database.get_jogador(str(member.id))
        if not jogador:
            return await interaction.response.send_message(embed=e_aviso("Não registrado", f"{member.mention} não possui registro."), ephemeral=True)
        embed = discord.Embed(title=f"👤 Perfil — {member.display_name}", color=0xE8A020)
        embed.add_field(name="Discord",       value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Nick FF",       value=f"`{jogador[2]}`",           inline=True)
        embed.add_field(name="ID FF",         value=f"`{jogador[3]}`",           inline=True)
        embed.add_field(name="Registrado em", value=jogador[4],                  inline=False)
        embed.add_field(name="Status",        value=jogador[5],                  inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="FFC • Staff • Perfil")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class HistoricoBuscaModal(discord.ui.Modal, title="📋 Histórico de Punições"):
    busca = discord.ui.TextInput(
        label="Nick FF, nome no Discord ou ID",
        placeholder="Ex: NatanFF | Natan | 123456789",
        min_length=2, max_length=40, required=True
    )
    async def on_submit(self, interaction: discord.Interaction):
        member = buscar_membro(interaction.guild, self.busca.value)
        if not member:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Nenhum membro com `{self.busca.value}`."), ephemeral=True)
        punicoes = await database.get_punicoes_membro(str(member.id))
        if not punicoes:
            return await interaction.response.send_message(embed=e_aviso("Sem punições", f"{member.mention} não possui punições."), ephemeral=True)
        embed = discord.Embed(title=f"📋 Histórico — {member.display_name}", color=0xE8A020)
        for p in punicoes[:10]:
            duracao = "Permanente" if p[6] else f"{p[5]}h"
            embed.add_field(name=f"#{p[0]} — {p[3].upper()} ({duracao})", value=f"**Motivo:** {p[4]}\n**Data:** {p[8]}", inline=False)
        embed.set_footer(text=f"FFC • {len(punicoes)} punição(ões) total")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AdvertirBuscaModal(discord.ui.Modal, title="⚠️ Advertir Membro"):
    busca  = discord.ui.TextInput(label="Nick FF, nome no Discord ou ID", placeholder="Ex: NatanFF | Natan | 123456789", min_length=2, max_length=40, required=True)
    motivo = discord.ui.TextInput(label="Motivo", style=discord.TextStyle.paragraph, min_length=5, max_length=300, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        member = buscar_membro(interaction.guild, self.busca.value)
        if not member:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Nenhum membro com `{self.busca.value}`."), ephemeral=True)
        pode, motivo_h = guards.pode_punir(interaction.user, member)
        if not pode:
            return await interaction.response.send_message(embed=guards.embed_sem_permissao(motivo_h), ephemeral=True)
        ultima      = await database.get_ultima_punicao(str(member.id), "advertencia")
        reincidente = ultima is not None
        await database.salvar_punicao(str(member.id), str(member), "advertencia", self.motivo.value, 0, False, str(interaction.user.id))
        try:
            await member.send(embed=discord.Embed(title="⚠️ Advertência Recebida", description=f"**Servidor:** {interaction.guild.name}\n**Motivo:** {self.motivo.value}\n\nReincidência resultará em punição mais severa.", color=0xF39C12))
        except discord.Forbidden:
            pass
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Advertência aplicada",
            description=f"**Membro:** {member.mention}\n**Motivo:** {self.motivo.value}" + ("\n⚠️ **Reincidente**" if reincidente else ""),
            color=0xF39C12
        ), ephemeral=True)
        await log_staff(interaction.guild, "⚠️ Advertência", interaction.user, [("Membro", str(member)), ("Motivo", self.motivo.value)])

class MutarBuscaModal(discord.ui.Modal, title="🔇 Mutar Membro"):
    busca   = discord.ui.TextInput(label="Nick FF, nome no Discord ou ID", placeholder="Ex: NatanFF | Natan | 123456789", min_length=2, max_length=40, required=True)
    motivo  = discord.ui.TextInput(label="Motivo", style=discord.TextStyle.paragraph, min_length=5, max_length=300, required=True)
    duracao = discord.ui.TextInput(label="Duração em horas (0 = permanente)", placeholder="Ex: 24", min_length=1, max_length=5, required=True, default="24")
    async def on_submit(self, interaction: discord.Interaction):
        member = buscar_membro(interaction.guild, self.busca.value)
        if not member:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Nenhum membro com `{self.busca.value}`."), ephemeral=True)
        pode, motivo_h = guards.pode_punir(interaction.user, member)
        if not pode:
            return await interaction.response.send_message(embed=guards.embed_sem_permissao(motivo_h), ephemeral=True)
        try:
            horas = int(self.duracao.value.strip())
        except ValueError:
            return await interaction.response.send_message(embed=e_erro("Duração inválida", "Digite um número inteiro."), ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        from cogs.punicoes import garantir_cargo_mutado, salvar_cargos_membro, _cargos_para_salvar, enviar_timer_dm, remover_mute_automatico
        permanente  = horas == 0
        segundos    = horas * 3600
        ultima      = await database.get_ultima_punicao(str(member.id), "mute")
        reincidente = ultima is not None
        if reincidente and not permanente:
            horas = horas * 2; segundos = horas * 3600
        cargos_ids  = _cargos_para_salvar(member)
        await salvar_cargos_membro(str(member.id), cargos_ids)
        cargo_muted = await garantir_cargo_mutado(interaction.guild)
        cargos_rem  = [r for r in member.roles if r.name not in {"@everyone","🔇 Mutado"} and not r.managed and "|" not in r.name]
        if cargos_rem:
            try: await member.remove_roles(*cargos_rem, reason="[FFC] Mute")
            except discord.Forbidden: pass
        await member.add_roles(cargo_muted, reason=f"[FFC] Mute — {self.motivo.value}")
        if not permanente:
            await enviar_timer_dm(member, self.motivo.value, segundos)
            asyncio.create_task(remover_mute_automatico(member, segundos))
        await database.salvar_punicao(str(member.id), str(member), "mute", self.motivo.value, 0 if permanente else horas, permanente, str(interaction.user.id))
        duracao_txt = "Permanente" if permanente else f"{horas}h"
        if reincidente and not permanente: duracao_txt += " *(dobrado)*"
        expira_txt  = "nunca" if permanente else f"<t:{int((datetime.now(timezone.utc)+timedelta(seconds=segundos)).timestamp())}:R>"
        await interaction.followup.send(embed=discord.Embed(
            title="🔇 Mute aplicado!",
            description=f"**Membro:** {member.mention}\n**Duração:** `{duracao_txt}`\n**Expira:** {expira_txt}\n**Motivo:** {self.motivo.value}\n**Cargos salvos:** {len(cargos_ids)}",
            color=0xE8A020
        ), ephemeral=True)
        await log_staff(interaction.guild, "🔇 Mute Aplicado", interaction.user, [("Membro", str(member)), ("Duração", duracao_txt), ("Motivo", self.motivo.value)])

class DesmustarBuscaModal(discord.ui.Modal, title="🔊 Desmutar Membro"):
    busca = discord.ui.TextInput(label="Nick FF, nome no Discord ou ID", placeholder="Ex: NatanFF | Natan | 123456789", min_length=2, max_length=40, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        member = buscar_membro(interaction.guild, self.busca.value)
        if not member:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Nenhum membro com `{self.busca.value}`."), ephemeral=True)
        cargo_muted = discord.utils.get(interaction.guild.roles, name="🔇 Mutado")
        if not cargo_muted or cargo_muted not in member.roles:
            return await interaction.response.send_message(embed=e_aviso("Sem mute", f"{member.mention} não está mutado."), ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        from cogs.punicoes import restaurar_cargos_membro
        await restaurar_cargos_membro(member)
        try:
            await member.send(embed=discord.Embed(title="🔊 Mute removido!", description="Seu mute foi removido pela staff e seus cargos foram restaurados.", color=0x2ECC71))
        except discord.Forbidden:
            pass
        await interaction.followup.send(embed=discord.Embed(title="🔊 Desmutado", description=f"{member.mention} desmutado e cargos restaurados.", color=0x2ECC71), ephemeral=True)
        await log_staff(interaction.guild, "🔊 Desmutado", interaction.user, [("Membro", str(member))])

class BanirBuscaModal(discord.ui.Modal, title="🔨 Banir Membro"):
    busca  = discord.ui.TextInput(label="Nick FF, nome no Discord ou ID", placeholder="Ex: NatanFF | Natan | 123456789", min_length=2, max_length=40, required=True)
    motivo = discord.ui.TextInput(label="Motivo", style=discord.TextStyle.paragraph, min_length=5, max_length=300, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        member = buscar_membro(interaction.guild, self.busca.value)
        if not member:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Nenhum membro com `{self.busca.value}`."), ephemeral=True)
        pode, motivo_h = guards.pode_punir(interaction.user, member)
        if not pode:
            return await interaction.response.send_message(embed=guards.embed_sem_permissao(motivo_h), ephemeral=True)
        try:
            await member.ban(reason=f"[FFC] {self.motivo.value} — por {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message(embed=e_erro("Sem permissão", "Não foi possível banir."), ephemeral=True)
        await database.salvar_punicao(str(member.id), str(member), "ban", self.motivo.value, 0, True, str(interaction.user.id))
        await interaction.response.send_message(embed=discord.Embed(title="🔨 Membro banido", description=f"**{member}** foi banido.\n**Motivo:** {self.motivo.value}", color=0xE74C3C), ephemeral=True)
        await log_staff(interaction.guild, "🔨 Banido", interaction.user, [("Membro", str(member)), ("Motivo", self.motivo.value)])

# ─────────────────────────────────────────────────────────────────
# MODAIS sem busca de membro
# ─────────────────────────────────────────────────────────────────
class ListarTimesModal(discord.ui.Modal, title="⚔️ Filtrar Times"):
    filtro = discord.ui.TextInput(label="Nome do time (vazio = todos)", required=False, max_length=30)
    async def on_submit(self, interaction: discord.Interaction):
        times = await database.get_todos_times()
        if not times:
            return await interaction.response.send_message(embed=e_aviso("Sem times", "Nenhum cadastrado."), ephemeral=True)
        f = self.filtro.value.strip().lower()
        if f: times = [t for t in times if f in t[1].lower()]
        embed = discord.Embed(title="📋 Times Cadastrados", color=0xE8A020)
        for t in times[:15]:
            membros = await database.get_membros_time(t[0])
            status  = "🔒" if t[6] == "locked" else "🟢"
            embed.add_field(name=f"{status} {t[1]} ({t[4]})", value=f"Capitão: {t[3]} | {len(membros)}/{t[5]}", inline=False)
        embed.set_footer(text=f"FFC • {len(times)} time(s)")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class TravarTimeModal(discord.ui.Modal, title="🔒 Travar/Destravar Time"):
    nome = discord.ui.TextInput(label="Nome do time", min_length=2, max_length=30, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        time = await database.get_time_por_nome(self.nome.value.strip())
        if not time:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Time **{self.nome.value}** não existe."), ephemeral=True)
        novo = "open" if time[6] == "locked" else "locked"
        await database.atualizar_status_time(time[0], novo)
        emoji = "🔒" if novo == "locked" else "🟢"
        await interaction.response.send_message(embed=discord.Embed(title=f"{emoji} Time {'bloqueado' if novo=='locked' else 'desbloqueado'}", description=f"**{time[1]}** atualizado.", color=0xE8A020), ephemeral=True)

class AprovarResultadoModal(discord.ui.Modal, title="✅ Aprovar Resultado"):
    resultado_id = discord.ui.TextInput(label="ID do Resultado", placeholder="Ex: 1", min_length=1, max_length=5, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        rid = self.resultado_id.value.strip()
        if not rid.isdigit():
            return await interaction.response.send_message(embed=e_erro("ID inválido", "Apenas números."), ephemeral=True)
        resultado = await database.get_resultado_por_id(int(rid))
        if not resultado:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Resultado `#{rid}` não existe."), ephemeral=True)
        if resultado[7] != "pendente":
            return await interaction.response.send_message(embed=e_aviso("Já processado", f"Já foi **{resultado[7]}**."), ephemeral=True)
        await database.atualizar_resultado(int(rid), "aprovado", None)
        await database.incrementar_ranking(resultado[3], resultado[2], "vitoria")
        from cogs.resultados import postar_resultado_oficial, notificar_capitao
        await postar_resultado_oficial(interaction.guild, resultado)
        await notificar_capitao(interaction.guild, resultado, aprovado=True, motivo=None)
        await interaction.response.send_message(embed=discord.Embed(title="✅ Aprovado!", description=f"**{resultado[3]}** vs **{resultado[4]}** — `{resultado[5]}`", color=0x2ECC71), ephemeral=True)
        await log_staff(interaction.guild, "✅ Resultado Aprovado", interaction.user, [("ID", rid), ("Time", resultado[3])])

class ContestarResultadoModal(discord.ui.Modal, title="❌ Contestar Resultado"):
    resultado_id = discord.ui.TextInput(label="ID do Resultado", placeholder="Ex: 1", min_length=1, max_length=5, required=True)
    motivo       = discord.ui.TextInput(label="Motivo", style=discord.TextStyle.paragraph, min_length=5, max_length=300, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        rid = self.resultado_id.value.strip()
        if not rid.isdigit():
            return await interaction.response.send_message(embed=e_erro("ID inválido", "Apenas números."), ephemeral=True)
        resultado = await database.get_resultado_por_id(int(rid))
        if not resultado:
            return await interaction.response.send_message(embed=e_erro("Não encontrado", f"Resultado `#{rid}` não existe."), ephemeral=True)
        await database.atualizar_resultado(int(rid), "contestado", self.motivo.value.strip())
        from cogs.resultados import notificar_capitao
        await notificar_capitao(interaction.guild, resultado, aprovado=False, motivo=self.motivo.value.strip())
        await interaction.response.send_message(embed=discord.Embed(title="❌ Contestado", description="Capitão notificado.", color=0xE74C3C), ephemeral=True)
        await log_staff(interaction.guild, "❌ Resultado Contestado", interaction.user, [("ID", rid), ("Motivo", self.motivo.value)])

class AnunciarModal(discord.ui.Modal, title="📢 Novo Anúncio"):
    titulo    = discord.ui.TextInput(label="Título", min_length=3, max_length=80, required=True)
    mensagem  = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.paragraph, min_length=5, max_length=1000, required=True)
    mencionar = discord.ui.TextInput(label="Mencionar @everyone? (sim/não)", max_length=3, required=True, default="não")
    async def on_submit(self, interaction: discord.Interaction):
        canal = discord.utils.get(interaction.guild.text_channels, name="📢anúncios")
        if not canal:
            return await interaction.response.send_message(embed=e_erro("Canal não encontrado", "#📢anúncios não existe."), ephemeral=True)
        embed   = discord.Embed(title=f"📢 {self.titulo.value.strip()}", description=self.mensagem.value.strip(), color=0xE8A020)
        embed.set_footer(text=f"FFC • Anúncio por {interaction.user.display_name}")
        content = "@everyone" if self.mencionar.value.strip().lower() == "sim" else ""
        await canal.send(content=content, embed=embed)
        await interaction.response.send_message("✅ Anúncio postado!", ephemeral=True)

class CronogramaModal(discord.ui.Modal, title="🗓️ Atualizar Cronograma"):
    conteudo = discord.ui.TextInput(label="Conteúdo (\\n = nova linha)", style=discord.TextStyle.paragraph, min_length=5, max_length=1000, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        canal = discord.utils.get(interaction.guild.text_channels, name="🗓cronograma")
        if not canal:
            return await interaction.response.send_message(embed=e_erro("Canal não encontrado", "#🗓cronograma não existe."), ephemeral=True)
        async for msg in canal.history(limit=20):
            if msg.author == interaction.client.user:
                try: await msg.delete()
                except: pass
        embed = discord.Embed(title="🗓️ Cronograma de Campeonatos", description=self.conteudo.value.replace("\\n", "\n"), color=0xE8A020)
        embed.set_footer(text="Free Fire Championships • Cronograma")
        await canal.send(embed=embed)
        await interaction.response.send_message("✅ Cronograma atualizado!", ephemeral=True)

# ─────────────────────────────────────────────────────────────────
# VIEW PRINCIPAL — Painel Staff
# ─────────────────────────────────────────────────────────────────
class PainelStaffView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def _check(self, i): return _eh_staff(i.user)

    @discord.ui.button(label="Ver Perfil",    style=discord.ButtonStyle.secondary, emoji="👤", custom_id="staff_perfil",       row=0)
    async def perfil(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(PerfilBuscaModal())

    @discord.ui.button(label="Listar Times",  style=discord.ButtonStyle.secondary, emoji="⚔️", custom_id="staff_listar",       row=0)
    async def listar(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(ListarTimesModal())

    @discord.ui.button(label="Travar Time",   style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="staff_travar",       row=0)
    async def travar(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(TravarTimeModal())

    @discord.ui.button(label="Status Camp",   style=discord.ButtonStyle.primary,   emoji="🏆", custom_id="staff_status_camp",  row=1)
    async def status_camp(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        camp = await database.get_campeonato_ativo()
        if not camp:
            return await i.response.send_message(embed=e_aviso("Nenhum campeonato", "Nenhum ativo."), ephemeral=True)
        inscritos = await database.get_inscritos_campeonato(camp[0])
        pendentes = len([r for r in await database.get_todos_resultados_campeonato(camp[0]) if r[7] == "pendente"])
        premio    = round(camp[3] * len(inscritos) * 0.7, 2)
        lucro     = round(camp[3] * len(inscritos) * 0.3, 2)
        embed = discord.Embed(title=f"🏆 {camp[1]}", color=0xE8A020)
        embed.add_field(name="Modo",      value=camp[2],              inline=True)
        embed.add_field(name="Status",    value=camp[6],              inline=True)
        embed.add_field(name="Taxa",      value=f"R$ {camp[3]:.2f}", inline=True)
        embed.add_field(name="Inscritos", value=f"{len(inscritos)}/{camp[4]}", inline=True)
        embed.add_field(name="Prêmio",    value=f"R$ {premio:.2f}", inline=True)
        embed.add_field(name="Lucro",     value=f"R$ {lucro:.2f}",  inline=True)
        embed.add_field(name="Pendentes", value=str(pendentes),      inline=True)
        embed.set_footer(text=f"FFC • ID: {camp[0]}")
        await i.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Aprovar Res.",  style=discord.ButtonStyle.success,   emoji="✅", custom_id="staff_aprovar",      row=1)
    async def aprovar(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(AprovarResultadoModal())

    @discord.ui.button(label="Contestar Res", style=discord.ButtonStyle.danger,    emoji="❌", custom_id="staff_contestar",    row=1)
    async def contestar(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(ContestarResultadoModal())

    @discord.ui.button(label="Advertir",      style=discord.ButtonStyle.secondary, emoji="⚠️", custom_id="staff_advertir",     row=2)
    async def advertir(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(AdvertirBuscaModal())

    @discord.ui.button(label="Mutar",         style=discord.ButtonStyle.danger,    emoji="🔇", custom_id="staff_mutar",        row=2)
    async def mutar(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(MutarBuscaModal())

    @discord.ui.button(label="Desmutar",      style=discord.ButtonStyle.success,   emoji="🔊", custom_id="staff_desmutar",     row=2)
    async def desmutar(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(DesmustarBuscaModal())

    @discord.ui.button(label="Banir",         style=discord.ButtonStyle.danger,    emoji="🔨", custom_id="staff_banir",        row=2)
    async def banir(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(BanirBuscaModal())

    @discord.ui.button(label="Histórico",     style=discord.ButtonStyle.secondary, emoji="📋", custom_id="staff_historico",    row=2)
    async def historico(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(HistoricoBuscaModal())

    @discord.ui.button(label="Anunciar",      style=discord.ButtonStyle.primary,   emoji="📢", custom_id="staff_anunciar",     row=3)
    async def anunciar(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(AnunciarModal())

    @discord.ui.button(label="Cronograma",    style=discord.ButtonStyle.primary,   emoji="🗓️", custom_id="staff_cronograma",   row=3)
    async def cronograma(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        await i.response.send_modal(CronogramaModal())

    @discord.ui.button(label="Status Bot",    style=discord.ButtonStyle.secondary, emoji="📊", custom_id="staff_status_bot",   row=3)
    async def status_bot(self, i, _):
        if not self._check(i): return await _sem_perm(i)
        guild     = i.guild
        camp      = await database.get_campeonato_ativo()
        inscritos = await database.get_inscritos_campeonato(camp[0]) if camp else []
        times     = await database.get_todos_times()
        tickets   = await database.get_tickets_abertos()
        jogadores = await database.get_total_jogadores()
        embed = discord.Embed(title="📊 Status — Championship BOT", color=0xE8A020)
        embed.add_field(name="🎮 Jogadores", value=str(jogadores),    inline=True)
        embed.add_field(name="⚔️ Times",     value=str(len(times)),   inline=True)
        embed.add_field(name="🎫 Tickets",   value=str(len(tickets)), inline=True)
        embed.add_field(name="🏆 Campeonato",value=f"{camp[1]} ({camp[6]})" if camp else "Nenhum", inline=False)
        embed.add_field(name="🤖 Latência",  value=f"{round(i.client.latency*1000)}ms", inline=True)
        embed.set_footer(text=f"FFC • {guild.member_count} membros")
        await i.response.send_message(embed=embed, ephemeral=True)

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────
class PainelStaffCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def postar_painel_staff(self):
        canal = self.bot.get_channel(CANAL_STAFF_ID)
        if not canal:
            print(f"  ⚠️   Canal staff ID {CANAL_STAFF_ID} não encontrado.")
            return
        async for msg in canal.history(limit=30):
            if msg.author == self.bot.user:
                try: await msg.delete()
                except: pass
        embed = discord.Embed(
            title="🛡️ Painel da Staff — Free Fire Championships",
            description=(
                "Controle completo do servidor. Apenas staff pode usar.\n\n"
                "**👤 Registro & Times**\n"
                "`Ver Perfil` · `Listar Times` · `Travar Time`\n\n"
                "**🏆 Campeonatos**\n"
                "`Status Camp` · `Aprovar Resultado` · `Contestar Resultado`\n\n"
                "**⚠️ Punições** — busca por nick FF, nome Discord ou ID\n"
                "`Advertir` · `Mutar` · `Desmutar` · `Banir` · `Histórico`\n\n"
                "**📣 Utilidades**\n"
                "`Anunciar` · `Cronograma` · `Status Bot`"
            ),
            color=0xE8A020
        )
        embed.set_footer(text="Free Fire Championships • Staff Panel")
        await canal.send(embed=embed, view=PainelStaffView())
        print(f"  📨  Painel staff postado em #{canal.name}")

async def setup(bot):
    bot.add_view(PainelStaffView())
    await bot.add_cog(PainelStaffCog(bot))

def _eh_staff(m): return m.guild_permissions.manage_roles or m.guild_permissions.administrator
async def _sem_perm(i): await i.response.send_message(embed=discord.Embed(title="🚫 Sem Permissão", description="Apenas staff.", color=0xE74C3C), ephemeral=True)
def e_erro(t, d):  return discord.Embed(title=f"❌ {t}", description=d, color=0xE74C3C)
def e_aviso(t, d): return discord.Embed(title=f"⚠️ {t}", description=d, color=0xF39C12)

async def log_staff(guild, titulo, autor, campos):
    log_ch = discord.utils.get(guild.text_channels, name="📋logs")
    if not log_ch: return
    embed = discord.Embed(title=titulo, color=0xE8A020)
    for nome, valor in campos:
        embed.add_field(name=nome, value=str(valor), inline=True)
    embed.add_field(name="Por", value=str(autor), inline=False)
    embed.set_footer(text="FFC • Log Staff")
    await log_ch.send(embed=embed)
