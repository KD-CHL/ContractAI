import{C as $,z as m,R as E,E as h,A as Y,D as Z,d as O,x as n,H as J,ai as U,I as V,J as W,aj as ee,v as Q,y as te,T as re,U as ie,N as ae,ak as ne,al as oe,a9 as A,u as le,o as se,am as F,c as H,b as g,t as B,f as i,h as c,w as a,B as I,an as N,k as de,r as G,p as K,j as u,e as p,m as R,ao as ce}from"./index-JKv9wurx.js";import{N as ue,a as L}from"./Grid-CQ7s5bmT.js";import{N as T}from"./Skeleton-DqHB_0bg.js";import{N as M}from"./Statistic-B_jGjWon.js";import{N as me}from"./Empty-v75PMxk5.js";import{N as q}from"./Tag-2dIdwluN.js";import{u as ve,_ as fe}from"./_plugin-vue_export-helper-nsZAGd0n.js";import"./get-slot-Bk_rJcZu.js";import"./next-frame-once-C5Ksf8W7.js";import"./use-houdini-CahkfEBX.js";import"./use-locale-DU2sUPS-.js";const he=$([m("list",`
 --n-merged-border-color: var(--n-border-color);
 --n-merged-color: var(--n-color);
 --n-merged-color-hover: var(--n-color-hover);
 margin: 0;
 font-size: var(--n-font-size);
 transition:
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 padding: 0;
 list-style-type: none;
 color: var(--n-text-color);
 background-color: var(--n-merged-color);
 `,[E("show-divider",[m("list-item",[$("&:not(:last-child)",[h("divider",`
 background-color: var(--n-merged-border-color);
 `)])])]),E("clickable",[m("list-item",`
 cursor: pointer;
 `)]),E("bordered",`
 border: 1px solid var(--n-merged-border-color);
 border-radius: var(--n-border-radius);
 `),E("hoverable",[m("list-item",`
 border-radius: var(--n-border-radius);
 `,[$("&:hover",`
 background-color: var(--n-merged-color-hover);
 `,[h("divider",`
 background-color: transparent;
 `)])])]),E("bordered, hoverable",[m("list-item",`
 padding: 12px 20px;
 `),h("header, footer",`
 padding: 12px 20px;
 `)]),h("header, footer",`
 padding: 12px 0;
 box-sizing: border-box;
 transition: border-color .3s var(--n-bezier);
 `,[$("&:not(:last-child)",`
 border-bottom: 1px solid var(--n-merged-border-color);
 `)]),m("list-item",`
 position: relative;
 padding: 12px 0; 
 box-sizing: border-box;
 display: flex;
 flex-wrap: nowrap;
 align-items: center;
 transition:
 background-color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 `,[h("prefix",`
 margin-right: 20px;
 flex: 0;
 `),h("suffix",`
 margin-left: 20px;
 flex: 0;
 `),h("main",`
 flex: 1;
 `),h("divider",`
 height: 1px;
 position: absolute;
 bottom: 0;
 left: 0;
 right: 0;
 background-color: transparent;
 transition: background-color .3s var(--n-bezier);
 pointer-events: none;
 `)])]),Y(m("list",`
 --n-merged-color-hover: var(--n-color-hover-modal);
 --n-merged-color: var(--n-color-modal);
 --n-merged-border-color: var(--n-border-color-modal);
 `)),Z(m("list",`
 --n-merged-color-hover: var(--n-color-hover-popover);
 --n-merged-color: var(--n-color-popover);
 --n-merged-border-color: var(--n-border-color-popover);
 `))]),ge=Object.assign(Object.assign({},V.props),{size:{type:String,default:"medium"},bordered:Boolean,clickable:Boolean,hoverable:Boolean,showDivider:{type:Boolean,default:!0}}),X=te("n-list"),pe=O({name:"List",props:ge,slots:Object,setup(t){const{mergedClsPrefixRef:e,inlineThemeDisabled:d,mergedRtlRef:_}=J(t),b=U("List",_,e),k=V("List","-list",he,ee,t,e);re(X,{showDividerRef:ie(t,"showDivider"),mergedClsPrefixRef:e});const y=Q(()=>{const{common:{cubicBezierEaseInOut:x},self:{fontSize:w,textColor:o,color:C,colorModal:S,colorPopover:D,borderColor:s,borderColorModal:r,borderColorPopover:f,borderRadius:l,colorHover:z,colorHoverModal:j,colorHoverPopover:P}}=k.value;return{"--n-font-size":w,"--n-bezier":x,"--n-text-color":o,"--n-color":C,"--n-border-radius":l,"--n-border-color":s,"--n-border-color-modal":r,"--n-border-color-popover":f,"--n-color-modal":S,"--n-color-popover":D,"--n-color-hover":z,"--n-color-hover-modal":j,"--n-color-hover-popover":P}}),v=d?W("list",void 0,y,t):void 0;return{mergedClsPrefix:e,rtlEnabled:b,cssVars:d?void 0:y,themeClass:v==null?void 0:v.themeClass,onRender:v==null?void 0:v.onRender}},render(){var t;const{$slots:e,mergedClsPrefix:d,onRender:_}=this;return _==null||_(),n("ul",{class:[`${d}-list`,this.rtlEnabled&&`${d}-list--rtl`,this.bordered&&`${d}-list--bordered`,this.showDivider&&`${d}-list--show-divider`,this.hoverable&&`${d}-list--hoverable`,this.clickable&&`${d}-list--clickable`,this.themeClass],style:this.cssVars},e.header?n("div",{class:`${d}-list__header`},e.header()):null,(t=e.default)===null||t===void 0?void 0:t.call(e),e.footer?n("div",{class:`${d}-list__footer`},e.footer()):null)}}),be=O({name:"ListItem",slots:Object,setup(){const t=ae(X,null);return t||ne("list-item","`n-list-item` must be placed in `n-list`."),{showDivider:t.showDividerRef,mergedClsPrefix:t.mergedClsPrefixRef}},render(){const{$slots:t,mergedClsPrefix:e}=this;return n("li",{class:`${e}-list-item`},t.prefix?n("div",{class:`${e}-list-item__prefix`},t.prefix()):null,t.default?n("div",{class:`${e}-list-item__main`},t):null,t.suffix?n("div",{class:`${e}-list-item__suffix`},t.suffix()):null,this.showDivider&&n("div",{class:`${e}-list-item__divider`}))}}),xe=m("thing",`
 display: flex;
 transition: color .3s var(--n-bezier);
 font-size: var(--n-font-size);
 color: var(--n-text-color);
`,[m("thing-avatar",`
 margin-right: 12px;
 margin-top: 2px;
 `),m("thing-avatar-header-wrapper",`
 display: flex;
 flex-wrap: nowrap;
 `,[m("thing-header-wrapper",`
 flex: 1;
 `)]),m("thing-main",`
 flex-grow: 1;
 `,[m("thing-header",`
 display: flex;
 margin-bottom: 4px;
 justify-content: space-between;
 align-items: center;
 `,[h("title",`
 font-size: 16px;
 font-weight: var(--n-title-font-weight);
 transition: color .3s var(--n-bezier);
 color: var(--n-title-text-color);
 `)]),h("description",[$("&:not(:last-child)",`
 margin-bottom: 4px;
 `)]),h("content",[$("&:not(:first-child)",`
 margin-top: 12px;
 `)]),h("footer",[$("&:not(:first-child)",`
 margin-top: 12px;
 `)]),h("action",[$("&:not(:first-child)",`
 margin-top: 12px;
 `)])])]),_e=Object.assign(Object.assign({},V.props),{title:String,titleExtra:String,description:String,descriptionClass:String,descriptionStyle:[String,Object],content:String,contentClass:String,contentStyle:[String,Object],contentIndented:Boolean}),ye=O({name:"Thing",props:_e,slots:Object,setup(t,{slots:e}){const{mergedClsPrefixRef:d,inlineThemeDisabled:_,mergedRtlRef:b}=J(t),k=V("Thing","-thing",xe,oe,t,d),y=U("Thing",b,d),v=Q(()=>{const{self:{titleTextColor:w,textColor:o,titleFontWeight:C,fontSize:S},common:{cubicBezierEaseInOut:D}}=k.value;return{"--n-bezier":D,"--n-font-size":S,"--n-text-color":o,"--n-title-font-weight":C,"--n-title-text-color":w}}),x=_?W("thing",void 0,v,t):void 0;return()=>{var w;const{value:o}=d,C=y?y.value:!1;return(w=x==null?void 0:x.onRender)===null||w===void 0||w.call(x),n("div",{class:[`${o}-thing`,x==null?void 0:x.themeClass,C&&`${o}-thing--rtl`],style:_?void 0:v.value},e.avatar&&t.contentIndented?n("div",{class:`${o}-thing-avatar`},e.avatar()):null,n("div",{class:`${o}-thing-main`},!t.contentIndented&&(e.header||t.title||e["header-extra"]||t.titleExtra||e.avatar)?n("div",{class:`${o}-thing-avatar-header-wrapper`},e.avatar?n("div",{class:`${o}-thing-avatar`},e.avatar()):null,e.header||t.title||e["header-extra"]||t.titleExtra?n("div",{class:`${o}-thing-header-wrapper`},n("div",{class:`${o}-thing-header`},e.header||t.title?n("div",{class:`${o}-thing-header__title`},e.header?e.header():t.title):null,e["header-extra"]||t.titleExtra?n("div",{class:`${o}-thing-header__extra`},e["header-extra"]?e["header-extra"]():t.titleExtra):null),e.description||t.description?n("div",{class:[`${o}-thing-main__description`,t.descriptionClass],style:t.descriptionStyle},e.description?e.description():t.description):null):null):n(A,null,e.header||t.title||e["header-extra"]||t.titleExtra?n("div",{class:`${o}-thing-header`},e.header||t.title?n("div",{class:`${o}-thing-header__title`},e.header?e.header():t.title):null,e["header-extra"]||t.titleExtra?n("div",{class:`${o}-thing-header__extra`},e["header-extra"]?e["header-extra"]():t.titleExtra):null):null,e.description||t.description?n("div",{class:[`${o}-thing-main__description`,t.descriptionClass],style:t.descriptionStyle},e.description?e.description():t.description):null),e.default||t.content?n("div",{class:[`${o}-thing-main__content`,t.contentClass],style:t.contentStyle},e.default?e.default():t.content):null,e.footer?n("div",{class:`${o}-thing-main__footer`},e.footer()):null,e.action?n("div",{class:`${o}-thing-main__action`},e.action()):null))}}}),ke={class:"dashboard-page"},we={class:"page-header"},$e={class:"page-subtitle"},Ce={class:"quick-actions"},ze={class:"review-meta"},Re={class:"review-time"},Se=O({__name:"DashboardView",setup(t){const e=de(),d=ve(),_=le(),b=G(!0),k=K({total_reviews:0,high_risk_count:0,recent_reviews:[]}),y=K({open_items:0,overdue_items:0}),v=G([]);se(async()=>{await x()});async function x(){b.value=!0;try{const[s,r]=await Promise.allSettled([F.get("/dashboard/summary"),F.get("/operations/summary")]);if(s.status==="fulfilled"){const f=s.value.data;k.total_reviews=f.total_reviews??0,k.high_risk_count=f.high_risk_count??0,k.recent_reviews=f.recent_reviews??[],v.value=f.recent_reviews??[]}if(r.status==="fulfilled"){const f=r.value.data;y.open_items=f.open_items??0,y.overdue_items=f.overdue_items??0}}catch{d.error("获取工作台数据失败")}finally{b.value=!1}}function w(s){return{high:"error",medium:"warning",low:"info",none:"success"}[s]||"info"}function o(s){return{high:"高风险",medium:"中风险",low:"低风险",none:"无风险"}[s]||"未知"}function C(s){return{pending:"info",complete:"success",failed:"error"}[s]||"default"}function S(s){return{pending:"审阅中",complete:"已完成",failed:"审阅失败"}[s]||s}function D(s){if(!s)return"";const r=new Date(s),l=new Date().getTime()-r.getTime(),z=Math.floor(l/6e4),j=Math.floor(l/36e5),P=Math.floor(l/864e5);return z<1?"刚刚":z<60?`${z} 分钟前`:j<24?`${j} 小时前`:P<7?`${P} 天前`:r.toLocaleDateString("zh-CN",{month:"short",day:"numeric"})}return(s,r)=>{var f;return u(),H("div",ke,[g("div",we,[r[4]||(r[4]=g("h1",{class:"page-title"},"工作台",-1)),g("p",$e,"欢迎回来，"+B((f=i(_).user)==null?void 0:f.display_name),1)]),c(i(ue),{cols:4,"x-gap":16,"y-gap":16,responsive:"screen","collapsed-rows":1,"item-responsive":""},{default:a(()=>[c(i(L),{span:"4 m:2 l:1"},{default:a(()=>[c(i(N),{class:"metric-card",bordered:!1},{default:a(()=>[b.value?(u(),p(i(T),{key:0,text:"",repeat:2})):(u(),p(i(M),{key:1,label:"审阅总数",value:k.total_reviews},{prefix:a(()=>[...r[5]||(r[5]=[g("span",{class:"metric-icon"},"📄",-1)])]),_:1},8,["value"]))]),_:1})]),_:1}),c(i(L),{span:"4 m:2 l:1"},{default:a(()=>[c(i(N),{class:"metric-card metric-card--danger",bordered:!1},{default:a(()=>[b.value?(u(),p(i(T),{key:0,text:"",repeat:2})):(u(),p(i(M),{key:1,label:"高风险项",value:k.high_risk_count},{prefix:a(()=>[...r[6]||(r[6]=[g("span",{class:"metric-icon"},"🚨",-1)])]),_:1},8,["value"]))]),_:1})]),_:1}),c(i(L),{span:"4 m:2 l:1"},{default:a(()=>[c(i(N),{class:"metric-card metric-card--warning",bordered:!1},{default:a(()=>[b.value?(u(),p(i(T),{key:0,text:"",repeat:2})):(u(),p(i(M),{key:1,label:"待处理工单",value:y.open_items},{prefix:a(()=>[...r[7]||(r[7]=[g("span",{class:"metric-icon"},"🔧",-1)])]),_:1},8,["value"]))]),_:1})]),_:1}),c(i(L),{span:"4 m:2 l:1"},{default:a(()=>[c(i(N),{class:"metric-card metric-card--overdue",bordered:!1},{default:a(()=>[b.value?(u(),p(i(T),{key:0,text:"",repeat:2})):(u(),p(i(M),{key:1,label:"逾期项",value:y.overdue_items},{prefix:a(()=>[...r[8]||(r[8]=[g("span",{class:"metric-icon"},"⏰",-1)])]),_:1},8,["value"]))]),_:1})]),_:1})]),_:1}),g("div",Ce,[c(i(I),{type:"primary",size:"large",onClick:r[0]||(r[0]=l=>i(e).push("/reviews/new")),class:"action-btn"},{icon:a(()=>[...r[9]||(r[9]=[g("span",null,"✨",-1)])]),default:a(()=>[r[10]||(r[10]=R(" 新建审阅 ",-1))]),_:1}),c(i(I),{size:"large",onClick:r[1]||(r[1]=l=>i(e).push("/work")),class:"action-btn"},{icon:a(()=>[...r[11]||(r[11]=[g("span",null,"🔧",-1)])]),default:a(()=>[r[12]||(r[12]=R(" 查看处置中心 ",-1))]),_:1})]),c(i(N),{title:"最近审阅",bordered:!1,class:"recent-card"},{"header-extra":a(()=>[c(i(I),{text:"",type:"primary",onClick:r[2]||(r[2]=l=>i(e).push("/reviews"))},{default:a(()=>[...r[13]||(r[13]=[R(" 查看全部 ",-1)])]),_:1})]),default:a(()=>[b.value?(u(),p(i(T),{key:0,height:200})):(u(),H(A,{key:1},[v.value.length===0?(u(),p(i(me),{key:0,description:"暂无审阅记录，点击「新建审阅」开始",class:"empty-state"},{extra:a(()=>[c(i(I),{type:"primary",size:"small",onClick:r[3]||(r[3]=l=>i(e).push("/reviews/new"))},{default:a(()=>[...r[14]||(r[14]=[R(" 新建审阅 ",-1)])]),_:1})]),_:1})):(u(),p(i(pe),{key:1,hoverable:"",clickable:""},{default:a(()=>[(u(!0),H(A,null,ce(v.value,l=>(u(),p(i(be),{key:l.id,onClick:z=>i(e).push(`/reviews/${l.id}`)},{prefix:a(()=>[c(i(q),{type:w(l.risk_level),size:"small",round:""},{default:a(()=>[R(B(o(l.risk_level)),1)]),_:2},1032,["type"])]),suffix:a(()=>[g("div",ze,[c(i(q),{type:C(l.status),size:"tiny",bordered:!1},{default:a(()=>[R(B(S(l.status)),1)]),_:2},1032,["type"]),g("span",Re,B(D(l.created_at)),1)])]),default:a(()=>[c(i(ye),{title:l.name,description:l.summary||"暂无摘要"},null,8,["title","description"])]),_:2},1032,["onClick"]))),128))]),_:1}))],64))]),_:1})])}}}),Ve=fe(Se,[["__scopeId","data-v-1eb982d5"]]);export{Ve as default};
