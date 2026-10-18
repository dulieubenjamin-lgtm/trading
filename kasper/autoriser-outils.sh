#!/bin/bash
# Autorise les outils dont la veille a besoin et BLOQUE ceux qui effacent
# (dessins, alertes) ou modifient les scripts Pine. Ajoute aux reglages
# existants de ~/claudeverstradingview/.claude/settings.local.json sans rien retirer.
mkdir -p "$HOME/claudeverstradingview/.claude"
node -e '
const fs=require("fs");
const p=process.env.HOME+"/claudeverstradingview/.claude/settings.local.json";
let s={};try{s=JSON.parse(fs.readFileSync(p,"utf8"))}catch(e){}
if(fs.existsSync(p))fs.copyFileSync(p,p+".bak");
s.permissions=s.permissions||{};
const tv="mcp__claudeverstradingview__";
const allow=["mcp__obscanner",
 ...["tv_health_check","tv_ui_state","quote_get","symbol_info","chart_get_state","chart_set_symbol","chart_set_timeframe","data_get_pine_boxes","data_get_ohlcv","alert_list","alert_create","draw_shape","draw_list","capture_screenshot","ui_keyboard","ui_click","ui_mouse_click","ui_find_element","ui_type_text"].map(t=>tv+t),
 "Read(//Users/benji/claudeverstradingview/**)","Read(//Users/benji/trading/kasper/**)"];
const deny=[...["draw_clear","draw_remove_one","alert_delete","morning_brief","pine_set_source","pine_save","pine_new","pine_smart_compile","replay_trade","layout_switch","tab_close"].map(t=>tv+t),
 "Bash(node scalper-run.js:*)","Bash(node ./scalper-run.js:*)"];
const add=(k,l)=>{s.permissions[k]=[...new Set([...(s.permissions[k]||[]),...l])]};
add("allow",allow);add("deny",deny);
s.permissions.allow=s.permissions.allow.filter(r=>!deny.includes(r));
fs.writeFileSync(p,JSON.stringify(s,null,2)+"\n");
console.log("OK :",s.permissions.allow.length,"outils autorises,",s.permissions.deny.length,"bloques.");
console.log("Bloques :",deny.map(d=>d.replace(tv,"")).join(", "));'
