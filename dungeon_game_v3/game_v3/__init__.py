from engine import registry
from engine.core import state

# Each menu page: register_menu_page(key, title, options_fn, handler, parent=None)
# options_fn() -> list of (label, value) tuples shown to player
# handler(choice_value, **kwargs) -> str

def _sep(title:str)->str:return f"\n{'='*40}\n  {title}\n{'='*40}"

# ---- Main menu (shown when no context) ----
def _main_options():
    opts=[("Move","move"),("Look around","look"),("Inventory","inventory"),("Talk to NPC","talk")]
    room=state.world.current() if state.world else None
    if room:
        if room.enemies and any(e.get("profile").alive for e in room.enemies):
            opts.insert(0,("Enter combat","combat"))
        if room.npcs:
            npcs=", ".join(room.npcs)
            opts.append((f"Social actions [{npcs}]","social"))
    opts.append(("Shop","shop"))
    opts.append(("Gambling den","gamble"))
    opts.append(("Status","status"))
    opts.append(("Save game","save"))
    return opts

def _main_handler(choice:str,**kw)->str:
    from menus.navigation import handle_navigation
    return handle_navigation(choice,**kw)

registry.register_menu_page("main","Main Menu",_main_options,_main_handler,parent=None)

# ---- Combat menu ----
def _combat_options():
    opts=[("Attack","attack"),("Use item","use_item"),("Flee","flee")]
    return opts

def _combat_handler(choice:str,**kw)->str:
    from systems import combat
    if choice=="attack":return combat.combat_attack()
    if choice=="flee":return combat.combat_flee()
    if choice=="use_item":
        item=kw.get("item")
        if not item:return "Which item? (use_item <item_name>)"
        return combat.combat_use_item(item)
    return "Unknown combat action."

registry.register_menu_page("combat","Combat",_combat_options,_combat_handler,parent="main")

# ---- Social menu ----
def _social_options():
    room=state.world.current() if state.world else None
    if not room or not room.npcs:return [("(No one here)","none")]
    opts=[]
    for npc_name in room.npcs:
        opts.append((f"Talk to {npc_name}","talk_"+npc_name))
        opts.append((f"Actions with {npc_name}","actions_"+npc_name))
        opts.append((f"Check relationship: {npc_name}","rel_"+npc_name))
    opts.append(("Back","back"))
    return opts

def _social_handler(choice:str,**kw)->str:
    from systems.relationship import do_relationship_action,get_available_actions,get_relationship_status
    from systems.dialogue import start_dialogue,choose_option
    if choice.startswith("talk_"):
        name=choice[5:]
        return start_dialogue(name)
    if choice.startswith("actions_"):
        name=choice[8:]
        actions=get_available_actions(name)
        if not actions:return f"No actions available with {name}."
        lines=[f"Actions available with {name}:"]
        for k,v in actions.items():
            lines.append(f"  {k:<20} — {v['description']}")
        return "\n".join(lines)
    if choice.startswith("rel_"):
        name=choice[4:]
        return get_relationship_status(name)
    return "Back."

registry.register_menu_page("social","Social",_social_options,_social_handler,parent="main")
