(function(){
/* 章节对读页：指到一个字，高亮这一列；点一下把这一列钉住（再点取消），地址里的 #c<列> 也会钉住并滚到那里 */
var tds=[].slice.call(document.querySelectorAll('table.al td[data-col]'));
if(!tds.length)return;
var pinned=null;
function cols(i){return tds.filter(function(td){return td.dataset.col===String(i)})}
function mark(i,cls,on){if(i===null)return;cols(i).forEach(function(td){td.classList.toggle(cls,on)})}
function pin(i,scroll){
  mark(pinned,'pin',false);
  pinned=i===pinned?null:i;
  mark(pinned,'pin',true);
  try{history.replaceState(null,'',pinned===null?location.pathname+location.search:'#c'+pinned)}catch(e){}
  if(scroll&&pinned!==null){var a=document.getElementById('c'+pinned);if(a)a.scrollIntoView({block:'center'})}
}
var over=null;
document.addEventListener('mouseover',function(ev){
  var td=ev.target.closest&&ev.target.closest('table.al td[data-col]');
  var i=td?td.dataset.col:null;
  if(i===over)return;
  mark(over,'hl',false);over=i;mark(over,'hl',true);
});
document.addEventListener('click',function(ev){
  var td=ev.target.closest&&ev.target.closest('table.al td[data-col]');
  if(td)pin(td.dataset.col,false);
});
var m=/^#c(\d+)$/.exec(location.hash);
if(m)pin(m[1],true);
})();
