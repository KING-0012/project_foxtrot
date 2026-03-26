from engine import registry
import menus.commands  # registers all handlers on import

def handle_navigation(cmd:str,**kw)->str:
    result=registry.dispatch_command(cmd)
    if result is not None:return result
    return f"Unknown command: '{cmd.strip()}'. Type 'help' for commands."
