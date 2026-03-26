import random
from typing import Optional,List
from engine import registry
from engine.core import state,bus

def _player_atk()->int:
    s=state.player.get("stats")
    bonus=0
    inv=state.player.get("inventory")
    if inv and inv.equipped.get("weapon"):
        w=_get_item(inv.equipped["weapon"])
        if w:bonus=w.get("atk_bonus",0)
    return s.atk+bonus+random.randint(-2,4)

def _player_def()->int:
    s=state.player.get("stats")
    bonus=0
    inv=state.player.get("inventory")
    if inv and inv.equipped.get("armor"):
        a=_get_item(inv.equipped["armor"])
        if a:bonus=a.get("def_bonus",0)
    return s.defense+bonus

def _get_item(name:str)->Optional[dict]:
    from systems.economy import ITEMS
    return ITEMS.get(name)

def _living_enemies()->List:
    return [e for e in getattr(state,"enemy_queue",[]) if e.get("profile").alive]

def _current_target():
    living=_living_enemies()
    if not living:return None
    target=getattr(state,"current_enemy",None)
    if target and target.get("profile").alive:return target
    state.current_enemy=living[0]
    return state.current_enemy

def _combat_banner()->str:
    living=_living_enemies()
    if not living:return ""
    parts=[]
    for e in living:
        ep=e.get("profile");ec=e.get("combat")
        marker=" ◄" if e is _current_target() else ""
        parts.append(f"{ep.name}({ec.hp}/{ec.max_hp}hp){marker}")
    return "Enemies: "+" | ".join(parts)

def start_combat(enemies)->bool:
    if state.in_combat:return False
    if not isinstance(enemies,list):enemies=[enemies]
    living=[e for e in enemies if e.get("profile").alive]
    if not living:return False
    state.in_combat=True
    state.enemy_queue=living
    state.current_enemy=living[0]
    names=", ".join(e.get("profile").name for e in living)
    bus.emit("combat_start",enemies=living)
    state.log(f"\n⚔  Combat starts! Enemies: {names}","combat")
    state.log(_combat_banner(),"combat")
    return True

def combat_attack(target_name:Optional[str]=None)->str:
    if not state.in_combat:return "Not in combat."
    ps=state.player.get("stats")
    if target_name:
        for e in _living_enemies():
            if e.get("profile").name.lower()==target_name.lower():
                state.current_enemy=e;break
    enemy=_current_target()
    if not enemy:return _resolve_all_dead()
    ec=enemy.get("combat");ep=enemy.get("profile")
    dmg=max(0,_player_atk()-ec.defense+random.randint(-1,2))
    ec.hp-=dmg
    lines=[f"You hit {ep.name} for {dmg} dmg. ({max(0,ec.hp)}/{ec.max_hp} HP)"]
    if ec.hp<=0:
        ep.alive=False
        lines.append(_resolve_one_victory(enemy))
        nxt=_living_enemies()
        state.current_enemy=nxt[0] if nxt else None
    lines.extend(_party_attacks())
    if not _living_enemies():
        lines.append(_resolve_all_dead())
        return "\n".join(lines)
    for e in _living_enemies():
        ec2=e.get("combat");ep2=e.get("profile")
        edm=max(0,ec2.atk-_player_def()+random.randint(-1,2))
        ps.hp-=edm
        lines.append(f"{ep2.name} hits you for {edm} dmg. HP:{ps.hp}/{ps.max_hp}")
        if ps.hp<=0:
            lines.append(_resolve_defeat())
            return "\n".join(lines)
    lines.append(_combat_banner())
    return "\n".join(lines)

def _party_attacks()->List[str]:
    lines=[]
    party_comp=state.player.get("party")
    if not party_comp or not party_comp.members:return lines
    for member_name in party_comp.members:
        living=_living_enemies()
        if not living:break
        npc=state.get_npc(member_name)
        if not npc:continue
        p=npc.get("profile")
        if not getattr(p,"party_member",False):continue
        nc=npc.get("combat")
        target=living[0]
        tc=target.get("combat");tp=target.get("profile")
        atk=getattr(nc,"atk",6)+random.randint(-1,3)
        dmg=max(0,atk-tc.defense)
        tc.hp-=dmg
        if tc.hp<=0:
            tp.alive=False
            lines.append(f"  {p.name} finishes off {tp.name}! (+{tc.xp}xp +{tc.gold}g)")
            pstats=state.player.get("stats")
            pstats.gold+=tc.gold;pstats.xp+=tc.xp
            _check_levelup()
        else:
            lines.append(f"  {p.name} hits {tp.name} for {dmg}.")
    return lines

def combat_target(name:str)->str:
    if not state.in_combat:return "Not in combat."
    for e in _living_enemies():
        if e.get("profile").name.lower()==name.lower():
            state.current_enemy=e
            return f"Targeting {e.get('profile').name}. {_combat_banner()}"
    return f"No living enemy '{name}'."

def combat_flee()->str:
    if not state.in_combat:return "Not in combat."
    if random.random()<0.45:
        _end_combat()
        return "You fled!"
    ps=state.player.get("stats")
    lines=["Failed to flee!"]
    for e in _living_enemies():
        ec=e.get("combat");ep=e.get("profile")
        pen=max(0,ec.atk//2-_player_def())
        ps.hp-=pen
        lines.append(f"{ep.name} hits you for {pen}. HP:{ps.hp}")
        if ps.hp<=0:
            lines.append(_resolve_defeat())
            return "\n".join(lines)
    return "\n".join(lines)

def combat_use_item(item_name:str)->str:
    from systems.economy import use_item
    result=use_item(item_name)
    if state.in_combat:
        ps=state.player.get("stats")
        for e in _living_enemies():
            ec=e.get("combat");ep=e.get("profile")
            edm=max(0,ec.atk-_player_def()+random.randint(-1,2))
            ps.hp-=edm
            result+=f"\n{ep.name} hits you for {edm}. HP:{ps.hp}"
            if ps.hp<=0:return result+"\n"+_resolve_defeat()
    return result

def _resolve_one_victory(enemy)->str:
    ec=enemy.get("combat");ep=enemy.get("profile")
    ps=state.player.get("stats")
    ps.gold+=ec.gold;ps.xp+=ec.xp
    loot=_roll_loot(ec.loot_table)
    bus.emit("enemy_defeated",enemy=enemy)
    msg=f"{ep.name} defeated! +{ec.gold}g +{ec.xp}xp"
    if loot:
        state.player.get("inventory").items.append(loot)
        msg+=f" | loot: {loot}"
    _check_levelup()
    return msg

def _resolve_all_dead()->str:
    _end_combat()
    bus.emit("combat_victory")
    return "All enemies defeated! Victory!"

def _resolve_defeat()->str:
    ps=state.player.get("stats")
    ps.hp=ps.max_hp//2;ps.gold=max(0,ps.gold-10)
    if state.world:state.world.current_key="inn"
    bus.emit("combat_defeat")
    _end_combat()
    return "You were defeated... you wake in the inn. (-10g)"

def _end_combat():
    state.in_combat=False
    state.current_enemy=None
    state.enemy_queue=[]

def _check_levelup():
    ps=state.player.get("stats")
    while ps.xp>=ps.xp_next:
        ps.level+=1;ps.xp-=ps.xp_next
        ps.xp_next=int(ps.xp_next*1.4)
        ps.max_hp+=15;ps.hp=min(ps.hp+15,ps.max_hp)
        ps.atk+=2;ps.defense+=1
        state.log(f"\n★ Level {ps.level}! HP:{ps.max_hp} ATK:{ps.atk} DEF:{ps.defense}","system")
        bus.emit("level_up",level=ps.level)

def _roll_loot(table_name:str)->Optional[str]:
    fn=registry.get_loot_table(table_name)
    return fn() if fn else None

registry.register_combat_action("attack",combat_attack)
registry.register_combat_action("flee",combat_flee)
registry.register_combat_action("use_item",combat_use_item)
registry.register_combat_action("target",combat_target)
registry.register_system("combat",{"start":start_combat,"attack":combat_attack,
    "flee":combat_flee,"use_item":combat_use_item,"target":combat_target,
    "living_enemies":_living_enemies,"banner":_combat_banner})
