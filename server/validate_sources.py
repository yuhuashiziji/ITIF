import pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import app
sources=app.EDITOR.sources(app.CONFIG)
assert len({s['id'] for s in sources})==len(sources)
for s in sources:
 assert s['language'] in ('zh','en','other') and 300<=s['interval']<=604800
 assert s['kind'] in ('rss','hot','web') and s['attribution'] and s['url'].startswith(('http://','https://'))
print('Catalog validation PASS:',len(sources))
