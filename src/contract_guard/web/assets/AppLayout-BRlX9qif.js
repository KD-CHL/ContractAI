import{d as j,x as u,y as Z,z as h,A as vo,C as y,D as mo,E as f,F as $e,G as ho,V as Fe,H as Q,I as D,J as ee,v as x,r as M,o as we,K as ge,L as fo,M as po,N as G,O as go,P as bo,Q as xo,R as O,S as Co,T as X,U as le,W as Me,X as yo,Y as zo,Z as wo,_ as So,$ as _e,a0 as je,a1 as Ke,a2 as Ve,a3 as U,a4 as re,a5 as Io,a6 as J,a7 as Se,a8 as be,a9 as Ro,aa as he,ab as Po,ac as To,ad as ko,ae as No,af as _o,j as Y,e as ne,f as H,w as F,m as me,t as ie,h as $,B as xe,b as W,u as Ao,c as Ae,g as de,ag as Oe,ah as Oo,k as Bo,i as Ho,l as Eo}from"./index-JKv9wurx.js";import{u as Lo}from"./usePermission-Cf4Ey8z-.js";import{N as De}from"./Tooltip-D2e98BW4.js";import{_ as Ue,u as $o}from"./_plugin-vue_export-helper-nsZAGd0n.js";import{C as Fo}from"./ChevronRight-CY1skER3.js";import{f as fe,u as Ce}from"./get-S4-LhD0z.js";import{N as Ge}from"./Dropdown-BjvqItI_.js";import{V as Mo,c as pe}from"./Icon-DtLVfqeE.js";import{u as jo}from"./Popover-hxiDDyOr.js";import{N as Ko,a as Vo}from"./DrawerContent-DyT4JXsY.js";import{N as Do}from"./Divider-Cebv5Ywv.js";import{i as Uo,o as Go}from"./utils-BdAIMMzD.js";import{t as Wo}from"./Tag-2dIdwluN.js";import"./happens-in-CM8LO42l.js";import"./create-ref-setter-C4J8sofl.js";import"./next-frame-once-C5Ksf8W7.js";const qo=j({name:"ChevronDownFilled",render(){return u("svg",{viewBox:"0 0 16 16",fill:"none",xmlns:"http://www.w3.org/2000/svg"},u("path",{d:"M3.20041 5.73966C3.48226 5.43613 3.95681 5.41856 4.26034 5.70041L8 9.22652L11.7397 5.70041C12.0432 5.41856 12.5177 5.43613 12.7996 5.73966C13.0815 6.0432 13.0639 6.51775 12.7603 6.7996L8.51034 10.7996C8.22258 11.0668 7.77743 11.0668 7.48967 10.7996L3.23966 6.7996C2.93613 6.51775 2.91856 6.0432 3.20041 5.73966Z",fill:"currentColor"}))}}),Yo=Z("n-avatar-group"),Xo=h("avatar",`
 width: var(--n-merged-size);
 height: var(--n-merged-size);
 color: #FFF;
 font-size: var(--n-font-size);
 display: inline-flex;
 position: relative;
 overflow: hidden;
 text-align: center;
 border: var(--n-border);
 border-radius: var(--n-border-radius);
 --n-merged-color: var(--n-color);
 background-color: var(--n-merged-color);
 transition:
 border-color .3s var(--n-bezier),
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier);
`,[vo(y("&","--n-merged-color: var(--n-color-modal);")),mo(y("&","--n-merged-color: var(--n-color-popover);")),y("img",`
 width: 100%;
 height: 100%;
 `),f("text",`
 white-space: nowrap;
 display: inline-block;
 position: absolute;
 left: 50%;
 top: 50%;
 `),h("icon",`
 vertical-align: bottom;
 font-size: calc(var(--n-merged-size) - 6px);
 `),f("text","line-height: 1.25")]),Zo=Object.assign(Object.assign({},D.props),{size:[String,Number],src:String,circle:{type:Boolean,default:void 0},objectFit:String,round:{type:Boolean,default:void 0},bordered:{type:Boolean,default:void 0},onError:Function,fallbackSrc:String,intersectionObserverOptions:Object,lazy:Boolean,onLoad:Function,renderPlaceholder:Function,renderFallback:Function,imgProps:Object,color:String}),Jo=j({name:"Avatar",props:Zo,slots:Object,setup(e){const{mergedClsPrefixRef:o,inlineThemeDisabled:t}=Q(e),l=M(!1);let a=null;const n=M(null),d=M(null),p=()=>{const{value:b}=n;if(b&&(a===null||a!==b.innerHTML)){a=b.innerHTML;const{value:R}=d;if(R){const{offsetWidth:B,offsetHeight:v}=R,{offsetWidth:c,offsetHeight:S}=b,E=.9,V=Math.min(B/c*E,v/S*E,1);b.style.transform=`translateX(-50%) translateY(-50%) scale(${V})`}}},s=G(Yo,null),m=x(()=>{const{size:b}=e;if(b)return b;const{size:R}=s||{};return R||"medium"}),N=D("Avatar","-avatar",Xo,go,e,o),k=G(Wo,null),g=x(()=>{if(s)return!0;const{round:b,circle:R}=e;return b!==void 0||R!==void 0?b||R:k?k.roundRef.value:!1}),z=x(()=>s?!0:e.bordered||!1),_=x(()=>{const b=m.value,R=g.value,B=z.value,{color:v}=e,{self:{borderRadius:c,fontSize:S,color:E,border:V,colorModal:oe,colorPopover:K},common:{cubicBezierEaseInOut:se}}=N.value;let te;return typeof b=="number"?te=`${b}px`:te=N.value.self[bo("height",b)],{"--n-font-size":S,"--n-border":B?V:"none","--n-border-radius":R?"50%":c,"--n-color":v||E,"--n-color-modal":v||oe,"--n-color-popover":v||K,"--n-bezier":se,"--n-merged-size":`var(--n-avatar-size-override, ${te})`}}),w=t?ee("avatar",x(()=>{const b=m.value,R=g.value,B=z.value,{color:v}=e;let c="";return b&&(typeof b=="number"?c+=`a${b}`:c+=b[0]),R&&(c+="b"),B&&(c+="c"),v&&(c+=xo(v)),c}),_,e):void 0,P=M(!e.lazy);we(()=>{if(e.lazy&&e.intersectionObserverOptions){let b;const R=ge(()=>{b==null||b(),b=void 0,e.lazy&&(b=Go(d.value,e.intersectionObserverOptions,P))});fo(()=>{R(),b==null||b()})}}),po(()=>{var b;return e.src||((b=e.imgProps)===null||b===void 0?void 0:b.src)},()=>{l.value=!1});const A=M(!e.lazy);return{textRef:n,selfRef:d,mergedRoundRef:g,mergedClsPrefix:o,fitTextTransform:p,cssVars:t?void 0:_,themeClass:w==null?void 0:w.themeClass,onRender:w==null?void 0:w.onRender,hasLoadError:l,shouldStartLoading:P,loaded:A,mergedOnError:b=>{if(!P.value)return;l.value=!0;const{onError:R,imgProps:{onError:B}={}}=e;R==null||R(b),B==null||B(b)},mergedOnLoad:b=>{const{onLoad:R,imgProps:{onLoad:B}={}}=e;R==null||R(b),B==null||B(b),A.value=!0}}},render(){var e,o;const{$slots:t,src:l,mergedClsPrefix:a,lazy:n,onRender:d,loaded:p,hasLoadError:s,imgProps:m={}}=this;d==null||d();let N;const k=!p&&!s&&(this.renderPlaceholder?this.renderPlaceholder():(o=(e=this.$slots).placeholder)===null||o===void 0?void 0:o.call(e));return this.hasLoadError?N=this.renderFallback?this.renderFallback():$e(t.fallback,()=>[u("img",{src:this.fallbackSrc,style:{objectFit:this.objectFit}})]):N=ho(t.default,g=>{if(g)return u(Fe,{onResize:this.fitTextTransform},{default:()=>u("span",{ref:"textRef",class:`${a}-avatar__text`},g)});if(l||m.src){const z=this.src||m.src;return u("img",Object.assign(Object.assign({},m),{loading:Uo&&!this.intersectionObserverOptions&&n?"lazy":"eager",src:n&&this.intersectionObserverOptions?this.shouldStartLoading?z:void 0:z,"data-image-src":z,onLoad:this.mergedOnLoad,onError:this.mergedOnError,style:[m.style||"",{objectFit:this.objectFit},k?{height:"0",width:"0",visibility:"hidden",position:"absolute"}:""]}))}}),u("span",{ref:"selfRef",class:[`${a}-avatar`,this.themeClass],style:this.cssVars},N,n&&k)}}),Qo=h("breadcrumb",`
 white-space: nowrap;
 cursor: default;
 line-height: var(--n-item-line-height);
`,[y("ul",`
 list-style: none;
 padding: 0;
 margin: 0;
 `),y("a",`
 color: inherit;
 text-decoration: inherit;
 `),h("breadcrumb-item",`
 font-size: var(--n-font-size);
 transition: color .3s var(--n-bezier);
 display: inline-flex;
 align-items: center;
 `,[h("icon",`
 font-size: 18px;
 vertical-align: -.2em;
 transition: color .3s var(--n-bezier);
 color: var(--n-item-text-color);
 `),y("&:not(:last-child)",[O("clickable",[f("link",`
 cursor: pointer;
 `,[y("&:hover",`
 background-color: var(--n-item-color-hover);
 `),y("&:active",`
 background-color: var(--n-item-color-pressed); 
 `)])])]),f("link",`
 padding: 4px;
 border-radius: var(--n-item-border-radius);
 transition:
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier);
 color: var(--n-item-text-color);
 position: relative;
 `,[y("&:hover",`
 color: var(--n-item-text-color-hover);
 `,[h("icon",`
 color: var(--n-item-text-color-hover);
 `)]),y("&:active",`
 color: var(--n-item-text-color-pressed);
 `,[h("icon",`
 color: var(--n-item-text-color-pressed);
 `)])]),f("separator",`
 margin: 0 8px;
 color: var(--n-separator-color);
 transition: color .3s var(--n-bezier);
 user-select: none;
 -webkit-user-select: none;
 `),y("&:last-child",[f("link",`
 font-weight: var(--n-font-weight-active);
 cursor: unset;
 color: var(--n-item-text-color-active);
 `,[h("icon",`
 color: var(--n-item-text-color-active);
 `)]),f("separator",`
 display: none;
 `)])])]),We=Z("n-breadcrumb"),et=Object.assign(Object.assign({},D.props),{separator:{type:String,default:"/"}}),ot=j({name:"Breadcrumb",props:et,setup(e){const{mergedClsPrefixRef:o,inlineThemeDisabled:t}=Q(e),l=D("Breadcrumb","-breadcrumb",Qo,Co,e,o);X(We,{separatorRef:le(e,"separator"),mergedClsPrefixRef:o});const a=x(()=>{const{common:{cubicBezierEaseInOut:d},self:{separatorColor:p,itemTextColor:s,itemTextColorHover:m,itemTextColorPressed:N,itemTextColorActive:k,fontSize:g,fontWeightActive:z,itemBorderRadius:_,itemColorHover:w,itemColorPressed:P,itemLineHeight:A}}=l.value;return{"--n-font-size":g,"--n-bezier":d,"--n-item-text-color":s,"--n-item-text-color-hover":m,"--n-item-text-color-pressed":N,"--n-item-text-color-active":k,"--n-separator-color":p,"--n-item-color-hover":w,"--n-item-color-pressed":P,"--n-item-border-radius":_,"--n-font-weight-active":z,"--n-item-line-height":A}}),n=t?ee("breadcrumb",void 0,a,e):void 0;return{mergedClsPrefix:o,cssVars:t?void 0:a,themeClass:n==null?void 0:n.themeClass,onRender:n==null?void 0:n.onRender}},render(){var e;return(e=this.onRender)===null||e===void 0||e.call(this),u("nav",{class:[`${this.mergedClsPrefix}-breadcrumb`,this.themeClass],style:this.cssVars,"aria-label":"Breadcrumb"},u("ul",null,this.$slots))}});function tt(e=yo?window:null){const o=()=>{const{hash:a,host:n,hostname:d,href:p,origin:s,pathname:m,port:N,protocol:k,search:g}=(e==null?void 0:e.location)||{};return{hash:a,host:n,hostname:d,href:p,origin:s,pathname:m,port:N,protocol:k,search:g}},t=M(o()),l=()=>{t.value=o()};return we(()=>{e&&(e.addEventListener("popstate",l),e.addEventListener("hashchange",l))}),Me(()=>{e&&(e.removeEventListener("popstate",l),e.removeEventListener("hashchange",l))}),t}const rt={separator:String,href:String,clickable:{type:Boolean,default:!0},showSeparator:{type:Boolean,default:!0},onClick:Function},Be=j({name:"BreadcrumbItem",props:rt,slots:Object,setup(e,{slots:o}){const t=G(We,null);if(!t)return()=>null;const{separatorRef:l,mergedClsPrefixRef:a}=t,n=tt(),d=x(()=>e.href?"a":"span"),p=x(()=>n.value.href===e.href?"location":null);return()=>{const{value:s}=a;return u("li",{class:[`${s}-breadcrumb-item`,e.clickable&&`${s}-breadcrumb-item--clickable`]},u(d.value,{class:`${s}-breadcrumb-item__link`,"aria-current":p.value,href:e.href,onClick:e.onClick},o),e.showSeparator&&u("span",{class:`${s}-breadcrumb-item__separator`,"aria-hidden":"true"},$e(o.separator,()=>{var m;return[(m=e.separator)!==null&&m!==void 0?m:l.value]})))}}});function nt(e){const{baseColor:o,textColor2:t,bodyColor:l,cardColor:a,dividerColor:n,actionColor:d,scrollbarColor:p,scrollbarColorHover:s,invertedColor:m}=e;return{textColor:t,textColorInverted:"#FFF",color:l,colorEmbedded:d,headerColor:a,headerColorInverted:m,footerColor:d,footerColorInverted:m,headerBorderColor:n,headerBorderColorInverted:m,footerBorderColor:n,footerBorderColorInverted:m,siderBorderColor:n,siderBorderColorInverted:m,siderColor:a,siderColorInverted:m,siderToggleButtonBorder:`1px solid ${n}`,siderToggleButtonColor:o,siderToggleButtonIconColor:t,siderToggleButtonIconColorInverted:t,siderToggleBarColor:_e(l,p),siderToggleBarColorHover:_e(l,s),__invertScrollbar:"true"}}const Ie=zo({name:"Layout",common:So,peers:{Scrollbar:wo},self:nt}),qe=Z("n-layout-sider"),Re={type:String,default:"static"},it=h("layout",`
 color: var(--n-text-color);
 background-color: var(--n-color);
 box-sizing: border-box;
 position: relative;
 z-index: auto;
 flex: auto;
 overflow: hidden;
 transition:
 box-shadow .3s var(--n-bezier),
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier);
`,[h("layout-scroll-container",`
 overflow-x: hidden;
 box-sizing: border-box;
 height: 100%;
 `),O("absolute-positioned",`
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 `)]),lt={embedded:Boolean,position:Re,nativeScrollbar:{type:Boolean,default:!0},scrollbarProps:Object,onScroll:Function,contentClass:String,contentStyle:{type:[String,Object],default:""},hasSider:Boolean,siderPlacement:{type:String,default:"left"}},Ye=Z("n-layout");function Xe(e){return j({name:e?"LayoutContent":"Layout",props:Object.assign(Object.assign({},D.props),lt),setup(o){const t=M(null),l=M(null),{mergedClsPrefixRef:a,inlineThemeDisabled:n}=Q(o),d=D("Layout","-layout",it,Ie,o,a);function p(w,P){if(o.nativeScrollbar){const{value:A}=t;A&&(P===void 0?A.scrollTo(w):A.scrollTo(w,P))}else{const{value:A}=l;A&&A.scrollTo(w,P)}}X(Ye,o);let s=0,m=0;const N=w=>{var P;const A=w.target;s=A.scrollLeft,m=A.scrollTop,(P=o.onScroll)===null||P===void 0||P.call(o,w)};Ke(()=>{if(o.nativeScrollbar){const w=t.value;w&&(w.scrollTop=m,w.scrollLeft=s)}});const k={display:"flex",flexWrap:"nowrap",width:"100%",flexDirection:"row"},g={scrollTo:p},z=x(()=>{const{common:{cubicBezierEaseInOut:w},self:P}=d.value;return{"--n-bezier":w,"--n-color":o.embedded?P.colorEmbedded:P.color,"--n-text-color":P.textColor}}),_=n?ee("layout",x(()=>o.embedded?"e":""),z,o):void 0;return Object.assign({mergedClsPrefix:a,scrollableElRef:t,scrollbarInstRef:l,hasSiderStyle:k,mergedTheme:d,handleNativeElScroll:N,cssVars:n?void 0:z,themeClass:_==null?void 0:_.themeClass,onRender:_==null?void 0:_.onRender},g)},render(){var o;const{mergedClsPrefix:t,hasSider:l}=this;(o=this.onRender)===null||o===void 0||o.call(this);const a=l?this.hasSiderStyle:void 0,n=[this.themeClass,e&&`${t}-layout-content`,`${t}-layout`,`${t}-layout--${this.position}-positioned`];return u("div",{class:n,style:this.cssVars},this.nativeScrollbar?u("div",{ref:"scrollableElRef",class:[`${t}-layout-scroll-container`,this.contentClass],style:[this.contentStyle,a],onScroll:this.handleNativeElScroll},this.$slots):u(je,Object.assign({},this.scrollbarProps,{onScroll:this.onScroll,ref:"scrollbarInstRef",theme:this.mergedTheme.peers.Scrollbar,themeOverrides:this.mergedTheme.peerOverrides.Scrollbar,contentClass:this.contentClass,contentStyle:[this.contentStyle,a]}),this.$slots))}})}const He=Xe(!1),at=Xe(!0),st=h("layout-header",`
 transition:
 color .3s var(--n-bezier),
 background-color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 box-sizing: border-box;
 width: 100%;
 background-color: var(--n-color);
 color: var(--n-text-color);
`,[O("absolute-positioned",`
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 `),O("bordered",`
 border-bottom: solid 1px var(--n-border-color);
 `)]),ct={position:Re,inverted:Boolean,bordered:{type:Boolean,default:!1}},dt=j({name:"LayoutHeader",props:Object.assign(Object.assign({},D.props),ct),setup(e){const{mergedClsPrefixRef:o,inlineThemeDisabled:t}=Q(e),l=D("Layout","-layout-header",st,Ie,e,o),a=x(()=>{const{common:{cubicBezierEaseInOut:d},self:p}=l.value,s={"--n-bezier":d};return e.inverted?(s["--n-color"]=p.headerColorInverted,s["--n-text-color"]=p.textColorInverted,s["--n-border-color"]=p.headerBorderColorInverted):(s["--n-color"]=p.headerColor,s["--n-text-color"]=p.textColor,s["--n-border-color"]=p.headerBorderColor),s}),n=t?ee("layout-header",x(()=>e.inverted?"a":"b"),a,e):void 0;return{mergedClsPrefix:o,cssVars:t?void 0:a,themeClass:n==null?void 0:n.themeClass,onRender:n==null?void 0:n.onRender}},render(){var e;const{mergedClsPrefix:o}=this;return(e=this.onRender)===null||e===void 0||e.call(this),u("div",{class:[`${o}-layout-header`,this.themeClass,this.position&&`${o}-layout-header--${this.position}-positioned`,this.bordered&&`${o}-layout-header--bordered`],style:this.cssVars},this.$slots)}}),ut=h("layout-sider",`
 flex-shrink: 0;
 box-sizing: border-box;
 position: relative;
 z-index: 1;
 color: var(--n-text-color);
 transition:
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier),
 min-width .3s var(--n-bezier),
 max-width .3s var(--n-bezier),
 transform .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 background-color: var(--n-color);
 display: flex;
 justify-content: flex-end;
`,[O("bordered",[f("border",`
 content: "";
 position: absolute;
 top: 0;
 bottom: 0;
 width: 1px;
 background-color: var(--n-border-color);
 transition: background-color .3s var(--n-bezier);
 `)]),f("left-placement",[O("bordered",[f("border",`
 right: 0;
 `)])]),O("right-placement",`
 justify-content: flex-start;
 `,[O("bordered",[f("border",`
 left: 0;
 `)]),O("collapsed",[h("layout-toggle-button",[h("base-icon",`
 transform: rotate(180deg);
 `)]),h("layout-toggle-bar",[y("&:hover",[f("top",{transform:"rotate(-12deg) scale(1.15) translateY(-2px)"}),f("bottom",{transform:"rotate(12deg) scale(1.15) translateY(2px)"})])])]),h("layout-toggle-button",`
 left: 0;
 transform: translateX(-50%) translateY(-50%);
 `,[h("base-icon",`
 transform: rotate(0);
 `)]),h("layout-toggle-bar",`
 left: -28px;
 transform: rotate(180deg);
 `,[y("&:hover",[f("top",{transform:"rotate(12deg) scale(1.15) translateY(-2px)"}),f("bottom",{transform:"rotate(-12deg) scale(1.15) translateY(2px)"})])])]),O("collapsed",[h("layout-toggle-bar",[y("&:hover",[f("top",{transform:"rotate(-12deg) scale(1.15) translateY(-2px)"}),f("bottom",{transform:"rotate(12deg) scale(1.15) translateY(2px)"})])]),h("layout-toggle-button",[h("base-icon",`
 transform: rotate(0);
 `)])]),h("layout-toggle-button",`
 transition:
 color .3s var(--n-bezier),
 right .3s var(--n-bezier),
 left .3s var(--n-bezier),
 border-color .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 cursor: pointer;
 width: 24px;
 height: 24px;
 position: absolute;
 top: 50%;
 right: 0;
 border-radius: 50%;
 display: flex;
 align-items: center;
 justify-content: center;
 font-size: 18px;
 color: var(--n-toggle-button-icon-color);
 border: var(--n-toggle-button-border);
 background-color: var(--n-toggle-button-color);
 box-shadow: 0 2px 4px 0px rgba(0, 0, 0, .06);
 transform: translateX(50%) translateY(-50%);
 z-index: 1;
 `,[h("base-icon",`
 transition: transform .3s var(--n-bezier);
 transform: rotate(180deg);
 `)]),h("layout-toggle-bar",`
 cursor: pointer;
 height: 72px;
 width: 32px;
 position: absolute;
 top: calc(50% - 36px);
 right: -28px;
 `,[f("top, bottom",`
 position: absolute;
 width: 4px;
 border-radius: 2px;
 height: 38px;
 left: 14px;
 transition: 
 background-color .3s var(--n-bezier),
 transform .3s var(--n-bezier);
 `),f("bottom",`
 position: absolute;
 top: 34px;
 `),y("&:hover",[f("top",{transform:"rotate(12deg) scale(1.15) translateY(-2px)"}),f("bottom",{transform:"rotate(-12deg) scale(1.15) translateY(2px)"})]),f("top, bottom",{backgroundColor:"var(--n-toggle-bar-color)"}),y("&:hover",[f("top, bottom",{backgroundColor:"var(--n-toggle-bar-color-hover)"})])]),f("border",`
 position: absolute;
 top: 0;
 right: 0;
 bottom: 0;
 width: 1px;
 transition: background-color .3s var(--n-bezier);
 `),h("layout-sider-scroll-container",`
 flex-grow: 1;
 flex-shrink: 0;
 box-sizing: border-box;
 height: 100%;
 opacity: 0;
 transition: opacity .3s var(--n-bezier);
 max-width: 100%;
 `),O("show-content",[h("layout-sider-scroll-container",{opacity:1})]),O("absolute-positioned",`
 position: absolute;
 left: 0;
 top: 0;
 bottom: 0;
 `)]),vt=j({props:{clsPrefix:{type:String,required:!0},onClick:Function},render(){const{clsPrefix:e}=this;return u("div",{onClick:this.onClick,class:`${e}-layout-toggle-bar`},u("div",{class:`${e}-layout-toggle-bar__top`}),u("div",{class:`${e}-layout-toggle-bar__bottom`}))}}),mt=j({name:"LayoutToggleButton",props:{clsPrefix:{type:String,required:!0},onClick:Function},render(){const{clsPrefix:e}=this;return u("div",{class:`${e}-layout-toggle-button`,onClick:this.onClick},u(Ve,{clsPrefix:e},{default:()=>u(Fo,null)}))}}),ht={position:Re,bordered:Boolean,collapsedWidth:{type:Number,default:48},width:{type:[Number,String],default:272},contentClass:String,contentStyle:{type:[String,Object],default:""},collapseMode:{type:String,default:"transform"},collapsed:{type:Boolean,default:void 0},defaultCollapsed:Boolean,showCollapsedContent:{type:Boolean,default:!0},showTrigger:{type:[Boolean,String],default:!1},nativeScrollbar:{type:Boolean,default:!0},inverted:Boolean,scrollbarProps:Object,triggerClass:String,triggerStyle:[String,Object],collapsedTriggerClass:String,collapsedTriggerStyle:[String,Object],"onUpdate:collapsed":[Function,Array],onUpdateCollapsed:[Function,Array],onAfterEnter:Function,onAfterLeave:Function,onExpand:[Function,Array],onCollapse:[Function,Array],onScroll:Function},ft=j({name:"LayoutSider",props:Object.assign(Object.assign({},D.props),ht),setup(e){const o=G(Ye),t=M(null),l=M(null),a=M(e.defaultCollapsed),n=Ce(le(e,"collapsed"),a),d=x(()=>fe(n.value?e.collapsedWidth:e.width)),p=x(()=>e.collapseMode!=="transform"?{}:{minWidth:fe(e.width)}),s=x(()=>o?o.siderPlacement:"left");function m(v,c){if(e.nativeScrollbar){const{value:S}=t;S&&(c===void 0?S.scrollTo(v):S.scrollTo(v,c))}else{const{value:S}=l;S&&S.scrollTo(v,c)}}function N(){const{"onUpdate:collapsed":v,onUpdateCollapsed:c,onExpand:S,onCollapse:E}=e,{value:V}=n;c&&U(c,!V),v&&U(v,!V),a.value=!V,V?S&&U(S):E&&U(E)}let k=0,g=0;const z=v=>{var c;const S=v.target;k=S.scrollLeft,g=S.scrollTop,(c=e.onScroll)===null||c===void 0||c.call(e,v)};Ke(()=>{if(e.nativeScrollbar){const v=t.value;v&&(v.scrollTop=g,v.scrollLeft=k)}}),X(qe,{collapsedRef:n,collapseModeRef:le(e,"collapseMode")});const{mergedClsPrefixRef:_,inlineThemeDisabled:w}=Q(e),P=D("Layout","-layout-sider",ut,Ie,e,_);function A(v){var c,S;v.propertyName==="max-width"&&(n.value?(c=e.onAfterLeave)===null||c===void 0||c.call(e):(S=e.onAfterEnter)===null||S===void 0||S.call(e))}const b={scrollTo:m},R=x(()=>{const{common:{cubicBezierEaseInOut:v},self:c}=P.value,{siderToggleButtonColor:S,siderToggleButtonBorder:E,siderToggleBarColor:V,siderToggleBarColorHover:oe}=c,K={"--n-bezier":v,"--n-toggle-button-color":S,"--n-toggle-button-border":E,"--n-toggle-bar-color":V,"--n-toggle-bar-color-hover":oe};return e.inverted?(K["--n-color"]=c.siderColorInverted,K["--n-text-color"]=c.textColorInverted,K["--n-border-color"]=c.siderBorderColorInverted,K["--n-toggle-button-icon-color"]=c.siderToggleButtonIconColorInverted,K.__invertScrollbar=c.__invertScrollbar):(K["--n-color"]=c.siderColor,K["--n-text-color"]=c.textColor,K["--n-border-color"]=c.siderBorderColor,K["--n-toggle-button-icon-color"]=c.siderToggleButtonIconColor),K}),B=w?ee("layout-sider",x(()=>e.inverted?"a":"b"),R,e):void 0;return Object.assign({scrollableElRef:t,scrollbarInstRef:l,mergedClsPrefix:_,mergedTheme:P,styleMaxWidth:d,mergedCollapsed:n,scrollContainerStyle:p,siderPlacement:s,handleNativeElScroll:z,handleTransitionend:A,handleTriggerClick:N,inlineThemeDisabled:w,cssVars:R,themeClass:B==null?void 0:B.themeClass,onRender:B==null?void 0:B.onRender},b)},render(){var e;const{mergedClsPrefix:o,mergedCollapsed:t,showTrigger:l}=this;return(e=this.onRender)===null||e===void 0||e.call(this),u("aside",{class:[`${o}-layout-sider`,this.themeClass,`${o}-layout-sider--${this.position}-positioned`,`${o}-layout-sider--${this.siderPlacement}-placement`,this.bordered&&`${o}-layout-sider--bordered`,t&&`${o}-layout-sider--collapsed`,(!t||this.showCollapsedContent)&&`${o}-layout-sider--show-content`],onTransitionend:this.handleTransitionend,style:[this.inlineThemeDisabled?void 0:this.cssVars,{maxWidth:this.styleMaxWidth,width:fe(this.width)}]},this.nativeScrollbar?u("div",{class:[`${o}-layout-sider-scroll-container`,this.contentClass],onScroll:this.handleNativeElScroll,style:[this.scrollContainerStyle,{overflow:"auto"},this.contentStyle],ref:"scrollableElRef"},this.$slots):u(je,Object.assign({},this.scrollbarProps,{onScroll:this.onScroll,ref:"scrollbarInstRef",style:this.scrollContainerStyle,contentStyle:this.contentStyle,contentClass:this.contentClass,theme:this.mergedTheme.peers.Scrollbar,themeOverrides:this.mergedTheme.peerOverrides.Scrollbar,builtinThemeOverrides:this.inverted&&this.cssVars.__invertScrollbar==="true"?{colorHover:"rgba(255, 255, 255, .4)",color:"rgba(255, 255, 255, .3)"}:void 0}),this.$slots),l?l==="bar"?u(vt,{clsPrefix:o,class:t?this.collapsedTriggerClass:this.triggerClass,style:t?this.collapsedTriggerStyle:this.triggerStyle,onClick:this.handleTriggerClick}):u(mt,{clsPrefix:o,class:t?this.collapsedTriggerClass:this.triggerClass,style:t?this.collapsedTriggerStyle:this.triggerStyle,onClick:this.handleTriggerClick}):null,this.bordered?u("div",{class:`${o}-layout-sider__border`}):null)}}),ae=Z("n-menu"),Ze=Z("n-submenu"),Pe=Z("n-menu-item-group"),Ee=[y("&::before","background-color: var(--n-item-color-hover);"),f("arrow",`
 color: var(--n-arrow-color-hover);
 `),f("icon",`
 color: var(--n-item-icon-color-hover);
 `),h("menu-item-content-header",`
 color: var(--n-item-text-color-hover);
 `,[y("a",`
 color: var(--n-item-text-color-hover);
 `),f("extra",`
 color: var(--n-item-text-color-hover);
 `)])],Le=[f("icon",`
 color: var(--n-item-icon-color-hover-horizontal);
 `),h("menu-item-content-header",`
 color: var(--n-item-text-color-hover-horizontal);
 `,[y("a",`
 color: var(--n-item-text-color-hover-horizontal);
 `),f("extra",`
 color: var(--n-item-text-color-hover-horizontal);
 `)])],pt=y([h("menu",`
 background-color: var(--n-color);
 color: var(--n-item-text-color);
 overflow: hidden;
 transition: background-color .3s var(--n-bezier);
 box-sizing: border-box;
 font-size: var(--n-font-size);
 padding-bottom: 6px;
 `,[O("horizontal",`
 max-width: 100%;
 width: 100%;
 display: flex;
 overflow: hidden;
 padding-bottom: 0;
 `,[h("submenu","margin: 0;"),h("menu-item","margin: 0;"),h("menu-item-content",`
 padding: 0 20px;
 border-bottom: 2px solid #0000;
 `,[y("&::before","display: none;"),O("selected","border-bottom: 2px solid var(--n-border-color-horizontal)")]),h("menu-item-content",[O("selected",[f("icon","color: var(--n-item-icon-color-active-horizontal);"),h("menu-item-content-header",`
 color: var(--n-item-text-color-active-horizontal);
 `,[y("a","color: var(--n-item-text-color-active-horizontal);"),f("extra","color: var(--n-item-text-color-active-horizontal);")])]),O("child-active",`
 border-bottom: 2px solid var(--n-border-color-horizontal);
 `,[h("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-horizontal);
 `,[y("a",`
 color: var(--n-item-text-color-child-active-horizontal);
 `),f("extra",`
 color: var(--n-item-text-color-child-active-horizontal);
 `)]),f("icon",`
 color: var(--n-item-icon-color-child-active-horizontal);
 `)]),re("disabled",[re("selected, child-active",[y("&:focus-within",Le)]),O("selected",[q(null,[f("icon","color: var(--n-item-icon-color-active-hover-horizontal);"),h("menu-item-content-header",`
 color: var(--n-item-text-color-active-hover-horizontal);
 `,[y("a","color: var(--n-item-text-color-active-hover-horizontal);"),f("extra","color: var(--n-item-text-color-active-hover-horizontal);")])])]),O("child-active",[q(null,[f("icon","color: var(--n-item-icon-color-child-active-hover-horizontal);"),h("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-hover-horizontal);
 `,[y("a","color: var(--n-item-text-color-child-active-hover-horizontal);"),f("extra","color: var(--n-item-text-color-child-active-hover-horizontal);")])])]),q("border-bottom: 2px solid var(--n-border-color-horizontal);",Le)]),h("menu-item-content-header",[y("a","color: var(--n-item-text-color-horizontal);")])])]),re("responsive",[h("menu-item-content-header",`
 overflow: hidden;
 text-overflow: ellipsis;
 `)]),O("collapsed",[h("menu-item-content",[O("selected",[y("&::before",`
 background-color: var(--n-item-color-active-collapsed) !important;
 `)]),h("menu-item-content-header","opacity: 0;"),f("arrow","opacity: 0;"),f("icon","color: var(--n-item-icon-color-collapsed);")])]),h("menu-item",`
 height: var(--n-item-height);
 margin-top: 6px;
 position: relative;
 `),h("menu-item-content",`
 box-sizing: border-box;
 line-height: 1.75;
 height: 100%;
 display: grid;
 grid-template-areas: "icon content arrow";
 grid-template-columns: auto 1fr auto;
 align-items: center;
 cursor: pointer;
 position: relative;
 padding-right: 18px;
 transition:
 background-color .3s var(--n-bezier),
 padding-left .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 `,[y("> *","z-index: 1;"),y("&::before",`
 z-index: auto;
 content: "";
 background-color: #0000;
 position: absolute;
 left: 8px;
 right: 8px;
 top: 0;
 bottom: 0;
 pointer-events: none;
 border-radius: var(--n-border-radius);
 transition: background-color .3s var(--n-bezier);
 `),O("disabled",`
 opacity: .45;
 cursor: not-allowed;
 `),O("collapsed",[f("arrow","transform: rotate(0);")]),O("selected",[y("&::before","background-color: var(--n-item-color-active);"),f("arrow","color: var(--n-arrow-color-active);"),f("icon","color: var(--n-item-icon-color-active);"),h("menu-item-content-header",`
 color: var(--n-item-text-color-active);
 `,[y("a","color: var(--n-item-text-color-active);"),f("extra","color: var(--n-item-text-color-active);")])]),O("child-active",[h("menu-item-content-header",`
 color: var(--n-item-text-color-child-active);
 `,[y("a",`
 color: var(--n-item-text-color-child-active);
 `),f("extra",`
 color: var(--n-item-text-color-child-active);
 `)]),f("arrow",`
 color: var(--n-arrow-color-child-active);
 `),f("icon",`
 color: var(--n-item-icon-color-child-active);
 `)]),re("disabled",[re("selected, child-active",[y("&:focus-within",Ee)]),O("selected",[q(null,[f("arrow","color: var(--n-arrow-color-active-hover);"),f("icon","color: var(--n-item-icon-color-active-hover);"),h("menu-item-content-header",`
 color: var(--n-item-text-color-active-hover);
 `,[y("a","color: var(--n-item-text-color-active-hover);"),f("extra","color: var(--n-item-text-color-active-hover);")])])]),O("child-active",[q(null,[f("arrow","color: var(--n-arrow-color-child-active-hover);"),f("icon","color: var(--n-item-icon-color-child-active-hover);"),h("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-hover);
 `,[y("a","color: var(--n-item-text-color-child-active-hover);"),f("extra","color: var(--n-item-text-color-child-active-hover);")])])]),O("selected",[q(null,[y("&::before","background-color: var(--n-item-color-active-hover);")])]),q(null,Ee)]),f("icon",`
 grid-area: icon;
 color: var(--n-item-icon-color);
 transition:
 color .3s var(--n-bezier),
 font-size .3s var(--n-bezier),
 margin-right .3s var(--n-bezier);
 box-sizing: content-box;
 display: inline-flex;
 align-items: center;
 justify-content: center;
 `),f("arrow",`
 grid-area: arrow;
 font-size: 16px;
 color: var(--n-arrow-color);
 transform: rotate(180deg);
 opacity: 1;
 transition:
 color .3s var(--n-bezier),
 transform 0.2s var(--n-bezier),
 opacity 0.2s var(--n-bezier);
 `),h("menu-item-content-header",`
 grid-area: content;
 transition:
 color .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 opacity: 1;
 white-space: nowrap;
 color: var(--n-item-text-color);
 `,[y("a",`
 outline: none;
 text-decoration: none;
 transition: color .3s var(--n-bezier);
 color: var(--n-item-text-color);
 `,[y("&::before",`
 content: "";
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 `)]),f("extra",`
 font-size: .93em;
 color: var(--n-group-text-color);
 transition: color .3s var(--n-bezier);
 `)])]),h("submenu",`
 cursor: pointer;
 position: relative;
 margin-top: 6px;
 `,[h("menu-item-content",`
 height: var(--n-item-height);
 `),h("submenu-children",`
 overflow: hidden;
 padding: 0;
 `,[Io({duration:".2s"})])]),h("menu-item-group",[h("menu-item-group-title",`
 margin-top: 6px;
 color: var(--n-group-text-color);
 cursor: default;
 font-size: .93em;
 height: 36px;
 display: flex;
 align-items: center;
 transition:
 padding-left .3s var(--n-bezier),
 color .3s var(--n-bezier);
 `)])]),h("menu-tooltip",[y("a",`
 color: inherit;
 text-decoration: none;
 `)]),h("menu-divider",`
 transition: background-color .3s var(--n-bezier);
 background-color: var(--n-divider-color);
 height: 1px;
 margin: 6px 18px;
 `)]);function q(e,o){return[O("hover",e,o),y("&:hover",e,o)]}const Je=j({name:"MenuOptionContent",props:{collapsed:Boolean,disabled:Boolean,title:[String,Function],icon:Function,extra:[String,Function],showArrow:Boolean,childActive:Boolean,hover:Boolean,paddingLeft:Number,selected:Boolean,maxIconSize:{type:Number,required:!0},activeIconSize:{type:Number,required:!0},iconMarginRight:{type:Number,required:!0},clsPrefix:{type:String,required:!0},onClick:Function,tmNode:{type:Object,required:!0},isEllipsisPlaceholder:Boolean},setup(e){const{props:o}=G(ae);return{menuProps:o,style:x(()=>{const{paddingLeft:t}=e;return{paddingLeft:t&&`${t}px`}}),iconStyle:x(()=>{const{maxIconSize:t,activeIconSize:l,iconMarginRight:a}=e;return{width:`${t}px`,height:`${t}px`,fontSize:`${l}px`,marginRight:`${a}px`}})}},render(){const{clsPrefix:e,tmNode:o,menuProps:{renderIcon:t,renderLabel:l,renderExtra:a,expandIcon:n}}=this,d=t?t(o.rawNode):J(this.icon);return u("div",{onClick:p=>{var s;(s=this.onClick)===null||s===void 0||s.call(this,p)},role:"none",class:[`${e}-menu-item-content`,{[`${e}-menu-item-content--selected`]:this.selected,[`${e}-menu-item-content--collapsed`]:this.collapsed,[`${e}-menu-item-content--child-active`]:this.childActive,[`${e}-menu-item-content--disabled`]:this.disabled,[`${e}-menu-item-content--hover`]:this.hover}],style:this.style},d&&u("div",{class:`${e}-menu-item-content__icon`,style:this.iconStyle,role:"none"},[d]),u("div",{class:`${e}-menu-item-content-header`,role:"none"},this.isEllipsisPlaceholder?this.title:l?l(o.rawNode):J(this.title),this.extra||a?u("span",{class:`${e}-menu-item-content-header__extra`}," ",a?a(o.rawNode):J(this.extra)):null),this.showArrow?u(Ve,{ariaHidden:!0,class:`${e}-menu-item-content__arrow`,clsPrefix:e},{default:()=>n?n(o.rawNode):u(qo,null)}):null)}}),ue=8;function Te(e){const o=G(ae),{props:t,mergedCollapsedRef:l}=o,a=G(Ze,null),n=G(Pe,null),d=x(()=>t.mode==="horizontal"),p=x(()=>d.value?t.dropdownPlacement:"tmNodes"in e?"right-start":"right"),s=x(()=>{var g;return Math.max((g=t.collapsedIconSize)!==null&&g!==void 0?g:t.iconSize,t.iconSize)}),m=x(()=>{var g;return!d.value&&e.root&&l.value&&(g=t.collapsedIconSize)!==null&&g!==void 0?g:t.iconSize}),N=x(()=>{if(d.value)return;const{collapsedWidth:g,indent:z,rootIndent:_}=t,{root:w,isGroup:P}=e,A=_===void 0?z:_;return w?l.value?g/2-s.value/2:A:n&&typeof n.paddingLeftRef.value=="number"?z/2+n.paddingLeftRef.value:a&&typeof a.paddingLeftRef.value=="number"?(P?z/2:z)+a.paddingLeftRef.value:0}),k=x(()=>{const{collapsedWidth:g,indent:z,rootIndent:_}=t,{value:w}=s,{root:P}=e;return d.value||!P||!l.value?ue:(_===void 0?z:_)+w+ue-(g+w)/2});return{dropdownPlacement:p,activeIconSize:m,maxIconSize:s,paddingLeft:N,iconMarginRight:k,NMenu:o,NSubmenu:a,NMenuOptionGroup:n}}const ke={internalKey:{type:[String,Number],required:!0},root:Boolean,isGroup:Boolean,level:{type:Number,required:!0},title:[String,Function],extra:[String,Function]},gt=j({name:"MenuDivider",setup(){const e=G(ae),{mergedClsPrefixRef:o,isHorizontalRef:t}=e;return()=>t.value?null:u("div",{class:`${o.value}-menu-divider`})}}),Qe=Object.assign(Object.assign({},ke),{tmNode:{type:Object,required:!0},disabled:Boolean,icon:Function,onClick:Function}),bt=Se(Qe),xt=j({name:"MenuOption",props:Qe,setup(e){const o=Te(e),{NSubmenu:t,NMenu:l,NMenuOptionGroup:a}=o,{props:n,mergedClsPrefixRef:d,mergedCollapsedRef:p}=l,s=t?t.mergedDisabledRef:a?a.mergedDisabledRef:{value:!1},m=x(()=>s.value||e.disabled);function N(g){const{onClick:z}=e;z&&z(g)}function k(g){m.value||(l.doSelect(e.internalKey,e.tmNode.rawNode),N(g))}return{mergedClsPrefix:d,dropdownPlacement:o.dropdownPlacement,paddingLeft:o.paddingLeft,iconMarginRight:o.iconMarginRight,maxIconSize:o.maxIconSize,activeIconSize:o.activeIconSize,mergedTheme:l.mergedThemeRef,menuProps:n,dropdownEnabled:be(()=>e.root&&p.value&&n.mode!=="horizontal"&&!m.value),selected:be(()=>l.mergedValueRef.value===e.internalKey),mergedDisabled:m,handleClick:k}},render(){const{mergedClsPrefix:e,mergedTheme:o,tmNode:t,menuProps:{renderLabel:l,nodeProps:a}}=this,n=a==null?void 0:a(t.rawNode);return u("div",Object.assign({},n,{role:"menuitem",class:[`${e}-menu-item`,n==null?void 0:n.class]}),u(De,{theme:o.peers.Tooltip,themeOverrides:o.peerOverrides.Tooltip,trigger:"hover",placement:this.dropdownPlacement,disabled:!this.dropdownEnabled||this.title===void 0,internalExtraClass:["menu-tooltip"]},{default:()=>l?l(t.rawNode):J(this.title),trigger:()=>u(Je,{tmNode:t,clsPrefix:e,paddingLeft:this.paddingLeft,iconMarginRight:this.iconMarginRight,maxIconSize:this.maxIconSize,activeIconSize:this.activeIconSize,selected:this.selected,title:this.title,extra:this.extra,disabled:this.mergedDisabled,icon:this.icon,onClick:this.handleClick})}))}}),eo=Object.assign(Object.assign({},ke),{tmNode:{type:Object,required:!0},tmNodes:{type:Array,required:!0}}),Ct=Se(eo),yt=j({name:"MenuOptionGroup",props:eo,setup(e){const o=Te(e),{NSubmenu:t}=o,l=x(()=>t!=null&&t.mergedDisabledRef.value?!0:e.tmNode.disabled);X(Pe,{paddingLeftRef:o.paddingLeft,mergedDisabledRef:l});const{mergedClsPrefixRef:a,props:n}=G(ae);return function(){const{value:d}=a,p=o.paddingLeft.value,{nodeProps:s}=n,m=s==null?void 0:s(e.tmNode.rawNode);return u("div",{class:`${d}-menu-item-group`,role:"group"},u("div",Object.assign({},m,{class:[`${d}-menu-item-group-title`,m==null?void 0:m.class],style:[(m==null?void 0:m.style)||"",p!==void 0?`padding-left: ${p}px;`:""]}),J(e.title),e.extra?u(Ro,null," ",J(e.extra)):null),u("div",null,e.tmNodes.map(N=>Ne(N,n))))}}});function ye(e){return e.type==="divider"||e.type==="render"}function zt(e){return e.type==="divider"}function Ne(e,o){const{rawNode:t}=e,{show:l}=t;if(l===!1)return null;if(ye(t))return zt(t)?u(gt,Object.assign({key:e.key},t.props)):null;const{labelField:a}=o,{key:n,level:d,isGroup:p}=e,s=Object.assign(Object.assign({},t),{title:t.title||t[a],extra:t.titleExtra||t.extra,key:n,internalKey:n,level:d,root:d===0,isGroup:p});return e.children?e.isGroup?u(yt,he(s,Ct,{tmNode:e,tmNodes:e.children,key:n})):u(ze,he(s,wt,{key:n,rawNodes:t[o.childrenField],tmNodes:e.children,tmNode:e})):u(xt,he(s,bt,{key:n,tmNode:e}))}const oo=Object.assign(Object.assign({},ke),{rawNodes:{type:Array,default:()=>[]},tmNodes:{type:Array,default:()=>[]},tmNode:{type:Object,required:!0},disabled:Boolean,icon:Function,onClick:Function,domId:String,virtualChildActive:{type:Boolean,default:void 0},isEllipsisPlaceholder:Boolean}),wt=Se(oo),ze=j({name:"Submenu",props:oo,setup(e){const o=Te(e),{NMenu:t,NSubmenu:l}=o,{props:a,mergedCollapsedRef:n,mergedThemeRef:d}=t,p=x(()=>{const{disabled:g}=e;return l!=null&&l.mergedDisabledRef.value||a.disabled?!0:g}),s=M(!1);X(Ze,{paddingLeftRef:o.paddingLeft,mergedDisabledRef:p}),X(Pe,null);function m(){const{onClick:g}=e;g&&g()}function N(){p.value||(n.value||t.toggleExpand(e.internalKey),m())}function k(g){s.value=g}return{menuProps:a,mergedTheme:d,doSelect:t.doSelect,inverted:t.invertedRef,isHorizontal:t.isHorizontalRef,mergedClsPrefix:t.mergedClsPrefixRef,maxIconSize:o.maxIconSize,activeIconSize:o.activeIconSize,iconMarginRight:o.iconMarginRight,dropdownPlacement:o.dropdownPlacement,dropdownShow:s,paddingLeft:o.paddingLeft,mergedDisabled:p,mergedValue:t.mergedValueRef,childActive:be(()=>{var g;return(g=e.virtualChildActive)!==null&&g!==void 0?g:t.activePathRef.value.includes(e.internalKey)}),collapsed:x(()=>a.mode==="horizontal"?!1:n.value?!0:!t.mergedExpandedKeysRef.value.includes(e.internalKey)),dropdownEnabled:x(()=>!p.value&&(a.mode==="horizontal"||n.value)),handlePopoverShowChange:k,handleClick:N}},render(){var e;const{mergedClsPrefix:o,menuProps:{renderIcon:t,renderLabel:l}}=this,a=()=>{const{isHorizontal:d,paddingLeft:p,collapsed:s,mergedDisabled:m,maxIconSize:N,activeIconSize:k,title:g,childActive:z,icon:_,handleClick:w,menuProps:{nodeProps:P},dropdownShow:A,iconMarginRight:b,tmNode:R,mergedClsPrefix:B,isEllipsisPlaceholder:v,extra:c}=this,S=P==null?void 0:P(R.rawNode);return u("div",Object.assign({},S,{class:[`${B}-menu-item`,S==null?void 0:S.class],role:"menuitem"}),u(Je,{tmNode:R,paddingLeft:p,collapsed:s,disabled:m,iconMarginRight:b,maxIconSize:N,activeIconSize:k,title:g,extra:c,showArrow:!d,childActive:z,clsPrefix:B,icon:_,hover:A,onClick:w,isEllipsisPlaceholder:v}))},n=()=>u(Po,null,{default:()=>{const{tmNodes:d,collapsed:p}=this;return p?null:u("div",{class:`${o}-submenu-children`,role:"menu"},d.map(s=>Ne(s,this.menuProps)))}});return this.root?u(Ge,Object.assign({size:"large",trigger:"hover"},(e=this.menuProps)===null||e===void 0?void 0:e.dropdownProps,{themeOverrides:this.mergedTheme.peerOverrides.Dropdown,theme:this.mergedTheme.peers.Dropdown,builtinThemeOverrides:{fontSizeLarge:"14px",optionIconSizeLarge:"18px"},value:this.mergedValue,disabled:!this.dropdownEnabled,placement:this.dropdownPlacement,keyField:this.menuProps.keyField,labelField:this.menuProps.labelField,childrenField:this.menuProps.childrenField,onUpdateShow:this.handlePopoverShowChange,options:this.rawNodes,onSelect:this.doSelect,inverted:this.inverted,renderIcon:t,renderLabel:l}),{default:()=>u("div",{class:`${o}-submenu`,role:"menu","aria-expanded":!this.collapsed,id:this.domId},a(),this.isHorizontal?null:n())}):u("div",{class:`${o}-submenu`,role:"menu","aria-expanded":!this.collapsed,id:this.domId},a(),n())}}),St=Object.assign(Object.assign({},D.props),{options:{type:Array,default:()=>[]},collapsed:{type:Boolean,default:void 0},collapsedWidth:{type:Number,default:48},iconSize:{type:Number,default:20},collapsedIconSize:{type:Number,default:24},rootIndent:Number,indent:{type:Number,default:32},labelField:{type:String,default:"label"},keyField:{type:String,default:"key"},childrenField:{type:String,default:"children"},disabledField:{type:String,default:"disabled"},defaultExpandAll:Boolean,defaultExpandedKeys:Array,expandedKeys:Array,value:[String,Number],defaultValue:{type:[String,Number],default:null},mode:{type:String,default:"vertical"},watchProps:{type:Array,default:void 0},disabled:Boolean,show:{type:Boolean,default:!0},inverted:Boolean,"onUpdate:expandedKeys":[Function,Array],onUpdateExpandedKeys:[Function,Array],onUpdateValue:[Function,Array],"onUpdate:value":[Function,Array],expandIcon:Function,renderIcon:Function,renderLabel:Function,renderExtra:Function,dropdownProps:Object,accordion:Boolean,nodeProps:Function,dropdownPlacement:{type:String,default:"bottom"},responsive:Boolean,items:Array,onOpenNamesChange:[Function,Array],onSelect:[Function,Array],onExpandedNamesChange:[Function,Array],expandedNames:Array,defaultExpandedNames:Array}),ve=j({name:"Menu",inheritAttrs:!1,props:St,setup(e){const{mergedClsPrefixRef:o,inlineThemeDisabled:t}=Q(e),l=D("Menu","-menu",pt,No,e,o),a=G(qe,null),n=x(()=>{var C;const{collapsed:T}=e;if(T!==void 0)return T;if(a){const{collapseModeRef:r,collapsedRef:I}=a;if(r.value==="width")return(C=I.value)!==null&&C!==void 0?C:!1}return!1}),d=x(()=>{const{keyField:C,childrenField:T,disabledField:r}=e;return pe(e.items||e.options,{getIgnored(I){return ye(I)},getChildren(I){return I[T]},getDisabled(I){return I[r]},getKey(I){var L;return(L=I[C])!==null&&L!==void 0?L:I.name}})}),p=x(()=>new Set(d.value.treeNodes.map(C=>C.key))),{watchProps:s}=e,m=M(null);s!=null&&s.includes("defaultValue")?ge(()=>{m.value=e.defaultValue}):m.value=e.defaultValue;const N=le(e,"value"),k=Ce(N,m),g=M([]),z=()=>{g.value=e.defaultExpandAll?d.value.getNonLeafKeys():e.defaultExpandedNames||e.defaultExpandedKeys||d.value.getPath(k.value,{includeSelf:!1}).keyPath};s!=null&&s.includes("defaultExpandedKeys")?ge(z):z();const _=jo(e,["expandedNames","expandedKeys"]),w=Ce(_,g),P=x(()=>d.value.treeNodes),A=x(()=>d.value.getPath(k.value).keyPath);X(ae,{props:e,mergedCollapsedRef:n,mergedThemeRef:l,mergedValueRef:k,mergedExpandedKeysRef:w,activePathRef:A,mergedClsPrefixRef:o,isHorizontalRef:x(()=>e.mode==="horizontal"),invertedRef:le(e,"inverted"),doSelect:b,toggleExpand:B});function b(C,T){const{"onUpdate:value":r,onUpdateValue:I,onSelect:L}=e;I&&U(I,C,T),r&&U(r,C,T),L&&U(L,C,T),m.value=C}function R(C){const{"onUpdate:expandedKeys":T,onUpdateExpandedKeys:r,onExpandedNamesChange:I,onOpenNamesChange:L}=e;T&&U(T,C),r&&U(r,C),I&&U(I,C),L&&U(L,C),g.value=C}function B(C){const T=Array.from(w.value),r=T.findIndex(I=>I===C);if(~r)T.splice(r,1);else{if(e.accordion&&p.value.has(C)){const I=T.findIndex(L=>p.value.has(L));I>-1&&T.splice(I,1)}T.push(C)}R(T)}const v=C=>{const T=d.value.getPath(C??k.value,{includeSelf:!1}).keyPath;if(!T.length)return;const r=Array.from(w.value),I=new Set([...r,...T]);e.accordion&&p.value.forEach(L=>{I.has(L)&&!T.includes(L)&&I.delete(L)}),R(Array.from(I))},c=x(()=>{const{inverted:C}=e,{common:{cubicBezierEaseInOut:T},self:r}=l.value,{borderRadius:I,borderColorHorizontal:L,fontSize:so,itemHeight:co,dividerColor:uo}=r,i={"--n-divider-color":uo,"--n-bezier":T,"--n-font-size":so,"--n-border-color-horizontal":L,"--n-border-radius":I,"--n-item-height":co};return C?(i["--n-group-text-color"]=r.groupTextColorInverted,i["--n-color"]=r.colorInverted,i["--n-item-text-color"]=r.itemTextColorInverted,i["--n-item-text-color-hover"]=r.itemTextColorHoverInverted,i["--n-item-text-color-active"]=r.itemTextColorActiveInverted,i["--n-item-text-color-child-active"]=r.itemTextColorChildActiveInverted,i["--n-item-text-color-child-active-hover"]=r.itemTextColorChildActiveInverted,i["--n-item-text-color-active-hover"]=r.itemTextColorActiveHoverInverted,i["--n-item-icon-color"]=r.itemIconColorInverted,i["--n-item-icon-color-hover"]=r.itemIconColorHoverInverted,i["--n-item-icon-color-active"]=r.itemIconColorActiveInverted,i["--n-item-icon-color-active-hover"]=r.itemIconColorActiveHoverInverted,i["--n-item-icon-color-child-active"]=r.itemIconColorChildActiveInverted,i["--n-item-icon-color-child-active-hover"]=r.itemIconColorChildActiveHoverInverted,i["--n-item-icon-color-collapsed"]=r.itemIconColorCollapsedInverted,i["--n-item-text-color-horizontal"]=r.itemTextColorHorizontalInverted,i["--n-item-text-color-hover-horizontal"]=r.itemTextColorHoverHorizontalInverted,i["--n-item-text-color-active-horizontal"]=r.itemTextColorActiveHorizontalInverted,i["--n-item-text-color-child-active-horizontal"]=r.itemTextColorChildActiveHorizontalInverted,i["--n-item-text-color-child-active-hover-horizontal"]=r.itemTextColorChildActiveHoverHorizontalInverted,i["--n-item-text-color-active-hover-horizontal"]=r.itemTextColorActiveHoverHorizontalInverted,i["--n-item-icon-color-horizontal"]=r.itemIconColorHorizontalInverted,i["--n-item-icon-color-hover-horizontal"]=r.itemIconColorHoverHorizontalInverted,i["--n-item-icon-color-active-horizontal"]=r.itemIconColorActiveHorizontalInverted,i["--n-item-icon-color-active-hover-horizontal"]=r.itemIconColorActiveHoverHorizontalInverted,i["--n-item-icon-color-child-active-horizontal"]=r.itemIconColorChildActiveHorizontalInverted,i["--n-item-icon-color-child-active-hover-horizontal"]=r.itemIconColorChildActiveHoverHorizontalInverted,i["--n-arrow-color"]=r.arrowColorInverted,i["--n-arrow-color-hover"]=r.arrowColorHoverInverted,i["--n-arrow-color-active"]=r.arrowColorActiveInverted,i["--n-arrow-color-active-hover"]=r.arrowColorActiveHoverInverted,i["--n-arrow-color-child-active"]=r.arrowColorChildActiveInverted,i["--n-arrow-color-child-active-hover"]=r.arrowColorChildActiveHoverInverted,i["--n-item-color-hover"]=r.itemColorHoverInverted,i["--n-item-color-active"]=r.itemColorActiveInverted,i["--n-item-color-active-hover"]=r.itemColorActiveHoverInverted,i["--n-item-color-active-collapsed"]=r.itemColorActiveCollapsedInverted):(i["--n-group-text-color"]=r.groupTextColor,i["--n-color"]=r.color,i["--n-item-text-color"]=r.itemTextColor,i["--n-item-text-color-hover"]=r.itemTextColorHover,i["--n-item-text-color-active"]=r.itemTextColorActive,i["--n-item-text-color-child-active"]=r.itemTextColorChildActive,i["--n-item-text-color-child-active-hover"]=r.itemTextColorChildActiveHover,i["--n-item-text-color-active-hover"]=r.itemTextColorActiveHover,i["--n-item-icon-color"]=r.itemIconColor,i["--n-item-icon-color-hover"]=r.itemIconColorHover,i["--n-item-icon-color-active"]=r.itemIconColorActive,i["--n-item-icon-color-active-hover"]=r.itemIconColorActiveHover,i["--n-item-icon-color-child-active"]=r.itemIconColorChildActive,i["--n-item-icon-color-child-active-hover"]=r.itemIconColorChildActiveHover,i["--n-item-icon-color-collapsed"]=r.itemIconColorCollapsed,i["--n-item-text-color-horizontal"]=r.itemTextColorHorizontal,i["--n-item-text-color-hover-horizontal"]=r.itemTextColorHoverHorizontal,i["--n-item-text-color-active-horizontal"]=r.itemTextColorActiveHorizontal,i["--n-item-text-color-child-active-horizontal"]=r.itemTextColorChildActiveHorizontal,i["--n-item-text-color-child-active-hover-horizontal"]=r.itemTextColorChildActiveHoverHorizontal,i["--n-item-text-color-active-hover-horizontal"]=r.itemTextColorActiveHoverHorizontal,i["--n-item-icon-color-horizontal"]=r.itemIconColorHorizontal,i["--n-item-icon-color-hover-horizontal"]=r.itemIconColorHoverHorizontal,i["--n-item-icon-color-active-horizontal"]=r.itemIconColorActiveHorizontal,i["--n-item-icon-color-active-hover-horizontal"]=r.itemIconColorActiveHoverHorizontal,i["--n-item-icon-color-child-active-horizontal"]=r.itemIconColorChildActiveHorizontal,i["--n-item-icon-color-child-active-hover-horizontal"]=r.itemIconColorChildActiveHoverHorizontal,i["--n-arrow-color"]=r.arrowColor,i["--n-arrow-color-hover"]=r.arrowColorHover,i["--n-arrow-color-active"]=r.arrowColorActive,i["--n-arrow-color-active-hover"]=r.arrowColorActiveHover,i["--n-arrow-color-child-active"]=r.arrowColorChildActive,i["--n-arrow-color-child-active-hover"]=r.arrowColorChildActiveHover,i["--n-item-color-hover"]=r.itemColorHover,i["--n-item-color-active"]=r.itemColorActive,i["--n-item-color-active-hover"]=r.itemColorActiveHover,i["--n-item-color-active-collapsed"]=r.itemColorActiveCollapsed),i}),S=t?ee("menu",x(()=>e.inverted?"a":"b"),c,e):void 0,E=To(),V=M(null),oe=M(null);let K=!0;const se=()=>{var C;K?K=!1:(C=V.value)===null||C===void 0||C.sync({showAllItemsBeforeCalculate:!0})};function te(){return document.getElementById(E)}const ce=M(-1);function to(C){ce.value=e.options.length-C}function ro(C){C||(ce.value=-1)}const no=x(()=>{const C=ce.value;return{children:C===-1?[]:e.options.slice(C)}}),io=x(()=>{const{childrenField:C,disabledField:T,keyField:r}=e;return pe([no.value],{getIgnored(I){return ye(I)},getChildren(I){return I[C]},getDisabled(I){return I[T]},getKey(I){var L;return(L=I[r])!==null&&L!==void 0?L:I.name}})}),lo=x(()=>pe([{}]).treeNodes[0]);function ao(){var C;if(ce.value===-1)return u(ze,{root:!0,level:0,key:"__ellpisisGroupPlaceholder__",internalKey:"__ellpisisGroupPlaceholder__",title:"···",tmNode:lo.value,domId:E,isEllipsisPlaceholder:!0});const T=io.value.treeNodes[0],r=A.value,I=!!(!((C=T.children)===null||C===void 0)&&C.some(L=>r.includes(L.key)));return u(ze,{level:0,root:!0,key:"__ellpisisGroup__",internalKey:"__ellpisisGroup__",title:"···",virtualChildActive:I,tmNode:T,domId:E,rawNodes:T.rawNode.children||[],tmNodes:T.children||[],isEllipsisPlaceholder:!0})}return{mergedClsPrefix:o,controlledExpandedKeys:_,uncontrolledExpanededKeys:g,mergedExpandedKeys:w,uncontrolledValue:m,mergedValue:k,activePath:A,tmNodes:P,mergedTheme:l,mergedCollapsed:n,cssVars:t?void 0:c,themeClass:S==null?void 0:S.themeClass,overflowRef:V,counterRef:oe,updateCounter:()=>{},onResize:se,onUpdateOverflow:ro,onUpdateCount:to,renderCounter:ao,getCounter:te,onRender:S==null?void 0:S.onRender,showOption:v,deriveResponsiveState:se}},render(){const{mergedClsPrefix:e,mode:o,themeClass:t,onRender:l}=this;l==null||l();const a=()=>this.tmNodes.map(s=>Ne(s,this.$props)),d=o==="horizontal"&&this.responsive,p=()=>u("div",ko(this.$attrs,{role:o==="horizontal"?"menubar":"menu",class:[`${e}-menu`,t,`${e}-menu--${o}`,d&&`${e}-menu--responsive`,this.mergedCollapsed&&`${e}-menu--collapsed`],style:this.cssVars}),d?u(Mo,{ref:"overflowRef",onUpdateOverflow:this.onUpdateOverflow,getCounter:this.getCounter,onUpdateCount:this.onUpdateCount,updateCounter:this.updateCounter,style:{width:"100%",display:"flex",overflow:"hidden"}},{default:a,counter:this.renderCounter}):a());return d?u(Fe,{onResize:this.onResize},{default:p}):p()}}),It={class:"theme-icon"},Rt=j({__name:"ThemeToggle",setup(e){const o=_o();return(t,l)=>(Y(),ne(H(De),{trigger:"hover"},{trigger:F(()=>[$(H(xe),{quaternary:"",circle:"",size:"small",onClick:l[0]||(l[0]=a=>H(o).toggle())},{default:F(()=>[W("span",It,ie(H(o).isDark?"☀️":"🌙"),1)]),_:1})]),default:F(()=>[me(" "+ie(H(o).isDark?"切换到浅色模式":"切换到深色模式"),1)]),_:1}))}}),Pt=Ue(Rt,[["__scopeId","data-v-53e3679f"]]),Tt={key:0,class:"logo-text"},kt={class:"sider-bottom"},Nt={class:"header-left"},_t={class:"header-right"},At={key:0,class:"user-name"},Ot=j({__name:"AppLayout",setup(e){const o=Bo(),t=Eo(),l=$o(),a=Ao(),{isAdmin:n}=Lo(),d=M(!1),p=M(!1),s=M(!1);function m(){s.value=window.innerWidth<768}we(()=>{m(),window.addEventListener("resize",m)}),Me(()=>{window.removeEventListener("resize",m)});const N=x(()=>t.meta.title||"工作台"),k=x(()=>{var c;const v=(c=a.user)==null?void 0:c.display_name;return v?v.charAt(0).toUpperCase():"U"}),g=x(()=>{const v=t.path;return v.startsWith("/reviews/new")?"new":v.startsWith("/reviews")?"reviews":v.startsWith("/dashboard")?"dashboard":v.startsWith("/work")?"work":v.startsWith("/analytics")?"analytics":v.startsWith("/compare")?"compare":v.startsWith("/templates")?"templates":v.startsWith("/clauses")?"clauses":v.startsWith("/account")?"account":v.startsWith("/admin")?"admin":"dashboard"});function z(v){return()=>u("span",{style:"font-size: 16px"},v)}const _=x(()=>[{label:"工作台",key:"dashboard",icon:z("📊")},{label:"审阅记录",key:"reviews",icon:z("📄")},{label:"新建审阅",key:"new",icon:z("✨")},{label:"处置中心",key:"work",icon:z("🔧")},{label:"数据分析",key:"analytics",icon:z("📈")},{label:"合同对比",key:"compare",icon:z("⚖️")},{label:"模板库",key:"templates",icon:z("📁")},{label:"条款库",key:"clauses",icon:z("📚")}]),w=x(()=>{const v=[{label:"账户设置",key:"account",icon:z("👤")}];return n.value&&v.push({label:"管理后台",key:"admin",icon:z("⚙️")}),v}),P=[{label:"个人资料",key:"profile",icon:()=>u("span","👤")},{type:"divider",key:"d1"},{label:"退出登录",key:"logout",icon:()=>u("span","🚪")}];function A(v){R(v)}function b(v){p.value=!1,R(v)}function R(v){const S={dashboard:"/dashboard",reviews:"/reviews",new:"/reviews/new",work:"/work",analytics:"/analytics",compare:"/compare",templates:"/templates",clauses:"/clauses",account:"/account",admin:"/admin"}[v];S&&o.push(S)}function B(v){v==="profile"?o.push("/account"):v==="logout"&&(a.logout(),l.success("已退出登录"),o.push("/login"))}return(v,c)=>{const S=Ho("router-view");return Y(),ne(H(He),{"has-sider":"",class:"app-layout"},{default:F(()=>[s.value?de("",!0):(Y(),ne(H(ft),{key:0,bordered:"",collapsed:d.value,"collapse-mode":"width","collapsed-width":64,width:240,"show-trigger":"",onCollapse:c[1]||(c[1]=E=>d.value=!0),onExpand:c[2]||(c[2]=E=>d.value=!1),class:"app-sider"},{default:F(()=>[W("div",{class:"sider-logo",onClick:c[0]||(c[0]=E=>H(o).push("/dashboard"))},[c[6]||(c[6]=W("span",{class:"logo-icon"},"📋",-1)),$(Oe,{name:"fade"},{default:F(()=>[d.value?de("",!0):(Y(),Ae("span",Tt,"ContractGuard"))]),_:1})]),$(H(ve),{collapsed:d.value,"collapsed-width":64,"collapsed-icon-size":20,options:_.value,value:g.value,"onUpdate:value":A},null,8,["collapsed","options","value"]),W("div",kt,[$(H(ve),{collapsed:d.value,"collapsed-width":64,"collapsed-icon-size":20,options:w.value,value:g.value,"onUpdate:value":A},null,8,["collapsed","options","value"])])]),_:1},8,["collapsed"])),$(H(Vo),{show:p.value,"onUpdate:show":c[3]||(c[3]=E=>p.value=E),placement:"left",width:260},{default:F(()=>[$(H(Ko),{"native-scrollbar":!1},{default:F(()=>[c[7]||(c[7]=W("div",{class:"sider-logo drawer-logo"},[W("span",{class:"logo-icon"},"📋"),W("span",{class:"logo-text"},"ContractGuard")],-1)),$(H(ve),{options:_.value,value:g.value,"onUpdate:value":b},null,8,["options","value"]),$(H(Do)),$(H(ve),{options:w.value,value:g.value,"onUpdate:value":b},null,8,["options","value"])]),_:1})]),_:1},8,["show"]),$(H(He),{class:"main-layout"},{default:F(()=>[$(H(dt),{bordered:"",class:"app-header"},{default:F(()=>[W("div",Nt,[s.value?(Y(),ne(H(xe),{key:0,quaternary:"",circle:"",size:"small",onClick:c[4]||(c[4]=E=>p.value=!0),class:"mobile-menu-btn"},{default:F(()=>[...c[8]||(c[8]=[W("span",{style:{"font-size":"18px"}},"☰",-1)])]),_:1})):de("",!0),$(H(ot),null,{default:F(()=>[$(H(Be),{onClick:c[5]||(c[5]=E=>H(o).push("/dashboard"))},{default:F(()=>[...c[9]||(c[9]=[me(" 首页 ",-1)])]),_:1}),$(H(Be),null,{default:F(()=>[me(ie(N.value),1)]),_:1})]),_:1})]),W("div",_t,[$(Pt),$(H(Ge),{trigger:"click",options:P,onSelect:B},{default:F(()=>[$(H(xe),{quaternary:"",class:"user-btn"},{default:F(()=>{var E;return[$(H(Jo),{round:"",size:32,style:{backgroundColor:"#667eea",fontSize:"14px"}},{default:F(()=>[me(ie(k.value),1)]),_:1}),s.value?de("",!0):(Y(),Ae("span",At,ie((E=H(a).user)==null?void 0:E.display_name),1))]}),_:1})]),_:1})])]),_:1}),$(H(at),{class:"app-content","native-scrollbar":!1},{default:F(()=>[$(S,null,{default:F(({Component:E})=>[$(Oe,{name:"page-fade",mode:"out-in"},{default:F(()=>[(Y(),ne(Oo(E)))]),_:2},1024)]),_:1})]),_:1})]),_:1})]),_:1})}}}),Xt=Ue(Ot,[["__scopeId","data-v-9cbd6bd4"]]);export{Xt as default};
