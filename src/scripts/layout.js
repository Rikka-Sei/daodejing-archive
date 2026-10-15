(function(){
/* 透视页（简牍排布）：选一章，各本里写了这一章的简与行亮起来，其余变淡；地址里的 #ch<章> 同样生效 */
var input=document.getElementById('lv-n'),say=document.getElementById('lv-say'),clear=document.getElementById('lv-clear');
if(!input)return;
var tiles=[].slice.call(document.querySelectorAll('.sl')),total=+input.max||81;
function apply(n){
  var on=n>=1&&n<=total;
  document.body.classList.toggle('lv-pick',on);
  clear.hidden=!on;
  var parts=[];
  tiles.forEach(function(t){t.classList.toggle('hit',on&&t.dataset.ch.split(' ').indexOf(String(n))>=0)});
  if(on){
    [].slice.call(document.querySelectorAll('section.lv')).forEach(function(s){
      var hits=[].slice.call(s.querySelectorAll('.sl.hit')).map(function(t){return t.dataset.no});
      if(hits.length)parts.push(s.dataset.name+' '+s.dataset.unit+' '+hits.join('、'));
    });
    say.textContent=parts.length?'第 '+n+' 章：'+parts.join('；'):'第 '+n+' 章在这些本里都没有简或行';
  }else say.textContent='';
  try{history.replaceState(null,'',on?'#ch'+n:location.pathname+location.search)}catch(e){}
}
function read(){var v=parseInt(input.value,10);apply(isNaN(v)?0:v)}
input.addEventListener('input',read);
clear.addEventListener('click',function(){input.value='';apply(0);input.focus()});
var m=/^#ch(\d+)$/.exec(location.hash);
if(m){input.value=m[1];read()}
})();
