# Service Inviter

A World of Warcraft addon for the owner's play on WoW: Forever. Not practice software.
It watches chat for people buying a summon or port, invites them, and tracks each
customer from invite to paid (`/si` for the customer list, `/si setup` for every option).

## Install

Run `Install-ServiceInviter.bat` on the machine with WoW. It asks for admin (WoW lives
under Program Files), copies the addon into `_forever_\Interface\AddOns\ServiceInviter`,
and removes the old Trade Inviter from AddOns if it is there. `Install-ServiceInviter.bat
uninstall` removes Service Inviter.

## Change it

- The addon is `ServiceInviter/ServiceInviter.lua` (and its `.toc`).
- The installer is **built**, never hand-edited: change `installer.template.bat` or the
  addon, then run `python build.py`. CI runs `build.py --check` through the tests.

## Test it

```
pip install -r requirements.txt
pytest -q
```

The tests run the real addon file in Lua 5.1 (the game's Lua) against stubbed game
functions in `tests/stubs.lua`, so they are offline. They prove the logic, not the
game: how this client fires trade and spell events has to be watched in game.
