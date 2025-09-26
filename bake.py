import bpy

# Пути к моделям
emoca_path = "/workspace/emoca.obj"
next3d_path = "/workspace/next3d.obj"
output_tex = "/workspace/final_texture.png"

# Очистка сцены
bpy.ops.wm.read_factory_settings(use_empty=True)

# Импорт моделей
bpy.ops.import_scene.obj(filepath=emoca_path)
bpy.ops.import_scene.obj(filepath=next3d_path)

# Предположим имена объектов
emoca = bpy.data.objects[0]
next3d = bpy.data.objects[1]

# Материал для EMOCA
mat = bpy.data.materials.new(name="BakedMat")
mat.use_nodes = True
emoca.data.materials.append(mat)

# Новая текстура (4K)
img = bpy.data.images.new("BakedTex", width=4096, height=4096)

# Настройка Bake
nodes = mat.node_tree.nodes
tex_image = nodes.new(type="ShaderNodeTexImage")
tex_image.image = img
nodes.active = tex_image

# Выбор объектов
bpy.context.view_layer.objects.active = emoca
bpy.ops.object.select_all(action='DESELECT')
emoca.select_set(True)
next3d.select_set(True)

# Bake diffuse
bpy.ops.object.bake(type='DIFFUSE', use_clear=True, pass_filter={'COLOR'})

# Сохраняем текстуру
img.filepath_raw = output_tex
img.file_format = 'PNG'
img.save()
