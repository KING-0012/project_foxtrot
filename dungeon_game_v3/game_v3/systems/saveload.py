import json,os,copy
from engine.core import state

SAVE_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"saves")
SAVE_VERSION=2

# ---- Defaults used when loading an older save that's missing fields ----
_PLAYER_STAT_DEFAULTS={"name":"Hero","hp":100,"max_hp":100,"atk":10,"defense":5,
    "gold":50,"level":1,"xp":0,"xp_next":100}
_PLAYER_INV_DEFAULTS={"items":[],"equipped":{"weapon":None,"armor":None,"accessory":None}}
_PLAYER_FLAGS_DEFAULTS={"flags":{}}
_PLAYER_PARTY_DEFAULTS={"members":[]}

def _merge(target_obj,saved:dict,defaults:dict):
    for k,default in defaults.items():
        val=saved.get(k,default)
        setattr(target_obj,k,copy.deepcopy(val))

def _component_to_dict(comp)->dict:
    return copy.deepcopy(comp.__dict__)

def save_game(slot:str="slot1")->str:
    try:
        ps=state.player.get("stats")
        inv=state.player.get("inventory")
        flags=state.player.get("flags")
        party=state.player.get("party")
        npcs={}
        for k,npc in state.npcs.items():
            p=npc.get("profile")
            npcs[k]=copy.deepcopy(p.__dict__)
        dialogue_state=copy.deepcopy(getattr(state,"dialogue_state",{}))
        data={
            "version":SAVE_VERSION,
            "player":{
                "stats":_component_to_dict(ps),
                "inventory":_component_to_dict(inv),
                "flags":_component_to_dict(flags),
                "party":_component_to_dict(party),
            },
            "npcs":npcs,
            "dialogue_state":dialogue_state,
            "current_room":state.world.current_key if state.world else "town_square",
            "turn":state.turn,
            "flags":state.flags,
        }
        os.makedirs(SAVE_DIR,exist_ok=True)
        path=os.path.join(SAVE_DIR,f"{slot}.json")
        with open(path,"w") as f:json.dump(data,f,indent=2)
        return f"Game saved to {slot}."
    except Exception as e:
        return f"Save failed: {e}"

def load_game(slot:str="slot1")->str:
    path=os.path.join(SAVE_DIR,f"{slot}.json")
    if not os.path.exists(path):return f"No save found: {slot}."
    try:
        with open(path) as f:data=json.load(f)
        v=data.get("version",1)
        pdata=data.get("player",{})
        # load player — merge with defaults so missing fields don't crash
        _merge(state.player.get("stats"),pdata.get("stats",{}),_PLAYER_STAT_DEFAULTS)
        _merge(state.player.get("inventory"),pdata.get("inventory",{}),_PLAYER_INV_DEFAULTS)
        _merge(state.player.get("flags"),pdata.get("flags",{}),_PLAYER_FLAGS_DEFAULTS)
        _merge(state.player.get("party"),pdata.get("party",{}),_PLAYER_PARTY_DEFAULTS)
        # load NPC profiles — merge with current profile (so new fields survive)
        for name,saved_profile in data.get("npcs",{}).items():
            npc=state.get_npc(name)
            if npc:
                p=npc.get("profile")
                for fk,fv in saved_profile.items():
                    try:setattr(p,fk,copy.deepcopy(fv))
                    except:pass
        # restore dialogue state
        if hasattr(state,"dialogue_state"):
            state.dialogue_state.update(data.get("dialogue_state",{}))
        else:
            state.dialogue_state=data.get("dialogue_state",{})
        if state.world:state.world.current_key=data.get("current_room","town_square")
        state.turn=data.get("turn",0)
        state.flags=data.get("flags",{})
        note="" if v==SAVE_VERSION else f" (migrated from v{v})"
        return f"Game loaded from {slot}.{note}"
    except Exception as e:
        return f"Load failed: {e}"

def list_saves()->str:
    os.makedirs(SAVE_DIR,exist_ok=True)
    slots=[f for f in os.listdir(SAVE_DIR) if f.endswith(".json")]
    if not slots:return "No saves found."
    lines=["Saves:"]
    for s in sorted(slots):
        path=os.path.join(SAVE_DIR,s)
        try:
            with open(path) as f:d=json.load(f)
            pname=d.get("player",{}).get("stats",{}).get("name","?")
            lvl=d.get("player",{}).get("stats",{}).get("level","?")
            turn=d.get("turn","?")
            lines.append(f"  {s[:-5]:<12} — {pname} LV{lvl} turn:{turn}")
        except:
            lines.append(f"  {s[:-5]:<12} — (corrupt)")
    return "\n".join(lines)
