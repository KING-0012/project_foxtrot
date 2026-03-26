from engine.core import state,bus
from engine import registry
from systems import combat as _combat

def handle_navigation(cmd:str,**kw)->str:
    cmd=cmd.strip().lower()

    # ---- movement ----
    if cmd in("north","south","east","west","up","down","deeper","back","boss","escape"):
        if state.in_combat:return "You can't move during combat!"
        room=state.world.move(cmd)
        if not room:return "Can't go that way."
        enemies_alive=[e for e in room.enemies if e.get("profile").alive]
        result=[room.summary()]
        if enemies_alive:
            names=", ".join(e.get("profile").name for e in enemies_alive)
            result.append(f"\n{names} attack!")
            _combat.start_combat(enemies_alive)
        return "\n".join(result)

    # ---- look ----
    if cmd in("look","l","look around"):
        room=state.world.current()
        return room.summary() if room else "You are nowhere."

    # ---- status ----
    if cmd in("status","stat","stats","me"):
        ps=state.player.get("stats")
        inv=state.player.get("inventory")
        party=state.player.get("party")
        lines=[f"=== {ps.name} === LV{ps.level}",
               f"HP: {ps.hp}/{ps.max_hp}  ATK:{ps.atk}  DEF:{ps.defense}  Gold:{ps.gold}g",
               f"XP: {ps.xp}/{ps.xp_next}",
               f"Equipped: W={inv.equipped['weapon']} A={inv.equipped['armor']}"]
        if party.members:lines.append(f"Party: {', '.join(party.members)}")
        return "\n".join(lines)

    # ---- inventory ----
    if cmd in("inventory","inv","i","bag"):
        from systems.economy import show_inventory
        return show_inventory()

    # ---- shop ----
    if cmd in("shop","store"):
        room=state.world.current()
        if room and "shop" not in room.key and room.key!="town_square":
            return "No shop here."
        from systems.economy import show_shop
        return show_shop()

    # ---- buy / sell / equip / use ----
    if cmd.startswith("buy "):
        from systems.economy import buy_item
        return buy_item(cmd[4:].strip())
    if cmd.startswith("sell "):
        from systems.economy import sell_item
        return sell_item(cmd[5:].strip())
    if cmd.startswith("equip "):
        from systems.economy import equip_item
        return equip_item(cmd[6:].strip())
    if cmd.startswith("use "):
        from systems.economy import use_item
        return use_item(cmd[4:].strip())

    # ---- gamble ----
    if cmd in("gamble","den","games"):
        from systems.economy import list_gamble_games
        return list_gamble_games()
    if cmd.startswith("gamble ") or cmd.startswith("bet "):
        parts=cmd.split()
        if len(parts)<3:return "Usage: gamble <game> <bet>"
        from systems.economy import gamble
        try:return gamble(parts[1],int(parts[2]))
        except ValueError:return "Bet must be a number."

    # ---- combat ----
    if cmd in("attack","a","fight","hit"):
        if not state.in_combat:return "You're not in combat."
        return _combat.combat_attack()
    if cmd.startswith("attack "):
        if not state.in_combat:return "You're not in combat."
        return _combat.combat_attack(cmd[7:].strip())
    if cmd.startswith("target "):
        if not state.in_combat:return "You're not in combat."
        return _combat.combat_target(cmd[7:].strip())
    if cmd in("flee","run","escape"):
        if not state.in_combat:return "You're not in combat."
        return _combat.combat_flee()
    if cmd in("enemies","foes"):
        if not state.in_combat:return "Not in combat."
        return _combat._combat_banner()

    # ---- social ----
    if cmd.startswith("talk "):
        from systems.dialogue import start_dialogue
        return start_dialogue(cmd[5:].strip())
    if cmd.startswith("choose "):
        parts=cmd.split(maxsplit=2)
        if len(parts)<3:return "Usage: choose <npc_name> <number>"
        from systems.dialogue import choose_option
        try:return choose_option(parts[1],int(parts[2]))
        except ValueError:return "Choice must be a number."

    # ---- relationship actions ----
    # Format: do <action> <npc_name> [extra args]
    if cmd.startswith("do "):
        parts=cmd.split(maxsplit=2)
        if len(parts)<3:return "Usage: do <action> <npc_name>"
        action,npc_name=parts[1],parts[2].split()[0]
        extra={}
        if "give" in action or action=="gift":
            rest=parts[2].split()
            if len(rest)>1:extra={"item_name":rest[1]}
        from systems.relationship import do_relationship_action
        return do_relationship_action(action,npc_name,**extra)

    if cmd.startswith("actions "):
        from systems.relationship import get_available_actions
        name=cmd[8:].strip()
        actions=get_available_actions(name)
        if not actions:return f"No actions available with {name} right now."
        lines=[f"Available actions with {name}:"]
        for k,v in actions.items():
            lines.append(f"  {k:<20} [{v['category']}] — {v['description']}")
        return "\n".join(lines)

    if cmd.startswith("rel "):
        from systems.relationship import get_relationship_status
        return get_relationship_status(cmd[4:].strip())

    # ---- heal (rest at inn) ----
    if cmd in("rest","sleep","heal"):
        room=state.world.current()
        if not room or "inn" not in room.key:return "You need to be at the inn to rest."
        ps=state.player.get("stats")
        cost=10
        if ps.gold<cost:return f"Resting costs {cost}g. You don't have enough."
        ps.gold-=cost;ps.hp=ps.max_hp
        return f"You rest at the inn. Fully healed! (-{cost}g)"

    # ---- npcs ----
    if cmd in("npcs","people","who"):
        room=state.world.current()
        if not room:return "Nowhere."
        if not room.npcs:return "No one around."
        lines=["People here:"]
        for name in room.npcs:
            npc=state.get_npc(name)
            if npc:
                p=npc.get("profile")
                r=p.relationship
                lines.append(f"  {p.name} ({p.occupation}) mood:{p.mood} {r['status']}")
        return "\n".join(lines)


    # ---- party ----
    if cmd in("party","companions","members"):
        party=state.player.get("party")
        if not party.members:return "No one in your party."
        lines=["Party members:"]
        for name in party.members:
            npc=state.get_npc(name)
            if npc:
                p=npc.get("profile");nc=npc.get("combat")
                lines.append(f"  {p.name} ({p.occupation}) HP:{nc.hp}/{nc.max_hp} ATK:{nc.atk}")
        return "\n".join(lines)

    # ---- saves list ----
    if cmd in("saves","save list","slots"):
        from systems.saveload import list_saves
        return list_saves()

    # ---- help ----
    if cmd in("help","h","?","commands"):
        return _help()

    return f"Unknown command: '{cmd}'. Type 'help' for commands."

def _help()->str:
    return """
=== Commands ===
Movement:       north/south/east/west/up/down/deeper/back
Look:           look
Status:         status / inv(entory)
Combat:         attack / flee / use <item>
Shop:           shop / buy <item> / sell <item> / equip <item>
Gambling:       gamble / gamble <game> <bet>
Social:         talk <name> / choose <name> <num>
                do <action> <name>  (compliment, gift, hug, kiss, flirt, scare, argue...)
                actions <name>      (see available actions)
                rel <name>          (relationship status)
                npcs                (see who's here)
Rest:           rest (at inn, costs 10g)
"""
