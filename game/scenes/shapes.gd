class_name Shapes
extends RefCounted

## Procedurally-built meshes and materials for the placeholder presentation.
##
## There is no art in this project, so every visible thing is a primitive built
## in code. Keeping that construction here means the scene scripts stay about
## behaviour rather than about mesh plumbing.


## A flat wedge on the XZ plane: a triangle fan spanning `2 * half_angle_deg`,
## used to draw the attack arc. Built rather than authored because a torus
## segment is not a primitive Godot ships and a quad reads nothing like a swing.
static func arc_wedge(radius: float, half_angle_deg: float, segments: int) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()

	var half := deg_to_rad(half_angle_deg)
	var step := (half * 2.0) / float(maxi(1, segments))

	for i in segments:
		var a0 := -half + step * float(i)
		var a1 := a0 + step
		# Forward is -Z, so the wedge points the way the body faces.
		var p0 := Vector3(sin(a0), 0.0, -cos(a0)) * radius
		var p1 := Vector3(sin(a1), 0.0, -cos(a1)) * radius

		verts.append(Vector3.ZERO)
		verts.append(p0)
		verts.append(p1)
		for _n in 3:
			normals.append(Vector3.UP)
		uvs.append(Vector2(0.5, 1.0))
		uvs.append(Vector2(0.0, 0.0))
		uvs.append(Vector2(1.0, 0.0))

	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs

	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


## Matte surface for bodies and terrain. Low specular on purpose: shiny
## primitives look like a physics demo, matte ones read as objects.
static func solid(colour: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = colour
	mat.roughness = 0.85
	mat.metallic = 0.0
	mat.metallic_specular = 0.15
	return mat


## Unshaded additive surface for effects — a slash should glow rather than be lit.
static func glow(colour: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = colour
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.no_depth_test = false
	return mat


## Upright capsule mesh sized by radius and total height.
static func body_capsule(radius: float, height: float) -> CapsuleMesh:
	var mesh := CapsuleMesh.new()
	mesh.radius = radius
	mesh.height = maxf(height, radius * 2.0 + 0.01)
	mesh.radial_segments = 16
	mesh.rings = 6
	return mesh
