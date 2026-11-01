"""Free read-only quotes. No accounts or trading credentials required."""
import json, urllib.parse, concurrent.futures, datetime, math
COINS={'bitcoin':'BTC','ethereum':'ETH','solana':'SOL','binancecoin':'BNB'}
def number(value):
    value=float(value)
    if not math.isfinite(value):raise ValueError('Invalid price')
    return value
def binance_quotes(config,getjson):
    ids=config.get('coins',list(COINS));symbols=[COINS[c]+'USDT' for c in ids if c in COINS]
    if not symbols:raise ValueError('No supported Binance symbols')
    data=getjson('https://data-api.binance.vision/api/v3/ticker/24hr?'+urllib.parse.urlencode({'symbols':json.dumps(symbols,separators=(',',':'))}))
    if not isinstance(data,list):raise ValueError('Invalid Binance response')
    by={r['symbol']:r for r in data};rows=[]
    for c in ids:
        a=by.get(COINS.get(c,'')+'USDT')
        if a:rows.append({'name':c,'symbol':COINS[c],'price':number(a['lastPrice']),'change':number(a['priceChangePercent']),'time':int(a['closeTime'])/1000,'currency':'USDT','source':'Binance 公共行情','basis':'24小时涨跌'})
    if not rows:raise ValueError('No Binance prices')
    return {'rows':rows,'source':'Binance 公共行情（免密只读）','error':'' if len(rows)==len(ids) else '部分币种不受此来源支持','stale':len(rows)!=len(ids)}
def coingecko_quotes(config,getjson):
    ids=config.get('coins',list(COINS));data=getjson('https://api.coingecko.com/api/v3/simple/price?'+urllib.parse.urlencode({'ids':','.join(ids),'vs_currencies':'usd','include_24hr_change':'true','include_last_updated_at':'true'}));rows=[]
    for c in ids:
        a=data.get(c,{})
        if 'usd' in a:rows.append({'name':c,'symbol':COINS.get(c,c),'price':number(a['usd']),'change':number(a['usd_24h_change']) if a.get('usd_24h_change') is not None else None,'time':a.get('last_updated_at'),'currency':'USD','source':'CoinGecko','basis':'24小时涨跌'})
    if not rows:raise ValueError('No CoinGecko prices')
    return {'rows':rows,'source':'CoinGecko','error':'' if len(rows)==len(ids) else '部分币种缺失','stale':len(rows)!=len(ids)}
def crypto(config,getjson):
    errors=[]
    for fetch in (binance_quotes,coingecko_quotes):
        try:return fetch(config,getjson)
        except Exception as e:errors.append(fetch.__name__+': '+str(e))
    raise ValueError('; '.join(errors))
def tencent_us(config,request):
    symbols=config.get('us_stocks',['NVDA','AAPL','TSLA','MSFT']);raw=request('https://qt.gtimg.cn/q='+','.join('us'+s for s in symbols)).decode('gbk',errors='replace');rows=[]
    for line in raw.split(';'):
        if '="' not in line:continue
        a=line.split('="',1)[1].strip('"\r\n').split('~')
        if len(a)>35 and a[3]:
            symbol=a[2].split('.')[0]
            if symbol not in symbols:continue
            rows.append({'name':a[1],'symbol':symbol,'price':number(a[3]),'change':number(a[32]),'time':a[30],'currency':a[35] or 'USD','source':'腾讯财经美股','basis':'较前收盘涨跌 · 来源时间未换算'})
    if not rows:raise ValueError('No US quotes from Tencent')
    return rows
def yahoo(symbol,getjson):
    errors=[]
    for host in ('query1.finance.yahoo.com','query2.finance.yahoo.com'):
        try:
            r=getjson('https://'+host+'/v8/finance/chart/'+urllib.parse.quote(symbol,safe='')+'?interval=1d&range=5d')['chart']['result'][0];m=r['meta'];closes=[x for x in r['indicators']['quote'][0]['close'] if x is not None];previous=m.get('previousClose') or (closes[-2] if len(closes)>1 else None);px=number(m['regularMarketPrice'])
            return {'name':m.get('shortName',symbol),'symbol':symbol,'price':px,'change':(px/previous-1)*100 if previous else None,'time':m.get('regularMarketTime'),'currency':m.get('currency','USD'),'source':'Yahoo Finance','basis':'较前收盘涨跌 · 可能延迟'}
        except Exception as e:errors.append(str(e))
    raise ValueError('; '.join(errors))
def us(config,request,getjson):
    symbols=config.get('us_stocks',['NVDA','AAPL','TSLA','MSFT']);errors=[]
    try:rows=tencent_us(config,request)
    except Exception as e:rows=[];errors.append('Tencent: '+str(e))
    missing=[s for s in symbols if s not in {r['symbol'] for r in rows}]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={s:pool.submit(yahoo,s,getjson) for s in missing}
        for s,f in futures.items():
            try:rows.append(f.result())
            except Exception as e:errors.append(s+': '+str(e))
    if not rows:raise ValueError('; '.join(errors))
    rows.sort(key=lambda r:symbols.index(r['symbol']));partial=len(rows)!=len(symbols)
    return {'rows':rows,'source':' / '.join(dict.fromkeys(r['source'] for r in rows)),'error':'; '.join(errors) if partial else '','stale':partial}
