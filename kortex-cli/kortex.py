#!/usr/bin/env python3
"""
kortex — CLI para el supervisor de Claude Code
Uso: kortex <comando> [opciones]
"""
import sys
import json
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

API = "http://localhost:8080"


def _api(method: str, path: str, body: dict = None) -> dict:
    url = API + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {}
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"❌ API error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ {e}\n   ¿Está corriendo 'docker compose up'?", file=sys.stderr)
        sys.exit(1)


def cmd_watch(args):
    """Registra un proyecto y activa el watcher automático."""
    path = str(Path(args[0] if args else ".").resolve())
    name = None
    desc = None
    i = 1
    while i < len(args):
        if args[i] in ("-n", "--name") and i + 1 < len(args):
            name = args[i + 1]; i += 2
        elif args[i] in ("-d", "--desc") and i + 1 < len(args):
            desc = args[i + 1]; i += 2
        else:
            i += 1

    name = name or Path(path).name
    print(f"📁 Registrando proyecto: {name} → {path}")
    proj = _api("POST", "/projects", {"name": name, "path": path, "description": desc})
    print(f"✓ Proyecto creado  ID: {proj['id']}")

    print("⟳ Indexando codebase (puede tardar unos minutos)…")
    stats = _api("POST", "/ingest/codebase", {"project_id": proj["id"]})
    print(f"✓ {stats['files_indexed']} archivos · {stats['chunks_created']} chunks · {stats.get('commits_indexed', 0)} commits")

    print("👁  Activando watcher en tiempo real…")
    _api("POST", "/watch/start", {"project_id": proj["id"]})
    print(f"✓ Watcher activo. Git hook instalado en {path}/.git/hooks/post-commit")
    print(f"\n💡 Usa:  kortex ask 'tu tarea' -p {proj['id']}")


def cmd_ask(args):
    """Genera un prompt optimizado para Claude Code."""
    if not args:
        print("Uso: kortex ask '<tarea>' [-p <project_id>] [-c] [-n <chunks>]")
        sys.exit(1)

    task = args[0]
    project_id = None
    copy = False
    chunks = 8
    i = 1
    while i < len(args):
        if args[i] in ("-p", "--project") and i + 1 < len(args):
            project_id = args[i + 1]; i += 2
        elif args[i] in ("-c", "--copy"):
            copy = True; i += 1
        elif args[i] in ("-n", "--chunks") and i + 1 < len(args):
            chunks = int(args[i + 1]); i += 2
        else:
            i += 1

    print(f"🔍 Buscando contexto en RAG…")
    r = _api("POST", "/prompt/build", {
        "task": task,
        "project_id": project_id,
        "n_context_chunks": chunks,
    })

    prompt = r["prompt"]
    sep = "─" * 60
    print(f"\n{sep}")
    print(prompt)
    print(sep)
    print(f"\n📊 {r['context_chunks']} chunks · ~{r['tokens_estimate']} tokens · ~{r['tokens_saved_estimate']} tokens ahorrados")

    if copy:
        try:
            subprocess.run(["xclip", "-selection", "clipboard"],
                           input=prompt.encode(), check=True)
            print("✓ Copiado al portapapeles (xclip)")
        except FileNotFoundError:
            try:
                subprocess.run(["xsel", "--clipboard", "--input"],
                               input=prompt.encode(), check=True)
                print("✓ Copiado al portapapeles (xsel)")
            except FileNotFoundError:
                print("⚠ Instala xclip o xsel para copiar al portapapeles")


def cmd_status(args):
    """Muestra el estado del supervisor."""
    root = _api("GET", "/")
    projects = _api("GET", "/projects")
    watching = root.get("watching", [])

    print(f"\n🤖 Kortex F*Token v{root.get('version','1.0.0')}")
    print(f"   API: {API}")
    print(f"   Proyectos: {len(projects)}")
    print(f"   Vigilando: {len(watching)}")
    print()

    for p in projects:
        icon = "👁 " if p["id"] in watching else "   "
        chunks = p.get("chunks_count", "?")
        print(f"  {icon}{p['name']} [{p['id']}]")
        print(f"      {p['path']}")
        print(f"      {p.get('indexed_files', 0)} archivos · {chunks} chunks")
        if p.get("last_indexed"):
            print(f"      Indexado: {p['last_indexed']}")
        print()


def cmd_index(args):
    """Re-indexa un proyecto existente."""
    if not args:
        print("Uso: kortex index <project_id>")
        sys.exit(1)
    pid = args[0]
    print(f"⟳ Re-indexando proyecto {pid}…")
    stats = _api("POST", "/ingest/codebase", {"project_id": pid})
    print(f"✓ {stats['files_indexed']} archivos · {stats['chunks_created']} chunks · {stats.get('commits_indexed', 0)} commits")


def cmd_search(args):
    """Búsqueda semántica directa en el RAG."""
    if not args:
        print("Uso: kortex search '<consulta>' [-p <project_id>] [-n <results>]")
        sys.exit(1)
    query = args[0]
    project_id = None
    n = 5
    i = 1
    while i < len(args):
        if args[i] in ("-p", "--project") and i + 1 < len(args):
            project_id = args[i + 1]; i += 2
        elif args[i] in ("-n",) and i + 1 < len(args):
            n = int(args[i + 1]); i += 2
        else:
            i += 1

    results = _api("POST", "/context/search", {
        "query": query, "project_id": project_id, "n_results": n
    })

    for i, r in enumerate(results, 1):
        print(f"\n{'─'*50}")
        print(f"[{i}] {r['file_path']} (score: {r['score']}) [{r.get('language','')}]")
        print(r["content"][:500])


COMMANDS = {
    "watch": (cmd_watch, "Registra un proyecto y activa vigilancia en tiempo real"),
    "ask": (cmd_ask, "Genera un prompt optimizado para Claude Code"),
    "status": (cmd_status, "Muestra el estado del supervisor"),
    "index": (cmd_index, "Re-indexa un proyecto existente"),
    "search": (cmd_search, "Búsqueda semántica directa en el RAG"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("🤖 Kortex F*Token — Supervisor de Claude Code\n")
        print("Uso: kortex <comando> [opciones]\n")
        print("Comandos:")
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<10} {desc}")
        print()
        print("Ejemplos:")
        print("  kortex watch /home/user/Proyectos/gui -n 'GUI Project'")
        print("  kortex ask 'Implementar JWT en /api/auth/login' -c")
        print("  kortex status")
        return

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"❌ Comando desconocido: {cmd}")
        sys.exit(1)

    COMMANDS[cmd][0](sys.argv[2:])


if __name__ == "__main__":
    main()
