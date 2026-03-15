import aiosqlite
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "database.db")

# ─────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Jogadores
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jogadores (
                discord_id    TEXT PRIMARY KEY,
                discord_tag   TEXT NOT NULL,
                nick_ff       TEXT NOT NULL,
                id_ff         TEXT NOT NULL UNIQUE,
                registrado_em TEXT DEFAULT (datetime('now','localtime')),
                status        TEXT DEFAULT 'ativo'
            )
        """)
        # Times
        await db.execute("""
            CREATE TABLE IF NOT EXISTS times (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nome         TEXT NOT NULL UNIQUE,
                capitao_id   TEXT NOT NULL,
                capitao_nick TEXT NOT NULL,
                modo         TEXT NOT NULL,
                limite       INTEGER NOT NULL,
                status       TEXT DEFAULT 'open',
                criado_em    TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        # Membros dos times
        await db.execute("""
            CREATE TABLE IF NOT EXISTS time_membros (
                time_id    INTEGER NOT NULL,
                discord_id TEXT NOT NULL,
                nick_ff    TEXT NOT NULL,
                PRIMARY KEY (time_id, discord_id),
                FOREIGN KEY (time_id) REFERENCES times(id)
            )
        """)
        await db.commit()
    print("  🗄️   Banco de dados inicializado.")

# ─────────────────────────────────────────────────────────────────
# JOGADORES
# ─────────────────────────────────────────────────────────────────
async def get_jogador(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM jogadores WHERE discord_id = ?", (discord_id,)
        ) as c:
            return await c.fetchone()

async def get_jogador_por_id_ff(id_ff: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM jogadores WHERE id_ff = ?", (id_ff,)
        ) as c:
            return await c.fetchone()

async def registrar_jogador(discord_id, discord_tag, nick_ff, id_ff):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO jogadores (discord_id, discord_tag, nick_ff, id_ff) VALUES (?, ?, ?, ?)",
            (discord_id, discord_tag, nick_ff, id_ff)
        )
        await db.commit()

async def atualizar_jogador(discord_id, nick_ff, id_ff):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jogadores SET nick_ff = ?, id_ff = ? WHERE discord_id = ?",
            (nick_ff, id_ff, discord_id)
        )
        await db.commit()

# ─────────────────────────────────────────────────────────────────
# TIMES
# ─────────────────────────────────────────────────────────────────
async def criar_time(nome, capitao_id, capitao_nick, modo, limite):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO times (nome, capitao_id, capitao_nick, modo, limite) VALUES (?, ?, ?, ?, ?)",
            (nome, capitao_id, capitao_nick, modo, limite)
        )
        time_id = cursor.lastrowid
        await db.execute(
            "INSERT INTO time_membros (time_id, discord_id, nick_ff) VALUES (?, ?, ?)",
            (time_id, capitao_id, capitao_nick)
        )
        await db.commit()
        return time_id

async def get_time_por_nome(nome: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM times WHERE nome = ?", (nome,)
        ) as c:
            return await c.fetchone()

async def get_time_do_jogador(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT t.* FROM times t
            JOIN time_membros tm ON t.id = tm.time_id
            WHERE tm.discord_id = ?
        """, (discord_id,)) as c:
            return await c.fetchone()

async def get_membros_time(time_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM time_membros WHERE time_id = ?", (time_id,)
        ) as c:
            return await c.fetchall()

async def get_todos_times():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM times ORDER BY criado_em DESC") as c:
            return await c.fetchall()

async def entrar_time(time_id: int, discord_id: str, nick_ff: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO time_membros (time_id, discord_id, nick_ff) VALUES (?, ?, ?)",
            (time_id, discord_id, nick_ff)
        )
        await db.commit()

async def sair_time(time_id: int, discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM time_membros WHERE time_id = ? AND discord_id = ?",
            (time_id, discord_id)
        )
        await db.commit()

async def deletar_time(time_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM time_membros WHERE time_id = ?", (time_id,))
        await db.execute("DELETE FROM times WHERE id = ?", (time_id,))
        await db.commit()

async def atualizar_status_time(time_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE times SET status = ? WHERE id = ?", (status, time_id)
        )
        await db.commit()

# ─────────────────────────────────────────────────────────────────
# CAMPEONATOS (adicionado no init_db abaixo via patch)
# ─────────────────────────────────────────────────────────────────
async def _criar_tabelas_campeonato():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS campeonatos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT NOT NULL,
                modo       TEXT NOT NULL,
                taxa       REAL NOT NULL,
                minimo     INTEGER NOT NULL,
                maximo     INTEGER,
                status     TEXT DEFAULT 'criado',
                criado_por TEXT NOT NULL,
                criado_em  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inscricoes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                camp_id     INTEGER NOT NULL,
                discord_id  TEXT NOT NULL,
                nick_ff     TEXT NOT NULL,
                nome_time   TEXT,
                pago        INTEGER DEFAULT 0,
                inscrito_em TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (camp_id) REFERENCES campeonatos(id)
            )
        """)
        await db.commit()

async def criar_campeonato(nome, modo, taxa, minimo, maximo, criado_por):
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "INSERT INTO campeonatos (nome, modo, taxa, minimo, maximo, criado_por) VALUES (?,?,?,?,?,?)",
            (nome, modo, taxa, minimo, maximo, criado_por)
        )
        await db.commit()
        return c.lastrowid

async def get_campeonato_por_id(camp_id: int):
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM campeonatos WHERE id = ?", (camp_id,)) as c:
            return await c.fetchone()

async def get_campeonato_ativo():
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM campeonatos WHERE status IN ('aberto','em_andamento') ORDER BY id DESC LIMIT 1"
        ) as c:
            return await c.fetchone()

async def get_campeonatos_por_status(status: str):
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM campeonatos WHERE status = ? ORDER BY id DESC", (status,)
        ) as c:
            return await c.fetchall()

async def get_campeonatos_ativos():
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM campeonatos WHERE status IN ('criado','aberto','em_andamento') ORDER BY id DESC"
        ) as c:
            return await c.fetchall()

async def atualizar_status_campeonato(camp_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE campeonatos SET status = ? WHERE id = ?", (status, camp_id))
        await db.commit()

async def inscrever_jogador(camp_id, discord_id, nick_ff, nome_time):
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO inscricoes (camp_id, discord_id, nick_ff, nome_time) VALUES (?,?,?,?)",
            (camp_id, discord_id, nick_ff, nome_time)
        )
        await db.commit()

async def jogador_inscrito(camp_id: int, discord_id: str):
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM inscricoes WHERE camp_id = ? AND discord_id = ?", (camp_id, discord_id)
        ) as c:
            return await c.fetchone() is not None

async def get_inscritos_campeonato(camp_id: int):
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM inscricoes WHERE camp_id = ?", (camp_id,)
        ) as c:
            return await c.fetchall()

async def cancelar_inscricao(camp_id: int, discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM inscricoes WHERE camp_id = ? AND discord_id = ?", (camp_id, discord_id)
        )
        await db.commit()

# ─────────────────────────────────────────────────────────────────
# RESULTADOS
# ─────────────────────────────────────────────────────────────────
async def _criar_tabelas_resultados():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS resultados (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                camp_id      INTEGER NOT NULL,
                time_id      INTEGER NOT NULL,
                time_nome    TEXT NOT NULL,
                adversario   TEXT NOT NULL,
                placar       TEXT NOT NULL,
                link_video   TEXT,
                status       TEXT DEFAULT 'pendente',
                motivo       TEXT,
                enviado_por  TEXT NOT NULL,
                enviado_em   TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (camp_id) REFERENCES campeonatos(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ranking (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                time_nome    TEXT NOT NULL UNIQUE,
                time_id      INTEGER NOT NULL,
                vitorias     INTEGER DEFAULT 0,
                derrotas     INTEGER DEFAULT 0,
                camps_ganhos INTEGER DEFAULT 0,
                pontos       INTEGER DEFAULT 0,
                atualizado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        await db.commit()

async def salvar_resultado(camp_id, time_nome, time_id, adversario, placar, link_video, enviado_por):
    await _criar_tabelas_resultados()
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            """INSERT INTO resultados
               (camp_id, time_id, time_nome, adversario, placar, link_video, enviado_por)
               VALUES (?,?,?,?,?,?,?)""",
            (camp_id, time_id, time_nome, adversario, placar, link_video, enviado_por)
        )
        await db.commit()
        return c.lastrowid

async def get_resultado_por_id(resultado_id: int):
    await _criar_tabelas_resultados()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM resultados WHERE id = ?", (resultado_id,)
        ) as c:
            return await c.fetchone()

async def get_ultimo_resultado_time(camp_id: int, time_nome: str):
    await _criar_tabelas_resultados()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM resultados WHERE camp_id = ? AND time_nome = ? ORDER BY id DESC LIMIT 1",
            (camp_id, time_nome)
        ) as c:
            return await c.fetchone()

async def get_resultados_time(camp_id: int, time_nome: str):
    await _criar_tabelas_resultados()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM resultados WHERE camp_id = ? AND time_nome = ? ORDER BY id DESC",
            (camp_id, time_nome)
        ) as c:
            return await c.fetchall()

async def atualizar_resultado(resultado_id: int, status: str, motivo: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE resultados SET status = ?, motivo = ? WHERE id = ?",
            (status, motivo, resultado_id)
        )
        await db.commit()

async def get_time_inscrito_campeonato(camp_id: int, nome_time: str):
    await _criar_tabelas_campeonato()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM inscricoes WHERE camp_id = ? AND nome_time = ? LIMIT 1",
            (camp_id, nome_time)
        ) as c:
            return await c.fetchone()

# ─────────────────────────────────────────────────────────────────
# RANKING
# ─────────────────────────────────────────────────────────────────
async def incrementar_ranking(time_nome: str, time_id: int, tipo: str):
    await _criar_tabelas_resultados()
    async with aiosqlite.connect(DB_PATH) as db:
        # Garante que o time existe no ranking
        await db.execute(
            "INSERT OR IGNORE INTO ranking (time_nome, time_id) VALUES (?,?)",
            (time_nome, time_id)
        )
        col = {"vitoria": "vitorias", "derrota": "derrotas", "camp_ganho": "camps_ganhos"}.get(tipo)
        if col:
            pontos_extra = 3 if tipo == "vitoria" else (10 if tipo == "camp_ganho" else 0)
            await db.execute(
                f"UPDATE ranking SET {col} = {col} + 1, pontos = pontos + ? WHERE time_nome = ?",
                (pontos_extra, time_nome)
            )
        await db.commit()

async def get_ranking(limit: int = 10):
    await _criar_tabelas_resultados()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM ranking ORDER BY pontos DESC, vitorias DESC LIMIT ?", (limit,)
        ) as c:
            return await c.fetchall()

async def get_ranking_time(time_nome: str):
    await _criar_tabelas_resultados()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM ranking WHERE time_nome = ?", (time_nome,)
        ) as c:
            return await c.fetchone()

# ─────────────────────────────────────────────────────────────────
# PUNIÇÕES
# ─────────────────────────────────────────────────────────────────
async def _criar_tabelas_punicoes():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS punicoes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id   TEXT NOT NULL,
                discord_tag  TEXT NOT NULL,
                tipo         TEXT NOT NULL,
                motivo       TEXT NOT NULL,
                horas        INTEGER DEFAULT 0,
                permanente   INTEGER DEFAULT 0,
                aplicado_por TEXT NOT NULL,
                aplicado_em  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        await db.commit()

async def salvar_punicao(discord_id, discord_tag, tipo, motivo, horas, permanente, aplicado_por):
    await _criar_tabelas_punicoes()
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            """INSERT INTO punicoes (discord_id, discord_tag, tipo, motivo, horas, permanente, aplicado_por)
               VALUES (?,?,?,?,?,?,?)""",
            (discord_id, discord_tag, tipo, motivo, horas, 1 if permanente else 0, aplicado_por)
        )
        await db.commit()
        return c.lastrowid

async def get_ultima_punicao(discord_id: str, tipo: str):
    await _criar_tabelas_punicoes()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM punicoes WHERE discord_id = ? AND tipo = ? ORDER BY id DESC LIMIT 1",
            (discord_id, tipo)
        ) as c:
            return await c.fetchone()

async def get_punicoes_membro(discord_id: str):
    await _criar_tabelas_punicoes()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM punicoes WHERE discord_id = ? ORDER BY id DESC",
            (discord_id,)
        ) as c:
            return await c.fetchall()

# ─────────────────────────────────────────────────────────────────
# TICKETS
# ─────────────────────────────────────────────────────────────────
async def _criar_tabelas_tickets():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id   TEXT NOT NULL,
                discord_tag  TEXT NOT NULL,
                categoria    TEXT NOT NULL,
                status       TEXT DEFAULT 'aberto',
                criado_em    TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        await db.commit()

async def criar_ticket(discord_id, discord_tag, categoria):
    await _criar_tabelas_tickets()
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "INSERT INTO tickets (discord_id, discord_tag, categoria) VALUES (?,?,?)",
            (discord_id, discord_tag, categoria)
        )
        await db.commit()
        return c.lastrowid

async def get_ticket(ticket_id: int):
    await _criar_tabelas_tickets()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)) as c:
            return await c.fetchone()

async def get_ticket_aberto_membro(discord_id: str):
    await _criar_tabelas_tickets()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM tickets WHERE discord_id = ? AND status = 'aberto' ORDER BY id DESC LIMIT 1",
            (discord_id,)
        ) as c:
            return await c.fetchone()

async def get_tickets_abertos():
    await _criar_tabelas_tickets()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM tickets WHERE status = 'aberto'"
        ) as c:
            return await c.fetchall()

async def atualizar_ticket(ticket_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        await db.commit()

# ─────────────────────────────────────────────────────────────────
# SEGURANÇA / SEASON
# ─────────────────────────────────────────────────────────────────
async def get_total_jogadores():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM jogadores") as c:
            row = await c.fetchone()
            return row[0] if row else 0

async def get_todos_resultados_campeonato(camp_id: int):
    await _criar_tabelas_resultados()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM resultados WHERE camp_id = ?", (camp_id,)
        ) as c:
            return await c.fetchall()

async def resetar_season():
    """Zera ranking, deleta times e membros. Jogadores são mantidos."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM ranking")
        await db.execute("DELETE FROM time_membros")
        await db.execute("DELETE FROM times")
        await db.execute("UPDATE campeonatos SET status = 'cancelado' WHERE status IN ('aberto','em_andamento','criado')")
        await db.commit()

# ─────────────────────────────────────────────────────────────────
# SNAPSHOT DE CARGOS (mute)
# ─────────────────────────────────────────────────────────────────
async def _criar_tabela_snapshots():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cargos_snapshot (
                discord_id  TEXT PRIMARY KEY,
                cargos_json TEXT NOT NULL,
                salvo_em    TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        await db.commit()

async def salvar_cargos_snapshot(discord_id: str, cargos_json: str):
    await _criar_tabela_snapshots()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO cargos_snapshot (discord_id, cargos_json) VALUES (?, ?)",
            (discord_id, cargos_json)
        )
        await db.commit()

async def get_cargos_snapshot(discord_id: str):
    await _criar_tabela_snapshots()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT cargos_json FROM cargos_snapshot WHERE discord_id = ?", (discord_id,)
        ) as c:
            row = await c.fetchone()
            return row[0] if row else None

async def deletar_cargos_snapshot(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM cargos_snapshot WHERE discord_id = ?", (discord_id,)
        )
        await db.commit()
