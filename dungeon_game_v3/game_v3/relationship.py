from typing import Optional,Dict,Any
from engine import registry
from engine.entity import update_relationship
from engine.core import state,bus

def _npc(name:str):
    npc=state.get_npc(name)
    if not npc:return None,None
    p=npc.get("profile")
    return npc,p

def _mood_modifier(p)->float:
    mods={"happy":1.3,"excited":1.2,"neutral":1.0,"suspicious":0.7,"sad":0.8,"angry":0.5,"scared":0.4}
    return mods.get(p.mood,1.0)

def _check_condition(action_key:str,p)->bool:
    a=registry.get_relationship_action(action_key)
    if not a:return False
    if a["condition"] and not a["condition"](p):return False
    return True

def do_relationship_action(action_key:str,npc_name:str,**kwargs)->str:
    npc,p=_npc(npc_name)
    if p is None:return f"No one named {npc_name} here."
    action=registry.get_relationship_action(action_key)
    if not action:return f"Unknown action: {action_key}"
    if action["condition"] and not action["condition"](p.__dict__):
        return f"Can't do that with {p.name} right now."
    result=action["fn"](p.__dict__,**kwargs)
    bus.emit("relationship_action",action=action_key,npc=npc_name,result=result)
    return result

def get_available_actions(npc_name:str)->Dict[str,Dict]:
    npc,p=_npc(npc_name)
    if p is None:return {}
    available={}
    for k,v in registry.get_relationship_actions().items():
        if v["condition"] is None or v["condition"](p.__dict__):
            available[k]=v
    return available

def get_relationship_status(npc_name:str)->str:
    npc,p=_npc(npc_name)
    if p is None:return f"{npc_name} not found."
    r=p.relationship
    return (f"{p.name} — Status: {r['status']} | "
            f"Affinity:{r['affinity']:+d} Trust:{r['trust']:+d} "
            f"Romance:{r['romance']} Fear:{r['fear']}")

registry.register_system("relationship",{
    "do":do_relationship_action,
    "available":get_available_actions,
    "status":get_relationship_status,
})
