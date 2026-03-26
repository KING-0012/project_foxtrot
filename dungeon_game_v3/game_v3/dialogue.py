from typing import Dict,List,Callable,Optional,Any
from engine import registry
from engine.core import state

# Tree node schema:
# { "text": str, "options": [(label, next_key, Optional[Callable(profile)->bool])],
#   "on_enter": Optional[Callable(profile_dict)],
#   "on_exit": Optional[Callable(profile_dict)] }
#
# Stateful: each NPC tracks its current node in state.dialogue_state[npc_name]
# "end" key always terminates and resets to "start"

_TREES:Dict[str,Dict]={}
# state.dialogue_state: Dict[npc_name, current_node_key]  (set lazily)

def register_dialogue_tree(key:str,tree:Dict):_TREES[key]=tree
def get_tree(key:str)->Optional[Dict]:return _TREES.get(key)

def _ds()->Dict:
    if not hasattr(state,"dialogue_state"):state.dialogue_state={}
    return state.dialogue_state

def _get_node(tree:Dict,key:str)->Optional[Dict]:
    return tree.get(key)

def _render(npc_name:str,p,node:Dict)->str:
    text=node["text"].format(name=p.name,occupation=p.occupation,mood=p.mood,
                              **{k:getattr(p,k,"") for k in ["backstory","faction"] if hasattr(p,k)})
    opts=_filter_options(node.get("options",[]),p.__dict__)
    lines=[f"{p.name}: \"{text}\""]
    for i,(label,_,_) in enumerate(opts,1):lines.append(f"  {i}. {label}")
    if not opts:lines.append("  (no options — conversation ends)")
    return "\n".join(lines)

def start_dialogue(npc_name:str)->str:
    npc=state.get_npc(npc_name)
    if not npc:return f"No one named {npc_name}."
    p=npc.get("profile")
    if p.mood=="angry":return f"{p.name} turns away. 'Don't talk to me.'"
    key=p.dialogue_key
    tree=_TREES.get(key) or _TREES.get("generic")
    if not tree:return f"{p.name} has nothing to say."
    # Resume from current node if mid-conversation, else start fresh
    cur_key=_ds().get(npc_name,"start")
    node=_get_node(tree,cur_key) or _get_node(tree,"start")
    if cur_key=="start" or not node:
        cur_key="start"
        node=_get_node(tree,"start")
        if not node:return "..."
    if node.get("on_enter"):node["on_enter"](p.__dict__)
    _ds()[npc_name]=cur_key
    return _render(npc_name,p,node)

def choose_option(npc_name:str,choice:int)->str:
    npc=state.get_npc(npc_name)
    if not npc:return "Not found."
    p=npc.get("profile")
    key=p.dialogue_key
    tree=_TREES.get(key) or _TREES.get("generic")
    if not tree:return "..."
    cur_key=_ds().get(npc_name,"start")
    node=_get_node(tree,cur_key)
    if not node:return "..."
    opts=_filter_options(node.get("options",[]),p.__dict__)
    if choice<1 or choice>len(opts):return f"Choose 1-{len(opts)}."
    label,next_key,_=opts[choice-1]
    if node.get("on_exit"):node["on_exit"](p.__dict__)
    if next_key=="end":
        _ds()[npc_name]="start"
        return f"(You say goodbye to {p.name}.)"
    next_node=_get_node(tree,next_key)
    if not next_node:
        _ds()[npc_name]="start"
        return "..."
    if next_node.get("on_enter"):next_node["on_enter"](p.__dict__)
    _ds()[npc_name]=next_key
    return _render(npc_name,p,next_node)

def reset_dialogue(npc_name:str):
    _ds()[npc_name]="start"

def _filter_options(options:List,profile:Dict)->List:
    return [(l,k,c) for l,k,c in options if c is None or c(profile)]

# ---- Built-in trees ----
from engine.entity import update_relationship

register_dialogue_tree("generic",{
    "start":{
        "text":"Oh, hello there. Something I can help you with?",
        "on_enter":None,
        "options":[
            ("Just saying hi","just_hi",None),
            ("Tell me about yourself","about",None),
            ("What's going on in town?","rumors",None),
            ("Goodbye","end",None),
        ]
    },
    "just_hi":{
        "text":"Ha. Well, hi then. I'm {name}.",
        "on_enter":lambda p:update_relationship(p,affinity=2,event="said hello"),
        "options":[
            ("Nice to meet you, {name}... tell me more.","about",None),
            ("Take care.","end",None),
        ]
    },
    "about":{
        "text":"Me? I'm a {occupation}. It's a living. Some days better than others.",
        "on_enter":lambda p:update_relationship(p,affinity=3,trust=2,event="asked about me"),
        "options":[
            ("That sounds hard","empathy",None),
            ("Have you heard any rumors?","rumors",lambda p:p["relationship"]["affinity"]>=5),
            ("Cool. Bye.","end",None),
        ]
    },
    "empathy":{
        "text":"...Yeah. But it's mine. Thanks for asking.",
        "on_enter":lambda p:update_relationship(p,affinity=5,trust=4,event="showed empathy"),
        "options":[
            ("What have you heard around town?","rumors",None),
            ("Goodbye.","end",None),
        ]
    },
    "rumors":{
        "text":"Not much I know about. Though... I've heard strange things from the dungeon lately.",
        "on_enter":lambda p:update_relationship(p,affinity=2,event="chatted about rumors"),
        "options":[
            ("Strange how?","rumors_detail",lambda p:p["relationship"]["trust"]>=5),
            ("Interesting. Thanks.","end",None),
        ]
    },
    "rumors_detail":{
        "text":"People going in and not coming out. More than usual. Stay careful down there.",
        "on_enter":lambda p:update_relationship(p,trust=3,event="shared dungeon warning"),
        "options":[("I'll be careful. Thanks.","end",None)]
    },
})

register_dialogue_tree("innkeeper",{
    "start":{
        "text":"Welcome to the Wanderer's Inn! Rest, food, or just a drink?",
        "on_enter":None,
        "options":[
            ("I'd like a room","room",None),
            ("Just a drink","drink",None),
            ("Tell me about this place","about_inn",None),
            ("You seem like you've seen a lot...","personal",lambda p:p["relationship"]["affinity"]>=20),
            ("Goodbye","end",None),
        ]
    },
    "room":{
        "text":"10 gold a night. I'll put it on your tab.",
        "on_enter":lambda p:update_relationship(p,affinity=2,trust=3,event="rented room"),
        "options":[("Thanks, Mira.","end",None)]
    },
    "drink":{
        "text":"Coming right up. House wine or the strong stuff?",
        "on_enter":lambda p:update_relationship(p,affinity=3,event="ordered drink"),
        "options":[
            ("Strong stuff.","drink_strong",None),
            ("Wine, please.","drink_wine",None),
        ]
    },
    "drink_strong":{
        "text":"Good choice. That'll put hair on your... well. Here you go.",
        "on_enter":lambda p:update_relationship(p,affinity=4,event="shared a strong drink"),
        "options":[("Cheers.","end",None)]
    },
    "drink_wine":{
        "text":"Fine taste. I keep the good ones in the back.",
        "on_enter":lambda p:update_relationship(p,affinity=3,event="shared wine"),
        "options":[("Lovely.","start",None)]  # loops back — keep chatting
    },
    "about_inn":{
        "text":"My mother ran this place before me. Twenty years I've kept the lights on. Never closed, not once.",
        "on_enter":lambda p:update_relationship(p,trust=5,affinity=4,event="heard innkeeper's story"),
        "options":[
            ("That's impressive.","impressive",None),
            ("Do you ever miss her?","miss_mother",lambda p:p["relationship"]["trust"]>=15),
            ("Interesting. Thanks.","end",None),
        ]
    },
    "impressive":{
        "text":"*smiles quietly* It is, isn't it. Come back anytime.",
        "on_enter":lambda p:update_relationship(p,trust=6,affinity=6,event="praised innkeeper"),
        "options":[
            ("I always will.","end",None),
            ("Tell me more about yourself.","personal",lambda p:p["relationship"]["affinity"]>=20),
        ]
    },
    "miss_mother":{
        "text":"Every day. She used to say — 'Mira, a warm inn is a warm heart.' I think about that a lot.",
        "on_enter":lambda p:update_relationship(p,trust=10,affinity=8,romance=5,event="Mira shared about her mother"),
        "options":[
            ("She sounds wonderful.","mother_wonderful",None),
            ("I'm sorry for your loss.","end",None),
        ]
    },
    "mother_wonderful":{
        "text":"She was. *pauses* You're easy to talk to, you know that?",
        "on_enter":lambda p:update_relationship(p,trust=8,romance=8,affinity=6,event="Mira opened up"),
        "options":[("So are you, Mira.","end",None)]
    },
    "personal":{
        "text":"*leans on the counter* What do you want to know?",
        "on_enter":lambda p:update_relationship(p,affinity=3,event="Mira willing to open up"),
        "options":[
            ("Do you ever get lonely running this place?","lonely",None),
            ("What do you do when the inn closes?","after_hours",lambda p:p["relationship"]["trust"]>=20),
            ("Nothing. Never mind.","end",None),
        ]
    },
    "lonely":{
        "text":"...Sometimes. But then someone interesting walks in. *glances at you* And it's fine.",
        "on_enter":lambda p:update_relationship(p,romance=10,trust=8,affinity=6,event="Mira admitted loneliness"),
        "options":[("I'm glad I walked in.","end",None)]
    },
    "after_hours":{
        "text":"I sit by the fire and read. Boring answer, I know. But it's mine.",
        "on_enter":lambda p:update_relationship(p,trust=10,affinity=5,event="Mira shared private routine"),
        "options":[
            ("I'd like to join you someday.","join_fire",lambda p:p["relationship"]["romance"]>=20),
            ("Sounds peaceful.","end",None),
        ]
    },
    "join_fire":{
        "text":"*very quiet for a moment* ...Maybe you could. Bring wine.",
        "on_enter":lambda p:update_relationship(p,romance=15,trust=10,affinity=8,event="Mira invited player for evening"),
        "options":[("I'll bring the good stuff.","end",None)]
    },
})

registry.register_system("dialogue",{
    "start":start_dialogue,
    "choose":choose_option,
    "reset":reset_dialogue,
    "register":register_dialogue_tree,
    "get_tree":get_tree,
})
