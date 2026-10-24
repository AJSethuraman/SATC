# Roles — what a session is FOR, written where it survives the container

A session in this repository starts blank. Everything it knows about its job
arrives either in the prompt somebody pastes or in a hook, and a pasted prompt
dies with the container — which is continuity through memory, the exact thing
`canon` exists to replace.

**So a role lives here, versioned, and the SessionStart hook reads it out.**

## How a session gets one

The hook reads `$SATC_ROLE` and prints `<role>.md` if a file of that name is
here. Set it on the environment the session runs in:

    SATC_ROLE=research-desk

**No variable, or a name with no file, prints nothing.** That is deliberate and
it is the same rule the rest of this repository runs on: refuse rather than
default. A session handed a role it was not built for is worse than one handed
none — it will act on it. The firm, on `C7`: *"an agent... should really align
with its role"*, and the challenge that entry names is *"an agent given a role
name whose tools and context do not match it."*

## What belongs in a role file

**What the session is for, what arrives, what it hands back, and what it must
never do.** Not how to use a tool — a skill covers that, and duplicating it here
makes two copies that drift. A role file points at the skill.

Keep it short enough to be read every session, because it will be.
