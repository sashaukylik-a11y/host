extends CharacterBody3D

@export var hp := 100
@export var move_speed := 2.6
@export var detection_range := 22.0
@export var attack_range := 1.8
@export var attack_damage := 12

var target: Node3D
var awake := false
var attack_cooldown := 0.0
var gravity := 9.8
var dead := false

func _ready() -> void:
	add_to_group("enemy")
	gravity = float(ProjectSettings.get_setting("physics/3d/default_gravity", 9.8))
	target = get_tree().get_first_node_in_group("player")

func _physics_process(delta: float) -> void:
	if dead or target == null:
		return
	if not is_on_floor():
		velocity.y -= gravity * delta

	var distance := global_position.distance_to(target.global_position)
	if distance <= detection_range:
		awake = true
	if not awake:
		velocity.x = move_toward(velocity.x, 0.0, 8.0 * delta)
		velocity.z = move_toward(velocity.z, 0.0, 8.0 * delta)
		move_and_slide()
		return

	if distance > attack_range:
		var dir := target.global_position - global_position
		dir.y = 0.0
		dir = dir.normalized()
		velocity.x = dir.x * move_speed
		velocity.z = dir.z * move_speed
		if dir.length_squared() > 0.01:
			look_at(global_position + dir, Vector3.UP, true)
	else:
		velocity.x = move_toward(velocity.x, 0.0, 12.0 * delta)
		velocity.z = move_toward(velocity.z, 0.0, 12.0 * delta)
		attack_cooldown -= delta
		if attack_cooldown <= 0.0:
			attack_cooldown = 0.8
			if target.has_method("take_damage"):
				target.take_damage(attack_damage)
	move_and_slide()

func take_damage(amount: int, _hit_position := Vector3.ZERO) -> void:
	if dead:
		return
	awake = true
	hp -= amount
	var body := get_node_or_null("Body") as MeshInstance3D
	if body != null:
		var original := body.modulate
		body.modulate = Color(1.0, 0.2, 0.12)
		await get_tree().create_timer(0.06).timeout
		if is_instance_valid(body):
			body.modulate = original
	if hp <= 0:
		die()

func die() -> void:
	if dead:
		return
	dead = true
	get_tree().current_scene.enemy_destroyed(global_position)
	queue_free()
