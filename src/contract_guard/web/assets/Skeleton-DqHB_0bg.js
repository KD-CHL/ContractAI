import{_,C as v,z as w,d as H,x as p,ad as j,bN as E,a9 as O,H as A,I as y,v as k,P as I,bj as z}from"./index-JKv9wurx.js";import{u as L}from"./use-houdini-CahkfEBX.js";function T(e){const{heightSmall:s,heightMedium:n,heightLarge:i,borderRadius:a}=e;return{color:"#eee",colorEnd:"#ddd",borderRadius:a,heightSmall:s,heightMedium:n,heightLarge:i}}const $={common:_,self:T},F=v([w("skeleton",`
 height: 1em;
 width: 100%;
 transition:
 --n-color-start .3s var(--n-bezier),
 --n-color-end .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 animation: 2s skeleton-loading infinite cubic-bezier(0.36, 0, 0.64, 1);
 background-color: var(--n-color-start);
 `),v("@keyframes skeleton-loading",`
 0% {
 background: var(--n-color-start);
 }
 40% {
 background: var(--n-color-end);
 }
 80% {
 background: var(--n-color-start);
 }
 100% {
 background: var(--n-color-start);
 }
 `)]),K=Object.assign(Object.assign({},y.props),{text:Boolean,round:Boolean,circle:Boolean,height:[String,Number],width:[String,Number],size:String,repeat:{type:Number,default:1},animated:{type:Boolean,default:!0},sharp:{type:Boolean,default:!0}}),W=H({name:"Skeleton",inheritAttrs:!1,props:K,setup(e){L();const{mergedClsPrefixRef:s,mergedComponentPropsRef:n}=A(e),i=k(()=>{var o,t;return e.size||((t=(o=n==null?void 0:n.value)===null||o===void 0?void 0:o.Skeleton)===null||t===void 0?void 0:t.size)}),a=y("Skeleton","-skeleton",F,$,e,s);return{mergedClsPrefix:s,style:k(()=>{var o,t;const g=a.value,{common:{cubicBezierEaseInOut:S}}=g,h=g.self,{color:x,colorEnd:P,borderRadius:B}=h;let l;const{circle:d,sharp:C,round:R,width:r,height:c,text:b,animated:N}=e,f=i.value;f!==void 0&&(l=h[I("height",f)]);const u=d?(o=r??c)!==null&&o!==void 0?o:l:r,m=(t=d?r??c:c)!==null&&t!==void 0?t:l;return{display:b?"inline-block":"",verticalAlign:b?"-0.125em":"",borderRadius:d?"50%":R?"4096px":C?"":B,width:typeof u=="number"?z(u):u,height:typeof m=="number"?z(m):m,animation:N?"":"none","--n-bezier":S,"--n-color-start":x,"--n-color-end":P}})}},render(){const{repeat:e,style:s,mergedClsPrefix:n,$attrs:i}=this,a=p("div",j({class:`${n}-skeleton`,style:s},i));return e>1?p(O,null,E(e,null).map(o=>[a,`
`])):a}});export{W as N};
