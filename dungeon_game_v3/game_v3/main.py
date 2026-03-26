import sys,os
sys.path.insert(0,os.path.dirname(__file__))

from engine import registry
from engine.core import state,bus
from engine.entity import make_player

import systems.world
import systems.combat
import systems.relationship
import systems.economy
import systems.dialogue
import systems.saveload
import data.actions
import menus

def boot(player_name:str="Hero")->str:
    state.player=make_player(player_name)
    registry.get_system("world_builder")(state)
    state.world.current_key="town_square"
    return f"Welcome, {player_name}.\n\n{state.world.current().summary()}\n\nType 'help' for commands."

def tick(cmd:str)->str:
    state.turn+=1
    bus.emit("turn_start",turn=state.turn,cmd=cmd)
    from menus.navigation import handle_navigation
    result=handle_navigation(cmd)
    bus.emit("turn_end",turn=state.turn,result=result)
    return result

def run_repl():
    name=input("Enter your name: ").strip() or "Hero"
    print(boot(name))
    while True:
        try:
            cmd=input("\n> ").strip()
            if not cmd:continue
            if cmd.lower() in("quit","exit","q"):print("Farewell.");break
            print(tick(cmd))
        except(KeyboardInterrupt,EOFError):print("\nFarewell.");break

if __name__=="__main__":
    run_repl()
