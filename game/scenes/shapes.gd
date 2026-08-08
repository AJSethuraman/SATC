class_name Shapes
extends RefCounted

## Procedurally-built meshes and materials for the placeholder presentation.
##
## There is no art in this project, so every visible thing is a primitive built
## in code. Keeping that construction here means the scene scripts stay about
## behaviour rather than about mesh plumbing.


## A flat ring segment on the XZ plane spanning `2 * half_angle_deg`, used to
## draw the attack arc.
##
## A band rather than a filled fan on purpose: a solid wedge running from the
## feet out to full reach reads as a pizza slice lying on the floor, whereas a
## segment reads as the path a blade swept through. Built rather than authored
## because Godot ships no ring-segment primitive and a quad reads as neither.
static func arc_band(
	inner_radius: float, outer_radius: float, half_angle_deg: float, segments: int
) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()

	var half := deg_to_rad(half_angle_deg)
	var step := (half * 2.0) / float(maxi(1, segments))

	for i in segments:
		var a0 := -half + step * float(i)
		var a1 := a0 + step
		# Forward is -Z, so the arc sweeps across the way the body faces.
		var dir0 := Vector3(sin(a0), 0.0, -cos(a0))
		var dir1 := Vector3(sin(a1), 0.0, -cos(a1))
		var inner0 := dir0 * inner_radius
		var inner1 := dir1 * inner_radius
		var outer0 := dir0 * outer_radius
		var outer1 := dir1 * outer_radius

		# Two triangles per segment, wound so the band faces up.
		verts.append(inner0)
		verts.append(outer0)
		verts.append(outer1)
		verts.append(inner0)
		verts.append(outer1)
		verts.append(inner1)
		for _n in 6:
			normals.append(Vector3.UP)

		var u0 := float(i) / float(segments)
		var u1 := float(i + 1) / float(segments)
		uvs.append(Vector2(u0, 0.0))
		uvs.append(Vector2(u0, 1.0))
		uvs.append(Vector2(u1, 1.0))
		uvs.append(Vector2(u0, 0.0))
		uvs.append(Vector2(u1, 1.0))
		uvs.append(Vector2(u1, 0.0))

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
