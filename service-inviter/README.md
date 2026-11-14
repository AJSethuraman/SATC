# Service Inviter

A World of Warcraft addon for the owner's play on WoW: Forever. Not practice software.
It works out what the group can sell from who is in it (summons to where the warlock is,
the mage's portals, lockpicking, water, stones, buffs), invites buyers from chat, tells
each one what they're getting, from whom, where and who to pay, writes the ad, and tracks
each customer to paid. `/si` for the customer list, `/si setup` for the tabbed setup,
`/si bind ad F7` to post the ad with one key. The design and its sources: `docs/DESIGN.md`.

## Install

Run `Install-ServiceInviter.bat` on the machine with WoW. It asks for admin (WoW lives
under Program Files), copies the addon into `_forever_\Interface\AddOns\ServiceInviter`,
and removes the old Trade Inviter from AddOns if it is there. `Install-ServiceInviter.bat
uninstall` removes Service Inviter.

## Change it

- The rules are `ServiceInviter/Services.lua` (pure, tested on their own); the window and
  game events are `ServiceInviter/ServiceInviter.lua`; both are listed in the `.toc`.
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
