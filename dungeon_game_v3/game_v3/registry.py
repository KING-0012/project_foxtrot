from typing import Callable,Any,Dict,List,Optional
_systems:Dict[str,Any]={}
_actions:Dict[str,Callable]={}
_menu_pages:Dict[str,Dict]={}
_hooks:Dict[str,List[Callable]]={}
_npc_profile_extensions:List[Dict]=[]
_combat_actions:Dict[str,Callable]={}
_loot_tables:Dict[str,Callable]={}
_relationship_actions:Dict[str,Dict]={}

def register_system(name:str,system:Any):_systems[name]=system
def get_system(name:str):return _systems.get(name)
def all_systems()->Dict:return _systems

def register_action(name:str,fn:Callable,category:str="general"):
    _actions[name]={"fn":fn,"category":category}
def get_action(name:str)->Optional[Callable]:
    a=_actions.get(name);return a["fn"] if a else None
def get_actions_by_category(cat:str)->Dict[str,Callable]:
    return {k:v["fn"] for k,v in _actions.items() if v["category"]==cat}

def register_menu_page(key:str,title:str,options_fn:Callable,handler:Callable,parent:Optional[str]=None):
    _menu_pages[key]={"title":title,"options_fn":options_fn,"handler":handler,"parent":parent}
def get_menu_page(key:str)->Optional[Dict]:return _menu_pages.get(key)
def get_menu_pages()->Dict:return _menu_pages

def register_hook(event:str,fn:Callable):
    _hooks.setdefault(event,[]).append(fn)
def fire_hook(event:str,*args,**kwargs):
    for fn in _hooks.get(event,[]):fn(*args,**kwargs)

def register_npc_profile_extension(schema:Dict):
    _npc_profile_extensions.append(schema)
def get_npc_profile_extensions()->List[Dict]:return _npc_profile_extensions

def register_relationship_action(name:str,label:str,fn:Callable,condition:Optional[Callable]=None,
                                  affinity_cost:int=0,affinity_gain:int=0,trust_change:int=0,
                                  category:str="general",description:str=""):
    _relationship_actions[name]={"label":label,"fn":fn,"condition":condition,
        "affinity_cost":affinity_cost,"affinity_gain":affinity_gain,
        "trust_change":trust_change,"category":category,"description":description}
def get_relationship_action(name:str)->Optional[Dict]:return _relationship_actions.get(name)
def get_relationship_actions(category:Optional[str]=None)->Dict:
    if category is None:return _relationship_actions
    return {k:v for k,v in _relationship_actions.items() if v["category"]==category}

def register_combat_action(name:str,fn:Callable):_combat_actions[name]=fn
def get_combat_action(name:str)->Optional[Callable]:return _combat_actions.get(name)
def get_combat_actions()->Dict:return _combat_actions

def register_loot_table(name:str,fn:Callable):_loot_tables[name]=fn
def get_loot_table(name:str)->Optional[Callable]:return _loot_tables.get(name)
