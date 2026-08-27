import httpx
base='http://127.0.0.1:8000'
for p in ['/','/health','/market','/docs']:
    try:
        r=httpx.get(base+p, timeout=5.0)
        print(p, r.status_code, (r.headers.get('content-type') or '')[:80])
    except Exception as e:
        print(p, 'ERROR', e)
