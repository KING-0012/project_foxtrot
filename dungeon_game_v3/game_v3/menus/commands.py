from engine import registry
from engine.core import state
from systems import combat as _combat

# ---- movement ----
_MOVE_DIRS={"north","south","east","west","up","down","deeper","back","boss","escape"}

def _cmd_move(cmd,parts):
    if state.in_combat:return "You can't move during combat!"
    room=state.world.move(cmd)
    if not room:return "Can't go that way."
    registry.fire_hook("room_enter",room=room,state=state)
    enemies_alive=[e for e in room.enemies if e.get("profile").alive]
    result=[room.summary()]
    if enemies_alive:
        names=", ".join(e.get("profile").name for e in enemies_alive)
        result.append(f"\n{names} attack!")
        _combat.start_combat(enemies_alive)
    return "\n".join(result)

registry.register_command(_cmd_move,exact=_MOVE_DIRS,help_text="Move in a direction",category="movement")

# ---- look ----
def _cmd_look(cmd,parts):
    room=state.world.current()
    return room.summary() if room else "You are nowhere."

registry.register_command(_cmd_look,exact={"look","l","look around"},help_text="Look around",category="world")

# ---- status ----
def _cmd_status(cmd,parts):
    ps=state.player.get("stats")
    inv=state.player.get("inventory")
    party=state.player.get("party")
    lines=[f"=== {ps.name} === LV{ps.level}",
           f"HP: {ps.hp}/{ps.max_hp}  ATK:{ps.atk}  DEF:{ps.defense}  Gold:{ps.gold}g",
           f"XP: {ps.xp}/{ps.xp_next}",
           f"Equipped: W={inv.equipped['weapon']} A={inv.equipped['armor']}"]
    if party.members:lines.append(f"Party: {', '.join(party.members)}")
    return "\n".join(lines)

registry.register_command(_cmd_status,exact={"status","stat","stats","me"},help_text="Show player status",category="player")

# ---- inventory ----
def _cmd_inv(cmd,parts):
    from systems.economy import show_inventory
    return show_inventory()

registry.register_command(_cmd_inv,exact={"inventory","inv","i","bag"},help_text="Show inventory",category="player")

# ---- shop ----
def _cmd_shop(cmd,parts):
    room=state.world.current()
    if room and "shop" not in room.key and room.key!="town_square":
        return "No shop here."
    from systems.economy import show_shop
    return show_shop()

registry.register_command(_cmd_shop,exact={"shop","store"},help_text="Show shop",category="economy")

# ---- buy / sell / equip / use ----
def _cmd_buy(cmd,parts):
    from systems.economy import buy_item
    return buy_item(" ".join(parts))

def _cmd_sell(cmd,parts):
    from systems.economy import sell_item
    return sell_item(" ".join(parts))

def _cmd_equip(cmd,parts):
    from systems.economy import equip_item
    return equip_item(" ".join(parts))

def _cmd_use(cmd,parts):
    from systems.economy import use_item
    return use_item(" ".join(parts))

registry.register_command(_cmd_buy,prefix="buy ",help_text="buy <item>",category="economy")
registry.register_command(_cmd_sell,prefix="sell ",help_text="sell <item>",category="economy")
registry.register_command(_cmd_equip,prefix="equip ",help_text="equip <item>",category="economy")
registry.register_command(_cmd_use,prefix="use ",help_text="use <item>",category="player")

# ---- gamble ----
def _cmd_gamble_list(cmd,parts):
    from systems.economy import list_gamble_games
    return list_gamble_games()

def _cmd_gamble(cmd,parts):
    if len(parts)<2:return "Usage: gamble <game> <bet>"
    from systems.economy import gamble
    try:return gamble(parts[0],int(parts[1]))
    except ValueError:return "Bet must be a number."

registry.register_command(_cmd_gamble_list,exact={"gamble","den","games"},help_text="List gambling games",category="economy")
registry.register_command(_cmd_gamble,prefix="gamble ",help_text="gamble <game> <bet>",category="economy")
registry.register_command(_cmd_gamble,prefix="bet ",help_text="bet <game> <amount>",category="economy")

# ---- combat ----
def _cmd_attack(cmd,parts):
    if not state.in_combat:return "You're not in combat."
    target=parts[0] if parts else None
    return _combat.combat_attack(target)

def _cmd_flee(cmd,parts):
    if not state.in_combat:return "You're not in combat."
    return _combat.combat_flee()

def _cmd_enemies(cmd,parts):
    if not state.in_combat:return "Not in combat."
    return _combat._combat_banner()

def _cmd_target(cmd,parts):
    if not state.in_combat:return "Not in combat."
    if not parts:return "Usage: target <name>"
    return _combat.combat_target(parts[0])

registry.register_command(_cmd_attack,exact={"attack","a","fight","hit"},prefix="attack ",help_text="attack [target]",category="combat")
registry.register_command(_cmd_flee,exact={"flee","run"},help_text="Flee from combat",category="combat")
registry.register_command(_cmd_enemies,exact={"enemies","foes"},help_text="List enemies in combat",category="combat")
registry.register_command(_cmd_target,prefix="target ",help_text="target <name>",category="combat")

# ---- social / dialogue ----
def _cmd_talk(cmd,parts):
    from systems.dialogue import start_dialogue
    return start_dialogue(" ".join(parts))

def _cmd_choose(cmd,parts):
    if len(parts)<2:return "Usage: choose <npc_name> <number>"
    from systems.dialogue import choose_option
    try:return choose_option(parts[0],int(parts[1]))
    except ValueError:return "Choice must be a number."

registry.register_command(_cmd_talk,prefix="talk ",help_text="talk <npc>",category="social")
registry.register_command(_cmd_choose,prefix="choose ",help_text="choose <npc> <num>",category="social")

# ---- relationship actions ----
# Format: do <action> <npc_name> [item_name]
def _cmd_do(cmd,parts):
    if len(parts)<2:return "Usage: do <action> <npc_name> [item]"
    action=parts[0];npc_name=parts[1]
    extra={"item_name":parts[2]} if len(parts)>2 else {}
    from systems.relationship import do_relationship_action
    return do_relationship_action(action,npc_name,**extra)

def _cmd_actions(cmd,parts):
    from systems.relationship import get_available_actions
    if not parts:return "Usage: actions <npc_name>"
    actions=get_available_actions(parts[0])
    if not actions:return f"No actions available with {parts[0]} right now."
    lines=[f"Available actions with {parts[0]}:"]
    for k,v in actions.items():
        lines.append(f"  {k:<20} [{v['category']}] — {v['description']}")
    return "\n".join(lines)

def _cmd_rel(cmd,parts):
    from systems.relationship import get_relationship_status
    if not parts:return "Usage: rel <npc_name>"
    return get_relationship_status(parts[0])

registry.register_command(_cmd_do,prefix="do ",help_text="do <action> <npc> [item]",category="social")
registry.register_command(_cmd_actions,prefix="actions ",help_text="actions <npc>",category="social")
registry.register_command(_cmd_rel,prefix="rel ",help_text="rel <npc>",category="social")

# ---- rest ----
def _cmd_rest(cmd,parts):
    room=state.world.current()
    if not room or "inn" not in room.key:return "You need to be at the inn to rest."
    ps=state.player.get("stats")
    cost=10
    if ps.gold<cost:return f"Resting costs {cost}g. You don't have enough."
    ps.gold-=cost;ps.hp=ps.max_hp
    return f"You rest at the inn. Fully healed! (-{cost}g)"

registry.register_command(_cmd_rest,exact={"rest","sleep","heal"},help_text="Rest at inn (10g)",category="world")

# ---- npcs / party ----
def _cmd_npcs(cmd,parts):
    room=state.world.current()
    if not room:return "Nowhere."
    if not room.npcs:return "No one around."
    lines=["People here:"]
    for name in room.npcs:
        npc=state.get_npc(name)
        if npc:
            p=npc.get("profile");r=p.relationship
            lines.append(f"  {p.name} ({p.occupation}) mood:{p.mood} {r['status']}")
    return "\n".join(lines)

def _cmd_party(cmd,parts):
    party=state.player.get("party")
    if not party.members:return "No one in your party."
    lines=["Party:"]
    for name in party.members:
        npc=state.get_npc(name)
        if npc:
            p=npc.get("profile");nc=npc.get("combat")
            lines.append(f"  {p.name} ({p.occupation}) HP:{nc.hp}/{nc.max_hp} ATK:{nc.atk}")
    return "\n".join(lines)

registry.register_command(_cmd_npcs,exact={"npcs","people","who"},help_text="List NPCs here",category="world")
registry.register_command(_cmd_party,exact={"party","companions","members"},help_text="Show party",category="player")

# ---- saves ----
def _cmd_saves(cmd,parts):
    from systems.saveload import list_saves
    return list_saves()

registry.register_command(_cmd_saves,exact={"saves","save list","slots"},help_text="List save slots",category="system")

# ---- help — auto-generated from registry ----
def _cmd_help(cmd,parts):
    cats={}
    for entry in registry.get_commands():
        cat=entry["category"]
        if not entry["help"]:continue
        cats.setdefault(cat,[]).append(entry["help"])
    lines=["=== Commands ==="]
    for cat,cmds in cats.items():
        lines.append(f"{cat.capitalize()}:")
        for c in cmds:lines.append(f"  {c}")
    return "\n".join(lines)

registry.register_command(_cmd_help,exact={"help","h","?","commands"},help_text="Show this help",category="system")

# ---- save / load ----
def _cmd_save(cmd,parts):
    slot=parts[0] if parts else "slot1"
    from systems.saveload import save_game
    return save_game(slot)

def _cmd_load(cmd,parts):
    slot=parts[0] if parts else "slot1"
    from systems.saveload import load_game
    return load_game(slot)

registry.register_command(_cmd_save,exact={"save","save game"},prefix="save ",help_text="save [slot]",category="system")
registry.register_command(_cmd_load,prefix="load ",help_text="load <slot>",category="system")
