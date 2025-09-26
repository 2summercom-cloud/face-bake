# bake.py
import bpy
import sys
import os
import mathutils

def parse_args():
    argv = sys.argv
    if "--" in argv:
        idx = argv.index("--")
        args = argv[idx+1:]
    else:
        args = []
    # default values
    emoca = args[0] if len(args) > 0 else "/workspace/emoca.obj"
    next3d = args[1] if len(args) > 1 else "/workspace/next3d.obj"
    out_tex = args[2] if len(args) > 2 else "/workspace/final_texture.png"
    out_obj = args[3] if len(args) > 3 else "/workspace/final_emoca.obj"
    res = int(args[4]) if len(args) > 4 else int(os.environ.get("BAKED_RES", "2048"))
    return emoca, next3d, out_tex, out_obj, res

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def import_obj(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"OBJ not found: {path}")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.obj(filepath=path)
    after = set(bpy.data.objects)
    new = list(after - before)
    meshes = [o for o in new if o.type == 'MESH']
    if meshes:
        return meshes[0]
    # fallback: pick any mesh
    for o in bpy.data.objects:
        if o.type == 'MESH':
            return o
    raise RuntimeError("No mesh imported")

def ensure_uv(obj):
    if not obj.data.uv_layers:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.smart_project(angle_limit=66.0)
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False)

def center_and_scale(src, tgt):
    def center(obj):
        bb = [obj.matrix_world @ mathutils.Vector(b) for b in obj.bound_box]
        return sum(bb, mathutils.Vector()) / 8.0
    s_center = center(src)
    t_center = center(tgt)
    trans = t_center - s_center
    src.location += trans
    # scale uniformly
    s_size = max((v - s_center).length for v in [src.matrix_world @ mathutils.Vector(b) for b in src.bound_box])
    t_size = max((v - t_center).length for v in [tgt.matrix_world @ mathutils.Vector(b) for b in tgt.bound_box])
    if s_size > 0 and t_size > 0:
        scale = t_size / s_size
        src.scale = [c * scale for c in src.scale]

def create_image(name, w, h, path):
    img = bpy.data.images.new(name, width=w, height=h)
    img.filepath_raw = path
    img.file_format = 'PNG'
    return img

def assign_image_to_obj(obj, img):
    if not obj.data.materials:
        mat = bpy.data.materials.new(name="BakedMat")
        mat.use_nodes = True
        obj.data.materials.append(mat)
    else:
        mat = obj.data.materials[0]
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = img
    nodes.active = tex_node
    return tex_node

def bake_diffuse(target, source, img):
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    source.select_set(True)
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'
    bpy.context.scene.render.bake.use_clear = True
    # selected to active
    bpy.ops.object.bake(type='DIFFUSE', use_clear=True, use_selected_to_active=True, use_pass_direct=False, use_pass_indirect=False)
    img.save()

def export_obj(obj, path):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.export_scene.obj(filepath=path, use_materials=True, use_selection=True)

def main():
    emoca_path, next3d_path, out_tex, out_obj, res = parse_args()
    print("Baking with:", emoca_path, next3d_path, out_tex, out_obj, res)
    clear_scene()
    emoca = import_obj(emoca_path)
    next3d = import_obj(next3d_path)
    center_and_scale(next3d, emoca)
    ensure_uv(emoca)
    img = create_image("BakedTex", res, res, out_tex)
    assign_image_to_obj(emoca, img)
    bake_diffuse(emoca, next3d, img)
    export_obj(emoca, out_obj)
    print("Bake finished. Saved:", out_tex, out_obj)

if __name__ == "__main__":
    main()
