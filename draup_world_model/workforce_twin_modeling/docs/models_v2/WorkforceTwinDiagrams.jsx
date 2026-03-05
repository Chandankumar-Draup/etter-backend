import { useState, useMemo } from "react";

const TABS = [
  { id: "sfd", label: "① Stock & Flow", desc: "structural skeleton" },
  { id: "cld", label: "② Causal Loops", desc: "9 feedback loops" },
  { id: "beh", label: "③ Behavior", desc: "reference mode" },
  { id: "dom", label: "④ Dominance", desc: "which loops control" },
  { id: "evo", label: "⑤ Evolution", desc: "v1 → v2.1" },
];

/* ── shared arrow markers ── */
const Defs = () => (
  <defs>
    <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#555"/></marker>
    <marker id="arB" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#2060a0"/></marker>
    <marker id="arR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 2 L 10 5 L 0 8 z" fill="#a03030"/></marker>
    <marker id="arN" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 2 L 10 5 L 0 8 z" fill="#48a"/></marker>
    <marker id="fl" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 2 L 10 5 L 0 8 z" fill="#3070b0"/></marker>
    <marker id="fo" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 2 L 10 5 L 0 8 z" fill="#b04040"/></marker>
    <marker id="fk" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#886633"/></marker>
    <marker id="fg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 2 L 10 5 L 0 8 z" fill="#6a4"/></marker>
    <marker id="fL" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 2 L 10 5 L 0 8 z" fill="#aaa"/></marker>
    <filter id="sh" x="-3%" y="-3%" width="106%" height="112%"><feDropShadow dx="1" dy="2" stdDeviation="2.5" floodColor="#00000018"/></filter>
    <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f8f9ff"/><stop offset="100%" stopColor="#eef1f8"/></linearGradient>
    <linearGradient id="hg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#fff8f0"/><stop offset="100%" stopColor="#f5ece0"/></linearGradient>
  </defs>
);

/* ── small reusable bits ── */
const Stock = ({x,y,w=140,h=42,label,sub,fill="url(#sg)"}) => (
  <g><rect x={x} y={y} width={w} height={h} rx="5" fill={fill} stroke="#334" strokeWidth="2.2" filter="url(#sh)"/>
  <text x={x+w/2} y={sub?y+h/2-5:y+h/2+5} textAnchor="middle" fill="#222" fontSize="12.5" fontWeight="bold">{label}</text>
  {sub && <text x={x+w/2} y={y+h/2+10} textAnchor="middle" fill="#555" fontSize="10">{sub}</text>}</g>
);
const Lp = ({x,y,t,id}) => {
  const isR = t==="R";
  return <g><circle cx={x} cy={y} r={12} fill={isR?"#fff0f0":"#f0f5ff"} stroke={isR?"#a03030":"#2060a0"} strokeWidth="1.5"/>
  <text x={x} y={y+1} textAnchor="middle" dominantBaseline="middle" fill={isR?"#a03030":"#2060a0"} fontSize="9.5" fontWeight="bold">{t}{id}</text></g>;
};
const P = ({x,y,s,c="#555"}) => <text x={x} y={y} fill={c} fontSize="13" fontWeight="bold" fontStyle="italic">{s}</text>;
const Dl = ({x,y}) => <g><rect x={x-18} y={y-6} width="36" height="12" rx="2" fill="#fff5f5" stroke="#c44" strokeWidth="0.6"/><text x={x} y={y+3} textAnchor="middle" fill="#c44" fontSize="7" fontWeight="bold">DELAY</text></g>;

/* ═══════════════════════════════════════
   DIAGRAM 1: STOCK & FLOW
   ═══════════════════════════════════════ */
const SFD = () => (
  <svg viewBox="0 0 1100 830" style={{width:"100%",height:"auto"}} fontFamily="Georgia,serif"><Defs/><rect width="1100" height="830" fill="#fafafa"/>
  <text x="550" y="30" textAnchor="middle" fill="#222" fontSize="17" fontWeight="bold">STOCK-AND-FLOW DIAGRAM — Workforce Twin v2.1</text>
  <text x="550" y="50" textAnchor="middle" fill="#888" fontSize="12" fontStyle="italic">6 stocks, 12 flows, 9 feedback loops — the complete structural skeleton</text>
  <text x="550" y="66" textAnchor="middle" fill="#aaa" fontSize="10">"A stock is the memory of the history of changing flows within the system" — Donella Meadows</text>

  {/* Stock 1: Adoption */}
  <Stock x={435} y={95} w={200} h={52} label="AI Adoption Level" sub="0→90% (S-curve × human)"/>
  <polygon points="340,114 340,128 320,121" fill="#3070b0" opacity="0.7"/>
  <path d="M 280,121 L 435,121" fill="none" stroke="#3070b0" strokeWidth="2.8" markerEnd="url(#fl)"/>
  <text x="340" y="108" textAnchor="middle" fill="#3070b0" fontSize="9.5" fontStyle="italic">technology deployment</text>
  <path d="M 635,121 L 800,121" fill="none" stroke="#b04040" strokeWidth="2" markerEnd="url(#fo)"/>
  <text x="720" y="112" textAnchor="middle" fill="#b04040" fontSize="9.5" fontStyle="italic">adoption dampening</text>

  {/* Stock 2: Freed Capacity */}
  <Stock x={65} y={230} w={170} h={50} label="Freed Capacity" sub="hours/month"/>
  <path d="M 490,147 Q 350,195 235,238" fill="none" stroke="#3070b0" strokeWidth="2" markerEnd="url(#fl)"/>
  <text x="345" y="190" textAnchor="middle" fill="#3070b0" fontSize="9" fontStyle="italic">automation frees hours</text>
  <path d="M 150,280 L 150,328" fill="none" stroke="#b04040" strokeWidth="2" markerEnd="url(#fo)"/>
  <text x="195" y="316" fill="#b04040" fontSize="8.5">B1: absorption 30→37%</text>

  {/* Stock 3: Headcount */}
  <Stock x={50} y={388} w={170} h={50} label="Headcount" sub="540 → 474"/>
  <path d="M 150,328 Q 142,356 135,388" fill="none" stroke="#3070b0" strokeWidth="2" markerEnd="url(#fl)"/>
  <text x="108" y="360" fill="#3070b0" fontSize="8.5" fontStyle="italic">net freed → FTEs</text>
  <path d="M 135,438 L 135,490" fill="none" stroke="#b04040" strokeWidth="2" markerEnd="url(#fo)"/>
  <Dl x={135} y={480}/>

  {/* Stock 4: Skill Gap */}
  <Stock x={760} y={230} w={170} h={50} label="Skill Gap" sub="sunrise skills"/>
  <path d="M 595,147 Q 720,190 760,250" fill="none" stroke="#b04040" strokeWidth="2" markerEnd="url(#fo)"/>
  <text x="695" y="188" textAnchor="middle" fill="#b04040" fontSize="9" fontStyle="italic">automation opens gap</text>
  <path d="M 930,255 L 1020,255" fill="none" stroke="#6a4" strokeWidth="2" markerEnd="url(#fg)"/>
  <text x="975" y="246" textAnchor="middle" fill="#6a4" fontSize="9" fontStyle="italic">reskilling</text>
  <Dl x={970} y={262}/>
  <path d="M 845,230 Q 850,180 750,145 Q 680,128 635,121" fill="none" stroke="#2060a0" strokeWidth="1.5" strokeDasharray="5,3" markerEnd="url(#arB)"/>
  <text x="805" y="170" fill="#2060a0" fontSize="9" fontStyle="italic">B2: gap drags adoption</text>

  {/* Stock 5: Financial */}
  <Stock x={395} y={470} w={190} h={50} label="Financial Position" sub="-$2.2M → +$4.66M"/>
  <path d="M 220,435 Q 320,465 395,490" fill="none" stroke="#6a4" strokeWidth="2" markerEnd="url(#fg)"/>
  <text x="280" y="458" fill="#6a4" fontSize="9" fontStyle="italic">salary savings</text>
  <path d="M 585,490 L 750,490" fill="none" stroke="#b04040" strokeWidth="2" markerEnd="url(#fo)"/>
  <text x="670" y="483" fill="#b04040" fontSize="9" fontStyle="italic">license + training</text>
  <path d="M 490,470 Q 485,320 505,155" fill="none" stroke="#6a4" strokeWidth="1.4" strokeDasharray="4,3" markerEnd="url(#fg)"/>
  <text x="468" y="310" fill="#6a4" fontSize="9" fontStyle="italic">R3: reinvest</text>

  {/* Stock 6: Human System */}
  <rect x="290" y="570" width="480" height="200" rx="10" fill="url(#hg)" stroke="#886633" strokeWidth="2.2" filter="url(#sh)"/>
  <text x="530" y="592" textAnchor="middle" fill="#664422" fontSize="14" fontWeight="bold" letterSpacing="1.5">HUMAN SYSTEM STATE</text>
  <text x="530" y="608" textAnchor="middle" fill="#998866" fontSize="9.5" fontStyle="italic">the binding constraint — determines realized potential</text>

  {[{x:315,y:625,l:"Proficiency",v:"25→45",c:"#6a4"},{x:460,y:625,l:"Readiness",v:"45→55",c:"#48a"},{x:605,y:625,l:"Trust",v:"35→46",c:"#a64"}].map(({x,y,l,v,c})=>
    <g key={l}><rect x={x} y={y} width="120" height="38" rx="4" fill="#fff" stroke={c} strokeWidth="1.5"/>
    <text x={x+60} y={y+16} textAnchor="middle" fill="#333" fontSize="11" fontWeight="bold">{l}</text>
    <text x={x+60} y={y+31} textAnchor="middle" fill={c} fontSize="9.5">{v}</text></g>
  )}
  {[{x:365,y:690,l:"Pol.Capital",v:"60→71",c:"#777"},{x:510,y:690,l:"Fatigue",v:"0→0",c:"#aaa"}].map(({x,y,l,v,c})=>
    <g key={l}><rect x={x} y={y} width="110" height="32" rx="4" fill="#fff" stroke={c} strokeWidth="1.2"/>
    <text x={x+55} y={y+14} textAnchor="middle" fill="#444" fontSize="10" fontWeight="bold">{l}</text>
    <text x={x+55} y={y+27} textAnchor="middle" fill={c} fontSize="9">{v}</text></g>
  )}

  {/* R2: Adoption → Proficiency */}
  <path d="M 475,147 Q 330,400 375,620" fill="none" stroke="#6a4" strokeWidth="1.6" strokeDasharray="5,3" markerEnd="url(#fg)"/>
  <text x="335" y="415" fill="#6a4" fontSize="9" fontWeight="bold">R2: practice</text>
  {/* R5: Adoption → Readiness */}
  <path d="M 535,147 Q 540,400 520,620" fill="none" stroke="#48a" strokeWidth="1.6" strokeDasharray="5,3" markerEnd="url(#arN)"/>
  <text x="555" y="415" fill="#48a" fontSize="9" fontWeight="bold">R5: success</text>
  {/* R1: Adoption → Trust */}
  <path d="M 590,147 Q 740,400 680,620" fill="none" stroke="#a64" strokeWidth="1.6" strokeDasharray="5,3" markerEnd="url(#arR)"/>
  <text x="720" y="415" fill="#a64" fontSize="9" fontWeight="bold">R1: trust</text>
  {/* B3: Disruption → Readiness */}
  <path d="M 190,438 Q 310,545 460,620" fill="none" stroke="#b04040" strokeWidth="1.3" strokeDasharray="3,3" markerEnd="url(#fo)"/>
  <text x="280" y="525" fill="#b04040" fontSize="9">B3: disruption</text>
  {/* Key feedback */}
  <path d="M 530,570 Q 530,450 Q 510,300 520,155" fill="none" stroke="#886633" strokeWidth="3" markerEnd="url(#fk)"/>
  <rect x="410" y="340" width="160" height="40" rx="5" fill="#fff9f0" stroke="#886633" strokeWidth="1.2"/>
  <text x="490" y="356" textAnchor="middle" fill="#664422" fontSize="10.5" fontWeight="bold">effective_multiplier</text>
  <text x="490" y="372" textAnchor="middle" fill="#886633" fontSize="9.5">0.35p + 0.45r + 0.20t</text>

  <rect x="30" y="790" width="1040" height="32" rx="4" fill="#f0f0f0" stroke="#ddd"/>
  <text x="550" y="810" textAnchor="middle" fill="#666" fontSize="9">Legend: ━━ Inflow | ━━ Outflow | ━━━ Key feedback | ┅┅ Reinforcing | ╌╌ Balancing | □ Stock | ▭ Delay</text>
  </svg>
);

/* ═══════════════════════════════════════
   DIAGRAM 2: CAUSAL LOOP
   ═══════════════════════════════════════ */
const CLD = () => (
  <svg viewBox="0 0 1100 840" style={{width:"100%",height:"auto"}} fontFamily="Georgia,serif"><Defs/><rect width="1100" height="840" fill="#fafafa"/>
  <text x="550" y="30" textAnchor="middle" fill="#222" fontSize="17" fontWeight="bold">CAUSAL LOOP DIAGRAM — Workforce Twin v2.1 (9 Loops)</text>
  <text x="550" y="50" textAnchor="middle" fill="#888" fontSize="12" fontStyle="italic">4 balancing + 5 reinforcing loops — "S" = same direction, "O" = opposite direction</text>
  <text x="550" y="66" textAnchor="middle" fill="#aaa" fontSize="10">CLD Rules: nouns not verbs · S and O as you go · every diagram is real · no diagram is ever finished</text>

  {/* Central hub */}
  <rect x="425" y="225" width="190" height="55" rx="8" fill="#fff" stroke="#222" strokeWidth="2.8"/>
  <text x="520" y="250" textAnchor="middle" fill="#222" fontSize="15" fontWeight="bold">AI automation</text>
  <text x="520" y="270" textAnchor="middle" fill="#222" fontSize="15" fontWeight="bold">level</text>

  {/* Human Dynamics zone */}
  <rect x="20" y="78" width="370" height="240" rx="10" fill="none" stroke="#ddd" strokeWidth="1" strokeDasharray="5,3"/>
  <text x="205" y="96" textAnchor="middle" fill="#999" fontSize="11" letterSpacing="1.5">HUMAN DYNAMICS</text>
  <text x="90" y="145" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Resistance</text>
  <text x="280" y="145" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Trust in AI</text>
  <text x="180" y="225" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Adoption rate</text>
  <text x="90" y="290" textAnchor="middle" fill="#222" fontSize="13">Disruption level</text>
  <rect x="260" y="205" width="95" height="28" rx="4" fill="#e8f0ff" stroke="#48a" strokeWidth="1.5"/>
  <text x="307" y="224" textAnchor="middle" fill="#48a" fontSize="12" fontWeight="bold">Readiness</text>

  <path d="M 110,155 Q 140,188 160,212" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={118} y={192} s="O"/>
  <path d="M 260,155 Q 230,188 205,212" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={242} y={190} s="S"/>
  <path d="M 260,222 Q 228,222 210,222" fill="none" stroke="#48a" strokeWidth="2" markerEnd="url(#arN)"/><P x={238} y={240} s="S" c="#48a"/>
  <path d="M 225,225 Q 330,238 425,248" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={330} y={232} s="S"/>
  <path d="M 430,268 Q 260,298 138,290" fill="none" stroke="#555" strokeWidth="1.8" markerEnd="url(#ar)"/><P x={290} y={298} s="S"/>
  <path d="M 90,278 L 90,158" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={73} y={218} s="S"/>
  <path d="M 430,265 Q 365,310 335,290 Q 320,270 315,236" fill="none" stroke="#48a" strokeWidth="1.8" strokeDasharray="5,3" markerEnd="url(#arN)"/>
  <text x="368" y="318" fill="#48a" fontSize="9" fontStyle="italic">success → readiness (R5 NEW)</text>

  <Lp x={138} y={180} t="B" id="3"/><Lp x={300} y={180} t="R" id="1"/>
  <g><circle cx={345} cy={265} r={14} fill="#e8f0ff" stroke="#48a" strokeWidth="1.5"/>
  <text x="345" y="269" textAnchor="middle" fill="#48a" fontSize="9.5" fontWeight="bold">R5</text></g>
  <text x="362" y="283" fill="#48a" fontSize="7" fontWeight="bold">NEW</text>

  {/* Capability zone */}
  <rect x="690" y="78" width="310" height="210" rx="10" fill="none" stroke="#ddd" strokeWidth="1" strokeDasharray="5,3"/>
  <text x="845" y="96" textAnchor="middle" fill="#999" fontSize="11" letterSpacing="1.5">CAPABILITY</text>
  <text x="750" y="145" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">AI proficiency</text>
  <text x="940" y="145" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Effective AI use</text>
  <text x="845" y="240" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Results quality</text>

  <path d="M 810,142 Q 865,130 898,138" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={858} y={128} s="S"/>
  <path d="M 925,155 Q 900,195 870,228" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={908} y={195} s="S"/>
  <path d="M 815,235 Q 780,195 758,160" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={778} y={200} s="S"/>
  <Lp x={845} y={182} t="R" id="2"/>
  <path d="M 808,248 Q 540,135 320,140" fill="none" stroke="#aaa" strokeWidth="1.5" strokeDasharray="5,3" markerEnd="url(#fL)"/>
  <text x="565" y="168" fill="#aaa" fontSize="10" fontStyle="italic">S (builds trust → R1)</text>
  <path d="M 900,157 Q 790,205 615,245" fill="none" stroke="#555" strokeWidth="1.8" markerEnd="url(#ar)"/><P x={760} y={212} s="S"/>

  {/* Skill gap */}
  <text x="810" y="340" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Skill gap</text>
  <text x="960" y="398" textAnchor="middle" fill="#222" fontSize="12" fontWeight="bold">Training</text>
  <path d="M 610,275 Q 720,305 780,332" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={700} y={305} s="S"/>
  <path d="M 835,330 Q 915,280 940,165" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={900} y={270} s="O"/>
  <path d="M 928,393 Q 878,372 842,352" fill="none" stroke="#222" strokeWidth="1.5" markerEnd="url(#ar)"/><P x={892} y={372} s="O"/>
  <Dl x={875} y={357}/><Lp x={880} y={312} t="B" id="2"/>

  {/* Capacity zone */}
  <rect x="295" y="345" width="320" height="185" rx="10" fill="none" stroke="#ddd" strokeWidth="1" strokeDasharray="5,3"/>
  <text x="455" y="363" textAnchor="middle" fill="#999" fontSize="11" letterSpacing="1.5">CAPACITY</text>
  <text x="370" y="400" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Freed capacity</text>
  <text x="550" y="400" textAnchor="middle" fill="#222" fontSize="12" fontWeight="bold">Workload/person</text>
  <text x="370" y="470" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">HC reduction</text>
  <text x="550" y="470" textAnchor="middle" fill="#222" fontSize="12" fontWeight="bold">Redistribution</text>

  <path d="M 480,280 Q 430,340 388,386" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={430} y={335} s="S"/>
  <path d="M 370,412 L 370,455" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={356} y={438} s="S"/>
  <path d="M 410,470 Q 475,475 515,470" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={470} y={485} s="S"/>
  <path d="M 550,458 L 550,415" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={565} y={440} s="S"/>
  <path d="M 515,395 Q 455,390 410,396" fill="none" stroke="#2060a0" strokeWidth="1.5" markerEnd="url(#arB)"/><P x={460} y={386} s="O" c="#2060a0"/>
  <Lp x={460} y={428} t="B" id="1"/>
  <path d="M 515,390 Q 310,318 120,158" fill="none" stroke="#aaa" strokeWidth="1.3" strokeDasharray="5,3" markerEnd="url(#fL)"/>
  <text x="302" y="310" fill="#aaa" fontSize="9.5" fontStyle="italic">S (feeds resistance)</text>

  {/* Financial zone */}
  <rect x="45" y="560" width="310" height="130" rx="10" fill="none" stroke="#ddd" strokeWidth="1" strokeDasharray="5,3"/>
  <text x="200" y="578" textAnchor="middle" fill="#999" fontSize="11" letterSpacing="1.5">FINANCIAL</text>
  <text x="130" y="618" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Cost savings</text>
  <text x="290" y="618" textAnchor="middle" fill="#222" fontSize="13" fontWeight="bold">Budget</text>
  <text x="130" y="670" textAnchor="middle" fill="#222" fontSize="12">Avg seniority</text>

  <path d="M 340,485 Q 225,535 158,603" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={240} y={545} s="S"/>
  <path d="M 175,618 Q 225,615 250,618" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={218} y={612} s="S"/>
  <path d="M 330,610 Q 440,530 520,285" fill="none" stroke="#555" strokeWidth="1.8" markerEnd="url(#ar)"/><P x={440} y={470} s="S"/>
  <Lp x={310} y={555} t="R" id="3"/>

  <path d="M 320,490 Q 195,580 145,655" fill="none" stroke="#555" strokeWidth="1.3" markerEnd="url(#ar)"/><P x={220} y={590} s="S"/>
  <path d="M 105,665 Q 45,530 45,350 Q 45,290 430,255" fill="none" stroke="#555" strokeWidth="1.3" markerEnd="url(#ar)"/><P x={38} y={420} s="O"/>
  <Lp x={72} y={470} t="B" id="4"/>

  {/* Political Capital zone */}
  <rect x="570" y="560" width="350" height="130" rx="10" fill="none" stroke="#ddd" strokeWidth="1" strokeDasharray="5,3"/>
  <text x="745" y="578" textAnchor="middle" fill="#999" fontSize="11" letterSpacing="1.5">POLITICAL CAPITAL</text>
  <text x="650" y="625" textAnchor="middle" fill="#222" fontSize="12" fontWeight="bold">Success</text>
  <text x="850" y="625" textAnchor="middle" fill="#222" fontSize="12" fontWeight="bold">Capital</text>

  <path d="M 840,250 Q 760,440 672,608" fill="none" stroke="#555" strokeWidth="1.3" markerEnd="url(#ar)"/><P x={755} y={445} s="S"/>
  <path d="M 700,625 Q 770,622 810,625" fill="none" stroke="#555" strokeWidth="2" markerEnd="url(#ar)"/><P x={762} y={618} s="S"/>
  <path d="M 850,612 Q 680,565 340,615" fill="none" stroke="#555" strokeWidth="1.3" markerEnd="url(#ar)"/><P x={600} y={580} s="S"/>
  <Lp x={780} y={600} t="R" id="4"/>

  {/* Legend */}
  <rect x="25" y="715" width="1050" height="118" rx="6" fill="#f5f5f5" stroke="#ddd"/>
  <text x="550" y="736" textAnchor="middle" fill="#222" fontSize="12" fontWeight="bold">LOOP INVENTORY — 9 Feedback Loops</text>
  <text x="50" y="755" fill="#2060a0" fontSize="10" fontWeight="bold">BALANCING (4):</text>
  <text x="50" y="770" fill="#555" fontSize="9">B1: Capacity Absorption (30→37%) · B2: Skill Valley (gap→drag) · B3: Change Resistance (disruption→readiness↓) · B4: Seniority Offset</text>
  <text x="50" y="793" fill="#a03030" fontSize="10" fontWeight="bold">REINFORCING (5):</text>
  <text x="50" y="808" fill="#555" fontSize="9">R1: Trust (success→trust↑) · R2: Proficiency (practice→skill↑) · R3: Savings (savings→reinvest) · R4: Capital (success→capital↑)</text>
  <text x="50" y="823" fill="#48a" fontSize="9.5" fontWeight="bold">R5: Readiness Boost (success→readiness↑) — NEW in v2.1, counterbalances B3</text>
  </svg>
);

/* ═══════════════════════════════════════
   DIAGRAM 3: BEHAVIOR (Reference Mode)
   ═══════════════════════════════════════ */
const BEH = () => {
  const data=[{m:0,raw:13.9,eff:4,r:45.1,p:25.1,t:35,net:0},{m:6,raw:45.7,eff:16.6,r:45.6,p:26.3,t:35.7,net:-1501},{m:12,raw:74.4,eff:28.3,r:46.9,p:29.2,t:37.2,net:-863},{m:18,raw:86.6,eff:35.1,r:48.7,p:33,t:39.3,net:179},{m:24,raw:89.4,eff:39.1,r:50.7,p:37,t:41.6,net:1525},{m:30,raw:89.9,eff:41.9,r:52.8,p:41,t:44,net:3056},{m:36,raw:90,eff:44.7,r:55.1,p:44.9,t:46.4,net:4657}];
  const W=1100,ml=80,mr=40,cw=W-ml-mr;
  const sx=m=>ml+(m/36)*cw;
  const Chart=({y0,h,yMin,yMax,title,sub,lines,zeroLine,breakeven})=>{
    const sy=v=>y0+h-((v-yMin)/(yMax-yMin))*h;
    return <g>
      <rect x={ml} y={y0} width={cw} height={h} fill="#fff" stroke="#ddd" strokeWidth="0.5"/>
      {[0,6,12,18,24,30,36].map(m=><g key={m}><line x1={sx(m)} y1={y0} x2={sx(m)} y2={y0+h} stroke="#f0f0f0" strokeWidth="0.5"/><text x={sx(m)} y={y0+h+14} textAnchor="middle" fill="#999" fontSize="8">M{m}</text></g>)}
      {Array.from({length:5},(_,i)=>yMin+(i*(yMax-yMin))/4).map(v=><g key={v}><line x1={ml} y1={sy(v)} x2={ml+cw} y2={sy(v)} stroke="#f0f0f0" strokeWidth="0.5"/><text x={ml-6} y={sy(v)+3} textAnchor="end" fill="#999" fontSize="8">{Math.round(v)}</text></g>)}
      {zeroLine && <line x1={ml} y1={sy(0)} x2={ml+cw} y2={sy(0)} stroke="#ccc" strokeWidth="1"/>}
      {breakeven && <><line x1={sx(18)} y1={y0} x2={sx(18)} y2={y0+h} stroke="#2a7a2a" strokeWidth="1.5" strokeDasharray="6,4"/><text x={sx(18)+4} y={y0+14} fill="#2a7a2a" fontSize="9" fontWeight="bold">BREAKEVEN M18</text></>}
      <text x={ml+5} y={y0-8} fill="#333" fontSize="12" fontWeight="bold">{title}</text>
      <text x={ml+5+title.length*7.5} y={y0-8} fill="#888" fontSize="10" fontStyle="italic">  {sub}</text>
      {lines.map(({key,color,dash,w=2.5,label})=><g key={key}>
        <polyline points={data.map(d=>`${sx(d.m)},${sy(d[key])}`).join(" ")} fill="none" stroke={color} strokeWidth={w} strokeDasharray={dash||"none"}/>
        <text x={sx(36)+5} y={sy(data[data.length-1][key])+4} fill={color} fontSize="9" fontWeight="bold">{label}</text>
      </g>)}
    </g>;
  };

  return <svg viewBox={`0 0 ${W} 850`} style={{width:"100%",height:"auto"}} fontFamily="Georgia,serif"><Defs/><rect width={W} height="850" fill="#fafafa"/>
    <text x="550" y="28" textAnchor="middle" fill="#222" fontSize="17" fontWeight="bold">SIMULATION BEHAVIOR — Reference Mode v2.1</text>
    <text x="550" y="48" textAnchor="middle" fill="#888" fontSize="12" fontStyle="italic">Claims, Copilot deployment, P2-Balanced — "Stocks change slowly, even when flows change suddenly"</text>
    <Chart y0={95} h={200} yMin={0} yMax={100} title="Adoption" sub="— raw S-curve vs effective"
      lines={[{key:"raw",color:"#bbb",dash:"5,3",w:1.5,label:"raw 90%"},{key:"eff",color:"#2060a0",w:2.8,label:"effective 45%"}]}/>
    <Chart y0={340} h={200} yMin={20} yMax={60} title="Human System" sub="— the three dimensions"
      lines={[{key:"r",color:"#48a",w:2.5,label:"readiness 55"},{key:"p",color:"#6a4",w:2,label:"proficiency 45"},{key:"t",color:"#a64",w:2,label:"trust 46"}]}/>
    <Chart y0={585} h={200} yMin={-2000} yMax={5000} title="Financial" sub="— net cumulative ($K)" zeroLine breakeven
      lines={[{key:"net",color:"#2a7a2a",w:2.8,label:"$4,657K"}]}/>
    <rect x="80" y="808" width="940" height="32" rx="5" fill="#f0f5ff" stroke="#ddd"/>
    <text x="550" y="828" textAnchor="middle" fill="#555" fontSize="10">540→474 HC · 66 reduced · $4.66M net · M18 breakeven · 45% Y3 adoption · 35% avg dampening</text>
  </svg>;
};

/* ═══════════════════════════════════════
   DIAGRAM 4: LOOP DOMINANCE
   ═══════════════════════════════════════ */
const DOM = () => {
  const loops=[
    {l:"B1: Absorption",c:"#5577bb",s:[30,31,32,33,34,35],y:148,note:"always on — baseline drag"},
    {l:"B2: Skill Valley",c:"#6688cc",s:[5,22,15,10,8,5],y:193,note:"peaks M6, fades with reskilling"},
    {l:"B3: Resistance",c:"#7799dd",s:[15,28,25,19,14,5],y:238,note:"fades as R5 counterbalances"},
    {l:"B4: Seniority",c:"#88aaee",s:[0,2,5,8,10,13],y:283,note:"grows slowly as pool shifts"},
  ];
  const rloops=[
    {l:"R1: Trust",c:"#cc6644",s:[3,8,15,25,32,40],y:373,note:"slow start, compounds"},
    {l:"R2: Proficiency",c:"#bb5533",s:[5,12,22,35,42,45],y:418,note:"strongest reinforcing loop"},
    {l:"R3: Savings",c:"#dd8866",s:[0,0,0,5,10,18],y:463,note:"zero until breakeven"},
    {l:"R4: Capital",c:"#ee9977",s:[6,10,18,25,30,35],y:508,note:"enables bigger moves"},
    {l:"R5: Readiness ★",c:"#cc7755",s:[3,10,20,30,35,38],y:553,note:"NEW — counterbalances B3",isNew:true},
  ];
  const xs=[100,250,400,550,700,850];
  const Bar=({x,y,w,c,opacity})=><rect x={x-55} y={y} width={w} height="22" rx="3" fill={c} opacity={opacity}/>;

  return <svg viewBox="0 0 1100 750" style={{width:"100%",height:"auto"}} fontFamily="Georgia,serif"><Defs/><rect width="1100" height="750" fill="#fafafa"/>
    <text x="550" y="28" textAnchor="middle" fill="#222" fontSize="17" fontWeight="bold">LOOP DOMINANCE — Which Loops Control the System at Each Phase</text>
    <text x="550" y="48" textAnchor="middle" fill="#888" fontSize="12" fontStyle="italic">"The behavior is determined by which loop dominates" — Meadows</text>

    <line x1="100" y1="100" x2="1000" y2="100" stroke="#333" strokeWidth="2"/>
    {[0,6,12,18,24,30,36].map((m,i)=><g key={m}><line x1={xs[i]||1000} y1="95" x2={xs[i]||1000} y2="105" stroke="#333" strokeWidth="2"/><text x={xs[i]||1000} y="120" textAnchor="middle" fill="#333" fontSize="11" fontWeight="bold">M{m}</text></g>)}
    <text x="1000" y="120" textAnchor="middle" fill="#333" fontSize="11" fontWeight="bold">M36</text>
    <line x1="1000" y1="95" x2="1000" y2="105" stroke="#333" strokeWidth="2"/>

    {[{x1:100,x2:400,c:"#c44",l:"STARTUP"},{x1:400,x2:700,c:"#2a7a2a",l:"ACCELERATION"},{x1:700,x2:1000,c:"#2060a0",l:"MATURITY"}].map(({x1,x2,c,l})=>
      <g key={l}><rect x={x1} y="68" width={x2-x1} height="25" fill={c} opacity="0.08"/><text x={(x1+x2)/2} y="84" textAnchor="middle" fill={c} fontSize="10" fontWeight="bold">{l}</text></g>
    )}

    <line x1="550" y1="60" x2="550" y2="700" stroke="#2a7a2a" strokeWidth="1" strokeDasharray="6,4"/>
    <text x="555" y="72" fill="#2a7a2a" fontSize="9" fontWeight="bold">BREAKEVEN M18</text>

    <text x="37" y="225" textAnchor="middle" fill="#2060a0" fontSize="10" fontWeight="bold" transform="rotate(-90 37 225)">BALANCING</text>
    <line x1="50" y1="140" x2="50" y2="315" stroke="#2060a0" strokeWidth="2"/>
    {loops.map(({l,c,s,y,note})=><g key={l}>
      <text x="95" y={y+15} textAnchor="end" fill="#2060a0" fontSize="10" fontWeight="bold">{l}</text>
      {s.map((v,i)=><Bar key={i} x={xs[i]} y={y} w={Math.max(2,v*1.1)} c={c} opacity={0.2+v/70}/>)}
      <text x="95" y={y+30} textAnchor="end" fill="#888" fontSize="7.5">{note}</text>
    </g>)}

    <line x1="60" y1="340" x2="1050" y2="340" stroke="#ddd" strokeWidth="1"/>
    <text x="37" y="475" textAnchor="middle" fill="#a03030" fontSize="10" fontWeight="bold" transform="rotate(-90 37 475)">REINFORCING</text>
    <line x1="50" y1="355" x2="50" y2="580" stroke="#a03030" strokeWidth="2"/>
    {rloops.map(({l,c,s,y,note,isNew})=><g key={l}>
      <text x="95" y={y+15} textAnchor="end" fill={isNew?"#48a":"#a03030"} fontSize="10" fontWeight="bold">{l}</text>
      {s.map((v,i)=><Bar key={i} x={xs[i]} y={y} w={Math.max(2,v*1.1)} c={c} opacity={0.2+v/70}/>)}
      <text x="95" y={y+30} textAnchor="end" fill={isNew?"#48a":"#888"} fontSize="7.5" fontWeight={isNew?"bold":"normal"}>{note}</text>
    </g>)}

    <rect x="100" y="610" width="900" height="50" rx="6" fill="#fff" stroke="#ddd"/>
    <text x="550" y="628" textAnchor="middle" fill="#333" fontSize="11" fontWeight="bold">NET BALANCE OF FORCES</text>
    {[{x:175,l:"B ≫ R",s:"stuck",c:"#c44"},{x:325,l:"B > R",s:"slow",c:"#c44"},{x:475,l:"B ≈ R",s:"tipping",c:"#886"},{x:625,l:"R > B",s:"breakeven",c:"#2a7a2a"},{x:775,l:"R > B",s:"growing",c:"#2a7a2a"},{x:925,l:"R ≥ B",s:"stable",c:"#2060a0"}].map(({x,l,s,c})=>
      <g key={x}><text x={x} y={644} textAnchor="middle" fill={c} fontSize="11" fontWeight="bold">{l}</text><text x={x} y={656} textAnchor="middle" fill={c} fontSize="8.5">{s}</text></g>
    )}

    <rect x="100" y="680" width="900" height="55" rx="5" fill="#f8f8f8" stroke="#eee"/>
    <text x="550" y="700" textAnchor="middle" fill="#444" fontSize="11" fontWeight="bold">KEY INSIGHT</text>
    <text x="550" y="716" textAnchor="middle" fill="#666" fontSize="10">System flips from balancing- to reinforcing-dominant around M12-M18.</text>
    <text x="550" y="730" textAnchor="middle" fill="#2a7a2a" fontSize="10" fontWeight="bold">Before: stuck. After: momentum builds on itself.</text>
  </svg>;
};

/* ═══════════════════════════════════════
   DIAGRAM 5: MODEL EVOLUTION
   ═══════════════════════════════════════ */
const EVO = () => {
  const fixes = [
    {y:152,title:"FIX 1: effective_multiplier — Product → Weighted Blend",
     principle:"First Principle: Correlated dimensions, not independent events.",
     v1:"(p/100)×(r/100) = 0.1125",v2:"(0.35p+0.45r+0.20t)/100 = 0.360",
     impact:"3.2× increase. Alone flips 1→16 scenarios."},
    {y:246,title:"FIX 2: trust_multiplier — Linear → Smooth Threshold",
     principle:"Second-Order: Trust=35 ≠ 42% refuse to work.",
     v1:"min(1.0, trust/60) = 0.583",v2:"smooth band interpolation = 0.800",
     impact:"1.4× increase. Removes discontinuities."},
    {y:340,title:"FIX 3: R5 Readiness Boost — Missing Reinforcing Loop",
     principle:"Meadows: Every stock needs inflow AND outflow.",
     v1:"Δready = -resistance + 0.08",v2:"+ adoption_boost × (1-r/100)",
     impact:"5× faster readiness growth. Adds a new loop."},
    {y:434,title:"FIX 4: B1 Absorption — Off-by-One Error",
     principle:"First Principle: Zero reduction = zero overload.",
     v1:"overload = 1.0+ratio → 43.3%",v2:"overload = ratio → 30.0%",
     impact:"13% more capacity converts to FTEs."},
    {y:528,title:"FIX 5: R3 Savings — Connecting Dead Loop",
     principle:"Systems: Disconnected loop = no loop.",
     v1:"// (future iterations)",v2:"boost = r3_reinvestment(savings)",
     impact:"Small but completes savings flywheel."},
  ];

  return <svg viewBox="0 0 1100 780" style={{width:"100%",height:"auto"}} fontFamily="Georgia,serif"><Defs/><rect width="1100" height="780" fill="#fafafa"/>
    <text x="550" y="28" textAnchor="middle" fill="#222" fontSize="17" fontWeight="bold">MODEL EVOLUTION — From Broken to Realistic in 5 Fixes</text>
    <text x="550" y="48" textAnchor="middle" fill="#888" fontSize="12" fontStyle="italic">Each fix traces to a specific first-principles error — ~50 lines changed, 2 files</text>

    {[{x:55,l:"v1 ORIGINAL",s:"1/40 · -$214M",c:"#c44",bg:"#fff5f5"},{x:405,l:"v2 MULT FIX",s:"16/40 · +$28M",c:"#886622",bg:"#fff8f0"},{x:755,l:"v2.1 ALL FIXES",s:"25/40 · +$114M",c:"#2a7a2a",bg:"#f0fff0"}].map(({x,l,s,c,bg})=>
      <g key={l}><rect x={x} y="80" width="290" height="48" rx="6" fill={bg} stroke={c} strokeWidth="2"/>
      <text x={x+145} y="100" textAnchor="middle" fill={c} fontSize="14" fontWeight="bold">{l}</text>
      <text x={x+145} y="118" textAnchor="middle" fill={c} fontSize="10.5">{s}</text></g>
    )}
    <path d="M 350,104 L 400,104" fill="none" stroke="#886622" strokeWidth="2.5" markerEnd="url(#ar)"/>
    <path d="M 700,104 L 750,104" fill="none" stroke="#2a7a2a" strokeWidth="2.5" markerEnd="url(#fg)"/>

    {fixes.map(({y,title,principle,v1,v2,impact})=><g key={y}>
      <rect x="50" y={y} width="1000" height="78" rx="5" fill="#fff" stroke="#ddd" strokeWidth="0.5"/>
      <text x="68" y={y+17} fill="#333" fontSize="11.5" fontWeight="bold">{title}</text>
      <text x="68" y={y+33} fill="#888" fontSize="9" fontStyle="italic">{principle}</text>
      <rect x="68" y={y+40} width="300" height="20" rx="3" fill="#fff5f5"/>
      <text x="78" y={y+54} fill="#c44" fontSize="9.5" fontFamily="Courier New,monospace">{v1}</text>
      <text x="380" y={y+54} fill="#886622" fontSize="14" fontWeight="bold">→</text>
      <rect x="400" y={y+40} width="320" height="20" rx="3" fill="#f0fff0"/>
      <text x="410" y={y+54} fill="#2a7a2a" fontSize="9.5" fontFamily="Courier New,monospace">{v2}</text>
      <text x="740" y={y+54} fill="#333" fontSize="9.5" fontWeight="bold">{impact}</text>
    </g>)}

    <rect x="50" y="630" width="1000" height="130" rx="6" fill="#f0f5ff" stroke="#2060a0" strokeWidth="1.5"/>
    <text x="550" y="655" textAnchor="middle" fill="#222" fontSize="14" fontWeight="bold">COMBINED: 5 fixes, ~50 lines, fundamental improvement</text>
    {[{x:170,m:"Profitable",v1:"1/40",v2:"25/40"},{x:370,m:"Net savings",v1:"-$1.75M",v2:"+$4.66M"},{x:550,m:"Breakeven",v1:"Never",v2:"Month 18"},{x:730,m:"Y3 adoption",v1:"8%",v2:"45%"},{x:930,m:"Readiness Δ",v1:"+1.9",v2:"+10.0"}].map(({x,m,v1,v2})=>
      <g key={m}><text x={x} y={680} textAnchor="middle" fill="#666" fontSize="9">{m}</text>
      <text x={x} y={698} textAnchor="middle" fill="#c44" fontSize="10">{v1}</text>
      <text x={x} y={710} textAnchor="middle" fill="#555" fontSize="8">↓</text>
      <text x={x} y={726} textAnchor="middle" fill="#2a7a2a" fontSize="12" fontWeight="bold">{v2}</text></g>
    )}
    <text x="550" y="755" textAnchor="middle" fill="#886633" fontSize="10" fontStyle="italic">"The least obvious part of the system, its function or purpose, is often the most crucial determinant" — Meadows</text>
  </svg>;
};

/* ═══════════════════════════════════════
   MAIN APP
   ═══════════════════════════════════════ */
export default function App() {
  const [tab, setTab] = useState("sfd");
  const diagrams = { sfd: <SFD/>, cld: <CLD/>, beh: <BEH/>, dom: <DOM/>, evo: <EVO/> };

  return (
    <div style={{fontFamily:"Georgia,serif",background:"#f5f5f5",minHeight:"100vh"}}>
      <div style={{background:"#1a1a1a",padding:"10px 20px",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
        <div><span style={{color:"#fff",fontSize:15,fontWeight:"bold",letterSpacing:1.5}}>WORKFORCE TWIN</span>
        <span style={{color:"#777",fontSize:11,marginLeft:12}}>System Model & Simulation</span></div>
        <span style={{color:"#555",fontSize:10}}>v2.1 · 9 loops · 6 stocks · 12 flows</span>
      </div>
      <div style={{display:"flex",gap:0,borderBottom:"2px solid #ddd",background:"#fff",overflowX:"auto"}}>
        {TABS.map(({id,label,desc})=>(
          <button key={id} onClick={()=>setTab(id)} style={{
            padding:"8px 16px",fontSize:12,fontFamily:"Georgia,serif",
            fontWeight:tab===id?"bold":"normal",color:tab===id?"#222":"#888",
            background:tab===id?"#fafafa":"#fff",border:"none",
            borderBottom:tab===id?"3px solid #333":"3px solid transparent",
            cursor:"pointer",whiteSpace:"nowrap",minWidth:0
          }}><div>{label}</div><div style={{fontSize:9,color:"#aaa"}}>{desc}</div></button>
        ))}
      </div>
      <div style={{padding:"4px 8px",maxWidth:1200,margin:"0 auto"}}>{diagrams[tab]}</div>
      <div style={{textAlign:"center",padding:"8px",color:"#bbb",fontSize:9,borderTop:"1px solid #eee"}}>
        Etter · "A system is an interconnected set of elements coherently organized to achieve something" — Meadows
      </div>
    </div>
  );
}
