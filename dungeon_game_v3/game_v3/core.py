from typing import Any,Callable,Dict,List,Optional
from engine import registry

class EventBus:
    def __init__(self):self._listeners:Dict[str,List[Callable]]={}
    def on(self,event:str,fn:Callable):self._listeners.setdefault(event,[]).append(fn)
    def emit(self,event:str,*args,**kwargs):
        for fn in self._listeners.get(event,[]):fn(*args,**kwargs)
        registry.fire_hook(event,*args,**kwargs)  # also fire global hooks

class GameState:
    def __init__(self):
        self.player=None
        self.current_room=None
        self.world=None
        self.turn:int=0
        self.flags:Dict[str,Any]={}
        self.event_log:List[str]=[]
        self.npcs:Dict[str,Any]={}       # eid -> entity
        self.party:List[str]=[]           # eids of party members
        self.in_combat:bool=False
        self.current_enemy=None
        self.enemy_queue:list=[]
        self.dialogue_state:dict={}
        self.paused:bool=False

    def log(self,msg:str,category:str="info"):
        self.event_log.append({"msg":msg,"turn":self.turn,"cat":category})
        print(msg)

    def set_flag(self,key:str,val:Any=True):self.flags[key]=val
    def get_flag(self,key:str,default:Any=None)->Any:return self.flags.get(key,default)

    def add_npc(self,npc):
        p=npc.get("profile")
        key=p.name if p else npc.eid
        self.npcs[key]=npc
        return key

    def get_npc(self,name:str):
        return self.npcs.get(name) or self.npcs.get(name.capitalize()) or next(
            (v for k,v in self.npcs.items() if k.lower()==name.lower()),None)
    def all_npcs(self)->Dict:return self.npcs

bus=EventBus()
state=GameState()
