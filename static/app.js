(function(){var b=document.getElementById('cb'),$=function(i){return document.getElementById(i)};
function off(){if(window.GA_ID)window['ga-disable-'+window.GA_ID]=true}
try{if(localStorage.getItem('consent'))b.hidden=true}catch(x){}
[].forEach.call(document.querySelectorAll('[data-c]'),function(x){x.onclick=function(){try{localStorage.setItem('consent',x.dataset.c)}catch(y){}b.hidden=true;if(x.dataset.c==='no')off()}});
var el=$('dt'),f=$('f');if(!el||!f)return;var D=JSON.parse(el.textContent);
var usd=function(n){return '$'+Math.round(n).toLocaleString('en-US')},v=function(i){return Math.max(0,+$(i).value||0)};
function tax(b,inc){var t=0;for(var i=0;i<b.length;i++){var hi=i+1<b.length?b[i+1][0]:Infinity;if(inc>b[i][0])t+=(Math.min(inc,hi)-b[i][0])*b[i][1]/100}return t}
function run(){var h;if(D.t==='p'){var s=v('s'),fed=tax(D.fed,Math.max(0,s-D.std)),fi=Math.min(s,D.ssb)*.062+s*.0145,st=D.tt==='flat'?s*D.rate/100:D.tt==='brackets'?tax(D.br,s):0,n=s-fed-fi-st;
h='Take-home: <b>'+usd(n)+'</b>/yr &middot; '+usd(n/12)+'/mo &middot; '+usd(n/26)+' biweekly<br>Federal '+usd(fed)+' &middot; FICA '+usd(fi)+' &middot; State '+usd(st)}
else{var P=v('p'),L=P*(1-Math.min(v('d'),100)/100),m=v('r')/1200,k=v('y')*12||1,pi=m?L*m/(1-Math.pow(1+m,-k)):L/k,tx=P*D.prop/1200,ins=v('i')/12;
h='Monthly payment: <b>'+usd(pi+tx+ins)+'</b><br>Principal &amp; interest '+usd(pi)+' &middot; Property tax '+usd(tx)+' &middot; Insurance '+usd(ins)}
$('o').innerHTML=h}
f.addEventListener('input',run);run()})();
