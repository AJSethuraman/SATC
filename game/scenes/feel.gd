class_name Feel
extends RefCounted

## Every "game feel" number, in one place, on purpose.
##
## READ THIS BEFORE TUNING ANYTHING ELSE.
##
## The simulation layer (core/) is verified by tests: given a stat block, the
## damage that comes out is provably right. Nothing in *this* file can be
## verified that way. Whether a dash feels crisp or floaty, whether hit-stop
## reads as impact or as lag, whether the attack window is generous or sloppy —
## those are answered by a person holding a controller and saying "no, again".
##
## So they are gathered here rather than scattered through the scene code, and
## they are all plain constants. Change one, press play, change it again. That
## loop is the actual work of making this feel like Hades rather than like a
## spreadsheet with sprites, and it is the part that no amount of testing does
## for you.
##
## Starting values below are reasonable-looking guesses in the neighbourhood of
## the genre. They are not tuned. Assume every one of them is wrong.

# --- Movement -----------------------------------------------------------
## Fraction of the gap to target velocity closed per second. Higher is snappier
## and less floaty; too high and the character feels like it teleports.
const MOVE_ACCEL := 18.0
const MOVE_FRICTION := 22.0

# --- Dash ---------------------------------------------------------------
const DASH_SPEED := 900.0
const DASH_DURATION := 0.16
const DASH_COOLDOWN := 0.45
## Invulnerability window, measured from the start of the dash. Deliberately
## slightly longer than the dash itself — that overhang is most of why dodging
## feels fair rather than frame-perfect.
const DASH_IFRAMES := 0.22

# --- Attack -------------------------------------------------------------
const ATTACK_WINDUP := 0.06
const ATTACK_ACTIVE := 0.10
const ATTACK_RECOVERY := 0.16
## How late into recovery the next attack can be buffered. Without this, combos
## feel like they are dropping inputs.
const ATTACK_BUFFER := 0.18
const ATTACK_RANGE := 78.0
## Half-angle of the swing arc, in degrees.
const ATTACK_ARC := 55.0
## Forward lunge applied on swing. Small amounts read as commitment; large
## amounts read as a dash and ruin spacing.
const ATTACK_LUNGE := 140.0

# --- Impact -------------------------------------------------------------
## Frames of near-frozen time on a landed hit. This is the single highest-value
## knob in the file and the easiest to overdo.
const HITSTOP_NORMAL := 0.045
const HITSTOP_CRIT := 0.085
const HITSTOP_SCALE := 0.05

const SHAKE_NORMAL := 3.0
const SHAKE_CRIT := 7.0
const SHAKE_DECAY := 12.0

## How far a struck enemy is shoved, and how fast that decays.
const KNOCKBACK := 260.0
const KNOCKBACK_DECAY := 9.0

## Enemies stop chasing briefly when hit, so a combo does not get traded into.
const HITSTUN := 0.18

# --- Enemies ------------------------------------------------------------
const ENEMY_CONTACT_RANGE := 34.0
const ENEMY_ATTACK_COOLDOWN := 1.25
## Telegraph before an enemy commits to a hit. This is what makes an attack
## dodgeable rather than unfair.
const ENEMY_WINDUP := 0.35
const ENEMY_SEPARATION := 40.0

# --- Camera -------------------------------------------------------------
## Fraction of the distance to the player the camera closes per second. Lower
## trails behind and feels weighty; higher is locked-on and can feel rigid.
const CAMERA_LAG := 6.0
