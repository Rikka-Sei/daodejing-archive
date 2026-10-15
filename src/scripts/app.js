(function(){
var root=document.documentElement,body=document.body;
function qsa(s,r){return [].slice.call((r||document).querySelectorAll(s))}
function $(id){return document.getElementById(id)}

/* 排版、影像、字号、外观：几组开关，记在 localStorage，各页共用 */
var DEF={layout:'h',plates:'on',theme:'auto',rsize:'m'};
function get(k){try{return localStorage.getItem('dg.'+k)||DEF[k]}catch(e){return DEF[k]}}
function put(k,v){try{localStorage.setItem('dg.'+k,v)}catch(e){}}
function apply(){
  Object.keys(DEF).forEach(function(k){root.dataset[k]=get(k)});
  qsa('.seg button').forEach(function(b){b.setAttribute('aria-pressed',get(b.dataset.k)===b.dataset.v)});
}
qsa('.seg button').forEach(function(b){b.onclick=function(){put(b.dataset.k,b.dataset.v);apply();qsa('.units').forEach(function(u){u.scrollLeft=0})}});
apply();

/* 侧栏：窄屏滑出；宽屏可收起，并记住 */
var narrow=window.matchMedia('(max-width:860px)');
function collapse(off){body.classList.toggle('nosb',off);put('side',off?'off':'on')}
if(get('side')==='off')body.classList.add('nosb');
$('menu').onclick=function(){if(narrow.matches)body.classList.toggle('open');else collapse(false)};
$('sbclose').onclick=function(){if(narrow.matches)body.classList.remove('open');else collapse(true)};
$('side').addEventListener('click',function(ev){if(narrow.matches&&ev.target.closest('a'))body.classList.remove('open')});

/* 侧栏的两条轴：材料｜章节。只换显示的那一栏，不跳转；打开页面时停在哪条轴由页面决定 */
var side=$('side');
function setAxis(a){
  side.dataset.axis=a;
  qsa('.axis button').forEach(function(b){b.setAttribute('aria-pressed',b.dataset.axis===a)});
  sideSearch();
}
qsa('.axis button').forEach(function(b){b.onclick=function(){setAxis(b.dataset.axis)}});
(function(){
  var on=side.querySelector('.pane[data-pane=c] .item.on');
  if(on&&side.dataset.axis==='c')side.scrollTop=Math.max(0,on.offsetTop-side.clientHeight/2);
})();

/* 目录里的文件夹：展开或收起记在 localStorage，各页共用；当前所在的文件夹总是展开 */
var dirs=qsa('details.dir'),shut=[];
try{shut=JSON.parse(localStorage.getItem('dg.shut')||'[]')}catch(e){}
dirs.forEach(function(d){
  if(shut.indexOf(d.dataset.g)>=0&&!d.querySelector('.item.on'))d.open=false;
  d.addEventListener('toggle',function(){
    shut=shut.filter(function(g){return g!==d.dataset.g});
    if(!d.open)shut.push(d.dataset.g);
    put('shut',JSON.stringify(shut));
  });
});

/* 目录行右侧的“⋯”：整页只有一个浮层 #pop，内容取自该行里隐藏的 .menu-src */
var pop=$('pop'),popFor=null;
function closePop(){
  if(!popFor)return;
  pop.hidden=true;pop.innerHTML='';
  popFor.setAttribute('aria-expanded','false');popFor.closest('.item').classList.remove('mo');popFor=null;
}
function openPop(btn){
  var row=btn.closest('.item');
  closePop();popFor=btn;
  pop.innerHTML=row.querySelector('.menu-src').innerHTML;pop.hidden=false;
  btn.setAttribute('aria-expanded','true');row.classList.add('mo');
  var r=btn.getBoundingClientRect(),w=pop.offsetWidth,h=pop.offsetHeight;
  var top=r.bottom+4;if(top+h>window.innerHeight-8)top=Math.max(8,r.top-h-4);
  pop.style.left=Math.max(8,Math.min(r.right-w,window.innerWidth-w-8))+'px';pop.style.top=top+'px';
  var first=pop.querySelector('a');if(first)first.focus({preventScroll:true});
}
document.addEventListener('click',function(ev){
  var b=ev.target.closest&&ev.target.closest('.more');
  if(b){ev.preventDefault();ev.stopPropagation();if(popFor===b)closePop();else openPop(b);return}
  if(popFor)setTimeout(closePop,0);
});
document.addEventListener('keydown',function(ev){
  if(!popFor)return;
  if(ev.key==='Escape'){var b=popFor;closePop();b.focus();return}
  if(ev.key==='ArrowDown'||ev.key==='ArrowUp'){
    var a=qsa('#pop a'),i=a.indexOf(document.activeElement);
    a[(i+(ev.key==='ArrowDown'?1:-1)+a.length)%a.length].focus();ev.preventDefault();
  }
});
window.addEventListener('scroll',closePop,true);window.addEventListener('resize',closePop);

/* 顶栏：滚动后出现细分隔线 */
var bar=document.querySelector('.top');
function scrolled(){bar.classList.toggle('scrolled',window.scrollY>2)}
window.addEventListener('scroll',scrolled,{passive:true});scrolled();

/* 检索：本页有释文就过滤释文并高亮；否则过滤侧栏当前这一栏的目录 */
var q=$('q'),hits=$('hits'),units=qsa('.u');
function unmark(el){qsa('mark',el).forEach(function(m){var p=m.parentNode;p.replaceChild(document.createTextNode(m.textContent),m);p.normalize()})}
function mark(el,s){
  var w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),nodes=[],n;
  while(n=w.nextNode())nodes.push(n);
  nodes.forEach(function(t){
    var i=t.data.indexOf(s);if(i<0)return;
    var r=document.createRange();r.setStart(t,i);r.setEnd(t,i+s.length);
    var m=document.createElement('mark');r.surroundContents(m);
    var rest=m.nextSibling;if(rest&&rest.nodeType===3&&rest.data.indexOf(s)>=0)mark(rest.parentNode,s);
  });
}
function unitSearch(){
  var s=q.value.trim(),shown=0;
  units.forEach(function(u){
    var p=u.querySelector('p');unmark(p);
    var ok=!s||p.textContent.indexOf(s)>=0;
    if(s&&ok){shown++;mark(p,s)}
    u.hidden=!ok;
  });
  hits.textContent=s?'本页命中 '+shown+' 条':'';
}
function sideSearch(){
  if(!q||units.length)return;
  var s=q.value.trim(),pane=side.querySelector('.pane[data-pane='+side.dataset.axis+']');
  if(!pane)return;
  function name(it){var t=it.querySelector('.t');return t?t.textContent:''}
  function hit(it){
    if(!s)return true;
    if(it.dataset.n)return it.dataset.n===s||(it.dataset.t||'').indexOf(s)>=0;
    return name(it).indexOf(s)>=0;
  }
  function shown(it){return !it.hidden&&!it.closest('[hidden]')}
  qsa('details.dir',pane).forEach(function(d){
    var own=!!s&&name(d.querySelector('summary')).indexOf(s)>=0,any=false;
    qsa('.item',d.querySelector('.kids')).forEach(function(it){var ok=own||hit(it);it.hidden=!ok;if(ok)any=true});
    d.hidden=!(own||any);
    if(s&&!d.hidden)d.open=true;
  });
  qsa('.item:not(summary)',pane).forEach(function(it){if(!it.closest('details.dir'))it.hidden=!hit(it)});
  qsa('.sb-label',pane).forEach(function(l){
    var t=l.nextElementSibling;
    while(t&&!t.classList.contains('tree'))t=t.nextElementSibling;
    var on=!s||!t||qsa('.item:not(summary)',t).some(shown);
    l.hidden=!on;
  });
  var n=qsa('.item:not(summary)',pane).filter(shown).length;
  hits.textContent=s?(n?'找到 '+n+' 项':'没有找到'):'';
}
if(q){q.addEventListener('input',function(){if(units.length)unitSearch();else sideSearch()})}

/* 竖排时滚轮向下 = 往左翻（阅读器永远是竖排；释文页要选了竖排才是） */
document.addEventListener('wheel',function(ev){
  if(ev.ctrlKey||Math.abs(ev.deltaX)>=Math.abs(ev.deltaY)||!ev.target.closest)return;
  var u=ev.target.closest('.rd')||(root.dataset.layout==='v'?ev.target.closest('.units'):null);
  if(!u)return;
  u.scrollLeft-=ev.deltaY;ev.preventDefault();
},{passive:false});
})();
