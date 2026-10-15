(function(){
/* 阅读器：点一个字或拖选几个字，弹出“透视”——其他本在同一处写的什么。
   每个字带 data-k="章.列"；各章的对读表和公共部分（共用通行字规则、造字码位）第一次用到时才读取。
   比较与共用通行字的规则同 src/lib/alignment.ts，两处要一起改。 */
var rd=document.getElementById('rd'),lens=document.getElementById('lens');
if(!rd||!lens)return;
var body=document.body;
var CHAPTERS=rd.dataset.chapters,META=rd.dataset.meta,ME=rd.dataset.w;
var narrow=window.matchMedia('(max-width:640px)');
var MARKS=Array.from('∟＝●■◍▁◯□〼▩▦🅰🅱🅲🅳🅴');
var FLAG={'残':'残字','衍':'衍文','脱':'脱文','补':'补文','占':'占位'};
var meta=null,cache={},seq=0,picked=[];
function qsa(s,r){return [].slice.call((r||document).querySelectorAll(s))}
function uniq(a){return a.filter(function(x,i){return a.indexOf(x)===i})}
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#x27;'}[c]})}

/* 读取 */
function getJSON(u){return fetch(u).then(function(r){if(!r.ok)throw new Error(u+' '+r.status);return r.json()})}
function loadMeta(){
  if(meta)return Promise.resolve(meta);
  return getJSON(META).then(function(m){
    m.names={};m.versions.forEach(function(v){m.names[v.id]=v.short});
    return (meta=m);
  });
}
function cellOf(x){return typeof x==='string'?{t:x}:Object.assign({t:''},x)}
function kind(c){
  if(c.f==='脱')return 'tuo';
  if(c.f==='占')return 'zhan';
  if(!c.t)return 'blank';
  if(c.t==='□'||c.t==='〼')return 'miss';
  return MARKS.indexOf(c.t)>=0?'mark':'text';
}
/* 同一版本的几行（郭店六十四章分段）并成一行 */
function merge(c){
  var by={},order=[];
  c.rows.forEach(function(r){
    var cs=r.cells.map(cellOf);
    if(!by[r.version]){by[r.version]=cs;order.push(r.version)}
    else cs.forEach(function(x,i){if(kind(by[r.version][i])==='blank'&&kind(x)!=='blank')by[r.version][i]=x});
  });
  return {n:c.chapter,by:by,order:order};
}
function loadChapter(n){
  if(cache[n])return Promise.resolve(cache[n]);
  return getJSON(CHAPTERS+('00'+n).slice(-3)+'.json').then(function(c){return (cache[n]=merge(c))});
}

/* 字与比较 */
function toks(s){
  var cs=Array.from(s),out=[],i=0;
  while(i<cs.length){
    if(cs[i]!=='〚'){out.push(cs[i++]);continue}
    var d=0,j=i;
    for(;j<cs.length;j++){if(cs[j]==='〚')d++;else if(cs[j]==='〛')d--;if(d===0)break}
    out.push(cs.slice(i,j+1).join(''));i=j+1;
  }
  return out;
}
function glyph(t){
  var m=/^〚F([\s\S]+)〛$/.exec(t);
  if(m)return glyph(m[1]);
  var cp=t.charAt(0)==='〚'?meta.glyphs[t]:0;
  return cp?String.fromCodePoint(cp):t;
}
function show(s){return toks(s).map(glyph).join('')}
function key(c){return c.r?'（'+c.r+'）':c.c?'〈'+c.c+'〉':c.t}
function unwrap(k){return /^[（〈]/.test(k)?k.slice(1,-1):k}
function headOf(k){var g=meta.equivalents.same;for(var i=0;i<g.length;i++)if(g[i].indexOf(k)>=0)return g[i][0];return k}
function shared(keys){
  var eq=meta.equivalents;
  if(keys.some(function(k){return eq.fail.indexOf(k)>=0}))return null;
  var solid=keys.map(function(k){return eq.blank.indexOf(k)>=0?'':k}).filter(Boolean);
  if(solid.length<=1)return null;
  var distinct=uniq(solid),plain=distinct.filter(function(k){return !/^[（〈]/.test(k)});
  if(!plain.length)return null;
  if(uniq(distinct.map(function(k){return headOf(unwrap(k))})).length!==1)return null;
  var group=[];
  eq.same.forEach(function(g){if(g.indexOf(plain[0])>=0)group=group.concat(g)});
  var reading=group.length?plain.slice().sort(function(a,b){return group.indexOf(a)-group.indexOf(b)})[0]:plain[0];
  return {reading:reading,also:uniq(distinct.map(unwrap)).filter(function(k){return k!==reading})};
}
function diff(c,b){
  if(kind(c)!=='text'||c.t===b.t)return '';
  if(kind(b)!=='text')return 'diff';
  return headOf(unwrap(key(c)))===headOf(unwrap(key(b)))?'var':'diff';
}

/* 透视的内容：cols 是选中的那几列（升序） */
function charHtml(c,d){
  var k=kind(c);
  if(k==='text')return '<span class="g'+(c.f==='残'?' d-part':'')+(d?' '+d:'')+'">'+esc(show(c.t))+'</span>';
  if(k==='mark')return '<span class="g mk">'+esc(c.t)+'</span>';
  if(k==='miss')return '<span class="g d-missing">□</span>';
  return '<span class="g nil">·</span>';
}
function noteOf(c){
  var k=kind(c),s=[];
  if(k==='text'||k==='mark'){
    if(c.r)s.push('通行字 '+esc(show(c.r)));
    if(c.c)s.push('正确字 '+esc(show(c.c)));
    if(c.f&&FLAG[c.f])s.push(FLAG[c.f]);
    if(k==='mark')s.push('符号');
  }else if(k==='miss')s.push('缺字');
  else if(k==='tuo'||k==='zhan')s.push(FLAG[c.f]);
  else s.push('无字');
  return s.join(' · ');
}
function render(ch,cols,extra){
  var one=cols.length===1,base=ch.by[ch.order[0]],h=[];
  h.push('<h4>透视 · 第 '+ch.n+' 章 · 同处各本</h4>');
  ch.order.forEach(function(v){
    var cs=cols.map(function(i){return ch.by[v][i]||{t:''}});
    var me=v===ME?' me':'';
    h.push('<div class="lr'+me+'"><b>'+esc(meta.names[v]||v)+'</b>');
    if(one){h.push(charHtml(cs[0],v===ch.order[0]?'':diff(cs[0],base[cols[0]]||{t:''}))+'<small>'+noteOf(cs[0])+'</small>')}
    else h.push('<span class="gs">'+cs.map(function(c,k){return charHtml(c,v===ch.order[0]?'':diff(c,base[cols[k]]||{t:''}))}).join('')+'</span>');
    h.push('</div>');
  });
  var foot=[];
  if(one){
    var keys=ch.order.map(function(v){return key((ch.by[v][cols[0]])||{t:''})}),s=shared(keys);
    if(s)foot.push('共用通行字：<b class="g">'+esc(show(s.reading))+'</b>'+(s.also.length?'（'+s.also.map(function(x){return esc(show(x))}).join('、')+'同）':''));
    else if(!keys.some(function(k){return meta.equivalents.fail.indexOf(k)>=0})&&keys.filter(function(k){return k&&meta.equivalents.blank.indexOf(k)<0}).length>1)foot.push('各本用字有差异');
  }
  if(extra>0)foot.push('另有 '+extra+' 个字在别的章，这里只列了第 '+ch.n+' 章的');
  foot.push('<a href="'+esc(CHAPTERS+ch.n+'/#c'+cols[0])+'">在对读表里看 ›</a>');
  h.push('<div class="ft">'+foot.join('<br>')+'</div>');
  return h.join('');
}

/* 选中与弹出 */
function clearPicked(){picked.forEach(function(s){s.classList.remove('sel')});picked=[]}
function rectOf(spans){
  var l=1e9,t=1e9,r=-1e9,b=-1e9;
  spans.forEach(function(s){var q=s.getBoundingClientRect();l=Math.min(l,q.left);t=Math.min(t,q.top);r=Math.max(r,q.right);b=Math.max(b,q.bottom)});
  return {left:l,top:t,right:r,bottom:b};
}
function place(r){
  lens.hidden=false;
  if(narrow.matches){lens.style.left=lens.style.top='';return}
  var w=lens.offsetWidth,h=lens.offsetHeight,vw=window.innerWidth,vh=window.innerHeight;
  var x=r.left-w-12;if(x<8)x=Math.min(r.right+12,vw-w-8);
  var y=Math.max(8,Math.min(r.top-6,vh-h-8));
  lens.style.left=x+'px';lens.style.top=y+'px';
}
function close(){seq++;lens.hidden=true;clearPicked()}
function open(spans){
  var my=++seq;
  var n=+spans[0].dataset.k.split('.')[0];
  var same=spans.filter(function(s){return +s.dataset.k.split('.')[0]===n});
  var cols=uniq(same.map(function(s){return +s.dataset.k.split('.')[1]})).sort(function(a,b){return a-b});
  if(cols.length>40){lens.innerHTML='<h4>透视</h4><div class="ft">选得太多了，先选几个字试试。</div>';place(rectOf(spans));return}
  Promise.all([loadMeta(),loadChapter(n)]).then(function(r){
    if(my!==seq)return;
    clearPicked();same.forEach(function(s){s.classList.add('sel')});picked=same;
    lens.innerHTML=render(r[1],cols,spans.length-same.length);
    place(rectOf(same));
  }).catch(function(){
    if(my!==seq)return;
    lens.innerHTML='<h4>透视</h4><div class="ft">读不到这一章的对读表，稍后再试。</div>';place(rectOf(spans));
  });
}
rd.addEventListener('pointerup',function(ev){
  var t=ev.target;
  if(!t.closest||t.closest('a,button'))return;
  setTimeout(function(){
    var sel=window.getSelection(),spans=null;
    if(sel&&!sel.isCollapsed&&sel.rangeCount){
      var r=sel.getRangeAt(0);
      spans=qsa('.c[data-k]',rd).filter(function(s){return r.intersectsNode(s)});
    }
    if(!spans||!spans.length){
      var one=t.closest('.c[data-k]');
      if(!one){close();return}
      spans=[one];
    }
    open(spans);
  },0);
});
document.addEventListener('pointerdown',function(ev){if(!lens.hidden&&!lens.contains(ev.target))close()});
rd.addEventListener('scroll',function(){if(!lens.hidden)close()},{passive:true});

/* 专注模式：只留文字；键盘 ← → 翻一屏，F 进出专注，Esc 先关透视再退出专注 */
function focus(on){body.classList.toggle('focus',on===undefined?!body.classList.contains('focus'):on);close()}
var fb=document.getElementById('focus'),ub=document.getElementById('unfocus');
if(fb)fb.onclick=function(){focus()};
if(ub)ub.onclick=function(){focus(false)};
document.addEventListener('keydown',function(ev){
  if(ev.target.closest&&ev.target.closest('input,select,textarea'))return;
  if(ev.key==='Escape'){if(!lens.hidden)close();else if(body.classList.contains('focus'))focus(false);return}
  if(ev.metaKey||ev.ctrlKey||ev.altKey)return;
  if(ev.key==='f'||ev.key==='F'){focus();return}
  var step=Math.max(160,rd.clientWidth*.6);
  if(ev.key==='ArrowLeft'){rd.scrollBy({left:-step,behavior:'smooth'});ev.preventDefault()}
  else if(ev.key==='ArrowRight'){rd.scrollBy({left:step,behavior:'smooth'});ev.preventDefault()}
});
})();
