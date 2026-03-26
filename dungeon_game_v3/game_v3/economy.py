import random
from engine import registry
from engine.core import state,bus

ITEMS={
    "health_potion":  {"type":"consumable","description":"Restores 30 HP","price":20,"hp_restore":30},
    "elixir":         {"type":"consumable","description":"Restores 80 HP","price":60,"hp_restore":80},
    "antidote":       {"type":"consumable","description":"Cures poison","price":15},
    "iron_sword":     {"type":"weapon","description":"Basic sword","price":80,"atk_bonus":8},
    "steel_sword":    {"type":"weapon","description":"Sharp steel","price":180,"atk_bonus":16},
    "iron_armor":     {"type":"armor","description":"Basic protection","price":90,"def_bonus":6},
    "leather_armor":  {"type":"armor","description":"Light armor","price":50,"def_bonus":3},
    "silver_ring":    {"type":"accessory","description":"A gift worth giving","price":120,"gift_value":60},
    "roses":          {"type":"consumable","description":"Fresh flowers. A nice gift.","price":15,"gift_value":20},
    "fancy_wine":     {"type":"consumable","description":"High-quality wine. For sharing.","price":40,"gift_value":35},
    "lockpick":       {"type":"tool","description":"Opens locks","price":30},
}

SHOP_STOCK=["health_potion","elixir","antidote","iron_sword","steel_sword",
            "iron_armor","leather_armor","silver_ring","roses","fancy_wine","lockpick"]

def show_shop()->str:
    lines=["=== Equipment Shop ==="]
    inv=state.player.get("inventory")
    ps=state.player.get("stats")
    lines.append(f"Your gold: {ps.gold}")
    for name in SHOP_STOCK:
        item=ITEMS[name]
        equipped=""
        if inv.equipped.get(item["type"])==name:equipped=" [EQUIPPED]"
        lines.append(f"  {name:<18} {item['price']:>4}g — {item['description']}{equipped}")
    return "\n".join(lines)

def buy_item(item_name:str)->str:
    item=ITEMS.get(item_name)
    if not item:return f"No item named '{item_name}'."
    ps=state.player.get("stats")
    inv=state.player.get("inventory")
    if ps.gold<item["price"]:return f"Not enough gold. Need {item['price']}g, have {ps.gold}g."
    ps.gold-=item["price"]
    inv.items.append(item_name)
    bus.emit("item_bought",item=item_name)
    return f"Bought {item_name} for {item['price']}g. Gold remaining: {ps.gold}g."

def sell_item(item_name:str)->str:
    inv=state.player.get("inventory")
    if item_name not in inv.items:return f"You don't have {item_name}."
    item=ITEMS.get(item_name)
    price=item["price"]//2 if item else 5
    inv.items.remove(item_name)
    state.player.get("stats").gold+=price
    return f"Sold {item_name} for {price}g."

def equip_item(item_name:str)->str:
    inv=state.player.get("inventory")
    if item_name not in inv.items:return f"You don't have {item_name}."
    item=ITEMS.get(item_name)
    if not item or item["type"] not in ("weapon","armor","accessory"):return "Can't equip that."
    slot=item["type"]
    old=inv.equipped.get(slot)
    inv.equipped[slot]=item_name
    msg=f"Equipped {item_name}."
    if old:msg+=f" (replaced {old})"
    return msg

def use_item(item_name:str)->str:
    inv=state.player.get("inventory")
    if item_name not in inv.items:return f"You don't have {item_name}."
    item=ITEMS.get(item_name)
    if not item:return "Unknown item."
    ps=state.player.get("stats")
    if item["type"]=="consumable":
        inv.items.remove(item_name)
        if "hp_restore" in item:
            healed=min(item["hp_restore"],ps.max_hp-ps.hp)
            ps.hp+=healed
            return f"Used {item_name}. Restored {healed} HP. ({ps.hp}/{ps.max_hp})"
        return f"Used {item_name}."
    return f"{item_name} can't be used directly — equip it instead."

def show_inventory()->str:
    ps=state.player.get("stats")
    inv=state.player.get("inventory")
    lines=[f"=== Inventory === (Gold: {ps.gold}g)"]
    lines.append(f"HP: {ps.hp}/{ps.max_hp}  ATK:{ps.atk}  DEF:{ps.defense}  LV:{ps.level}")
    lines.append(f"Equipped: weapon={inv.equipped['weapon']} armor={inv.equipped['armor']} accessory={inv.equipped['accessory']}")
    if inv.items:lines.append("Items: "+", ".join(inv.items))
    else:lines.append("No items.")
    return "\n".join(lines)

# ---- Gambling ----
GAMBLE_GAMES={
    "dice": {"min_bet":5,"description":"Roll higher than the dealer (1-6)."},
    "cards":{"min_bet":10,"description":"Draw a card. Face card = win x3."},
    "slots": {"min_bet":15,"description":"Spin 3 slots. Match = big win."},
}

def gamble(game:str,bet:int)->str:
    ps=state.player.get("stats")
    g=GAMBLE_GAMES.get(game)
    if not g:return f"Unknown game: {game}. Try: {', '.join(GAMBLE_GAMES)}"
    if bet<g["min_bet"]:return f"Minimum bet for {game} is {g['min_bet']}g."
    if ps.gold<bet:return f"Not enough gold. Have {ps.gold}g."
    ps.gold-=bet

    if game=="dice":
        player_roll=random.randint(1,6)
        dealer_roll=random.randint(1,6)
        if player_roll>dealer_roll:
            ps.gold+=bet*2
            return f"Dice: You rolled {player_roll}, dealer {dealer_roll}. You win! +{bet}g."
        elif player_roll==dealer_roll:
            ps.gold+=bet
            return f"Dice: Both rolled {player_roll}. Tie — bet returned."
        return f"Dice: You rolled {player_roll}, dealer {dealer_roll}. You lose. -{bet}g."

    if game=="cards":
        deck=["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
        card=random.choice(deck)
        if card in("J","Q","K","A"):
            ps.gold+=bet*3
            return f"Cards: Drew {card}! Face card — triple win! +{bet*2}g."
        if int(card)>=7:
            ps.gold+=bet*2
            return f"Cards: Drew {card}. Win! +{bet}g."
        return f"Cards: Drew {card}. Low card — you lose. -{bet}g."

    if game=="slots":
        symbols=["🍒","🍋","⭐","💎","🎰"]
        s=[random.choice(symbols) for _ in range(3)]
        line=" | ".join(s)
        if s[0]==s[1]==s[2]:
            mult=10 if s[0]=="💎" else 5 if s[0]=="⭐" else 3
            ps.gold+=bet*mult
            return f"Slots: {line} — JACKPOT! x{mult} — +{bet*(mult-1)}g!"
        if s[0]==s[1] or s[1]==s[2] or s[0]==s[2]:
            ps.gold+=int(bet*1.5)
            return f"Slots: {line} — Pair! +{int(bet*0.5)}g."
        return f"Slots: {line} — No match. -{bet}g."

    return "Game ended."

def list_gamble_games()->str:
    lines=["=== The Den — Available Games ==="]
    ps=state.player.get("stats")
    lines.append(f"Your gold: {ps.gold}g")
    for name,g in GAMBLE_GAMES.items():
        lines.append(f"  {name:<8} min bet:{g['min_bet']}g — {g['description']}")
    return "\n".join(lines)

# ---- Loot tables ----
def _loot(pool,chance=0.4)->str:
    if random.random()>chance:return None
    return random.choice(pool)

registry.register_loot_table("goblin",lambda:_loot(["health_potion","lockpick","roses"],0.35))
registry.register_loot_table("orc",lambda:_loot(["iron_sword","health_potion","iron_armor"],0.45))
registry.register_loot_table("magic",lambda:_loot(["elixir","silver_ring","fancy_wine"],0.55))
registry.register_loot_table("bandit",lambda:_loot(["lockpick","iron_sword","health_potion"],0.5))
registry.register_loot_table("undead",lambda:_loot(["antidote","iron_armor"],0.3))
registry.register_loot_table("beast",lambda:_loot(["antidote","health_potion"],0.25))
registry.register_loot_table("dragon",lambda:_loot(["steel_sword","elixir","silver_ring"],0.99))
registry.register_loot_table("npc_basic",lambda:_loot(["health_potion","roses"],0.2))
registry.register_loot_table("slime",lambda:None)

registry.register_system("economy",{"buy":buy_item,"sell":sell_item,"equip":equip_item,
    "use":use_item,"shop":show_shop,"inventory":show_inventory,
    "gamble":gamble,"gamble_games":list_gamble_games})
