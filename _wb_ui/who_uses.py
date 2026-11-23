# -*- coding: utf-8 -*-
"""反查 UI 里每个 Image 用的到底是哪张图 / 哪个切片，按 GameObject 名字归类。"""
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_maps():
    g2p, id2name = {}, {}
    for dp, dn, fn in os.walk(os.path.join(ROOT, 'Assets')):
        for f in fn:
            if not f.endswith('.meta'):
                continue
            p = os.path.join(dp, f)
            try:
                t = open(p, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            m = re.search(r'^guid: ([0-9a-f]{32})', t, re.M)
            if not m:
                continue
            g = m.group(1)
            tex = p[:-5]
            g2p[g] = tex
            pairs = re.findall(r'- first:\n\s+213: (\d+)\n\s+second: (.*)', t)
            if pairs:
                id2name[g] = dict((a, b.strip()) for a, b in pairs)
    return g2p, id2name


def parse(path, g2p, id2name):
    t = open(path, encoding='utf-8', errors='ignore').read()
    docs = {}
    order = []
    for m in re.finditer(r'^--- !u!(\d+) &(-?\d+)(?: stripped)?\n', t, re.M):
        cls, fid = m.group(1), m.group(2)
        start = m.end()
        nxt = t.find('\n--- !u!', start)
        body = t[start:nxt if nxt > 0 else len(t)]
        docs[fid] = (cls, body)
        order.append(fid)
    rows = []
    for fid in order:
        cls, body = docs[fid]
        if cls != '114' or 'm_Sprite:' not in body:
            continue
        sp = re.search(r'm_Sprite: \{fileID: (-?\d+), guid: ([0-9a-f]{32})', body)
        if not sp:
            continue
        gob = re.search(r'm_GameObject: \{fileID: (-?\d+)\}', body)
        name = '?'
        if gob and gob.group(1) in docs:
            nm = re.search(r'  m_Name: (.*)', docs[gob.group(1)][1])
            if nm:
                name = nm.group(1).strip()
        tex = g2p.get(sp.group(2), sp.group(2))
        sub = id2name.get(sp.group(2), {}).get(sp.group(1), sp.group(1))
        rows.append((os.path.basename(os.path.dirname(tex)) + '/' + os.path.basename(tex), sub, name))
    return rows


if __name__ == '__main__':
    targets = sys.argv[1:] or [os.path.join(ROOT, 'Assets', 'Merge Beast', 'Scenes', 'Main.unity')]
    g2p, id2name = build_maps()
    for tp in targets:
        rows = parse(tp, g2p, id2name)
        print('== %s  (%d images)' % (os.path.relpath(tp, ROOT), len(rows)))
        key = re.compile(r'btn|button|shop|boost|upg|bag|book|merge|buff|add|star|iap|buy|close|exit|x$', re.I)
        for tex, sub, name in rows:
            if key.search(name):
                print('  %-34s %-26s <- %s' % (name[:34], str(sub)[:26], tex))
