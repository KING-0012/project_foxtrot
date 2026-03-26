from engine import registry
from engine.entity import update_relationship

# Each action: fn(profile_dict, **kwargs) -> str
# profile_dict is the NPC's profile (mutable)
# Returning a string = what gets shown to the player

def _upd(p,**kw):update_relationship(p,**kw)

# ---- Positive social ----
def act_compliment(p,**kw)->str:
    gain=8 if p["personality"]["shy"]<0.5 else 5
    _upd(p,affinity=gain,trust=2,event="player complimented me",sentiment="positive")
    p["mood"]="happy"
    return f"{p['name']} smiles. 'That's kind of you.'"

def act_gift(p,item_name="something",**kw)->str:
    val=kw.get("value",10)
    gain=min(20,5+val//5)
    _upd(p,affinity=gain,trust=gain//2,event=f"player gave me {item_name}",sentiment="positive")
    p["mood"]="happy"
    return f"{p['name']} accepts {item_name} warmly. (+{gain} affinity)"

def act_hug(p,**kw)->str:
    r=p["relationship"]
    if r["affinity"]<20:
        _upd(p,affinity=-5,trust=-5,event="player hugged without permission",sentiment="negative")
        p["mood"]="suspicious"
        return f"{p['name']} steps back. 'Don't touch me.'"
    _upd(p,affinity=10,romance=5,event="hugged player",sentiment="positive")
    p["mood"]="happy"
    return f"{p['name']} hugs you back."

def act_kiss(p,**kw)->str:
    r=p["relationship"]
    if r["romance"]<40 or r["affinity"]<40:
        _upd(p,affinity=-15,trust=-10,fear=5,event="player tried to kiss without consent",sentiment="negative")
        p["mood"]="angry"
        return f"{p['name']} pulls away sharply. 'What do you think you're doing?!'"
    _upd(p,romance=15,affinity=10,event="kissed player",sentiment="positive")
    p["mood"]="excited"
    return f"{p['name']}'s cheeks flush. She leans in."

def act_flirt(p,**kw)->str:
    if p["personality"].get("flirty",0)>0.5:
        _upd(p,affinity=8,romance=8,event="flirted with player",sentiment="positive")
        p["mood"]="excited"
        return f"{p['name']} grins. 'Oh? Tell me more.'"
    if p["personality"].get("shy",0)>0.6:
        _upd(p,affinity=3,romance=4,event="player flirted",sentiment="neutral")
        p["mood"]="happy"
        return f"{p['name']} blushes and looks away."
    _upd(p,affinity=4,romance=5,event="player flirted",sentiment="neutral")
    return f"{p['name']} raises an eyebrow with a small smile."

def act_ask_follow(p,**kw)->str:
    from engine.core import state
    r=p["relationship"]
    if r["affinity"]>=40 and r["trust"]>=30:
        p["party_member"]=True
        party=state.player.get("party")
        if p["name"] not in party.members:party.members.append(p["name"])
        _upd(p,affinity=5,trust=5,event="joined player party",sentiment="positive")
        return f"{p['name']} nods. 'I'll watch your back.'"
    return f"{p['name']} shakes her head. 'I don't know you well enough yet.'"

def act_ask_leave(p,**kw)->str:
    from engine.core import state
    p["party_member"]=False
    party=state.player.get("party")
    if p["name"] in party.members:party.members.remove(p["name"])
    _upd(p,event="left player party",sentiment="neutral")
    return f"{p['name']} waves farewell. 'Until we meet again.'"

# ---- Negative social ----
def act_scare(p,**kw)->str:
    _upd(p,fear=15,affinity=-10,trust=-10,event="player tried to scare me",sentiment="negative")
    if p["personality"].get("brave",0.5)>0.7:
        p["mood"]="angry"
        return f"{p['name']} glares back. 'You don't scare me.'"
    p["mood"]="scared"
    return f"{p['name']} flinches back, eyes wide."

def act_argue(p,**kw)->str:
    _upd(p,affinity=-12,trust=-8,event="argued with player",sentiment="negative")
    if p["personality"].get("aggressive",0)>0.5:
        p["mood"]="angry"
        return f"{p['name']} gets in your face. 'Say that again!'"
    p["mood"]="sad"
    return f"{p['name']} frowns. 'Fine. Believe what you want.'"

def act_threaten(p,**kw)->str:
    _upd(p,fear=20,affinity=-20,trust=-15,event="threatened by player",sentiment="negative")
    p["mood"]="scared"
    if p["personality"].get("brave",0.5)>0.8:
        p["mood"]="angry"
        return f"{p['name']} draws a blade. 'Try it.'"
    return f"{p['name']} pales. 'Please... don't.'"

def act_apologize(p,**kw)->str:
    r=p["relationship"]
    if r["affinity"]>=-20:
        _upd(p,affinity=8,trust=5,fear=-5,event="player apologized",sentiment="positive")
        p["mood"]="neutral"
        return f"{p['name']} sighs. 'Alright. Just... be careful with your words.'"
    _upd(p,affinity=4,event="player apologized",sentiment="neutral")
    return f"{p['name']} says nothing, but her expression softens slightly."

# ---- Neutral/info ----
def act_talk(p,topic="",**kw)->str:
    _upd(p,affinity=2,trust=2,event=f"talked about {topic or 'general things'}",sentiment="neutral")
    if p["mood"]=="angry":return f"{p['name']} ignores you."
    occ=p.get("occupation","wanderer")
    return f"{p['name']} chats with you about life as a {occ}."

def act_ask_rumors(p,**kw)->str:
    r=p["relationship"]
    if r["trust"]<10:
        return f"{p['name']} shrugs. 'Don't know much.' She doesn't look at you."
    _upd(p,affinity=2,event="player asked for rumors",sentiment="neutral")
    rumors=["There's something big in the lower dungeon.","The dealer cheats.","A noble's daughter went missing.",
            "The blacksmith hides enchanted goods.","An adventurer never came back from level 2."]
    import random
    return f"{p['name']} leans in. '{random.choice(rumors)}'"

def act_ask_secret(p,**kw)->str:
    r=p["relationship"]
    if r["trust"]<50:
        return f"{p['name']} laughs quietly. 'You think I'd tell you something like that?'"
    secrets=p.get("secrets",[])
    if not secrets:
        return f"{p['name']} tilts her head. 'I don't have any secrets. Or maybe I do and you'll never know.'"
    import random
    secret=random.choice(secrets)
    _upd(p,trust=10,affinity=5,event="shared secret with player",sentiment="positive")
    return f"{p['name']} whispers: '{secret}'"

# ---- Register all ----
_ACTIONS=[
    ("compliment","Compliment",act_compliment,None,0,8,"positive","Say something nice"),
    ("gift","Give a gift",act_gift,None,0,12,"positive","Give an item"),
    ("hug","Hug",act_hug,lambda p:p["relationship"]["affinity"]>=10,0,10,"physical","Embrace"),
    ("kiss","Kiss",act_kiss,lambda p:p["relationship"]["romance"]>=40,0,15,"romantic","Kiss"),
    ("flirt","Flirt",act_flirt,None,0,6,"romantic","Flirt"),
    ("ask_follow","Ask to follow",act_ask_follow,lambda p:p["relationship"]["affinity"]>=35 and p["relationship"]["trust"]>=20,0,5,"party","Recruit"),
    ("ask_leave","Ask to leave",act_ask_leave,lambda p:p.get("party_member",False),0,0,"party","Dismiss"),
    ("scare","Scare",act_scare,None,-10,0,"negative","Try to intimidate"),
    ("argue","Argue",act_argue,None,-12,0,"negative","Start a fight"),
    ("threaten","Threaten",act_threaten,None,-20,0,"negative","Make a threat"),
    ("apologize","Apologize",act_apologize,lambda p:p["relationship"]["affinity"]<30,-8,8,"social","Say sorry"),
    ("talk","Talk",act_talk,None,0,2,"social","General chat"),
    ("ask_rumors","Ask for rumors",act_ask_rumors,None,0,3,"social","Hear gossip"),
    ("ask_secret","Ask a secret",act_ask_secret,lambda p:p["relationship"]["trust"]>=40,0,5,"social","Learn secrets"),
]

for name,label,fn,cond,cost,gain,cat,desc in _ACTIONS:
    registry.register_relationship_action(name,label,fn,condition=cond,
        affinity_cost=cost,affinity_gain=gain,category=cat,description=desc)
