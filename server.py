from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json,time,secrets,random,threading,os
rooms={}; lock=threading.Lock()
def deal(r):
 d=[(v,s) for v in range(2,15) for s in '♠♥♦♣']; random.shuffle(d);r.update(deck=d[:16],public=d[16:19],start=time.time()+2,picks={},ready=[])
def score(cs):
 v=sorted([c[0] for c in cs],reverse=True);g=sorted([(v.count(x),x) for x in set(v)],reverse=True);f=len(set(c[1] for c in cs))==1;u=sorted(set(v));s=(u[-1] if len(u)==5 and u[-1]-u[0]==4 else 5 if u==[2,3,4,5,14] else 0)
 if f and s:return [8,s]
 if g[0][0]==4:return [7]+[x for n,x in g]
 if g[0][0]==3 and g[1][0]==2:return [6]+[x for n,x in g]
 if f:return [5]+v
 if s:return [4,s]
 return [3 if g[0][0]==3 else 2 if g[0][0]==g[1][0]==2 else 1 if g[0][0]==2 else 0]+[x for n,x in g]
class H(SimpleHTTPRequestHandler):
 def do_POST(self):
  try:
   a=json.loads(self.rfile.read(int(self.headers['Content-Length'])));op=a['op'];p=a.get('player');code=a.get('room','').upper()
   with lock:
    if op=='create':
     code=secrets.token_hex(3).upper();p=secrets.token_urlsafe(20);rooms[code]={'players':[p],'wins':[0,0],'round':1,'start':None}
    r=rooms[code]
    if op=='join' and p not in r['players']:
     if len(r['players'])==2:raise ValueError('房間已滿')
     p=secrets.token_urlsafe(20);r['players'].append(p);deal(r)
    if p not in r['players']:raise ValueError('無效玩家')
    now=time.time();phase='waiting' if r['start'] is None else 'prepare' if now<r['start'] else 'memory' if now<r['start']+30 else 'result' if len(r['picks'])==2 else 'choose'
    if op=='pick' and phase=='choose' and p not in r['picks']:
     x=a['picks'];assert len(x)==2 and len(set(x))==2 and all(type(i)==int and 0<=i<16 for i in x);r['picks'][p]=x
     if len(r['picks'])==2:
      scores=[score([r['deck'][i] for i in r['picks'][q]]+r['public']) for q in r['players']];r['scores']=scores;r['winner']=0 if scores[0]>scores[1] else 1 if scores[1]>scores[0] else -1
      if r['winner']>=0:r['wins'][r['winner']]+=1
      phase='result'
    if op=='next' and phase=='result':
     if p not in r['ready']:r['ready'].append(p)
     if len(r['ready'])==2:r['round']+=1;deal(r);phase='prepare'
    out=dict(room=code,player=p,seat=r['players'].index(p),phase=phase,round=r['round'],wins=r['wins'],remaining=max(0,(r['start'] or now)+30-now),prepare=max(0,(r['start'] or now)-now),own=r.get('picks',{}).get(p),ready=p in r.get('ready',[]))
    if phase in ('memory','result'):out['deck']=r['deck']
    if phase in ('choose','result'):out['public']=r['public']
    if phase=='result':out.update(picks=[r['picks'][q] for q in r['players']],scores=r['scores'],winner=r['winner'])
   self.send_json(out)
  except Exception as e:self.send_json({'error':str(e) or '操作無效'},400)
 def send_json(self,d,status=200):
  b=json.dumps(d,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
if __name__=='__main__':
 os.chdir(os.path.dirname(os.path.abspath(__file__)));ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT',8000))),H).serve_forever()
