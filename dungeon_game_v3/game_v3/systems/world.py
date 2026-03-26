import random
from typing import Dict,List,Optional,Callable
from engine import registry
from engine.entity import make_random_npc,make_enemy

class Room:
    def __init__(self,key:str,name:str,description:str,
                 exits:Optional[Dict[str,str]]=None,
                 on_enter:Optional[Callable]=None):
        self.key=key
        self.name=name
        self.description=description
        self.exits:Dict[str,str]=exits or {}
        self.npcs:List[str]=[]         # npc keys present in room
        self.enemies:List=[]
        self.items:List[str]=[]
        self.explored:bool=False
        self.tags:List[str]=[]
        self.on_enter:Optional[Callable]=on_enter

    def add_exit(self,direction:str,room_key:str):self.exits[direction]=room_key
    def summary(self)->str:
        parts=[f"[ {self.name} ]",self.description]
        if self.npcs:parts.append(f"People here: {', '.join(self.npcs)}")
        if self.enemies:parts.append(f"Enemies lurk here!")
        if self.items:parts.append(f"You see: {', '.join(self.items)}")
        exits=", ".join(f"{d}→{k}" for d,k in self.exits.items())
        if exits:parts.append(f"Exits: {exits}")
        return "\n".join(parts)

class World:
    def __init__(self):
        self.rooms:Dict[str,Room]={}
        self.current_key:str="town_square"
    def add_room(self,room:Room):self.rooms[room.key]=room;return self
    def current(self)->Optional[Room]:return self.rooms.get(self.current_key)
    def move(self,direction:str)->Optional[Room]:
        cur=self.current()
        if cur and direction in cur.exits:
            self.current_key=cur.exits[direction]
            return self.current()
        return None

def build_world(state)->World:
    from engine.core import bus
    w=World()

    sq=Room("town_square","Town Square",
        "A bustling square. Merchants hawk their wares. Women in all manner of dress pass by.")
    inn=Room("inn","The Wanderer's Inn",
        "Warm firelight, the smell of ale. A few patrons sit at tables.")
    shop=Room("shop","Equipment Shop",
        "Racks of weapons and armor. A tough-looking woman runs the counter.")
    gambling=Room("gambling_den","The Den",
        "Smoky, loud. Cards flip and dice roll. A woman dealer eyes you coolly.")
    dungeon_entrance=Room("dungeon_entrance","Dungeon Gate",
        "A dark archway descends into the earth. Cold air rises from below.")
    dungeon_1=Room("dungeon_1","Dungeon — Level 1",
        "Torchlit stone corridors. Distant sounds echo.")
    dungeon_2=Room("dungeon_2","Dungeon — Level 2",
        "Darker here. Bones crunch underfoot.")
    dungeon_boss=Room("dungeon_boss","Boss Chamber",
        "A vast chamber. Something massive stirs in the shadows.")

    sq.add_exit("north","inn");sq.add_exit("east","shop")
    sq.add_exit("west","gambling_den");sq.add_exit("south","dungeon_entrance")
    inn.add_exit("south","town_square")
    shop.add_exit("west","town_square")
    gambling.add_exit("east","town_square")
    dungeon_entrance.add_exit("north","town_square");dungeon_entrance.add_exit("down","dungeon_1")
    dungeon_1.add_exit("up","dungeon_entrance");dungeon_1.add_exit("deeper","dungeon_2")
    dungeon_2.add_exit("back","dungeon_1");dungeon_2.add_exit("boss","dungeon_boss")
    dungeon_boss.add_exit("escape","dungeon_2")

    # Populate NPCs
    innkeeper=make_random_npc("Mira","innkeeper",{"kind":0.9,"loyal":0.8})
    barmaid=make_random_npc("Sable","barmaid",{"flirty":0.7,"curious":0.6})
    shopkeeper=make_random_npc("Vex","blacksmith",{"brave":0.8,"greedy":0.4})
    dealer=make_random_npc("Raven","gambler",{"flirty":0.5,"aggressive":0.3})

    state.add_npc(innkeeper);state.add_npc(barmaid)
    state.add_npc(shopkeeper);state.add_npc(dealer)

    inn.npcs=["Mira","Sable"]
    shop.npcs=["Vex"]
    gambling.npcs=["Raven"]

    # Populate dungeon enemies
    dungeon_1.enemies=[make_enemy("goblin"),make_enemy("slime"),make_enemy("goblin")]
    dungeon_2.enemies=[make_enemy("orc"),make_enemy("skeleton"),make_enemy("bandit")]
    dungeon_boss.enemies=[make_enemy("dragon")]
    dungeon_boss.tags=["boss"]

    for room in [sq,inn,shop,gambling,dungeon_entrance,dungeon_1,dungeon_2,dungeon_boss]:
        w.add_room(room)

    state.world=w
    return w

registry.register_system("world_builder",build_world)

# ---- Respawn hook point ----
# Any LLM can register a respawn strategy without touching world.py or combat.py.
# Signature: respawn_fn(room, state) -> None
# Called by: registry.fire_hook("room_enter", room=room, state=state)
# Example registration:
#   from engine.entity import make_enemy
#   def my_respawn(room, state, **kw):
#       if "dungeon" in room.key and not any(e.get("profile").alive for e in room.enemies):
#           room.enemies = [make_enemy("goblin")]
#   registry.register_hook("room_enter", my_respawn)
