extends Node3D

const PLAYER_SCENE := preload("res://scenes/player.tscn")
const ENEMY_SCENE := preload("res://scenes/enemy.tscn")

var player: CharacterBody3D
var hud_layer: CanvasLayer
var objective_label: Label
var zone_label: Label
var stats_label: Label
var hint_label: Label
var notice_label: Label
var pause_panel: ColorRect
var hit_overlay: ColorRect
var marker: Node3D
var gate: StaticBody3D

var objective_step := 0
var modules := 0
var defense_started := false
var destroyed_enemies := 0
var notice_generation := 0
var story_nodes := {}
var materials := {}
var sfx_players := {}
var ambient_player: AudioStreamPlayer

var objective_positions := [
	Vector3(1.6, 1.0, -8.0),
	Vector3(-2.0, 1.0, -17.0),
	Vector3(2.8, 1.0, -22.0),
	Vector3(0.0, 1.0, -31.0),
	Vector3(0.0, 1.0, -43.0),
	Vector3(2.8, 1.0, -72.0),
	Vector3(0.0, 1.0, -91.0),
	Vector3(-4.0, 1.0, -106.0),
	Vector3(0.0, 1.0, -138.0),
	Vector3(0.0, 1.0, -155.0),
	Vector3(8.0, 1.0, -183.0),
	Vector3(0.0, 1.0, -184.0),
	Vector3(0.0, 1.0, -198.0)
]

var objective_text := [
	"Найдите фонарик",
	"Найдите предохранитель",
	"Восстановите питание",
	"Доберитесь до склада",
	"Возьмите пистолет",
	"Найдите ключ-карту",
	"Пройдите в лабораторию",
	"Найдите два энергомодуля",
	"Запустите основной генератор",
	"Выйдите во внешний двор",
	"Активируйте панель ворот",
	"Переживите последнюю атаку",
	"Покиньте комплекс"
]

func _ready() -> void:
	RenderingServer.set_default_clear_color(Color(0.004, 0.006, 0.011))
	create_environment()
	create_materials()
	create_audio()
	build_facility()
	create_story_props()
	create_player()
	create_hud()
	create_objective_marker()
	spawn_initial_enemies()
	update_hud()
	notify("Вы приходите в себя в заброшенном комплексе. Найдите источник света.", 6.0)

func create_environment() -> void:
	var world_environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.003, 0.005, 0.01)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.12, 0.16, 0.22)
	env.ambient_light_energy = 0.48
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	env.fog_enabled = true
	env.fog_light_color = Color(0.07, 0.1, 0.14)
	env.fog_light_energy = 0.6
	env.fog_density = 0.012
	env.fog_height = 1.6
	env.fog_height_density = 0.12
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world_environment.environment = env
	add_child(world_environment)

	var moon := DirectionalLight3D.new()
	moon.rotation_degrees = Vector3(-55.0, -25.0, 0.0)
	moon.light_color = Color(0.18, 0.28, 0.45)
	moon.light_energy = 0.45
	moon.shadow_enabled = true
	add_child(moon)

func create_audio() -> void:
	for key in ["shoot", "hit", "pickup", "alarm", "reload"]:
		var player_node := AudioStreamPlayer.new()
		var path := "res://assets/audio/" + key + ".wav"
		if ResourceLoader.exists(path):
			player_node.stream = load(path)
		player_node.volume_db = -8.0 if key == "shoot" else -5.0
		add_child(player_node)
		sfx_players[key] = player_node
	ambient_player = AudioStreamPlayer.new()
	if ResourceLoader.exists("res://assets/audio/ambient_technical.wav"):
		ambient_player.stream = load("res://assets/audio/ambient_technical.wav")
		ambient_player.volume_db = -18.0
		ambient_player.finished.connect(ambient_player.play)
		add_child(ambient_player)
		ambient_player.play()

func play_sfx(key: String) -> void:
	if sfx_players.has(key):
		var audio := sfx_players[key] as AudioStreamPlayer
		audio.stop()
		audio.play()

func create_materials() -> void:
	materials["concrete"] = make_material("res://assets/materials/concrete.png", Color(0.34, 0.35, 0.36), 0.05, 0.88)
	materials["metal"] = make_material("res://assets/materials/metal.png", Color(0.14, 0.16, 0.18), 0.78, 0.32)
	materials["rust"] = make_material("res://assets/materials/rust.png", Color(0.26, 0.15, 0.09), 0.48, 0.72)
	materials["floor"] = make_material("res://assets/materials/floor.png", Color(0.13, 0.14, 0.15), 0.22, 0.78)
	materials["lab"] = make_material("res://assets/materials/lab.png", Color(0.38, 0.43, 0.48), 0.46, 0.38)
	materials["yard"] = make_material("res://assets/materials/asphalt.png", Color(0.08, 0.09, 0.10), 0.0, 0.94)
	materials["hazard"] = make_material("res://assets/materials/hazard.png", Color(0.7, 0.48, 0.04), 0.32, 0.58)
	materials["crate"] = make_material("res://assets/materials/crate.png", Color(0.22, 0.16, 0.10), 0.05, 0.82)

func make_material(path: String, fallback: Color, metallic: float, roughness: float) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = fallback
	mat.metallic = metallic
	mat.roughness = roughness
	if ResourceLoader.exists(path):
		mat.albedo_texture = load(path)
		mat.uv1_scale = Vector3(2.0, 2.0, 2.0)
	return mat

func build_facility() -> void:
	build_segment(2.0, -24.0, 8.0, materials["concrete"], materials["floor"], Color(0.55, 0.08, 0.06), true)
	build_segment(-24.0, -58.0, 18.0, materials["rust"], materials["floor"], Color(0.18, 0.31, 0.42), true)
	build_segment(-58.0, -86.0, 8.0, materials["metal"], materials["floor"], Color(0.52, 0.08, 0.05), true)
	build_segment(-86.0, -122.0, 14.0, materials["lab"], materials["floor"], Color(0.12, 0.45, 0.62), true)
	build_segment(-122.0, -150.0, 16.0, materials["metal"], materials["hazard"], Color(0.8, 0.32, 0.05), true)
	build_segment(-150.0, -196.0, 24.0, materials["concrete"], materials["yard"], Color(0.13, 0.24, 0.38), false)

	make_static_box(Vector3(0, 2.75, 3.8), Vector3(8.0, 5.5, 0.35), materials["metal"], "StartWall")
	for z in [-34.0, -46.0, -96.0, -113.0, -133.0]:
		make_static_box(Vector3(-3.2, 1.1, z), Vector3(2.0, 2.2, 0.7), materials["crate"])
		make_static_box(Vector3(3.4, 0.8, z - 2.0), Vector3(1.4, 1.6, 1.4), materials["crate"])
	for z in [-62.0, -69.0, -78.0]:
		make_static_box(Vector3(-2.5, 1.5, z), Vector3(2.4, 3.0, 0.35), materials["metal"])
		make_static_box(Vector3(2.5, 1.0, z - 2.2), Vector3(2.1, 2.0, 0.35), materials["metal"])

	add_pipe_run(Vector3(-3.1, 4.25, -65.0), 18.0)
	add_pipe_run(Vector3(5.8, 4.3, -103.0), 28.0)
	add_warehouse_racks()
	add_lab_props()
	add_generator_props()
	add_yard_props()

	gate = make_static_box(Vector3(0, 2.5, -195.0), Vector3(8.0, 5.0, 0.5), materials["metal"], "ExitGate")
	var gate_sign := Label3D.new()
	gate_sign.text = "EXIT GATE 03"
	gate_sign.font_size = 64
	gate_sign.modulate = Color(0.2, 0.65, 1.0)
	gate_sign.position = Vector3(0, 4.2, -194.65)
	add_child(gate_sign)

func build_segment(z_start: float, z_end: float, width: float, wall_mat: Material, floor_mat: Material, light_color: Color, ceiling: bool) -> void:
	var length := absf(z_end - z_start)
	var center_z := (z_start + z_end) * 0.5
	make_static_box(Vector3(0, -0.12, center_z), Vector3(width, 0.24, length), floor_mat)
	make_static_box(Vector3(-width * 0.5, 2.7, center_z), Vector3(0.3, 5.4, length), wall_mat)
	make_static_box(Vector3(width * 0.5, 2.7, center_z), Vector3(0.3, 5.4, length), wall_mat)
	if ceiling:
		make_static_box(Vector3(0, 5.45, center_z), Vector3(width, 0.22, length), materials["metal"])
	var z := z_start - 5.0
	while z > z_end:
		var light := OmniLight3D.new()
		light.position = Vector3(0, 4.65, z)
		light.omni_range = minf(11.0, width * 0.85)
		light.light_energy = 2.4
		light.light_color = light_color
		light.shadow_enabled = true
		add_child(light)
		var fixture := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(1.4, 0.08, 0.32)
		fixture.mesh = mesh
		fixture.position = Vector3(0, 5.18 if ceiling else 4.8, z)
		var em := StandardMaterial3D.new()
		em.albedo_color = light_color * 0.35
		em.emission_enabled = true
		em.emission = light_color
		em.emission_energy_multiplier = 3.0
		fixture.material_override = em
		add_child(fixture)
		z -= 8.0

func add_pipe_run(origin: Vector3, length: float) -> void:
	for i in range(int(length / 2.0)):
		var pipe := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 0.11
		cyl.bottom_radius = 0.11
		cyl.height = 2.15
		pipe.mesh = cyl
		pipe.material_override = materials["rust"]
		pipe.rotation_degrees = Vector3(90.0, 0.0, 0.0)
		pipe.position = origin + Vector3(0, 0, -float(i) * 2.0)
		add_child(pipe)

func add_warehouse_racks() -> void:
	for side in [-1.0, 1.0]:
		for z in [-31.0, -39.0, -49.0]:
			var x := side * 6.0
			for h in [0.5, 1.7, 2.9]:
				make_deco_box(Vector3(x, h, z), Vector3(2.4, 0.12, 5.0), materials["metal"])
			for dz in [-2.3, 2.3]:
				make_deco_box(Vector3(x - 1.05, 1.7, z + dz), Vector3(0.12, 3.4, 0.12), materials["metal"])
				make_deco_box(Vector3(x + 1.05, 1.7, z + dz), Vector3(0.12, 3.4, 0.12), materials["metal"])
			add_model("res://assets/models/crate.glb", Vector3(x, 0.55, z), Vector3.ONE * 0.8, 0.0)

func add_lab_props() -> void:
	for z in [-94.0, -103.0, -114.0]:
		make_static_box(Vector3(-4.5, 0.55, z), Vector3(2.3, 1.1, 1.0), materials["lab"])
		make_static_box(Vector3(4.5, 0.55, z - 3.0), Vector3(2.3, 1.1, 1.0), materials["lab"])
		add_model("res://assets/models/terminal.glb", Vector3(-4.5, 1.25, z), Vector3.ONE * 0.9, 0.0)

func add_generator_props() -> void:
	make_static_box(Vector3(0, 1.7, -137.5), Vector3(5.0, 3.4, 3.2), materials["metal"])
	for x in [-5.3, 5.3]:
		make_static_box(Vector3(x, 1.25, -133.0), Vector3(2.2, 2.5, 2.2), materials["hazard"])
		add_model("res://assets/models/generator.glb", Vector3(x, 1.2, -133.0), Vector3.ONE, 0.0)

func add_yard_props() -> void:
	for pos in [Vector3(-7, 0.7, -160), Vector3(6, 0.7, -166), Vector3(-8, 0.7, -177), Vector3(7, 0.7, -188)]:
		make_static_box(pos, Vector3(3.2, 1.4, 1.8), materials["rust"])
	for x in [-8.5, 8.5]:
		for z in [-158.0, -170.0, -184.0]:
			var pole := make_static_box(Vector3(x, 2.4, z), Vector3(0.18, 4.8, 0.18), materials["metal"])
			var light := OmniLight3D.new()
			light.position = Vector3(x, 4.5, z)
			light.omni_range = 13.0
			light.light_energy = 2.6
			light.light_color = Color(0.22, 0.42, 0.65)
			light.shadow_enabled = true
			add_child(light)

func make_static_box(pos: Vector3, size: Vector3, mat: Material, node_name := "StaticBox") -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = node_name
	body.position = pos
	var mesh_instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh_instance.mesh = mesh
	mesh_instance.material_override = mat
	body.add_child(mesh_instance)
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	body.add_child(collision)
	add_child(body)
	return body

func make_deco_box(pos: Vector3, size: Vector3, mat: Material) -> MeshInstance3D:
	var item := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	item.mesh = mesh
	item.material_override = mat
	item.position = pos
	add_child(item)
	return item

func add_model(path: String, pos: Vector3, scl: Vector3, rot_y: float) -> void:
	if not ResourceLoader.exists(path):
		return
	var packed := load(path) as PackedScene
	if packed == null:
		return
	var instance := packed.instantiate()
	instance.position = pos
	instance.scale = scl
	instance.rotation.y = rot_y
	add_child(instance)

func create_story_props() -> void:
	story_nodes["flashlight"] = make_pickup("FLASHLIGHT", Vector3(1.6, 0.8, -8.0), Color(0.35, 0.75, 1.0))
	story_nodes["fuse"] = make_pickup("FUSE", Vector3(-2.0, 0.8, -17.0), Color(1.0, 0.65, 0.12))
	story_nodes["panel"] = make_pickup("POWER", Vector3(2.8, 1.3, -22.0), Color(1.0, 0.18, 0.08))
	story_nodes["pistol"] = make_pickup("PISTOL", Vector3(0.0, 0.85, -43.0), Color(0.25, 0.65, 1.0))
	story_nodes["key"] = make_pickup("KEYCARD", Vector3(2.8, 0.85, -72.0), Color(0.2, 0.85, 1.0))
	story_nodes["module1"] = make_pickup("MODULE A", Vector3(-4.0, 0.9, -106.0), Color(0.25, 1.0, 0.55))
	story_nodes["module2"] = make_pickup("MODULE B", Vector3(4.0, 0.9, -116.0), Color(0.25, 1.0, 0.55))
	story_nodes["generator"] = make_pickup("GENERATOR", Vector3(0.0, 1.6, -138.0), Color(1.0, 0.4, 0.08))
	story_nodes["gate_panel"] = make_pickup("GATE CTRL", Vector3(8.0, 1.25, -183.0), Color(0.2, 0.7, 1.0))

func make_pickup(text: String, pos: Vector3, color: Color) -> Node3D:
	var root := Node3D.new()
	root.position = pos
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.48, 0.48, 0.48)
	mesh.mesh = box
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color * 0.25
	mat.metallic = 0.5
	mat.roughness = 0.22
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 3.5
	mesh.material_override = mat
	root.add_child(mesh)
	var light := OmniLight3D.new()
	light.omni_range = 3.5
	light.light_energy = 2.0
	light.light_color = color
	root.add_child(light)
	var label := Label3D.new()
	label.text = text
	label.position = Vector3(0, 0.65, 0)
	label.font_size = 38
	label.modulate = color
	root.add_child(label)
	add_child(root)
	return root

func create_player() -> void:
	player = PLAYER_SCENE.instantiate()
	player.position = Vector3(0, 0.1, -2.5)
	add_child(player)
	player.health_changed.connect(_on_health_changed)
	player.ammo_changed.connect(_on_ammo_changed)

func create_hud() -> void:
	hud_layer = CanvasLayer.new()
	add_child(hud_layer)

	var top := ColorRect.new()
	top.color = Color(0.008, 0.012, 0.02, 0.86)
	top.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top.offset_bottom = 82
	hud_layer.add_child(top)

	objective_label = Label.new()
	objective_label.position = Vector2(30, 16)
	objective_label.add_theme_font_size_override("font_size", 23)
	objective_label.add_theme_color_override("font_color", Color(0.92, 0.96, 1.0))
	top.add_child(objective_label)

	zone_label = Label.new()
	zone_label.position = Vector2(30, 49)
	zone_label.add_theme_font_size_override("font_size", 14)
	zone_label.add_theme_color_override("font_color", Color(0.32, 0.68, 1.0))
	top.add_child(zone_label)

	stats_label = Label.new()
	stats_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	stats_label.position = Vector2(-350, 20)
	stats_label.size = Vector2(320, 45)
	stats_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	stats_label.add_theme_font_size_override("font_size", 20)
	stats_label.add_theme_color_override("font_color", Color(0.95, 0.97, 1.0))
	top.add_child(stats_label)

	var crosshair := Label.new()
	crosshair.text = "+"
	crosshair.set_anchors_preset(Control.PRESET_CENTER)
	crosshair.position = Vector2(-8, -15)
	crosshair.add_theme_font_size_override("font_size", 27)
	crosshair.add_theme_color_override("font_color", Color(0.92, 0.96, 1.0, 0.92))
	hud_layer.add_child(crosshair)

	hint_label = Label.new()
	hint_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	hint_label.position = Vector2(-210, -116)
	hint_label.size = Vector2(420, 40)
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint_label.add_theme_font_size_override("font_size", 18)
	hint_label.add_theme_color_override("font_color", Color(0.95, 0.78, 0.28))
	hud_layer.add_child(hint_label)

	notice_label = Label.new()
	notice_label.set_anchors_preset(Control.PRESET_CENTER_TOP)
	notice_label.position = Vector2(-360, 104)
	notice_label.size = Vector2(720, 60)
	notice_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	notice_label.add_theme_font_size_override("font_size", 21)
	notice_label.add_theme_color_override("font_color", Color(0.75, 0.88, 1.0))
	hud_layer.add_child(notice_label)

	pause_panel = ColorRect.new()
	pause_panel.color = Color(0.0, 0.0, 0.0, 0.72)
	pause_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	pause_panel.visible = false
	hud_layer.add_child(pause_panel)
	var pause_text := Label.new()
	pause_text.text = "ПАУЗА\n\nESC — продолжить\nWASD — движение\nShift — бег   Space — прыжок\nE — взаимодействие   R — перезарядка\nF — фонарик"
	pause_text.set_anchors_preset(Control.PRESET_CENTER)
	pause_text.position = Vector2(-250, -140)
	pause_text.size = Vector2(500, 280)
	pause_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	pause_text.add_theme_font_size_override("font_size", 21)
	pause_panel.add_child(pause_text)

	hit_overlay = ColorRect.new()
	hit_overlay.color = Color(0.65, 0.02, 0.01, 0.0)
	hit_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	hit_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_layer.add_child(hit_overlay)

func create_objective_marker() -> void:
	marker = Node3D.new()
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.26
	torus.outer_radius = 0.38
	ring.mesh = torus
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.08, 0.42, 0.78, 0.75)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.emission_enabled = true
	mat.emission = Color(0.08, 0.55, 1.0)
	mat.emission_energy_multiplier = 5.0
	ring.material_override = mat
	marker.add_child(ring)
	var light := OmniLight3D.new()
	light.omni_range = 3.0
	light.light_energy = 1.5
	light.light_color = Color(0.1, 0.6, 1.0)
	marker.add_child(light)
	add_child(marker)

func _process(delta: float) -> void:
	if marker != null:
		marker.rotation.y += delta * 1.4
		var target := objective_positions[mini(objective_step, objective_positions.size() - 1)]
		marker.position = target + Vector3(0, 1.55 + sin(Time.get_ticks_msec() * 0.003) * 0.12, 0)
	if player == null:
		return
	if objective_step == 3 and player.global_position.z < -29.0:
		advance(4, "СКЛАД B-12", "Найдите оружие. Здесь система безопасности всё ещё активна.")
	elif objective_step == 6 and player.global_position.z < -90.0:
		advance(7, "ЛАБОРАТОРИЯ", "По журналам авария началась здесь. Найдите два энергомодуля.")
	elif objective_step == 9 and player.global_position.z < -153.0:
		advance(10, "ВНЕШНИЙ ДВОР", "Вы почти снаружи. Главные ворота заблокированы.")
	elif objective_step == 12 and player.global_position.z < -198.0:
		finish_game()
	update_proximity_hint()
	update_zone()

func update_zone() -> void:
	if player == null:
		return
	var z := player.global_position.z
	var name := "ТЕХНИЧЕСКИЙ БЛОК"
	if z < -24: name = "СКЛАД"
	if z < -58: name = "СЛУЖЕБНЫЕ КОРИДОРЫ"
	if z < -86: name = "ЛАБОРАТОРИЯ"
	if z < -122: name = "ГЕНЕРАТОРНАЯ"
	if z < -150: name = "ВНЕШНИЙ ДВОР"
	zone_label.text = "ЗОНА: " + name

func update_proximity_hint() -> void:
	var target := objective_positions[mini(objective_step, objective_positions.size() - 1)]
	var dist := player.global_position.distance_to(target)
	hint_label.text = "[E] Взаимодействовать" if dist < 2.4 and objective_step not in [3, 6, 9, 11, 12] else ""

func try_interact(who: Node3D) -> void:
	if who != player:
		return
	var target := objective_positions[mini(objective_step, objective_positions.size() - 1)]
	if player.global_position.distance_to(target) > 2.5:
		notify("Подойдите ближе к объекту.")
		return
	match objective_step:
		0:
			hide_story("flashlight")
			player.flashlight.visible = true
			advance(1, "ТЕХНИЧЕСКИЙ БЛОК", "Фонарик работает. Найдите предохранитель.")
		1:
			hide_story("fuse")
			advance(2, "ТЕХНИЧЕСКИЙ БЛОК", "Предохранитель найден. Верните питание на щитке.")
		2:
			hide_story("panel")
			advance(3, "ТЕХНИЧЕСКИЙ БЛОК", "Питание восстановлено. Проход на склад разблокирован.")
		4:
			hide_story("pistol")
			player.give_pistol()
			advance(5, "СКЛАД B-12", "Пистолет найден. Ищите ключ-карту в служебном секторе.")
			spawn_enemy(Vector3(-4, 0.1, -48), 90)
			spawn_enemy(Vector3(5, 0.1, -53), 90)
		5:
			hide_story("key")
			advance(6, "СЛУЖЕБНЫЕ КОРИДОРЫ", "Ключ-карта получена. Доступ к лаборатории разрешён.")
			player.add_ammo(24)
		7:
			if modules == 0 and player.global_position.distance_to(Vector3(-4, 1, -106)) < 2.5:
				modules = 1
				hide_story("module1")
				notify("Энергомодуль 1/2")
				objective_positions[7] = Vector3(4, 1, -116)
			elif modules == 1 and player.global_position.distance_to(Vector3(4, 1, -116)) < 2.5:
				modules = 2
				hide_story("module2")
				advance(8, "ЛАБОРАТОРИЯ", "Энергомодули 2/2. Запустите главный генератор.")
			else:
				notify("Второй модуль находится глубже в лаборатории.")
		8:
			hide_story("generator")
			advance(9, "ГЕНЕРАТОРНАЯ", "Генератор запущен. Открылся путь во внешний двор.")
			spawn_enemy(Vector3(-5, 0.1, -144), 120)
			spawn_enemy(Vector3(5, 0.1, -146), 120)
		10:
			hide_story("gate_panel")
			start_defense()

func hide_story(key: String) -> void:
	play_sfx("pickup")
	if story_nodes.has(key) and is_instance_valid(story_nodes[key]):
		story_nodes[key].visible = false

func advance(step: int, _zone: String, message: String) -> void:
	objective_step = step
	update_hud()
	notify(message, 5.0)

func start_defense() -> void:
	if defense_started:
		return
	defense_started = true
	objective_step = 11
	play_sfx("alarm")
	update_hud()
	notify("ТРЕВОГА: ворота открываются. Удерживайте двор!", 6.0)
	for pos in [Vector3(-8, 0.1, -169), Vector3(8, 0.1, -172), Vector3(-7, 0.1, -183), Vector3(6, 0.1, -189), Vector3(0, 0.1, -176)]:
		spawn_enemy(pos, 130)

func spawn_initial_enemies() -> void:
	spawn_enemy(Vector3(4, 0.1, -66), 85)
	spawn_enemy(Vector3(-3, 0.1, -80), 85)
	spawn_enemy(Vector3(-5, 0.1, -100), 105)
	spawn_enemy(Vector3(5, 0.1, -119), 105)

func spawn_enemy(pos: Vector3, hp: int) -> void:
	var enemy = ENEMY_SCENE.instantiate()
	enemy.position = pos
	enemy.hp = hp
	add_child(enemy)

func enemy_destroyed(pos: Vector3) -> void:
	destroyed_enemies += 1
	spawn_sparks(pos)
	if objective_step == 11 and get_tree().get_nodes_in_group("enemy").size() <= 1:
		objective_step = 12
		update_hud()
		notify("Ворота открыты. БЕГИТЕ!", 5.0)
		open_gate()

func open_gate() -> void:
	if gate != null and is_instance_valid(gate):
		gate.queue_free()
		gate = null

func spawn_impact(pos: Vector3, normal: Vector3) -> void:
	var mark := MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = 0.035
	mesh.height = 0.07
	mark.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(1.0, 0.55, 0.16)
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.22, 0.05)
	mat.emission_energy_multiplier = 4.0
	mark.material_override = mat
	mark.position = pos + normal * 0.03
	add_child(mark)
	get_tree().create_timer(0.18).timeout.connect(mark.queue_free)

func spawn_sparks(pos: Vector3) -> void:
	for i in range(6):
		var spark := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		sphere.radius = 0.025
		sphere.height = 0.05
		spark.mesh = sphere
		var mat := StandardMaterial3D.new()
		mat.emission_enabled = true
		mat.emission = Color(1.0, 0.25 + float(i) * 0.05, 0.03)
		mat.emission_energy_multiplier = 5.0
		spark.material_override = mat
		spark.position = pos + Vector3(randf_range(-0.25, 0.25), randf_range(0.0, 0.45), randf_range(-0.25, 0.25))
		add_child(spark)
		get_tree().create_timer(0.25 + randf() * 0.35).timeout.connect(spark.queue_free)

func update_hud() -> void:
	if objective_label == null:
		return
	objective_label.text = "OBJECTIVE  //  " + objective_text[mini(objective_step, objective_text.size() - 1)]
	if player != null:
		stats_label.text = "HP %03d    AMMO %02d / %03d" % [player.hp, player.ammo, player.reserve_ammo]

func _on_health_changed(_value: int) -> void:
	update_hud()

func _on_ammo_changed(_current: int, _reserve: int) -> void:
	update_hud()

func notify(text: String, seconds := 3.0) -> void:
	notice_generation += 1
	var generation := notice_generation
	notice_label.text = text
	await get_tree().create_timer(seconds).timeout
	if generation == notice_generation and is_instance_valid(notice_label):
		notice_label.text = ""

func set_pause_ui(value: bool) -> void:
	if pause_panel != null:
		pause_panel.visible = value

func player_hit_feedback() -> void:
	if hit_overlay == null:
		return
	hit_overlay.color.a = 0.22
	var tween := create_tween()
	tween.tween_property(hit_overlay, "color:a", 0.0, 0.24)

func player_died() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var dialog := AcceptDialog.new()
	dialog.title = "NEON RIFT"
	dialog.dialog_text = "Система костюма отключена. Попробуйте снова."
	dialog.confirmed.connect(get_tree().reload_current_scene)
	hud_layer.add_child(dialog)
	dialog.popup_centered(Vector2i(520, 220))

func finish_game() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var cfg := ConfigFile.new()
	cfg.load("user://progress.cfg")
	var wins := int(cfg.get_value("progress", "wins", 0)) + 1
	cfg.set_value("progress", "wins", wins)
	cfg.set_value("progress", "escaped", true)
	cfg.save("user://progress.cfg")
	var dialog := AcceptDialog.new()
	dialog.title = "ESCAPED"
	dialog.dialog_text = "Вы выбрались из комплекса.\n\nNEON RIFT: ABANDONED\nMonoSystem"
	dialog.confirmed.connect(get_tree().quit)
	hud_layer.add_child(dialog)
	dialog.popup_centered(Vector2i(560, 260))
