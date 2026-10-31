import {el,button,icon} from './ui.js';
import {flowColors,languageColor} from './colors.js';

export function folderTree(files,name='Repository'){
 const root={path:'',label:name,kind:'folder',children:[],files:[],fileCount:0,directFiles:0,languages:{}};
 const nodes=new Map([['',root]]);
 for(const file of files){
  const parts=file.path.split('/').filter(Boolean);const folders=parts.slice(0,-1);
  let node=root;node.fileCount++;node.languages[file.language]=(node.languages[file.language]||0)+1;
  folders.forEach((part,i)=>{const path=folders.slice(0,i+1).join('/');if(!nodes.has(path)){const child={path,label:part,kind:'folder',children:[],files:[],fileCount:0,directFiles:0,languages:{}};nodes.set(path,child);node.children.push(child);}node=nodes.get(path);node.fileCount++;node.languages[file.language]=(node.languages[file.language]||0)+1;});
  node.directFiles++;const item={path:file.path,label:parts.at(-1),kind:'file',language:file.language,children:[],files:[],fileCount:1,directFiles:0,languages:{[file.language]:1}};node.files.push(item);nodes.set(file.path,item);
 }
 for(const n of nodes.values()){n.children.sort((a,b)=>a.label.localeCompare(b.label));n.files.sort((a,b)=>a.label.localeCompare(b.label));}
 return {root,nodes};
}

export function folderLayout(tree,expanded=new Set(['']),vertical=false,rootFiles=false){
 const nodes=[],edges=[];let leaf=0,maxDepth=0;
 function visit(node,depth,color){
  const item={...node,x:140+depth*290,y:0,color:node.kind==='file'?languageColor(node.language):color,depth};nodes.push(item);maxDepth=Math.max(maxDepth,depth);
  const children=expanded.has(node.path)?[...node.children,...(node.path||rootFiles||!node.children.length?node.files:[])]:[];
  if(children.length){const placed=children.map((child,i)=>{const c=visit(child,depth+1,depth===0?flowColors[i%flowColors.length]:color);edges.push({from:item,to:c,color:c.color});return c;});item.y=(placed[0].y+placed.at(-1).y)/2;}
  else{item.y=65+leaf*105;leaf++;}
  return item;
 }
 visit(tree.root,0,'#176ee0');if(vertical){for(const n of nodes){n.x=110+(n.y-65)*2;n.y=70+n.depth*140;}return {nodes,edges,width:Math.max(230,leaf*210+10),height:(maxDepth+1)*140};}return {nodes,edges,width:Math.max(600,290*maxDepth+280),height:Math.max(280,leaf*105+25)};
}

export class FolderMap{
 constructor(container,files,{name='Repository',onSelect=()=>{},onExpand=()=>{}}={}){
  this.container=container;this.tree=folderTree(files,name);this.expanded=this.mainFolders();this.selected='';this.rootFiles=!this.tree.root.children.length;this.onSelect=onSelect;this.zoom=1;this.x=0;this.y=0;
  this.build(onExpand);this.render();this.resize=new ResizeObserver(()=>this.render());this.resize.observe(this.viewport);this.onSelect(this.tree.root);
 }
 mainFolders(){const paths=new Set(['']);let node=this.tree.root;while(node.children.length===1){node=node.children[0];paths.add(node.path);}return paths;}
 build(onExpand){
  this.container.replaceChildren();const toolbar=el('div',null,'graph-toolbar');toolbar.append(el('span','Folders & files','folder-view-label'));
  const actions=el('div',null,'graph-actions');const files=button('Root files','file','root-files-toggle');files.setAttribute('aria-pressed',String(this.rootFiles));files.title='Show or hide files directly in the repository root';files.onclick=()=>{this.rootFiles=!this.rootFiles;files.setAttribute('aria-pressed',String(this.rootFiles));this.render();};actions.append(files);
  const collapse=button('Main folders','folder','quiet');collapse.onclick=()=>{this.expanded=this.mainFolders();this.rootFiles=!this.tree.root.children.length;files.setAttribute('aria-pressed',String(this.rootFiles));this.selected='';this.render();this.onSelect(this.tree.root);};actions.append(collapse);
  for(const [label,ic,fn]of [['Zoom out','minus',()=>this.scale(.85)],['Zoom in','plus',()=>this.scale(1.18)],['Fit map','fit',()=>this.fit(true)],['Expand map','expand',onExpand]]){const b=button('',ic,'icon-button');b.setAttribute('aria-label',label);b.title=label;b.onclick=fn;actions.append(b);}toolbar.append(actions);
  this.viewport=el('div',null,'graph-viewport folder-viewport');this.viewport.tabIndex=0;this.viewport.setAttribute('role','region');this.viewport.setAttribute('aria-label','Repository structure. Select a folder to expand it or a file to open its source. Arrow keys pan, plus and minus zoom, zero fits the map.');
  this.world=el('div',null,'graph-world');this.viewport.append(this.world,el('div','Expand folders · click files to read code','graph-hint'));this.container.append(toolbar,this.viewport);
  this.viewport.addEventListener('pointerdown',e=>{if(e.target.closest('button')||e.button!==0)return;this.drag={px:e.clientX,py:e.clientY,x:this.x,y:this.y};this.viewport.setPointerCapture(e.pointerId);});
  this.viewport.addEventListener('pointermove',e=>{if(!this.drag)return;this.x=this.drag.x+e.clientX-this.drag.px;this.y=this.drag.y+e.clientY-this.drag.py;this.transform();});
  this.viewport.addEventListener('pointerup',()=>this.drag=null);this.viewport.addEventListener('pointercancel',()=>this.drag=null);
  this.viewport.addEventListener('wheel',e=>{e.preventDefault();if(e.ctrlKey||e.metaKey)this.scale(e.deltaY<0?1.1:.9);else{this.x-=e.deltaX;this.y-=e.deltaY;this.transform();}},{passive:false});
  this.viewport.addEventListener('keydown',e=>{if(e.target.closest('button'))return;const delta={ArrowLeft:[35,0],ArrowRight:[-35,0],ArrowUp:[0,35],ArrowDown:[0,-35]}[e.key];if(delta){e.preventDefault();this.x+=delta[0];this.y+=delta[1];this.transform();}else if(['+','=','-','0'].includes(e.key)){e.preventDefault();if(e.key==='0')this.fit(true);else this.scale(e.key==='-'?.85:1.18);}});
 }
 select(path,toggle=true){const node=this.tree.nodes.get(path);if(!node)return;this.selected=path;if(toggle&&node.kind==='folder'&&(node.children.length||node.files.length)){if(this.expanded.has(path))this.expanded.delete(path);else this.expanded.add(path);}this.render();this.onSelect(node);[...this.world.querySelectorAll('button')].find(b=>b.dataset.path===path)?.focus({preventScroll:true});}
 render(){
  this.vertical=this.viewport.clientWidth<480;this.data=folderLayout(this.tree,this.expanded,this.vertical,this.rootFiles);this.world.style.width=this.data.width+'px';this.world.style.height=this.data.height+'px';this.world.replaceChildren();
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.classList.add('graph-lines');svg.setAttribute('width',this.data.width);svg.setAttribute('height',this.data.height);
  for(const edge of this.data.edges){const a=edge.from,b=edge.to,p=document.createElementNS(svg.namespaceURI,'path'),mid=(a.x+b.x)/2;p.setAttribute('d',this.vertical?`M${a.x},${a.y+34} C${a.x},${(a.y+b.y)/2} ${b.x},${(a.y+b.y)/2} ${b.x},${b.y-34}`:`M${a.x+100},${a.y} C${mid},${a.y} ${mid},${b.y} ${b.x-100},${b.y}`);p.setAttribute('class','graph-edge folder-edge');p.style.stroke=edge.color;svg.append(p);}this.world.append(svg);
  for(const n of this.data.nodes){const b=el('button',null,'folder-node '+n.kind+(n.path===this.selected?' selected':''));b.type='button';b.dataset.path=n.path;b.style.left=(n.x-100)+'px';b.style.top=(n.y-34)+'px';b.style.setProperty('--folder-color',n.color);b.title=n.path||n.label;
   if(n.kind==='folder'&&(n.children.length||n.files.length))b.setAttribute('aria-expanded',String(this.expanded.has(n.path)));b.setAttribute('aria-label',n.kind==='file'?`Open ${n.path}, ${n.language}`:`${n.path||n.label}, ${n.fileCount} files, ${this.expanded.has(n.path)?'collapse':'expand'} folder`);
   const mark=el('span',null,'folder-node-icon');mark.append(icon(n.kind==='file'?'file':n.path?'folder':'network'));const copy=el('span',null,'folder-node-copy');copy.append(el('strong',n.label),el('span',n.kind==='file'?n.language:`${n.fileCount} files · ${n.children.length} folders`));b.append(mark,copy);if(n.kind==='folder'&&(n.children.length||n.files.length))b.append(icon(this.expanded.has(n.path)?'minus':'plus'));b.onclick=()=>this.select(n.path);this.world.append(b);
  }this.fit();
 }
 fit(all=false){if(!this.data)return;const w=this.viewport.clientWidth,h=this.viewport.clientHeight;this.zoom=Math.min(1.15,(w-30)/this.data.width,(h-40)/this.data.height);if(!all&&this.zoom<.65){this.zoom=.8;const n=this.data.nodes.find(n=>n.path===this.selected)||this.data.nodes[0];this.x=w/2-n.x*this.zoom;this.y=h/2-n.y*this.zoom;}else{this.x=(w-this.data.width*this.zoom)/2;this.y=(h-this.data.height*this.zoom)/2;}this.transform();}
 scale(factor){const old=this.zoom;this.zoom=Math.max(.15,Math.min(2.5,this.zoom*factor));const cx=this.viewport.clientWidth/2,cy=this.viewport.clientHeight/2;this.x=cx-(cx-this.x)*this.zoom/old;this.y=cy-(cy-this.y)*this.zoom/old;this.transform();}
 transform(){this.world.style.transform=`translate(${this.x}px,${this.y}px) scale(${this.zoom})`;}
 destroy(){this.resize.disconnect();}
}
