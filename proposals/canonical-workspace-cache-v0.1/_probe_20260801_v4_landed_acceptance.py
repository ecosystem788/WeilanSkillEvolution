import subprocess, os, json, hashlib

REPO = r'D:\WeilanSkillEvolution'
ARCH = 'proposals/canonical-workspace-cache-v0.1/execution-wf-20260801-075758-0b0905-v3-gitattributes'


def git(*args):
    p = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True)
    return p.returncode, p.stdout.decode('utf-8', 'replace').strip(), p.stderr.decode('utf-8', 'replace').strip()

out = {'archive': ARCH, 'files': []}
names = sorted(os.listdir(os.path.join(REPO, ARCH.replace('/', os.sep))))
for n in names:
    rel = ARCH + '/' + n
    disk = os.path.join(REPO, rel.replace('/', os.sep))
    b = open(disk, 'rb').read()
    rc1, raw, _ = git('hash-object', '-t', 'blob', '--no-filters', '--', rel)
    rc2, filt, _ = git('hash-object', '-t', 'blob', '--path', rel, '--', rel)
    rc3, attr, _ = git('check-attr', 'text', 'eol', '--', rel)
    out['files'].append({
        'path': rel,
        'size': len(b),
        'sha256': hashlib.sha256(b).hexdigest(),
        'crlf_count': b.count(b'\r\n'),
        'raw_oid': raw,
        'filtered_oid': filt,
        'raw_equals_filtered': raw == filt and rc1 == 0 and rc2 == 0,
        'check_attr': attr.replace('\n', ' | '),
    })

# scope guard: did any tracked path's attributes move?
rc, tracked, _ = git('ls-files', '--', 'proposals/canonical-workspace-cache-v0.1')
out['tracked_in_package'] = len([x for x in tracked.splitlines() if x.strip()])
out['summary'] = {
    'files_checked': len(out['files']),
    'raw_equals_filtered': sum(1 for f in out['files'] if f['raw_equals_filtered']),
}
print(json.dumps(out, ensure_ascii=False, indent=1))
