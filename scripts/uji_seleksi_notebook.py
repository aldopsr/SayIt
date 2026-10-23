"""Uji lokal logika seleksi data notebook, dengan dataset buatan.

Yang dibuktikan:
  1. foto SENDIRI tanpa berkas label  -> DILEWATI
  2. foto SENDIRI dengan label kosong -> DILEWATI
  3. gambar latar dataset PUBLIK      -> TETAP DIPAKAI (tidak boleh kena aturan baru)
  4. sidik jari lipatan berubah bila daftar foto berubah
"""
import hashlib
import json
import tempfile
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

S = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()) / 'uji_seleksi'
shutil.rmtree(S, ignore_errors=True)

CLASSES = ['1000', '2000', '5000', '10000', '20000', '50000', '100000']
NESTED_CONTAIN = 0.85


def buat(root, isi):
    """isi: {nama_berkas: None (tanpa .txt) | '' (kosong) | 'baris label'}"""
    (root / 'test' / 'images').mkdir(parents=True)
    (root / 'test' / 'labels').mkdir(parents=True)
    for nama, lab in isi.items():
        cv2.imwrite(str(root / 'test' / 'images' / f'{nama}.jpg'),
                    np.full((40, 40, 3), 128, np.uint8))
        if lab is not None:
            (root / 'test' / 'labels' / f'{nama}.txt').write_text(lab)


buat(S / 'sendiri', {
    '5000_a': '2 0.5 0.5 0.3 0.3',
    '2000_b': '1 0.5 0.5 0.3 0.3',
    '5000_tanpa_txt': None,
    '5000_txt_kosong': '',
})
buat(S / 'publik', {
    '10000_x': '3 0.5 0.5 0.3 0.3',
    'latar_jalanan': '',
})

# ---- fungsi bantu asli dari notebook (sel 10), disalin apa adanya
import re
exec_ns = {'Path': Path, 'cv2': cv2, 'np': np, 'defaultdict': defaultdict, 're': re}
nb = json.loads(Path('notebooks/04_money_kfold.ipynb').read_text(encoding='utf-8'))
src10 = ''.join(nb['cells'][10]['source'])
src10 = src10[:src10.index('def phash_bits')]  # phash butuh PIL+imagehash, tidak dipakai di sini
exec(compile(src10, 'sel10', 'exec'), exec_ns)
globals().update({k: v for k, v in exec_ns.items() if not k.startswith('__')})

# ---- sel 12 apa adanya
src12 = ''.join(nb['cells'][12]['source'])
DATASETS = [
    dict(nama='SENDIRI', root=S / 'sendiri', names=CLASSES, mode='percaya_label', sendiri=True),
    dict(nama='PUB', root=S / 'publik', names=CLASSES, mode='percaya_label'),
]
ns = dict(globals())
ns.update(Counter=Counter, defaultdict=defaultdict, DATASETS=DATASETS,
          CLASSES=CLASSES, NESTED_CONTAIN=NESTED_CONTAIN, Path=Path, cv2=cv2, np=np)
exec(compile(src12, 'sel12', 'exec'), ns)

records = ns['records']
dilewati = ns['dilewati']
dipakai = sorted(r['asal'] for r in records)

print()
print('dipakai  :', dipakai)
print('dilewati :', dilewati)

assert 'SENDIRI/5000_tanpa_txt.jpg' in dilewati, 'foto sendiri tanpa .txt harusnya dilewati'
assert 'SENDIRI/5000_txt_kosong.jpg' in dilewati, 'foto sendiri berlabel kosong harusnya dilewati'
assert 'SENDIRI/5000_a.jpg' in dipakai and 'SENDIRI/2000_b.jpg' in dipakai
assert 'PUB/latar_jalanan.jpg' in dipakai, 'gambar latar PUBLIK TIDAK boleh ikut dibuang'
assert all(r['labels'] for r in records if r['sendiri'])
print('OK  1-3: foto sendiri tanpa label dilewati, latar publik tetap dipakai')

# ---- sidik jari lipatan (sel 26)
src26 = ''.join(nb['cells'][26]['source'])
fn = src26[src26.index('def sidik_lipatan'):src26.index('hasil_fold = {}')]
ns2 = {'records': records, 'hashlib': hashlib, 'chr': chr, 'sorted': sorted}
exec(compile(fn, 'sel26', 'exec'), ns2)
sidik = ns2['sidik_lipatan']

bagi_a = {id(r): ('test' if r['sendiri'] else 'train') for r in records}
bagi_b = dict(bagi_a)
bagi_b[id(records[0])] = 'train'
assert sidik(bagi_a) == sidik(bagi_a), 'sidik harus stabil'
assert sidik(bagi_a) != sidik(bagi_b), 'sidik harus berubah bila pembagian berubah'

sidik_a = sidik(bagi_a)   # dihitung SEBELUM records ditukar
tambahan = records + [{'dataset': 'SENDIRI', 'path': Path('x'), 'asal': 'SENDIRI/baru',
                       'labels': [('5000', [.5, .5, .3, .3])], 'sendiri': True}]
ns2['records'] = tambahan
bagi_c = {id(r): ('test' if r['sendiri'] else 'train') for r in tambahan}
assert sidik(bagi_c) != sidik_a, 'sidik harus berubah bila ada foto baru'
print('OK  4: sidik jari lipatan berubah bila foto atau pembagiannya berubah')

shutil.rmtree(S, ignore_errors=True)
print()
print('SEMUA UJI LULUS')
