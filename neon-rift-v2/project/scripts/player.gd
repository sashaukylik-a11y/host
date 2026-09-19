extends CharacterBody3D

signal health_changed(value: int)
signal ammo_changed(current: int, reserve: int)

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var flashlight: SpotLight3D = $Head/Camera3D/Flashlight
@onready var weapon: Node3D = $Head/Camera3D/Weapon
@onready var muzzle: MeshInstance3D = $Head/Camera3D/Weapon/Muzzle
@onready var muzzle_light: OmniLight3D = $Head/Camera3D/Weapon/Muzzle/MuzzleLight

var move_speed := 4.2
var sprint_speed := 6.7
var jump_velocity := 5.0
var mouse_sensitivity := 0.0020
var hp := 100
var ammo := 0
var reserve_ammo := 0
var magazine_size := 12
var weapon_owned := false
var reloading := false
var can_fire := true
var gravity := 9.8

func _ready() -> void:
	add_to_group("player")
	gravity = float(ProjectSettings.get_setting("physics/3d/default_gravity", 9.8))
	var cfg := ConfigFile.new()
	if cfg.load("user://settings.cfg") == OK:
		mouse_sensitivity = float(cfg.get_value("input", "mouse_sensitivity", mouse_sensitivity))
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		head.rotation.x = clamp(head.rotation.x - event.relative.y * mouse_sensitivity, deg_to_rad(-85.0), deg_to_rad(85.0))
	elif event.is_action_pressed("pause_game"):
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		else:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		get_tree().current_scene.set_pause_ui(Input.mouse_mode != Input.MOUSE_MODE_CAPTURED)
	elif event.is_action_pressed("shoot"):
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
			get_tree().current_scene.set_pause_ui(false)
		else:
			fire()
	elif event.is_action_pressed("interact"):
		get_tree().current_scene.try_interact(self)
	elif event.is_action_pressed("reload"):
		reload_weapon()
	elif event.is_action_pressed("flashlight"):
		flashlight.visible = not flashlight.visible

func _physics_process(delta: float) -> void:
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		velocity.x = move_toward(velocity.x, 0.0, 18.0 * delta)
		velocity.z = move_toward(velocity.z, 0.0, 18.0 * delta)
		move_and_slide()
		return

	if not is_on_floor():
		velocity.y -= gravity * delta
	elif Input.is_action_just_pressed("jump"):
		velocity.y = jump_velocity

	var input_vec := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var direction := (transform.basis * Vector3(input_vec.x, 0.0, input_vec.y)).normalized()
	var speed := sprint_speed if Input.is_action_pressed("sprint") else move_speed
	if direction.length_squared() > 0.01:
		velocity.x = direction.x * speed
		velocity.z = direction.z * speed
	else:
		velocity.x = move_toward(velocity.x, 0.0, 22.0 * delta)
		velocity.z = move_toward(velocity.z, 0.0, 22.0 * delta)
	move_and_slide()

func give_pistol() -> void:
	weapon_owned = true
	ammo = 12
	reserve_ammo = 60
	weapon.visible = true
	ammo_changed.emit(ammo, reserve_ammo)

func add_ammo(amount: int) -> void:
	reserve_ammo += amount
	ammo_changed.emit(ammo, reserve_ammo)

func heal(amount: int) -> void:
	hp = mini(100, hp + amount)
	health_changed.emit(hp)

func take_damage(amount: int) -> void:
	hp = maxi(0, hp - amount)
	health_changed.emit(hp)
	get_tree().current_scene.player_hit_feedback()
	if hp <= 0:
		get_tree().current_scene.player_died()

func fire() -> void:
	if not weapon_owned or reloading or not can_fire:
		return
	if ammo <= 0:
		get_tree().current_scene.notify("Магазин пуст. Нажмите R.")
		return
	ammo -= 1
	ammo_changed.emit(ammo, reserve_ammo)
	can_fire = false
	muzzle.visible = true
	muzzle_light.visible = true
	head.rotation.x = clamp(head.rotation.x - deg_to_rad(0.55), deg_to_rad(-85.0), deg_to_rad(85.0))

	var origin := camera.global_position
	var direction := -camera.global_transform.basis.z
	var query := PhysicsRayQueryParameters3D.create(origin, origin + direction * 120.0, 3)
	query.exclude = [get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		var collider = hit.get("collider")
		if collider != null and collider.has_method("take_damage"):
			collider.take_damage(34, hit.get("position", Vector3.ZERO))
		get_tree().current_scene.spawn_impact(hit.get("position", Vector3.ZERO), hit.get("normal", Vector3.UP))

	await get_tree().create_timer(0.045).timeout
	muzzle.visible = false
	muzzle_light.visible = false
	await get_tree().create_timer(0.105).timeout
	can_fire = true

func reload_weapon() -> void:
	if not weapon_owned or reloading or ammo >= magazine_size or reserve_ammo <= 0:
		return
	reloading = true
	get_tree().current_scene.notify("Перезарядка…")
	await get_tree().create_timer(0.85).timeout
	var need := magazine_size - ammo
	var moved := mini(need, reserve_ammo)
	ammo += moved
	reserve_ammo -= moved
	reloading = false
	ammo_changed.emit(ammo, reserve_ammo)

func save_settings() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("input", "mouse_sensitivity", mouse_sensitivity)
	cfg.save("user://settings.cfg")
