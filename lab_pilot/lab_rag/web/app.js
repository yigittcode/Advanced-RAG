const $ = id => document.getElementById(id);
let report;
function node(tag, text, cls) { const el=document.createElement(tag); el.textContent=text; if(cls)el.className=cls; return el; }
async function request(path, body) {
  const response=await fetch(path, body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {});
  const data=await response.json(); if(!response.ok)throw new Error(data.error||'İstek başarısız'); return data;
}
async function busy(task) {
  $('error').hidden=true; $('search').disabled=true; $('evaluate').disabled=true;
  try { await task(); } catch(e) { $('error').textContent=e.message; $('error').hidden=false; }
  finally { $('search').disabled=false; $('evaluate').disabled=false; }
}
const options=()=>({method:$('method').value,k:Number($('k').value)});
document.querySelectorAll('[data-q]').forEach(button=>button.addEventListener('click',()=>{$('question').value=button.dataset.q;$('question').focus();}));
$('query-form').addEventListener('submit',event=>{event.preventDefault();busy(async()=>{
  const data=await request('/api/search',{...options(),question:$('question').value});
  $('result').hidden=false;
  $('result-title').textContent=(data.mode==='evidence'?'Getirilen kaynak parçaları':'Model cevabı ve kaynakları')+' · '+data.method;
  $('latency').textContent=Object.values(data.timing_ms).reduce((a,b)=>a+b,0).toFixed(1)+' ms · '+data.llm_calls+' model çağrısı';
  $('answer').textContent=data.status==='evidence_only'?'':data.answer;
  $('warning').textContent=data.warnings.join(' '); $('warning').hidden=!data.warnings.length;
  $('sources').replaceChildren();
  for(const hit of data.sources){
    const article=node('article','', 'source'), head=node('div','', 'source-head');
    head.append(node('span','['+hit.citation+'] '+hit.title,'source-tag'),node('span','Skor '+hit.score));
    article.append(head,node('p',hit.context_text),node('small',hit.source+' · satır '+hit.start_line+'–'+hit.end_line+' · '+hit.chunk_id));
    $('sources').append(article);
  }
  $('trace').textContent=JSON.stringify(data,null,2);
});});
$('evaluate').addEventListener('click',()=>busy(async()=>{
  report=await request('/api/evaluate',{...options(),split:$('split').value});
  const method=Object.keys(report.results)[0], summary=report.results[method].summary, k=report.config.k;
  $('evaluation').replaceChildren(node('p',method+' · '+report.config.split+' · k='+k,'subtext')); const grid=node('div','','metrics');
  for(const [label,value] of [['Recall@'+k,summary['recall@'+k]],['MRR@'+k,summary['mrr@'+k]],['nDCG@'+k,summary['ndcg@'+k]]]){
    const card=node('div','','metric');card.append(node('strong',Number(value).toFixed(3)),node('span',label));grid.append(card);
  }
  $('evaluation').append(grid,node('p',summary.answerable_count+' cevaplanabilir / '+summary.unanswerable_count+' cevapsız soru. Cevapsız sorularda aday getirme oranı: '+(summary.negative_candidate_rate===null?'—':(summary.negative_candidate_rate*100).toFixed(0)+'%')+'. Bu oran cevap uydurma oranı değildir.','notice'));
  $('evaluation').append(node('p','p50 '+summary.latency_p50_ms+' ms · p95 '+summary.latency_p95_ms+' ms · '+summary.llm_calls+' model çağrısı. Sentetik küçük set; production başarısı değildir.','subtext'));
  const details=node('details','');details.append(node('summary','Soru bazında sonuçları incele'),node('pre',JSON.stringify(report.results[method].queries,null,2)));$('evaluation').append(details);
  $('download').hidden=false;
}));
$('download').addEventListener('click',()=>{if(!report)return; const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='rag-evaluation.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
busy(async()=>{const status=await request('/api/status');$('mode').textContent=status.mode==='llm'?'LLM bağlı · '+status.llm_model:'Yerel · Kaynak gösterimi';$('stats').textContent=status.documents+' belge / '+status.chunks+' parça · Corpus '+status.corpus_sha256.slice(0,10);for(const method of status.methods.filter(x=>!['bm25','lexical'].includes(x))){const option=node('option',method==='dense'?'Dense · gerçek embedding':'Hybrid · BM25 + dense');option.value=method;$('method').append(option);}});
