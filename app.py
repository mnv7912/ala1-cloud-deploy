import os
import platform
import socket
from datetime import datetime
import psutil
from flask import Flask, request, redirect, render_template_string

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL), "PostgreSQL (Managed Cloud DB)"
    import sqlite3
    return sqlite3.connect("local_fallback.db"), "SQLite (Local Storage)"


def init_db():
    conn, _ = get_db()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deployment_logs (
                id SERIAL PRIMARY KEY,
                node_name TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deployment_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_name TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
    conn.commit()
    cur.close()
    conn.close()


init_db()

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ALA 1 | Cloud Service Deployment</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-6">
  <div class="max-w-3xl mx-auto space-y-6">
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6">
      <div class="flex flex-wrap justify-between items-center gap-2 border-b border-slate-800 pb-4 mb-4">
        <div>
          <span class="text-xs uppercase tracking-wider text-sky-400 font-semibold">BETCE17336 • Cloud Computing (ALA 1)</span>
          <h1 class="text-2xl font-bold mt-1">Cloud Compute & Managed Storage Service</h1>
        </div>
        <span class="px-3 py-1 text-xs font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          ● Live on Cloud
        </span>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <p class="text-slate-400">Student</p>
          <p class="font-semibold mt-0.5">Manav B. Joshi</p>
        </div>
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <p class="text-slate-400">Enrollment</p>
          <p class="font-semibold mt-0.5">20230905090512</p>
        </div>
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <p class="text-slate-400">Compute Host</p>
          <p class="font-mono mt-0.5 truncate">{{ hostname }}</p>
        </div>
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <p class="text-slate-400">Storage Backend</p>
          <p class="font-semibold text-sky-400 mt-0.5">{{ db_type }}</p>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-3 text-xs mt-3">
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <p class="text-slate-400">OS / Runtime</p>
          <p class="font-mono mt-0.5">{{ os_info }} / Python {{ py_ver }}</p>
        </div>
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <p class="text-slate-400">Allocated vCPUs</p>
          <p class="font-mono mt-0.5">{{ cpu_count }} Cores</p>
        </div>
        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800">
          <p class="text-slate-400">Memory Usage</p>
          <p class="font-mono mt-0.5">{{ mem_used }} MB / {{ mem_total }} MB</p>
        </div>
      </div>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6">
      <h2 class="text-lg font-semibold mb-3">Cloud Database Persistence Test</h2>
      <form method="POST" action="/add" class="flex flex-col sm:flex-row gap-3 mb-5">
        <input name="node_name" required placeholder="Service / Node (e.g., Mumbai-Edge-01)"
               class="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm flex-1" />
        <input name="note" required placeholder="Deployment log message..."
               class="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm flex-1" />
        <button type="submit" class="bg-sky-600 hover:bg-sky-500 text-white font-medium px-4 py-2 rounded-lg text-sm">
          Write to DB
        </button>
      </form>

      <div class="space-y-2">
        {% for row in rows %}
        <div class="flex justify-between items-center bg-slate-950 border border-slate-800 px-4 py-2.5 rounded-lg text-sm">
          <div>
            <span class="font-mono text-sky-400 font-semibold">[{{ row[1] }}]</span>
            <span class="ml-2 text-slate-200">{{ row[2] }}</span>
          </div>
          <span class="text-xs text-slate-500 font-mono">{{ row[3] }}</span>
        </div>
        {% else %}
        <p class="text-xs text-slate-400">No records yet. Add an entry above to verify live cloud persistence.</p>
        {% endfor %}
      </div>
    </div>
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    conn, db_type = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, node_name, note, created_at FROM deployment_logs ORDER BY id DESC LIMIT 10")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    vm = psutil.virtual_memory()
    return render_template_string(
        HTML,
        hostname=socket.gethostname(),
        db_type=db_type,
        os_info=platform.system(),
        py_ver=platform.python_version(),
        cpu_count=psutil.cpu_count(logical=True),
        mem_used=round(vm.used / (1024 * 1024), 1),
        mem_total=round(vm.total / (1024 * 1024), 1),
        rows=rows,
    )


@app.route("/add", methods=["POST"])
def add():
    node_name = request.form.get("node_name", "").strip()
    note = request.form.get("note", "").strip()
    if node_name and note:
        conn, _ = get_db()
        cur = conn.cursor()
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        placeholder = "%s" if DATABASE_URL else "?"
        cur.execute(
            f"INSERT INTO deployment_logs (node_name, note, created_at) VALUES ({placeholder}, {placeholder}, {placeholder})",
            (node_name, note, ts),
        )
        conn.commit()
        cur.close()
        conn.close()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
