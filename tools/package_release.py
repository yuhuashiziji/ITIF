"""Build an allowlisted source archive; never collect runtime state."""
import argparse, hashlib, json, re, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES=['每日聚合站_融合版.html','启动服务.cmd','README.md','AUTHORS.md','LICENSE','CONTRIBUTING.md','CHANGELOG.md','DESIGN.md','.gitignore','requirements.txt']
def build(output):
    files=[ROOT/name for name in ROOT_FILES]
    for folder,pattern in [('server','*.py'),('server','*.js'),('server','*.css'),('tests','test_*.py'),('tests','test_*.js'),('docs','*.md'),('content/weekly','*.md'),('.github','*.md'),('.github','*.yml'),('tools','*.py'),('hosting/php','*.php'),('hosting/php','*.js'),('public-data','*.json')]:
        search=(ROOT/folder).rglob(pattern) if folder=='.github' else (ROOT/folder).glob(pattern)
        files.extend(p for p in search if '__pycache__' not in p.parts)
    files.extend(ROOT/'server'/name for name in ['sources.json','config.example.json'])
    files=sorted(p for p in set(files) if p != ROOT/'hosting/php/config.php');manifest=[]
    for path in files:
        relative=path.relative_to(ROOT).as_posix()
        if not path.is_file():raise ValueError('Missing release file: '+relative)
        text=path.read_text(encoding='utf-8-sig')
        # Do not include fetched competitor pages, local paths or credential material.
        forbidden=['top'+'hub.today','C:'+chr(92)+'Users'+chr(92),'D:'+chr(92)+'每日聚合站','-----BEGIN '+'PRIVATE KEY-----']
        if any(value.casefold() in text.casefold() for value in forbidden):raise ValueError('Private or excluded content: '+relative)
        if re.search(r'(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_]{20,}',text):raise ValueError('Possible credential: '+relative)
        manifest.append({'path':relative,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    output.mkdir(parents=True,exist_ok=True)
    archive=output/'itif-source.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for row in manifest:z.write(ROOT/row['path'],'itif/'+row['path'])
        z.writestr('itif/MANIFEST.json',json.dumps({'project':'ITIF 信息台','version':'0.2.0','files':manifest},ensure_ascii=False,indent=2))
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'itif-source.sha256').write_text(checksum+'  itif-source.zip\n',encoding='utf-8')
    print(f'Built {archive.name}: {len(files)} source files, {archive.stat().st_size} bytes')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist');args=parser.parse_args();build(args.output)
