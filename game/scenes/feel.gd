class_name Feel
extends RefCounted

## Every "game feel" and presentation number, in one place, on purpose.
##
## READ THIS BEFORE TUNING ANYTHING ELSE.
##
## The simulation layer (core/) is verified by tests: given a stat block, the
## damage that comes out is provably right. Nothing in *this* file can be
## verified that way. Whether a dash feels crisp or floaty, whether hit-stop
## reads as impact or as lag, whether the camera angle flatters the scene —
## those are answered by a person at a keyboard saying "no, again".
##
## So they are gathered here rather than scattered through the scene code, and
## they are all plain constants. Change one, press play, change it again. That
## loop is the actual work of making this feel like Hades rather than like a
## spreadsheet with shapes, and it is the part no amount of testing does for you.
##
## Starting values are reasonable-looking guesses in the neighbourhood of the
## genre. They are not tuned. Assume every one of them is wrong.

# --- World scale --------------------------------------------------------
## core/ speaks in pixels — 220 move speed, 78 attack range — because it was
## written against a flat 2D prototype. The 3D presentation works in metres, so
## everything crossing that boundary is converted here rather than in ten places.
const UNITS_PER_PIXEL := 1.0 / 32.0

## Arena footprint on the ground plane, in metres.
const ARENA := Vector2(26.0, 20.0)
const WALL_THICKNESS := 1.2
const WALL_HEIGHT := 1.6

# --- Body proportions ---------------------------------------------------
const PLAYER_RADIUS := 0.42
const PLAYER_HEIGHT := 1.7
const ENEMY_RADIUS := 0.40
const ENEMY_HEIGHT := 1.5
const ELITE_SCALE := 1.5

# --- Movement -----------------------------------------------------------
## Fraction of the gap to target velocity closed per second. Higher is snappier
## and less floaty; too high and the character feels like it teleports.
const MOVE_ACCEL := 18.0
const MOVE_FRICTION := 22.0

# --- Dash ---------------------------------------------------------------
const DASH_SPEED := 28.0
const DASH_DURATION := 0.16
const DASH_COOLDOWN := 0.45
## Invulnerability measured from the start of the dash. Deliberately a little
## longer than the dash itself — that overhang is most of why dodging feels fair
## rather than frame-perfect.
const DASH_IFRAMES := 0.22

# --- Attack -------------------------------------------------------------
const ATTACK_WINDUP := 0.06
const ATTACK_ACTIVE := 0.10
const ATTACK_RECOVERY := 0.16
## How late into recovery the next attack can be buffered. Without this, combos
## feel like they are dropping inputs.
const ATTACK_BUFFER := 0.18
const ATTACK_RANGE := 2.6
## Half-angle of the swing arc, in degrees.
const ATTACK_ARC := 55.0
## Forward lunge on the swing. Small amounts read as commitment; large amounts
## read as a second dash and wreck spacing.
const ATTACK_LUNGE := 5.0

# --- Impact -------------------------------------------------------------
## Frames of near-frozen time on a landed hit. The highest-value knob in this
## file, and the easiest to overdo.
##
## Counted in frames rather than seconds because that is how hit-stop is
## actually authored — fighting games specify it in frames — and because a
## wall-clock timer stretches to absurdity whenever the engine is not running at
## real speed, which is exactly what happens while recording a demo.
const HITSTOP_FRAMES_NORMAL := 3
const HITSTOP_FRAMES_CRIT := 6
const HITSTOP_SCALE := 0.05

const SHAKE_NORMAL := 0.12
const SHAKE_CRIT := 0.28
const SHAKE_DECAY := 1.4

const KNOCKBACK := 7.0
const KNOCKBACK_DECAY := 9.0

## Enemies stop chasing briefly when hit, so a combo does not get traded into.
const HITSTUN := 0.18

# --- Procedural animation ----------------------------------------------
## No hand-drawn frames exist, so every bit of life in this prototype comes from
## code deforming primitives. This is the cheapest convincing substitute for
## animation, and the section most worth playing with.

## How far the body leans into its movement direction, in degrees at full speed.
const LEAN_DEGREES := 14.0
const LEAN_RESPONSE := 9.0

## Dash squash: scale along travel, and the matching pinch across it.
const DASH_STRETCH := 1.06
const DASH_SQUASH := 0.94
## Degrees the body tips into a dash. Does the work the old stretch was doing,
## without flattening a standing figure onto the floor.
const DASH_LEAN := -24.0

## Windup crouch before a swing, then the overshoot on release.
const ATTACK_CROUCH := 0.88
const ATTACK_POP := 1.12
const SHAPE_RECOVERY := 12.0

## Idle bob, so nothing ever sits perfectly still.
const BOB_HEIGHT := 0.045
const BOB_SPEED := 2.2

## Seconds the white hit-flash lasts on a struck body.
const FLASH_TIME := 0.12

## The swing arc, and how fast it fades.
##
## Drawn as a band rather than a filled fan: a solid wedge from the feet to full
## reach reads as a pizza slice sitting on the floor, where a ring segment reads
## as the path a blade swept through. Inner edge as a fraction of reach.
const SLASH_FADE := 15.0
const SLASH_SEGMENTS := 20
const SLASH_INNER_RATIO := 0.7
const SLASH_ALPHA := 0.3
## Lifted just off the floor so it does not z-fight with it.
const SLASH_HEIGHT := 0.14

# --- Enemies ------------------------------------------------------------
const ENEMY_CONTACT_RANGE := 1.5
const ENEMY_ATTACK_COOLDOWN := 1.25
## Telegraph before an enemy commits. This is what makes an attack dodgeable
## rather than unfair.
const ENEMY_WINDUP := 0.35
const ENEMY_SEPARATION := 2.1
## Strength of that push. Must exceed the chase speed at close range or the pack
## collapses into one overlapping mass — which is what it did at 4.0.
const SEPARATION_FORCE := 9.0
## How much a winding-up enemy swells, as a scale multiplier.
const ENEMY_TELL_SWELL := 1.18

# --- Camera -------------------------------------------------------------
## Fixed isometric-ish rig: the camera never rotates, it only follows.
## Elevation is the angle above the horizon; lower is more dramatic and hides
## less of the floor, higher reads more like a map.
const CAMERA_ELEVATION := 42.0
const CAMERA_AZIMUTH := 45.0
## Orthographic, so there is no perspective distortion across the arena and
## depth reads purely from the angle and the shadows.
const CAMERA_SIZE := 11.0
const CAMERA_DISTANCE := 45.0

## Fraction of the distance to the player the camera closes per second. Lower
## trails behind and feels weighty; higher is locked-on and can feel rigid.
const CAMERA_LAG := 6.0
## How far the camera leads the aim direction. A little makes the view feel
## intentional; a lot makes it seasick.
const CAMERA_AIM_LEAD := 1.6

# --- Palette ------------------------------------------------------------
## Placeholder colours. Lighting is doing the work that art would otherwise do,
## so these are deliberately desaturated — saturated primaries on lit primitives
## read as a debug view rather than a game.
const COLOUR_FLOOR := Color(0.13, 0.12, 0.15)
const COLOUR_WALL := Color(0.22, 0.20, 0.25)
const COLOUR_PLAYER := Color(0.86, 0.87, 0.91)
const COLOUR_ENEMY := Color(0.46, 0.31, 0.36)
const COLOUR_ELITE := Color(0.74, 0.27, 0.28)
const COLOUR_TELL := Color(1.0, 0.72, 0.26)
const COLOUR_IFRAME := Color(0.48, 0.78, 1.0)
const COLOUR_SLASH := Color(1.0, 0.94, 0.76)

const LIGHT_COLOUR := Color(1.0, 0.94, 0.86)
const LIGHT_ENERGY := 1.5
const AMBIENT_COLOUR := Color(0.30, 0.32, 0.44)
const AMBIENT_ENERGY := 0.55
const FOG_COLOUR := Color(0.05, 0.05, 0.07)
