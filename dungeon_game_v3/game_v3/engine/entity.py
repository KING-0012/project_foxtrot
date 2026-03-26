import uuid,random
from typing import Any,Dict,List,Optional
from engine import registry

class Component:
    def __init__(self,**kwargs):
        for k,v in kwargs.items():setattr(self,k,v)

class Entity:
    def __init__(self,eid:Optional[str]=None):
        self.eid=eid or str(uuid.uuid4())[:8]
        self._components:Dict[str,Component]={}
    def add(self,name:str,component:Component)->"Entity":
        self._components[name]=component;return self
    def get(self,name:str)->Optional[Component]:return self._components.get(name)
    def has(self,name:str)->bool:return name in self._components
    def remove(self,name:str):self._components.pop(name,None)

# ---- NPC Profile ----
# Core schema. Any LLM can call register_npc_profile_extension({field:default,...}) to add fields.
_BASE_PROFILE={
    "name":"Unknown",
    "age":25,
    "appearance":"plain",          # expandable: hair, eyes, height, etc.
    "personality":{                # trait dict — add traits freely
        "brave":0.5,"kind":0.5,"flirty":0.0,"aggressive":0.0,
        "shy":0.0,"curious":0.5,"loyal":0.5,"greedy":0.0,
    },
    "occupation":"wanderer",
    "faction":None,                 # expandable
    "backstory":"",
    "secrets":[],                   # list of strings
    "mood":"neutral",               # neutral|happy|angry|sad|scared|excited|suspicious
    "relationship":{                # player→npc
        "affinity":0,               # -100 to 100
        "trust":0,                  # -100 to 100
        "romance":0,                # 0-100
        "fear":0,                   # 0-100
        "history":[],               # log of interactions
        "status":"stranger",        # stranger|acquaintance|friend|close|romantic|rival|enemy
    },
    "party_member":False,
    "alive":True,
    "tags":[],                      # free tags for LLM use
    "inventory":[],
    "dialogue_key":"generic",       # maps to dialogue system
    "memory":[],                    # list of {event,timestamp,sentiment}
}

def make_npc_profile(**overrides)->Dict:
    import copy
    p=copy.deepcopy(_BASE_PROFILE)
    # apply registered extensions
    for ext in registry.get_npc_profile_extensions():
        for k,v in ext.items():
            if k not in p:p[k]=copy.deepcopy(v)
    _deep_update(p,overrides)
    return p

def _deep_update(d:Dict,u:Dict):
    for k,v in u.items():
        if isinstance(v,dict) and isinstance(d.get(k),dict):_deep_update(d[k],v)
        else:d[k]=v

def update_relationship(profile:Dict,affinity:int=0,trust:int=0,romance:int=0,
                         fear:int=0,event:str="",sentiment:str="neutral"):
    r=profile["relationship"]
    r["affinity"]=max(-100,min(100,r["affinity"]+affinity))
    r["trust"]=max(-100,min(100,r["trust"]+trust))
    r["romance"]=max(0,min(100,r["romance"]+romance))
    r["fear"]=max(0,min(100,r["fear"]+fear))
    if event:
        r["history"].append(event)
        profile["memory"].append({"event":event,"sentiment":sentiment})
    _recalculate_status(r)

def _recalculate_status(r:Dict):
    a,t,ro,fe=r["affinity"],r["trust"],r["romance"],r["fear"]
    if a<=-50 or t<=-40:r["status"]="enemy"
    elif fe>=60:r["status"]="afraid"
    elif ro>=60:r["status"]="romantic"
    elif a>=70 and t>=50:r["status"]="close"
    elif a>=40 and t>=20:r["status"]="friend"
    elif a>=10 or t>=10:r["status"]="acquaintance"
    else:r["status"]="stranger"

# ---- Player entity ----
def make_player(name:str)->Entity:
    p=Entity(eid="player")
    p.add("stats",Component(
        name=name,hp=100,max_hp=100,
        atk=10,defense=5,
        gold=50,level=1,xp=0,xp_next=100,
    ))
    p.add("inventory",Component(items=[],equipped={"weapon":None,"armor":None,"accessory":None}))
    p.add("flags",Component(flags={}))  # game flags for quests etc.
    p.add("party",Component(members=[]))
    return p

# ---- NPC entity ----
FEMALE_NAMES=["Aria","Sable","Lyra","Mira","Vex","Cira","Zoe","Nael","Tessa","Rin",
              "Hana","Raven","Cass","Elia","Faye","Kira","Mona","Nyx","Pris","Sora"]
OCCUPATIONS=["guard","merchant","innkeeper","barmaid","thief","mage","adventurer",
              "blacksmith","healer","assassin","noble","beggar","dancer","scholar"]

def make_random_npc(name:Optional[str]=None,occupation:Optional[str]=None,
                    personality_overrides:Optional[Dict]=None)->Entity:
    npc=Entity()
    chosen_name=name or random.choice(FEMALE_NAMES)
    chosen_occ=occupation or random.choice(OCCUPATIONS)
    pers={"brave":round(random.random(),2),"kind":round(random.random(),2),
          "flirty":round(random.random(),2),"aggressive":round(random.random(),2),
          "shy":round(random.random(),2),"curious":round(random.random(),2),
          "loyal":round(random.random(),2),"greedy":round(random.random(),2)}
    if personality_overrides:pers.update(personality_overrides)
    profile=make_npc_profile(name=chosen_name,occupation=chosen_occ,personality=pers)
    npc.add("profile",Component(**profile))
    npc.add("combat",Component(
        hp=random.randint(20,60),max_hp=random.randint(20,60),
        atk=random.randint(3,12),defense=random.randint(1,6),
        hostile=False,loot_table="npc_basic",
    ))
    return npc

# ---- Enemy entity ----
ENEMY_TYPES={
    "goblin":   {"hp":20,"atk":5,"defense":2,"reward_gold":(5,15),"xp":20,"loot_table":"goblin"},
    "orc":      {"hp":40,"atk":10,"defense":4,"reward_gold":(10,25),"xp":40,"loot_table":"orc"},
    "slime":    {"hp":12,"atk":3,"defense":1,"reward_gold":(2,8),"xp":10,"loot_table":"slime"},
    "witch":    {"hp":30,"atk":14,"defense":2,"reward_gold":(15,35),"xp":55,"loot_table":"magic"},
    "bandit":   {"hp":35,"atk":9,"defense":5,"reward_gold":(20,50),"xp":45,"loot_table":"bandit"},
    "skeleton": {"hp":25,"atk":7,"defense":6,"reward_gold":(5,12),"xp":30,"loot_table":"undead"},
    "spider":   {"hp":18,"atk":8,"defense":1,"reward_gold":(3,10),"xp":22,"loot_table":"beast"},
    "dragon":   {"hp":200,"atk":30,"defense":15,"reward_gold":(200,500),"xp":300,"loot_table":"dragon"},
}

def make_enemy(etype:str)->Entity:
    base=ENEMY_TYPES.get(etype,ENEMY_TYPES["goblin"]).copy()
    e=Entity()
    mn,mx=base.pop("reward_gold")
    e.add("profile",Component(name=etype.capitalize(),type=etype,alive=True))
    base["max_hp"]=base["hp"]
    e.add("combat",Component(gold=random.randint(mn,mx),**base))
    return e
