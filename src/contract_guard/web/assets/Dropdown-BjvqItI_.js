import{B as Pe,V as Re,a as Ie,r as Ke,N as Ce,p as ce}from"./Popover-hxiDDyOr.js";import{c5 as Oe,p as _e,aE as q,M as ie,c6 as ze,c7 as De,L as $e,aC as G,r as T,y as de,d as j,x as s,a6 as J,N as F,ad as pe,ag as Ae,a8 as V,v as w,bo as fe,T as L,a9 as Te,aI as Fe,c8 as je,bp as Be,bn as Me,z as N,aw as Ee,C as E,a4 as le,R as I,E as _,aa as Le,H as He,I as ve,J as Ue,c9 as We,a3 as te,U as K,P as A}from"./index-JKv9wurx.js";import{N as qe,c as Ge}from"./Icon-DtLVfqeE.js";import{C as Ve}from"./ChevronRight-CY1skER3.js";import{h as se}from"./happens-in-CM8LO42l.js";import{u as Je}from"./get-S4-LhD0z.js";import{c as Xe}from"./create-ref-setter-C4J8sofl.js";function Qe(e={},t){const d=_e({ctrl:!1,command:!1,win:!1,shift:!1,tab:!1}),{keydown:i,keyup:r}=e,o=a=>{switch(a.key){case"Control":d.ctrl=!0;break;case"Meta":d.command=!0,d.win=!0;break;case"Shift":d.shift=!0;break;case"Tab":d.tab=!0;break}i!==void 0&&Object.keys(i).forEach(m=>{if(m!==a.key)return;const b=i[m];if(typeof b=="function")b(a);else{const{stop:g=!1,prevent:x=!1}=b;g&&a.stopPropagation(),x&&a.preventDefault(),b.handler(a)}})},p=a=>{switch(a.key){case"Control":d.ctrl=!1;break;case"Meta":d.command=!1,d.win=!1;break;case"Shift":d.shift=!1;break;case"Tab":d.tab=!1;break}r!==void 0&&Object.keys(r).forEach(m=>{if(m!==a.key)return;const b=r[m];if(typeof b=="function")b(a);else{const{stop:g=!1,prevent:x=!1}=b;g&&a.stopPropagation(),x&&a.preventDefault(),b.handler(a)}})},v=()=>{(t===void 0||t.value)&&(q("keydown",document,o),q("keyup",document,p)),t!==void 0&&ie(t,a=>{a?(q("keydown",document,o),q("keyup",document,p)):(G("keydown",document,o),G("keyup",document,p))})};return ze()?(De(v),$e(()=>{(t===void 0||t.value)&&(G("keydown",document,o),G("keyup",document,p))})):v(),Oe(d)}function Ye(e,t,d){const i=T(e.value);let r=null;return ie(e,o=>{r!==null&&window.clearTimeout(r),o===!0?d&&!d.value?i.value=!0:r=window.setTimeout(()=>{i.value=!0},t):i.value=!1}),i}const ae=de("n-dropdown-menu"),X=de("n-dropdown"),ue=de("n-dropdown-option"),he=j({name:"DropdownDivider",props:{clsPrefix:{type:String,required:!0}},render(){return s("div",{class:`${this.clsPrefix}-dropdown-divider`})}}),Ze=j({name:"DropdownGroupHeader",props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0}},setup(){const{showIconRef:e,hasSubmenuRef:t}=F(ae),{renderLabelRef:d,labelFieldRef:i,nodePropsRef:r,renderOptionRef:o}=F(X);return{labelField:i,showIcon:e,hasSubmenu:t,renderLabel:d,nodeProps:r,renderOption:o}},render(){var e;const{clsPrefix:t,hasSubmenu:d,showIcon:i,nodeProps:r,renderLabel:o,renderOption:p}=this,{rawNode:v}=this.tmNode,a=s("div",Object.assign({class:`${t}-dropdown-option`},r==null?void 0:r(v)),s("div",{class:`${t}-dropdown-option-body ${t}-dropdown-option-body--group`},s("div",{"data-dropdown-option":!0,class:[`${t}-dropdown-option-body__prefix`,i&&`${t}-dropdown-option-body__prefix--show-icon`]},J(v.icon)),s("div",{class:`${t}-dropdown-option-body__label`,"data-dropdown-option":!0},o?o(v):J((e=v.title)!==null&&e!==void 0?e:v[this.labelField])),s("div",{class:[`${t}-dropdown-option-body__suffix`,d&&`${t}-dropdown-option-body__suffix--has-submenu`],"data-dropdown-option":!0})));return p?p({node:a,option:v}):a}});function re(e,t){return e.type==="submenu"||e.type===void 0&&e[t]!==void 0}function eo(e){return e.type==="group"}function be(e){return e.type==="divider"}function oo(e){return e.type==="render"}const we=j({name:"DropdownOption",props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0},parentKey:{type:[String,Number],default:null},placement:{type:String,default:"right-start"},props:Object,scrollable:Boolean},setup(e){const t=F(X),{hoverKeyRef:d,keyboardKeyRef:i,lastToggledSubmenuKeyRef:r,pendingKeyPathRef:o,activeKeyPathRef:p,animatedRef:v,mergedShowRef:a,renderLabelRef:m,renderIconRef:b,labelFieldRef:g,childrenFieldRef:x,renderOptionRef:k,nodePropsRef:P,menuPropsRef:z}=t,S=F(ue,null),C=F(ae),O=F(fe),U=w(()=>e.tmNode.rawNode),H=w(()=>{const{value:n}=x;return re(e.tmNode.rawNode,n)}),Q=w(()=>{const{disabled:n}=e.tmNode;return n}),Y=w(()=>{if(!H.value)return!1;const{key:n,disabled:c}=e.tmNode;if(c)return!1;const{value:y}=d,{value:D}=i,{value:ne}=r,{value:$}=o;return y!==null?$.includes(n):D!==null?$.includes(n)&&$[$.length-1]!==n:ne!==null?$.includes(n):!1}),Z=w(()=>i.value===null&&!v.value),ee=Ye(Y,300,Z),oe=w(()=>!!(S!=null&&S.enteringSubmenuRef.value)),B=T(!1);L(ue,{enteringSubmenuRef:B});function M(){B.value=!0}function W(){B.value=!1}function R(){const{parentKey:n,tmNode:c}=e;c.disabled||a.value&&(r.value=n,i.value=null,d.value=c.key)}function l(){const{tmNode:n}=e;n.disabled||a.value&&d.value!==n.key&&R()}function u(n){if(e.tmNode.disabled||!a.value)return;const{relatedTarget:c}=n;c&&!se({target:c},"dropdownOption")&&!se({target:c},"scrollbarRail")&&(d.value=null)}function f(){const{value:n}=H,{tmNode:c}=e;a.value&&!n&&!c.disabled&&(t.doSelect(c.key,c.rawNode),t.doUpdateShow(!1))}return{labelField:g,renderLabel:m,renderIcon:b,siblingHasIcon:C.showIconRef,siblingHasSubmenu:C.hasSubmenuRef,menuProps:z,popoverBody:O,animated:v,mergedShowSubmenu:w(()=>ee.value&&!oe.value),rawNode:U,hasSubmenu:H,pending:V(()=>{const{value:n}=o,{key:c}=e.tmNode;return n.includes(c)}),childActive:V(()=>{const{value:n}=p,{key:c}=e.tmNode,y=n.findIndex(D=>c===D);return y===-1?!1:y<n.length-1}),active:V(()=>{const{value:n}=p,{key:c}=e.tmNode,y=n.findIndex(D=>c===D);return y===-1?!1:y===n.length-1}),mergedDisabled:Q,renderOption:k,nodeProps:P,handleClick:f,handleMouseMove:l,handleMouseEnter:R,handleMouseLeave:u,handleSubmenuBeforeEnter:M,handleSubmenuAfterEnter:W}},render(){var e,t;const{animated:d,rawNode:i,mergedShowSubmenu:r,clsPrefix:o,siblingHasIcon:p,siblingHasSubmenu:v,renderLabel:a,renderIcon:m,renderOption:b,nodeProps:g,props:x,scrollable:k}=this;let P=null;if(r){const O=(e=this.menuProps)===null||e===void 0?void 0:e.call(this,i,i.children);P=s(me,Object.assign({},O,{clsPrefix:o,scrollable:this.scrollable,tmNodes:this.tmNode.children,parentKey:this.tmNode.key}))}const z={class:[`${o}-dropdown-option-body`,this.pending&&`${o}-dropdown-option-body--pending`,this.active&&`${o}-dropdown-option-body--active`,this.childActive&&`${o}-dropdown-option-body--child-active`,this.mergedDisabled&&`${o}-dropdown-option-body--disabled`],onMousemove:this.handleMouseMove,onMouseenter:this.handleMouseEnter,onMouseleave:this.handleMouseLeave,onClick:this.handleClick},S=g==null?void 0:g(i),C=s("div",Object.assign({class:[`${o}-dropdown-option`,S==null?void 0:S.class],"data-dropdown-option":!0},S),s("div",pe(z,x),[s("div",{class:[`${o}-dropdown-option-body__prefix`,p&&`${o}-dropdown-option-body__prefix--show-icon`]},[m?m(i):J(i.icon)]),s("div",{"data-dropdown-option":!0,class:`${o}-dropdown-option-body__label`},a?a(i):J((t=i[this.labelField])!==null&&t!==void 0?t:i.title)),s("div",{"data-dropdown-option":!0,class:[`${o}-dropdown-option-body__suffix`,v&&`${o}-dropdown-option-body__suffix--has-submenu`]},this.hasSubmenu?s(qe,null,{default:()=>s(Ve,null)}):null)]),this.hasSubmenu?s(Pe,null,{default:()=>[s(Re,null,{default:()=>s("div",{class:`${o}-dropdown-offset-container`},s(Ie,{show:this.mergedShowSubmenu,placement:this.placement,to:k&&this.popoverBody||void 0,teleportDisabled:!k},{default:()=>s("div",{class:`${o}-dropdown-menu-wrapper`},d?s(Ae,{onBeforeEnter:this.handleSubmenuBeforeEnter,onAfterEnter:this.handleSubmenuAfterEnter,name:"fade-in-scale-up-transition",appear:!0},{default:()=>P}):P)}))})]}):null);return b?b({node:C,option:i}):C}}),no=j({name:"NDropdownGroup",props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0},parentKey:{type:[String,Number],default:null}},render(){const{tmNode:e,parentKey:t,clsPrefix:d}=this,{children:i}=e;return s(Te,null,s(Ze,{clsPrefix:d,tmNode:e,key:e.key}),i==null?void 0:i.map(r=>{const{rawNode:o}=r;return o.show===!1?null:be(o)?s(he,{clsPrefix:d,key:r.key}):r.isGroup?(Fe("dropdown","`group` node is not allowed to be put in `group` node."),null):s(we,{clsPrefix:d,tmNode:r,parentKey:t,key:r.key})}))}}),to=j({name:"DropdownRenderOption",props:{tmNode:{type:Object,required:!0}},render(){const{rawNode:{render:e,props:t}}=this.tmNode;return s("div",t,[e==null?void 0:e()])}}),me=j({name:"DropdownMenu",props:{scrollable:Boolean,showArrow:Boolean,arrowStyle:[String,Object],clsPrefix:{type:String,required:!0},tmNodes:{type:Array,default:()=>[]},parentKey:{type:[String,Number],default:null}},setup(e){const{renderIconRef:t,childrenFieldRef:d}=F(X);L(ae,{showIconRef:w(()=>{const r=t.value;return e.tmNodes.some(o=>{var p;if(o.isGroup)return(p=o.children)===null||p===void 0?void 0:p.some(({rawNode:a})=>r?r(a):a.icon);const{rawNode:v}=o;return r?r(v):v.icon})}),hasSubmenuRef:w(()=>{const{value:r}=d;return e.tmNodes.some(o=>{var p;if(o.isGroup)return(p=o.children)===null||p===void 0?void 0:p.some(({rawNode:a})=>re(a,r));const{rawNode:v}=o;return re(v,r)})})});const i=T(null);return L(Be,null),L(Me,null),L(fe,i),{bodyRef:i}},render(){const{parentKey:e,clsPrefix:t,scrollable:d}=this,i=this.tmNodes.map(r=>{const{rawNode:o}=r;return o.show===!1?null:oo(o)?s(to,{tmNode:r,key:r.key}):be(o)?s(he,{clsPrefix:t,key:r.key}):eo(o)?s(no,{clsPrefix:t,tmNode:r,parentKey:e,key:r.key}):s(we,{clsPrefix:t,tmNode:r,parentKey:e,key:r.key,props:o.props,scrollable:d})});return s("div",{class:[`${t}-dropdown-menu`,d&&`${t}-dropdown-menu--scrollable`],ref:"bodyRef"},d?s(je,{contentClass:`${t}-dropdown-menu__content`},{default:()=>i}):i,this.showArrow?Ke({clsPrefix:t,arrowStyle:this.arrowStyle,arrowClass:void 0,arrowWrapperClass:void 0,arrowWrapperStyle:void 0}):null)}}),ro=N("dropdown-menu",`
 transform-origin: var(--v-transform-origin);
 background-color: var(--n-color);
 border-radius: var(--n-border-radius);
 box-shadow: var(--n-box-shadow);
 position: relative;
 transition:
 background-color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
`,[Ee(),N("dropdown-option",`
 position: relative;
 `,[E("a",`
 text-decoration: none;
 color: inherit;
 outline: none;
 `,[E("&::before",`
 content: "";
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 `)]),N("dropdown-option-body",`
 display: flex;
 cursor: pointer;
 position: relative;
 height: var(--n-option-height);
 line-height: var(--n-option-height);
 font-size: var(--n-font-size);
 color: var(--n-option-text-color);
 transition: color .3s var(--n-bezier);
 `,[E("&::before",`
 content: "";
 position: absolute;
 top: 0;
 bottom: 0;
 left: 4px;
 right: 4px;
 transition: background-color .3s var(--n-bezier);
 border-radius: var(--n-border-radius);
 `),le("disabled",[I("pending",`
 color: var(--n-option-text-color-hover);
 `,[_("prefix, suffix",`
 color: var(--n-option-text-color-hover);
 `),E("&::before","background-color: var(--n-option-color-hover);")]),I("active",`
 color: var(--n-option-text-color-active);
 `,[_("prefix, suffix",`
 color: var(--n-option-text-color-active);
 `),E("&::before","background-color: var(--n-option-color-active);")]),I("child-active",`
 color: var(--n-option-text-color-child-active);
 `,[_("prefix, suffix",`
 color: var(--n-option-text-color-child-active);
 `)])]),I("disabled",`
 cursor: not-allowed;
 opacity: var(--n-option-opacity-disabled);
 `),I("group",`
 font-size: calc(var(--n-font-size) - 1px);
 color: var(--n-group-header-text-color);
 `,[_("prefix",`
 width: calc(var(--n-option-prefix-width) / 2);
 `,[I("show-icon",`
 width: calc(var(--n-option-icon-prefix-width) / 2);
 `)])]),_("prefix",`
 width: var(--n-option-prefix-width);
 display: flex;
 justify-content: center;
 align-items: center;
 color: var(--n-prefix-color);
 transition: color .3s var(--n-bezier);
 z-index: 1;
 `,[I("show-icon",`
 width: var(--n-option-icon-prefix-width);
 `),N("icon",`
 font-size: var(--n-option-icon-size);
 `)]),_("label",`
 white-space: nowrap;
 flex: 1;
 z-index: 1;
 `),_("suffix",`
 box-sizing: border-box;
 flex-grow: 0;
 flex-shrink: 0;
 display: flex;
 justify-content: flex-end;
 align-items: center;
 min-width: var(--n-option-suffix-width);
 padding: 0 8px;
 transition: color .3s var(--n-bezier);
 color: var(--n-suffix-color);
 z-index: 1;
 `,[I("has-submenu",`
 width: var(--n-option-icon-suffix-width);
 `),N("icon",`
 font-size: var(--n-option-icon-size);
 `)]),N("dropdown-menu","pointer-events: all;")]),N("dropdown-offset-container",`
 pointer-events: none;
 position: absolute;
 left: 0;
 right: 0;
 top: -4px;
 bottom: -4px;
 `)]),N("dropdown-divider",`
 transition: background-color .3s var(--n-bezier);
 background-color: var(--n-divider-color);
 height: 1px;
 margin: 4px 0;
 `),N("dropdown-menu-wrapper",`
 transform-origin: var(--v-transform-origin);
 width: fit-content;
 `),E(">",[N("scrollbar",`
 height: inherit;
 max-height: inherit;
 `)]),le("scrollable",`
 padding: var(--n-padding);
 `),I("scrollable",[_("content",`
 padding: var(--n-padding);
 `)])]),io={animated:{type:Boolean,default:!0},keyboard:{type:Boolean,default:!0},size:String,inverted:Boolean,placement:{type:String,default:"bottom"},onSelect:[Function,Array],options:{type:Array,default:()=>[]},menuProps:Function,showArrow:Boolean,renderLabel:Function,renderIcon:Function,renderOption:Function,nodeProps:Function,labelField:{type:String,default:"label"},keyField:{type:String,default:"key"},childrenField:{type:String,default:"children"},value:[String,Number]},ao=Object.keys(ce),lo=Object.assign(Object.assign(Object.assign({},ce),io),ve.props),bo=j({name:"Dropdown",inheritAttrs:!1,props:lo,setup(e){const t=T(!1),d=Je(K(e,"show"),t),i=w(()=>{const{keyField:l,childrenField:u}=e;return Ge(e.options,{getKey(f){return f[l]},getDisabled(f){return f.disabled===!0},getIgnored(f){return f.type==="divider"||f.type==="render"},getChildren(f){return f[u]}})}),r=w(()=>i.value.treeNodes),o=T(null),p=T(null),v=T(null),a=w(()=>{var l,u,f;return(f=(u=(l=o.value)!==null&&l!==void 0?l:p.value)!==null&&u!==void 0?u:v.value)!==null&&f!==void 0?f:null}),m=w(()=>i.value.getPath(a.value).keyPath),b=w(()=>i.value.getPath(e.value).keyPath),g=V(()=>e.keyboard&&d.value);Qe({keydown:{ArrowUp:{prevent:!0,handler:Z},ArrowRight:{prevent:!0,handler:Y},ArrowDown:{prevent:!0,handler:ee},ArrowLeft:{prevent:!0,handler:Q},Enter:{prevent:!0,handler:oe},Escape:H}},g);const{mergedClsPrefixRef:x,inlineThemeDisabled:k,mergedComponentPropsRef:P}=He(e),z=w(()=>{var l,u;return e.size||((u=(l=P==null?void 0:P.value)===null||l===void 0?void 0:l.Dropdown)===null||u===void 0?void 0:u.size)||"medium"}),S=ve("Dropdown","-dropdown",ro,We,e,x);L(X,{labelFieldRef:K(e,"labelField"),childrenFieldRef:K(e,"childrenField"),renderLabelRef:K(e,"renderLabel"),renderIconRef:K(e,"renderIcon"),hoverKeyRef:o,keyboardKeyRef:p,lastToggledSubmenuKeyRef:v,pendingKeyPathRef:m,activeKeyPathRef:b,animatedRef:K(e,"animated"),mergedShowRef:d,nodePropsRef:K(e,"nodeProps"),renderOptionRef:K(e,"renderOption"),menuPropsRef:K(e,"menuProps"),doSelect:C,doUpdateShow:O}),ie(d,l=>{!e.animated&&!l&&U()});function C(l,u){const{onSelect:f}=e;f&&te(f,l,u)}function O(l){const{"onUpdate:show":u,onUpdateShow:f}=e;u&&te(u,l),f&&te(f,l),t.value=l}function U(){o.value=null,p.value=null,v.value=null}function H(){O(!1)}function Q(){M("left")}function Y(){M("right")}function Z(){M("up")}function ee(){M("down")}function oe(){const l=B();l!=null&&l.isLeaf&&d.value&&(C(l.key,l.rawNode),O(!1))}function B(){var l;const{value:u}=i,{value:f}=a;return!u||f===null?null:(l=u.getNode(f))!==null&&l!==void 0?l:null}function M(l){const{value:u}=a,{value:{getFirstAvailableNode:f}}=i;let n=null;if(u===null){const c=f();c!==null&&(n=c.key)}else{const c=B();if(c){let y;switch(l){case"down":y=c.getNext();break;case"up":y=c.getPrev();break;case"right":y=c.getChild();break;case"left":y=c.getParent();break}y&&(n=y.key)}}n!==null&&(o.value=null,p.value=n)}const W=w(()=>{const{inverted:l}=e,u=z.value,{common:{cubicBezierEaseInOut:f},self:n}=S.value,{padding:c,dividerColor:y,borderRadius:D,optionOpacityDisabled:ne,[A("optionIconSuffixWidth",u)]:$,[A("optionSuffixWidth",u)]:ye,[A("optionIconPrefixWidth",u)]:ge,[A("optionPrefixWidth",u)]:xe,[A("fontSize",u)]:Se,[A("optionHeight",u)]:Ne,[A("optionIconSize",u)]:ke}=n,h={"--n-bezier":f,"--n-font-size":Se,"--n-padding":c,"--n-border-radius":D,"--n-option-height":Ne,"--n-option-prefix-width":xe,"--n-option-icon-prefix-width":ge,"--n-option-suffix-width":ye,"--n-option-icon-suffix-width":$,"--n-option-icon-size":ke,"--n-divider-color":y,"--n-option-opacity-disabled":ne};return l?(h["--n-color"]=n.colorInverted,h["--n-option-color-hover"]=n.optionColorHoverInverted,h["--n-option-color-active"]=n.optionColorActiveInverted,h["--n-option-text-color"]=n.optionTextColorInverted,h["--n-option-text-color-hover"]=n.optionTextColorHoverInverted,h["--n-option-text-color-active"]=n.optionTextColorActiveInverted,h["--n-option-text-color-child-active"]=n.optionTextColorChildActiveInverted,h["--n-prefix-color"]=n.prefixColorInverted,h["--n-suffix-color"]=n.suffixColorInverted,h["--n-group-header-text-color"]=n.groupHeaderTextColorInverted):(h["--n-color"]=n.color,h["--n-option-color-hover"]=n.optionColorHover,h["--n-option-color-active"]=n.optionColorActive,h["--n-option-text-color"]=n.optionTextColor,h["--n-option-text-color-hover"]=n.optionTextColorHover,h["--n-option-text-color-active"]=n.optionTextColorActive,h["--n-option-text-color-child-active"]=n.optionTextColorChildActive,h["--n-prefix-color"]=n.prefixColor,h["--n-suffix-color"]=n.suffixColor,h["--n-group-header-text-color"]=n.groupHeaderTextColor),h}),R=k?Ue("dropdown",w(()=>`${z.value[0]}${e.inverted?"i":""}`),W,e):void 0;return{mergedClsPrefix:x,mergedTheme:S,mergedSize:z,tmNodes:r,mergedShow:d,handleAfterLeave:()=>{e.animated&&U()},doUpdateShow:O,cssVars:k?void 0:W,themeClass:R==null?void 0:R.themeClass,onRender:R==null?void 0:R.onRender}},render(){const e=(i,r,o,p,v)=>{var a;const{mergedClsPrefix:m,menuProps:b}=this;(a=this.onRender)===null||a===void 0||a.call(this);const g=(b==null?void 0:b(void 0,this.tmNodes.map(k=>k.rawNode)))||{},x={ref:Xe(r),class:[i,`${m}-dropdown`,`${m}-dropdown--${this.mergedSize}-size`,this.themeClass],clsPrefix:m,tmNodes:this.tmNodes,style:[...o,this.cssVars],showArrow:this.showArrow,arrowStyle:this.arrowStyle,scrollable:this.scrollable,onMouseenter:p,onMouseleave:v};return s(me,pe(this.$attrs,x,g))},{mergedTheme:t}=this,d={show:this.mergedShow,theme:t.peers.Popover,themeOverrides:t.peerOverrides.Popover,internalOnAfterLeave:this.handleAfterLeave,internalRenderBody:e,onUpdateShow:this.doUpdateShow,"onUpdate:show":void 0};return s(Ce,Object.assign({},Le(this.$props,ao),d),{trigger:()=>{var i,r;return(r=(i=this.$slots).default)===null||r===void 0?void 0:r.call(i)}})}});export{bo as N,Qe as u};
