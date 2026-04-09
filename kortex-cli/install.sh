#!/bin/bash
# Instala el CLI de Kortex en el sistema
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="/usr/local/bin/kortex"

echo "🤖 Instalando Kortex CLI…"
sudo cp "$SCRIPT_DIR/kortex.py" "$TARGET"
sudo chmod +x "$TARGET"

# Asegurar que el shebang de python3 funcione
if ! command -v python3 &>/dev/null; then
  echo "⚠ python3 no encontrado. Instálalo primero."
  exit 1
fi

echo "✓ Instalado en $TARGET"
echo ""
echo "Prueba con:  kortex status"
echo "             kortex watch /ruta/proyecto -n 'Mi Proyecto'"
echo "             kortex ask 'implementa autenticación JWT' -c"
