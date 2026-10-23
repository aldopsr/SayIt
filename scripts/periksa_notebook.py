"""Pemeriksaan wajib tiap kali notebook disentuh: format, sintaks, urutan nama."""
import ast
import builtins
import json
import sys
from pathlib import Path

NB = Path('notebooks/04_money_kfold.ipynb')
nb = json.loads(NB.read_text(encoding='utf-8'))
cells = nb['cells']
galat = []

# 1. format sumber: tiap baris kecuali yang terakhir harus berakhir newline
for i, c in enumerate(cells):
    src = c['source']
    if not isinstance(src, list):
        galat.append(f'sel {i}: source bukan list')
        continue
    for j, ln in enumerate(src[:-1]):
        if not ln.endswith(chr(10)):
            galat.append(f'sel {i} baris {j}: tidak diakhiri newline -> {ln[:50]!r}')
    # baris terakhir boleh diakhiri newline; Jupyter menerima keduanya

# 2. sintaks tiap sel kode
pohon = {}
for i, c in enumerate(cells):
    if c['cell_type'] != 'code':
        continue
    s = ''.join(c['source'])
    if s.lstrip().startswith('!') or s.lstrip().startswith('%'):
        continue
    try:
        pohon[i] = ast.parse(s)
    except SyntaxError as e:
        galat.append(f'sel {i}: SyntaxError baris {e.lineno}: {e.msg}')

# 3. urutan nama: tidak ada nama dipakai sebelum didefinisikan (Run all aman)
tersedia = set(dir(builtins)) | {'display', 'get_ipython', 'In', 'Out'}


def definisi(t):
    out = set()
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.add(n.id)
        elif isinstance(n, ast.alias):
            out.add((n.asname or n.name).split('.')[0])
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
    return out


for i in sorted(pohon):
    t = pohon[i]
    lokal = definisi(t)
    for n in ast.walk(t):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            if n.id not in tersedia and n.id not in lokal:
                galat.append(f'sel {i} baris {n.lineno}: nama {n.id!r} dipakai sebelum didefinisikan')
    tersedia |= lokal

if galat:
    print('GAGAL:')
    for g in galat:
        print('  -', g)
    sys.exit(1)
print(f'LULUS: {len(cells)} sel, {len(pohon)} sel kode diurai, format dan urutan nama aman')
