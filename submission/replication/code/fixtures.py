"""Local test fixtures: a todo app with UI mutations, and a checkout flow with iframe / shadow-DOM / canvas conditions.
Run twice on different ports to get a cross-origin iframe:  python fixtures.py 8801 & python fixtures.py 8802"""
import sys
from aiohttp import web

TODO = r"""<!doctype html><html><head><meta charset=utf-8><title>Tasks</title>
<style>body{font:15px system-ui;max-width:520px;margin:30px auto}li{display:flex;gap:8px;align-items:center;padding:4px 0}
button{padding:4px 10px}.row{display:flex;gap:6px}.row input[type=text]{flex:1;padding:6px}</style></head><body><div id=app></div>
<script>
const V=new URLSearchParams(location.search).get('v')||'A';
const T={A:{ph:'What needs to be done?',add:'Add',del:'Delete',all:'All',act:'Active',done:'Completed',clear:'Clear completed',left:n=>n+' items left'},
 C:{ph:'New chore…',add:'Create task',del:'Remove',all:'Everything',act:'Pending',done:'Done',clear:'Archive finished',left:n=>n+' to go'}};
T.B=T.A; T.D={...T.A,add:'✚',del:'🗑',clear:'⌫'}; T.E={...T.A,add:'✚',del:'🗑',clear:'⌫',all:'●',act:'○',done:'✔'};
const L=T[V]; const aria=V==='D'?{add:'Add task',del:'Delete task',clear:'Clear completed tasks'}:{};
const cls=(n)=>V==='B'?'x'+[...n].reduce((a,c)=>(a*31+c.charCodeAt(0))%9973,7).toString(36):n;
let S={todos:[{text:'Buy milk',done:false},{text:'Walk dog',done:false},{text:'Write report',done:false}],filter:'all'};
let inputVal='';
window.__state=()=>({todos:S.todos.map(t=>({text:t.text,done:t.done})),filter:S.filter,input:document.querySelector('[data-gt=input]').value});
window.__reset=(s,inp)=>{S=JSON.parse(JSON.stringify(s));render(inp||'');};
function el(tag,props={},kids=[]){const e=document.createElement(tag);for(const[k,v]of Object.entries(props)){if(k==='class')e.className=cls(v);else if(k==='id')e.id=V==='B'?cls(v):v;else if(k==='aria'&&v)e.setAttribute('aria-label',v);else if(k.startsWith('on'))e.addEventListener(k.slice(2),v);else e.setAttribute(k,v)}
 kids.forEach(k=>e.append(k));return e}
function render(inp=document.querySelector('[data-gt=input]')?.value||''){
 const app=document.getElementById('app');app.replaceChildren();
 const input=el('input',{type:'text',id:'new-todo',class:'new-todo',placeholder:L.ph,'data-gt':'input'});input.value=inp;
 const add=el('button',{class:'add-btn',aria:aria.add,'data-gt':'add',onclick:()=>{const v=input.value.trim();if(v){S.todos.push({text:v,done:false});render('')}}},[L.add]);
 const vis=S.todos.filter(t=>S.filter==='all'||(S.filter==='active'?!t.done:t.done));
 const ul=el('ul',{class:'todo-list'});
 vis.forEach(t=>{const cb=el('input',{type:'checkbox',class:'toggle','data-gt':'toggle:'+t.text,onchange:()=>{t.done=!t.done;render(input.value)}});cb.checked=t.done;
  ul.append(el('li',{},[cb,el('span',{class:'label'},[t.text]),el('button',{class:'destroy',aria:aria.del,'data-gt':'del:'+t.text,onclick:()=>{S.todos=S.todos.filter(x=>x!==t);render(input.value)}},[L.del])]))});
 const F=(k,txt,gt)=>el('button',{class:'filter-'+k,'data-filter':k,'data-gt':gt,onclick:()=>{S.filter=k;render(input.value)}},[txt]);
 const filters=el('div',{class:'filters row'},[F('all',L.all,'f:all'),F('active',L.act,'f:active'),F('completed',L.done,'f:done')]);
 const clear=el('button',{class:'clear-completed',aria:aria.clear,'data-gt':'clear',onclick:()=>{S.todos=S.todos.filter(t=>!t.done);render(input.value)}},[L.clear]);
 const count=el('div',{class:'count'},[L.left(S.todos.filter(t=>!t.done).length)]);
 const parts=[el('h1',{},['Tasks']),el('div',{class:'row'},[input,add]),ul,count,filters,clear];
 if(V==='B')parts.splice(2,0,parts.pop()),parts.splice(3,0,parts.pop());   // shuffle control order in B
 parts.forEach(p=>app.append(p));}
render();
</script></body></html>"""

SHOP = r"""<!doctype html><html><head><meta charset=utf-8><title>Mug Shop</title>
<style>body{font:15px system-ui;max-width:640px;margin:24px auto}.card{border:1px solid #ccc;padding:10px;margin:8px 0;display:flex;justify-content:space-between}
iframe{width:100%;height:330px;border:1px solid #aaa}</style></head><body>
<h1>Mug Shop</h1>
<div id=products>
 <div class=card data-card><span>Red mug - $9</span><button data-gt="add-red">Add to cart</button></div>
 <div class=card data-card><span>Blue mug - $11</span><button data-gt="add-blue">Add to cart</button></div>
 <div class=card data-card><span>Green mug - $10</span><button data-gt="add-green">Add to cart</button></div>
</div>
<p id=cartinfo>Cart: empty</p><button id=co data-gt="checkout" disabled>Go to checkout</button>
<div id=checkout hidden><h2>Checkout</h2><div id=slot></div></div>
<p id=status></p>
<script>
const Q=new URLSearchParams(location.search), FR=Q.get('frame')||'none', M=Q.get('m')||'plain';
const other=location.port==='8801'?'8802':'8801';
let st={cart:[],stage:'shop',fields:{},order:null};
window.__shop=()=>JSON.parse(JSON.stringify(st));
document.querySelectorAll('[data-gt^=add-]').forEach(b=>b.onclick=()=>{st.cart.push(b.parentElement.firstElementChild.textContent.split(' -')[0]);
 document.getElementById('cartinfo').textContent='Cart: '+st.cart.join(', ');document.getElementById('co').disabled=false});
document.getElementById('co').onclick=()=>{st.stage='checkout';document.getElementById('checkout').hidden=false;
 const slot=document.getElementById('slot');
 if(FR==='none'){fetch('/pay?m='+M+'&inline=1').then(r=>r.text()).then(h=>{const d=document.createElement('div');d.innerHTML=h;slot.append(d);d.querySelectorAll('script').forEach(s=>{const n=document.createElement('script');n.textContent=s.textContent;document.body.append(n)})})}
 else{const f=document.createElement('iframe');f.title='Secure payment';
  f.src=FR==='same'?'/pay?m='+M:FR==='cross'?'http://localhost:'+other+'/pay?m='+M:'http://localhost:'+other+'/relay?m='+M;slot.append(f)}};
addEventListener('message',e=>{const d=e.data||{};if(d.type==='field')st.fields[d.name]=d.value;
 if(d.type==='paid'){st.order=d.order;st.stage='done';document.getElementById('status').textContent='Order confirmed for '+d.order.holder}});
</script></body></html>"""

RELAY = r"""<!doctype html><html><body><p>Secure payment provider</p><iframe style="width:100%;height:300px" src="http://localhost:%OTHER%/pay?m=%M%"></iframe>
<script>addEventListener('message',e=>parent.postMessage(e.data,'*'))</script></body></html>"""

def pay_html(m, inline):
    fields = """<label>Cardholder name <input data-gt="holder" name="holder" id=h></label><br>
<label>Card number <input data-gt="cardno" name="cardno" id=c></label><br>
<label>Country <select data-gt="country" name="country" id=k><option>France</option><option>Germany</option><option>Spain</option></select></label><br>"""
    paybtn = '<button data-gt="pay" id=pay>Pay now</button>'
    if m == "canvas":
        paybtn = '<canvas id=cv width=120 height=36 data-gt="pay" style="border:1px solid #333;cursor:pointer"></canvas>'
    body = fields + paybtn
    wire = """const post=(o)=>(inline?window:parent).postMessage(o,'*');
const q=(s)=>R.querySelector(s);
for(const n of ['h','c','k']){const e=R.querySelector('#'+n);e.addEventListener('input',()=>post({type:'field',name:e.name,value:e.value}));e.addEventListener('change',()=>post({type:'field',name:e.name,value:e.value}))}
const doPay=()=>post({type:'paid',order:{holder:q('#h').value,cardno:q('#c').value,country:q('#k').value}});
const b=R.querySelector('#pay'); if(b)b.addEventListener('click',doPay);
const cv=R.querySelector('#cv'); if(cv){const g=cv.getContext('2d');g.font='16px sans-serif';g.fillText('Pay now',20,24);cv.addEventListener('click',doPay)}"""
    if m in ("shadow-open", "shadow-closed"):
        mode = "open" if m == "shadow-open" else "closed"
        return f"""<pay-card></pay-card><script>
const inline={'true' if inline else 'false'};
class P extends HTMLElement{{constructor(){{super();const R=this.attachShadow({{mode:'{mode}'}});R.innerHTML=`{body}`;{wire}}}}}
customElements.define('pay-card',P);</script>"""
    return f"""<div id=root>{body}</div><script>const inline={'true' if inline else 'false'};const R=document.getElementById('root');{wire}</script>"""


async def todo(r): return web.Response(text=TODO, content_type="text/html")
async def shop(r): return web.Response(text=SHOP, content_type="text/html")
async def relay(r):
    other = "8801" if r.url.port == 8802 else "8802"   # nested: relay on one origin, pay form on the other
    return web.Response(text=RELAY.replace("%OTHER%", other).replace("%M%", r.query.get("m", "plain")), content_type="text/html")
async def pay(r):
    m, inline = r.query.get("m", "plain"), r.query.get("inline") == "1"
    html = pay_html(m, inline)
    if not inline:
        html = f"<!doctype html><html><head><meta charset=utf-8><title>Pay</title></head><body style='font:15px system-ui'>{html}</body></html>"
    return web.Response(text=html, content_type="text/html")

def make():
    a = web.Application()
    a.add_routes([web.get("/todo", todo), web.get("/shop", shop), web.get("/relay", relay), web.get("/pay", pay)])
    return a

if __name__ == "__main__":
    web.run_app(make(), host="127.0.0.1", port=int(sys.argv[1]), print=None)
