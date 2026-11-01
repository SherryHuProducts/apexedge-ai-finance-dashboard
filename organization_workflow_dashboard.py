"""Interactive OLX organization and cross-functional workflow diagrams."""
import streamlit as st
import streamlit.components.v1 as components

DIAGRAM_HTML = r"""
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
*{box-sizing:border-box}body{margin:0;background:#fbfaf7;color:#292620;font:14px/1.45 Arial,sans-serif}
.toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:12px 15px;background:#f4efe8;border:1px solid #e4ddd4;border-radius:12px}
button,select,input,textarea{font:inherit}button,.pick{background:#fffefa;border:1px solid #d9d0c4;border-radius:8px;padding:7px 11px;color:#342e27;cursor:pointer}
button:hover{background:#eee6db}.primary{background:#35312b;color:white}.primary:hover{background:#514a41}
.pill{font-size:11px;border-radius:20px;background:#ebe4da;padding:5px 9px} .spacer{flex:1}
.shell{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:12px;margin-top:12px}
.board{position:relative;width:100%;height:640px;background-color:#fffefa;background-image:radial-gradient(#e7dfd4 1px,transparent 1px);background-size:20px 20px;border:1px solid #e8e0d6;border-radius:12px;overflow:hidden}
.links{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.link{fill:none;stroke:#b5a99b;stroke-width:2}.link.dash{stroke-dasharray:6 5}
.node{position:absolute;width:180px;min-height:85px;background:#fff;border:1px solid #d7cabb;border-radius:11px;box-shadow:0 3px 12px #62544310;padding:12px;cursor:grab;user-select:none;touch-action:none}
.node:active{cursor:grabbing}.node.selected{outline:2px solid #ab8e69}.node h3{font-size:13px;line-height:1.3;margin:0 0 6px}.node .cn{font-size:12px;color:#74675a;margin-bottom:5px}.node .detail{font-size:11px;color:#71685d}
.node.lead{background:#ede5d9}.node.data{background:#f1f5f2;border-color:#b7c9bb}.node.finance{background:#f5f0e7}.node.sales{background:#f7f0ec}.node.tech{background:#edf1f3}
.panel{background:#fffefa;border:1px solid #e8e0d6;border-radius:12px;padding:15px;min-width:0}
.panel h3{margin:0 0 10px}.field{display:block;font-size:12px;color:#6c5e50;margin:10px 0 3px}input,textarea{width:100%;border:1px solid #d9cfc2;border-radius:7px;padding:7px;background:white;color:#302923}
textarea{min-height:95px;resize:vertical}.hint{color:#796c60;font-size:12px}.actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
footer{font-size:12px;color:#786c60;margin:11px 2px}.status{color:#67594a;font-size:12px}
@media(max-width:740px){.shell{grid-template-columns:1fr}.board{height:540px}.panel{max-width:none}}
</style></head><body>
<div class="toolbar">
 <strong>OLX · Transformation Canvas</strong>
 <select id="mode"><option value="org">Organization / 组织架构</option><option value="flow">Workflow / 协作流程</option></select>
 <span class="pill">Proposed design / 拟议方案</span><span class="spacer"></span>
 <button id="add" class="primary">+ Add module / 新增</button><button id="reset">Reset / 重置</button>
 <button id="export">Export JSON / 导出</button><label class="pick" for="import">Import / 导入</label><input id="import" type="file" accept=".json,application/json" hidden>
</div>
<div class="shell"><section class="board" id="board" aria-label="Draggable canvas"><svg class="links" id="links"></svg></section>
<aside class="panel"><h3>Module details / 模块设置</h3><div class="hint" id="help">Click a module to edit. Drag it to rearrange. / 点击编辑，拖动调整位置。</div>
<label class="field">Title / 英文标题</label><input id="title" placeholder="Select a module">
<label class="field">中文名称</label><input id="cn"><label class="field">Responsibilities / 职责</label><textarea id="detail"></textarea>
<div class="actions"><button id="save" class="primary">Apply / 应用</button><button id="remove">Remove / 删除</button></div>
<hr style="border:0;border-top:1px solid #e8e0d6;margin:17px 0"><div class="hint"><strong>How it works / 使用方法</strong><p>Connectors are directional. Dragging a module updates the arrows immediately. Edits remain in this session; export JSON to keep a permanent copy.</p><p>箭头表示协作方向。当前编辑仅保存在本次页面会话；需要永久保留请导出 JSON。</p></div>
<div class="status" id="status"></div></aside></div>
<footer>Illustrative design for interview discussions. Not OLX's approved organizational chart or deployed system architecture. / 面试展示用拟议设计，非 OLX 已批准的正式架构。</footer>
<script>
(function(){
"use strict";
var defaults={
org:{nodes:[
{id:"ceo",title:"CEO",cn:"首席执行官",detail:"Executive sponsorship / 战略统筹",kind:"lead",x:315,y:20},
{id:"office",title:"AI Transformation Office",cn:"AI 转型办公室",detail:"Proposed cross-functional steering, priorities and controls / 跨部门协调",kind:"lead",x:315,y:135},
{id:"cfo",title:"CFO / Corporate Finance",cn:"财务负责人",detail:"Financial definitions, close and control / 财务口径与控制",kind:"finance",x:50,y:255},
{id:"saleslead",title:"Head of Sales",cn:"销售负责人",detail:"Commercial execution / 商业决策",kind:"sales",x:315,y:255},
{id:"ithead",title:"Head of IT",cn:"IT 负责人",detail:"Data access and security / 接口与安全",kind:"tech",x:580,y:255},
{id:"acct",title:"Accounting",cn:"会计团队",detail:"Record · Reconcile · Control · Close",kind:"finance",x:12,y:410},
{id:"analyst",title:"AI Finance Analysts",cn:"AI 财务分析",detail:"Integrate · Analyze · Forecast · Recommend",kind:"finance",x:212,y:410},
{id:"commercial",title:"Pricing & Channel Sales",cn:"定价、促销与渠道",detail:"Price · Promote · Sell · Execute",kind:"sales",x:412,y:410},
{id:"platform",title:"Data & Security / IT",cn:"数据集成与安全",detail:"Connect · Govern · Secure · Support",kind:"tech",x:612,y:410}
],edges:[["ceo","office"],["ceo","cfo"],["ceo","saleslead"],["ceo","ithead"],["cfo","acct"],["cfo","analyst"],["saleslead","commercial"],["ithead","platform"]]},
flow:{nodes:[
{id:"systems",title:"Authorized Business Systems",cn:"经授权的业务系统",detail:"Orders, inventory, marketplace, ads · Read-only extracts / 订单、库存、广告",kind:"data",x:28,y:42},
{id:"accounting",title:"Corporate Finance",cn:"公司财务与会计",detail:"Record · Reconcile · Control · Close; GL controls / 总账控制数",kind:"finance",x:28,y:320},
{id:"analyst",title:"AI Finance Analysts",cn:"AI 财务分析",detail:"Integrate · Analyze · Forecast · Recommend; evidence-based findings / 利润分析与建议",kind:"finance",x:305,y:145},
{id:"sales",title:"Sales / Commercial",cn:"销售与商业团队",detail:"Price · Promote · Sell · Execute; review outcomes / 商业行动与复盘",kind:"sales",x:585,y:42},
{id:"it",title:"IT / Data Governance",cn:"信息技术与数据治理",detail:"APIs · Permissions · Validation · Monitoring / 系统权限与质量",kind:"tech",x:585,y:320}
],edges:[["systems","analyst"],["systems","accounting"],["accounting","analyst"],["analyst","sales"],["sales","systems"],["it","systems"],["it","analyst"]]}
};
var mode=document.getElementById("mode"),board=document.getElementById("board"),svg=document.getElementById("links");
var state=JSON.parse(JSON.stringify(defaults)),selected=null,drag=null;
function current(){return state[mode.value]}function node(id){return current().nodes.find(function(n){return n.id===id})}
function setStatus(m){document.getElementById("status").textContent=m}
function draw(){
board.querySelectorAll(".node").forEach(function(x){x.remove()});svg.innerHTML="";
var rect=board.getBoundingClientRect(), W=rect.width,H=rect.height;
current().edges.forEach(function(edge){var a=node(edge[0]),b=node(edge[1]);if(!a||!b)return;
var x1=(a.x+90)/800*W,y1=(a.y+43)/640*H,x2=(b.x+90)/800*W,y2=(b.y+43)/640*H;
var path=document.createElementNS("http://www.w3.org/2000/svg","path");
path.setAttribute("class","link");path.setAttribute("d","M"+x1+","+y1+" Q"+((x1+x2)/2)+","+((y1+y2)/2-30)+" "+x2+","+y2);
svg.appendChild(path)});
current().nodes.forEach(function(n){
var el=document.createElement("div");el.className="node "+(n.kind||"")+" "+(selected===n.id?"selected":"");el.dataset.id=n.id;
el.style.left=(n.x/800*W)+"px";el.style.top=(n.y/640*H)+"px";
var h=document.createElement("h3");h.textContent=n.title;el.appendChild(h);
var cn=document.createElement("div");cn.className="cn";cn.textContent=n.cn;el.appendChild(cn);
var d=document.createElement("div");d.className="detail";d.textContent=n.detail;el.appendChild(d);
el.addEventListener("pointerdown",function(e){if(e.button!==0)return;selected=n.id;drag={id:n.id,pointerX:e.clientX,pointerY:e.clientY,x:n.x,y:n.y};
el.setPointerCapture(e.pointerId);populate();drawSelection();e.preventDefault()});
el.addEventListener("pointermove",function(e){if(!drag||drag.id!==n.id)return;var r=board.getBoundingClientRect();n.x=Math.max(0,Math.min(800-185,drag.x+(e.clientX-drag.pointerX)*800/r.width));n.y=Math.max(0,Math.min(640-90,drag.y+(e.clientY-drag.pointerY)*640/r.height));drawLinksOnly();el.style.left=n.x/800*r.width+"px";el.style.top=n.y/640*r.height+"px"});
el.addEventListener("pointerup",function(){drag=null;render()});board.appendChild(el)
})
}
function drawLinksOnly(){var paths=svg.querySelectorAll("path"),r=board.getBoundingClientRect();current().edges.forEach(function(e,i){var a=node(e[0]),b=node(e[1]);if(!a||!b)return;var x1=(a.x+90)/800*r.width,y1=(a.y+43)/640*r.height,x2=(b.x+90)/800*r.width,y2=(b.y+43)/640*r.height;paths[i].setAttribute("d","M"+x1+","+y1+" Q"+((x1+x2)/2)+","+((y1+y2)/2-30)+" "+x2+","+y2)})}
function drawSelection(){board.querySelectorAll(".node").forEach(function(el){el.classList.toggle("selected",el.dataset.id===selected)})}
function populate(){var n=node(selected);["title","cn","detail"].forEach(function(k){document.getElementById(k).value=n?n[k]:""})}
function render(){if(selected&&!node(selected))selected=null;draw();populate()}
mode.addEventListener("change",function(){selected=null;render()});
document.getElementById("save").onclick=function(){var n=node(selected);if(!n)return setStatus("Select a module first / 请先选模块");["title","cn","detail"].forEach(function(k){n[k]=document.getElementById(k).value.trim()});render();setStatus("Updated / 已更新")};
document.getElementById("add").onclick=function(){var id="custom_"+Date.now();current().nodes.push({id:id,title:"New Module",cn:"新模块",detail:"Edit responsibilities / 编辑职责",kind:"data",x:280,y:500});selected=id;render()};
document.getElementById("remove").onclick=function(){if(!selected)return;current().nodes=current().nodes.filter(function(n){return n.id!==selected});current().edges=current().edges.filter(function(e){return e[0]!==selected&&e[1]!==selected});selected=null;render()};
document.getElementById("reset").onclick=function(){state[mode.value]=JSON.parse(JSON.stringify(defaults[mode.value]));selected=null;render();setStatus("Reset to illustrative template / 已重置")};
document.getElementById("export").onclick=function(){var blob=new Blob([JSON.stringify(state,null,2)],{type:"application/json"});var url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="olx_organization_workflow.json";a.click();setTimeout(function(){URL.revokeObjectURL(url)},1000)};
document.getElementById("import").onchange=function(e){var f=e.target.files[0];if(!f)return;var reader=new FileReader();reader.onload=function(){try{var x=JSON.parse(reader.result);["org","flow"].forEach(function(k){if(!x[k]||!Array.isArray(x[k].nodes)||!Array.isArray(x[k].edges))throw Error("Missing diagram "+k);x[k].nodes.forEach(function(n){if(typeof n.id!=="string"||typeof n.x!=="number"||typeof n.y!=="number")throw Error("Invalid node")})});state=x;selected=null;render();setStatus("Imported / 已导入")}catch(err){setStatus("Invalid JSON: "+err.message)}};reader.readAsText(f)};
window.addEventListener("resize",render);render();
})();
</script></body></html>
"""

def organization_workflow_page():
    st.title("Organization & Workflow / 组织架构与工作流程")
    st.caption("Interactive proposed structure and collaboration model / 可拖拽的拟议组织架构与协作流程")
    st.info("Design canvas only. Move modules, edit their responsibilities, and export JSON to preserve changes. No real OLX organizational data is implied.")
    components.html(DIAGRAM_HTML, height=810, scrolling=False)
