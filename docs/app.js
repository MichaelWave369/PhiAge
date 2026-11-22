/* ΦAge static research dashboard. No external dependencies or API calls. */
"use strict";
const SVG_NS = "http://www.w3.org/2000/svg";
const $ = id => document.getElementById(id);
const clamp = n => Math.max(0, Math.min(1, n));
let lastRun = null;

function toyModel(steps, generation, repair, boost) {
  let damage = 0.18, inflammation = 0.08, senescence = 0.04, capacity = 0.85;
  const series = [];
  for (let t = 0; t <= steps; t++) {
    series.push({step:t, damage, inflammation, senescence, repair_capacity:capacity});
    const d=damage, i=inflammation, s=senescence;
    damage=clamp(d+0.2*(generation*(1+0.5*i)-repair*capacity*(1+boost)));
    inflammation=clamp(i+0.013*d+0.006*s-0.012*i);
    senescence=clamp(s+0.012*d-0.006*s);
    capacity=clamp(capacity+0.003*(1-d)-0.008*d);
  }
  return {model:"phiage-toy-feedback/v0.1",parameters:{steps,generation,repair,boost},
    series,warning:"Toy equations; arbitrary dimensionless parameters, not calibrated to humans. No clinical or longevity prediction."};
}
function createSvg(tag, attrs) {
  const node=document.createElementNS(SVG_NS,tag);
  for(const key of Object.keys(attrs)) node.setAttribute(key,String(attrs[key]));
  return node;
}
function drawChart(series) {
  const svg=$("chart"); svg.replaceChildren();
  const left=48,right=614,top=18,bottom=270,w=right-left,h=bottom-top;
  for(let y=0;y<=4;y++){
    const v=y/4, yy=bottom-v*h;
    svg.append(createSvg("line",{x1:left,x2:right,y1:yy,y2:yy,stroke:"#304157","stroke-width":1}));
    const label=createSvg("text",{x:36,y:yy+4,fill:"#94a5ba","font-size":11,"text-anchor":"end"});
    label.textContent=v.toFixed(2); svg.append(label);
  }
  for(let t=0;t<=80;t+=20){
    const xx=left+w*t/80;
    const label=createSvg("text",{x:xx,y:295,fill:"#94a5ba","font-size":11,"text-anchor":"middle"});
    label.textContent=String(t);svg.append(label);
  }
  for(const [key,color] of [["damage","#ffbb84"],["inflammation","#91b7fc"],["repair_capacity","#72e4c4"]]){
    const points=series.map(d=>(left+w*d.step/80).toFixed(1)+","+(bottom-h*d[key]).toFixed(1)).join(" ");
    svg.append(createSvg("polyline",{points,fill:"none",stroke:color,"stroke-width":2.5,"stroke-linejoin":"round","stroke-linecap":"round"}));
  }
  const label=createSvg("text",{x:331,y:307,fill:"#94a5ba","font-size":10,"text-anchor":"middle"});
  label.textContent="SIMULATION STEPS (NOT YEARS)";svg.append(label);
}
function renderSim() {
  const generation=Number($("generation").value),repair=Number($("repair").value),boost=Number($("boost").value);
  $("generation-value").textContent=generation.toFixed(3);
  $("repair-value").textContent=repair.toFixed(3);
  $("boost-value").textContent=boost.toFixed(2);
  lastRun=toyModel(80,generation,repair,boost);
  drawChart(lastRun.series);
  const end=lastRun.series[lastRun.series.length-1];
  $("damage-final").textContent=end.damage.toFixed(3);
  $("inflammation-final").textContent=end.inflammation.toFixed(3);
  $("repair-final").textContent=end.repair_capacity.toFixed(3);
}
function setupSim(){
  for(const id of ["generation","repair","boost"]) $(id).addEventListener("input",renderSim);
  $("reset").addEventListener("click",()=>{
    $("generation").value="0.06";$("repair").value="0.04";$("boost").value="0";renderSim();
  });
  $("export").addEventListener("click",()=>{
    if(!lastRun)return;
    const blob=new Blob([JSON.stringify(lastRun,null,2)+"\n"],{type:"application/json"});
    const url=URL.createObjectURL(blob);
    const link=document.createElement("a");link.href=url;link.download="phiage-toy-simulation.json";
    document.body.append(link);link.click();link.remove();URL.revokeObjectURL(url);
  });
  renderSim();
}
function hallmarkCard(h,index){
  const card=document.createElement("article");card.className="hallmark";
  const head=document.createElement("div");head.className="hallmark-head";
  const number=document.createElement("span");number.className="num";number.textContent="H"+String(index+1).padStart(2,"0");
  const tier=document.createElement("span");tier.className="tier";tier.textContent=h.scale;
  head.append(number,tier);
  const title=document.createElement("h3");title.textContent=h.name;
  const question=document.createElement("p");question.textContent=h.question;
  card.append(head,title,question);
  return card;
}
async function setupHallmarks(){
  const host=$("hallmark-grid");
  try{
    const response=await fetch("./hallmarks.json");
    if(!response.ok)throw Error("HTTP "+response.status);
    const data=await response.json();
    if(!Array.isArray(data.hallmarks)||data.hallmarks.length!==12)throw Error("invalid taxonomy");
    const catalog=data.hallmarks;
    const render=scale=>{
      host.replaceChildren();
      for(const [index,h] of catalog.entries())if(scale==="All"||h.scale===scale)host.append(hallmarkCard(h,index));
    };
    document.querySelectorAll(".filter").forEach(button=>button.addEventListener("click",()=>{
      document.querySelectorAll(".filter").forEach(b=>{
        const active=b===button;b.classList.toggle("active",active);b.setAttribute("aria-pressed",String(active));
      });render(button.dataset.scale);
    }));
    render("All");
  }catch(error){
    host.replaceChildren();
    const p=document.createElement("p");p.className="muted";
    p.textContent="Could not load bundled hallmark data. View data/hallmarks.json in the repository.";
    host.append(p);console.error("Taxonomy load failed",error);
  }
}
async function setupSources(){
  const host=$("source-grid");
  try {
    const response=await fetch("./sources.json");
    if(!response.ok)throw Error("HTTP "+response.status);
    const data=await response.json();
    if(data.schema_version!=="phiage-source-registry/v0.2"||!Array.isArray(data.sources))throw Error("invalid source schema");
    host.replaceChildren();
    $("candidate-count").textContent=String(data.sources.length);
    // The browser has no authority to certify datasets. It displays only manual review metadata.
    const approved=data.sources.filter(s=>s.review_state==="approved" && s.license_status==="reviewed" &&
      s.access_scope==="public_processed" && s.sample_overlap_status==="documented_nonoverlap" &&
      s.metadata_complete===true && /^[0-9a-f]{64}$/.test(s.curated_file_sha256||"") &&
      s.age_resolution!=="unverified" && !s.overlap_with.length);
    $("ready-count").textContent=String(approved.length);
    for(const s of data.sources){
      const item=document.createElement("article");item.className="source-card";
      const line=document.createElement("div");line.className="source-card-top";
      const id=document.createElement("span");id.textContent=s.accession;
      const chip=document.createElement("span");chip.className="status";
      chip.textContent=s.review_state==="approved"?"MANUALLY MARKED APPROVED":"CANDIDATE";
      line.append(id,chip);
      const heading=document.createElement("h3");heading.textContent=s.title;
      const details=document.createElement("p");details.className="source-meta";
      details.textContent=s.assay.replaceAll("_"," ")+" · "+s.tissues.join(", ");
      const caveat=document.createElement("p");caveat.className="source-detail";
      caveat.textContent=s.limitations[0];
      const link=document.createElement("a");link.href=s.source_url;link.target="_blank";link.rel="noopener noreferrer";
      link.textContent="View original source ↗";
      item.append(line,heading,details,caveat,link);host.append(item);
    }
  } catch(error){
    host.replaceChildren();
    const p=document.createElement("p");p.className="muted";
    p.textContent="Source metadata unavailable. See the GitHub source registry.";
    host.append(p);console.error("Source registry load failed",error);
  }
}

async function setupQualityObservation(){
  const host=$("qc-classifications");
  try {
    const response=await fetch("./feature_qc_summary.json");
    if(!response.ok)throw Error("HTTP "+response.status);
    const data=await response.json();
    const q=data.report;
    if(data.schema_version!=="phiage-observed-feature-qc-summary/v0.5"||
       q.claim_level!=="TECHNICAL_QC_ONLY"||q.analysis_ready!==false||
       q.feature_rows!==q.all_sample_zero_rows+q.informative_feature_rows)
      throw Error("invalid QC result contract");
    const count=n=>new Intl.NumberFormat("en-US").format(n);
    $("qc-features").textContent=count(q.feature_rows);
    $("qc-informative").textContent=count(q.informative_feature_rows);
    $("qc-correlations").textContent=q.nonzero_similarity_median===null?
      "undefined":q.nonzero_similarity_median.toFixed(3);
    host.replaceChildren();
    for(const item of q.annotation_tokens){
      const card=document.createElement("article");card.className="source-card";
      const top=document.createElement("div");top.className="source-card-top";
      const label=document.createElement("span");label.textContent=item.label;
      const value=document.createElement("strong");value.className="qc-count";value.textContent=count(item.count);
      top.append(label,value);
      const detail=document.createElement("p");detail.className="source-detail";
      detail.textContent="Entries carrying this depositor annotation label; not independently curated.";
      card.append(top,detail);host.append(card);
    }
  } catch(error){
    host.replaceChildren();
    const p=document.createElement("p");p.className="muted";
    p.textContent="The archived QC receipt is unavailable. See the repository for recorded results.";
    host.append(p);console.error("QC receipt load failed",error);
  }
}


async function setupReplicationCensus(){
  try{
    const response=await fetch("./cohort_census_summary.json");
    if(!response.ok)throw Error("HTTP "+response.status);
    const x=await response.json();
    if(x.receipt_type!=="phiage-candidate-cohort-source-observation/v0.6" ||
       x.analysis_ready!==false ||
       x.claim_level!=="COHORT_METADATA_DISCOVERY_ONLY" ||
       x.observed_public_gsm_samples!==x.reported_disease_normal_labels+x.reported_disease_hgps_labels ||
       x.sample_title_fpkm_header_exact_matches!==x.observed_public_gsm_samples)
      throw Error("invalid cohort receipt");
    $("rep-samples").textContent=String(x.observed_public_gsm_samples);
    $("rep-normal").textContent=String(x.reported_disease_normal_labels);
    $("rep-hgps").textContent=String(x.reported_disease_hgps_labels);
    $("rep-crosswalk").textContent=String(x.sample_title_fpkm_header_exact_matches);
    $("rep-age").textContent=String(x.sample_age_values_parsed);
  }catch(error){
    console.error("Replication census receipt unavailable",error);
    for(const id of ["rep-samples","rep-normal","rep-hgps","rep-crosswalk","rep-age"])
      $(id).textContent="unavailable";
  }
}

document.addEventListener("DOMContentLoaded",()=>{setupSim();setupHallmarks();setupSources();setupQualityObservation();setupReplicationCensus();});
