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


async function setupReplicationQuality(){
  try{
    const [qres,ores]=await Promise.all([
      fetch("./replication_qc_summary.json"),
      fetch("./transcript_overlap_summary.json")
    ]);
    if(!qres.ok||!ores.ok)throw Error("missing verified receipt");
    const q=await qres.json(), o=await ores.json();
    const a=q.sample_metadata_qc, b=q.expression_qc;
    if(q.receipt_type!=="phiage-observed-replication-readiness/v0.7"||
       o.receipt_type!=="phiage-observed-transcript-id-overlap/v0.7"||
       q.analysis_ready!==false||o.analysis_ready!==false||
       q.age_association_tested!==false||o.expression_scale_harmonized!==false||
       o.exact_refseq_identifier_overlap+o.source_a_only_accessions!==o.GSE113957_unique_refseq_ids||
       a.observed_gsm_count!==b.expression_sample_columns)
       throw Error("inconsistent or unauthorized research receipt");
    const n=x=>new Intl.NumberFormat("en-US").format(x);
    $("rep-shared-ids").textContent=n(o.exact_refseq_identifier_overlap);
    $("rep-unique-cells").textContent=n(a.cell_id_label.unique_labels);
    $("rep-fpkm-features").textContent=n(b.feature_rows);
    const portion=100*o.exact_refseq_identifier_overlap/o.GSE113957_unique_refseq_ids;
    $("rep-overlap-bar").style.width=portion.toFixed(2)+"%";
    $("rep-overlap-caption").textContent=
      portion.toFixed(1)+"% exact RefSeq text match; "+
      n(o.source_a_only_accessions)+" unmatched from each cohort. No expression-scale equivalence.";
    const platforms=a.platform_group_counts;
    $("rep-platform-caveat").textContent=
      "Source platform distribution: "+
      Object.entries(platforms).map(([name,groups])=>
       name+": "+Object.entries(groups).map(([group,count])=>count+" "+group.replace("_label_explicit","")).join(", ")
      ).join("; ")+". This may confound naive group comparisons.";
  }catch(error){
    console.error("Replication QC receipts unavailable",error);
    $("rep-overlap-caption").textContent="Archived technical QC receipt unavailable.";
    $("rep-platform-caveat").textContent="Platform audit cannot be displayed.";
  }
}


async function setupDesignPreflight(){
  try{
    const res=await fetch("./design_preflight_summary.json");
    if(!res.ok)throw Error("source receipt unavailable");
    const d=await res.json();
    if(d.receipt_type!=="phiage-source-observed-platform-preflight/v0.8"||
       d.analysis_ready!==false||d.training_or_hypothesis_test_performed!==false||
       d.donor_independence_verified!==false||
       d.eligible_adult_healthy.sample_count!==
         d.primary_platform_healthy_adult.sample_count+d.transport_platform_healthy_adult.sample_count)
      throw Error("unsafe or inconsistent design receipt");
    $("design-adults").textContent=String(d.eligible_adult_healthy.sample_count);
    $("design-primary").textContent=String(d.primary_platform_healthy_adult.sample_count);
    $("design-transport").textContent=String(d.transport_platform_healthy_adult.sample_count);
    const host=$("design-decades");host.replaceChildren();
    for(const [decade,counts] of Object.entries(d.shared_decade_sample_counts)){
      const item=document.createElement("div");item.className="design-decade";
      const title=document.createElement("strong");title.textContent=decade;
      const details=document.createElement("span");
      details.textContent="GPL18573: "+counts.primary_count+" · GPL16791: "+counts.transport_count;
      item.append(title,details);
      if(d.sparse_shared_age_decades.includes(decade)){
        const warning=document.createElement("em");warning.textContent="Sparse";
        item.append(warning);
      }
      host.append(item);
    }
    $("design-gate-status").textContent=d.exploratory_transport_metadata_gate_passed?
       "Minimum descriptive support observed, but biological analysis remains blocked.":
       "Design feasibility blocked: "+d.transport_metadata_gate_blockers.join("; ")+". No model trained.";
  }catch(error){
    console.error("Design preflight receipt:",error);
    $("design-gate-status").textContent="Design receipt unavailable; no research readiness is claimed.";
  }
}


async function setupCommonSupport(){
  try {
    const response=await fetch("./common_support_summary.json");
    if(!response.ok)throw Error("source-backed receipt not available");
    const r=await response.json();
    if(r.receipt_type!=="phiage-source-observed-common-support/v0.9"||
       r.analysis_ready!==false||r.age_effect_tested!==false||
       r.sample_matching_performed!==false||
       r.claim_level!=="COMMON_SUPPORT_METADATA_AUDIT_ONLY"||
       r.primary_metadata.n+r.comparison_metadata.n !==
          r.sex_by_age_decade_strata.reduce((sum,s)=>sum+s.primary_n+s.comparison_n,0)||
       r.maximum_balanced_pair_capacity!==
          r.sex_by_age_decade_strata.reduce((sum,s)=>sum+s.maximum_balanced_pairs,0))
      throw Error("unsafe or inconsistent source receipt");
    $("balance-primary").textContent=String(r.primary_metadata.n);
    $("balance-secondary").textContent=String(r.comparison_metadata.n);
    $("balance-capacity").textContent=String(r.maximum_balanced_pair_capacity);
    const host=$("balance-rows");host.replaceChildren();
    for(const entry of r.sex_by_age_decade_strata){
      const row=document.createElement("div");
      row.className="balance-decade";
      const name=document.createElement("strong");
      name.textContent=entry.decade+" · "+entry.sex;
      const values=document.createElement("span");
      values.textContent="GPL18573: "+entry.primary_n+" · GPL16791: "+entry.comparison_n;
      row.append(name,values);
      if(!entry.at_least_two_each){
        const label=document.createElement("em");
        label.textContent=entry.maximum_balanced_pairs===0?"Missing stratum":"Sparse stratum";
        row.append(label);
      }
      host.append(row);
    }
    $("balance-conclusion").textContent=
       r.metadata_balance_thresholds_passed ?
       "Minimum metadata support met, but biological modeling is still blocked." :
       "Common-support gate blocked: "+r.metadata_blockers.join("; ")+". No model was trained.";
  }catch(error){
    console.error("Common support dashboard",error);
    $("balance-conclusion").textContent="Verified common-support receipt unavailable; the research gate remains closed.";
  }
}


async function setupProvenanceGate(){
  try{
    const response=await fetch("./provenance_gate_summary.json");
    if(!response.ok)throw Error("no archived provenance receipt");
    const d=await response.json();
    if(d.receipt_type!=="phiage-source-observed-provenance-coverage/v1.0"||
       d.analysis_ready!==false||d.donor_independence_verified!==false||
       d.age_effects_tested!==false||d.cross_cohort_same_person_linkage_evaluable!==false||
       d.claim_level!=="SOURCE_PROVENANCE_GAPS_ONLY")
      throw Error("unsafe or invalid provenance receipt");
    const [a,b]=d.source_cohorts;
    if(a.accession!=="GSE113957"||b.accession!=="GSE307377"||
       a.identity.cell_id_field_present>a.geo_sample_records||
       b.identity.cell_line_description_field_present>b.geo_sample_records)
      throw Error("invalid source sample counts");
    $("source-a-cellids").textContent=String(a.identity.cell_id_field_present);
    $("source-b-linefields").textContent=String(b.identity.cell_line_description_field_present);
    $("source-donorids").textContent=String(a.identity.subject_identifier_field_present+
                                          b.identity.subject_identifier_field_present);
    const host=$("provenance-observations");host.replaceChildren();
    for(const cohort of [a,b]){
      const el=document.createElement("div");el.className="provenance-stat";
      const title=document.createElement("strong");title.textContent=cohort.accession;
      const p=document.createElement("span");
      const growth=cohort.public_protocol_metadata.growth;
      const extract=cohort.public_protocol_metadata.extraction;
      p.textContent=cohort.geo_sample_records+" GEO samples · "+
        cohort.identity.sample_level_passage_field_present+" passage fields · "+
        growth.samples_with_nonempty+" growth protocols · "+
        extract.samples_with_nonempty+" extraction protocols";
      el.append(title,p);host.append(el);
    }
    $("provenance-blocked").textContent=
      "Person-level linkage remains unavailable. "+d.gate_blockers.length+
      " source and comparability blockers are documented; no independent replication has been claimed.";
  }catch(error){
    console.error("Provenance receipt:",error);
    $("provenance-blocked").textContent="Source-backed provenance receipt unavailable; donor independence remains unverified.";
  }
}

document.addEventListener("DOMContentLoaded",()=>{setupSim();setupHallmarks();setupSources();setupQualityObservation();setupReplicationCensus();setupReplicationQuality();setupDesignPreflight();setupCommonSupport();setupProvenanceGate();});
