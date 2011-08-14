import bpy
import os
import sys
import math
import mathutils



def print_indent():
    global indent_level, export_file
    for i in range(indent_level):
        export_file.write("  ")
        
def write_indented(s):
    global export_file
    print_indent()
    export_file.write(s)
    export_file.write("\n")

def open_class(name):
    global export_file, indent_level
    print_indent()
    export_file.write(name)
    export_file.write(" {\n")
    indent_level += 1
    
def close_class():
    global export_file, indent_level
    indent_level -= 1
    print_indent()
    export_file.write("}\n")

def write_lamp(l):
    global current_scene
    
    lamp = l.data
    if lamp.type == "AREA":
        print("Warning: Area lamp type is not supported in openscenegraph. Skipping.\n")
        return
    if lamp.type == 'SUN':
        print("Warning: Sun lamp type is not supported in openscenegraph. Skipping.\n")
        return


    open_class("LightSource")
    write_indented("name \"%s\"" % l.name)
    open_class("Light")
    write_indented("ambient %f %f %f %f" % (current_scene.world.ambient_color[0], current_scene.world.ambient_color[1], current_scene.world.ambient_color[2], 1))

    if lamp.use_diffuse:
        write_indented("diffuse %f %f %f %f" % (lamp.color[0], lamp.color[1], lamp.color[2], 1))
    else:
        write_indented("diffuse 0 0 0 0")

    if lamp.use_specular:
        write_indented("specular 1.00000 1.00000 1.00000 1.00000")
    else:
        write_indented("specular 0 0 0 0")

    if lamp.type == 'POINT':
        write_indented("position %f %f %f" % (l.location[0], l.location[1], l.location[2]))
        write_indented("constant_attenuation %f" % lamp.distance)
        write_indented("linear_attenuation %f" % lamp.linear_attenuation)
        write_indented("quadratic_attenuation %f" % lamp.quadratic_attenuation)
    if lamp.type == 'SPOT':
        write_indented("position %f %f %f" % (l.location[0], l.location[1], l.location[2]))
        v = mathutils.Vector((0, 0, -1))
        v.normalize()
        v.rotate(l.rotation_euler)
        write_indented("direction %f %f %f" % (v[0], v[1], v[2]))
        write_indented("constant_attenuation %f" % lamp.distance)
        write_indented("linear_attenuation %f" % lamp.distance)
        write_indented("quadratic_attenuation %f" % lamp.quadratic_attenuation)
        write_indented("spot_exponent %f" % lamp.spot_blend)
        write_indented("spot_cutoff %f" % math.degrees(lamp.spot_size))
    elif lamp.type == "HEMI":
        write_indented("position %f %f %f" % (l.location[0], l.location[1], l.location[2]))
        write_indented("constant_attenuation %f" % lamp.distance)
        v = mathutils.Vector((0, 0, -1))
        v.normalize()
        v.rotate(l.rotation_euler)
        write_indented("direction %f %f %f" % (v[0], v[1], v[2]))


    close_class()
    write_indented("num_children 0")
    close_class()

    
def write_mesh(m):
    global current_scene
    open_class("Geode")
    write_indented("name \"%s\"" % m.name)
    # count the drawables
    # draw each material as a separate geometry - but they all share the same vertex and normal lists

    modified_mesh = m.to_mesh(current_scene, apply_modifiers, 'RENDER')
    material_index = 0

    write_indented("num_drawables %d" % len(m.material_slots))

    for material_slot in m.material_slots:
        open_class("Geometry")

        # write the material
        open_class("StateSet")

        write_indented("GL_BLEND ON")
        open_class("Material")
        write_indented("name \"%s\"" % material_slot.name)

        
        write_indented("ColorMode OFF")
        write_indented("ambientColor %f %f %f %f" % (material_slot.material.ambient, 
                                                     material_slot.material.ambient, 
                                                     material_slot.material.ambient, 
                                                     material_slot.material.ambient))

        d = material_slot.material.diffuse_color
        if material_slot.material.use_object_color:
            d[0] *= m.color[0]
            d[1] *= m.color[1]
            d[2] *= m.color[2]

        write_indented("diffuseColor %f %f %f %f" % (d[0] * material_slot.material.diffuse_intensity,
                                                     d[1] * material_slot.material.diffuse_intensity,
                                                     d[2] * material_slot.material.diffuse_intensity,
                                                     1))
        
        write_indented("specularColor %f %f %f %f" % (0,
                                                     0,
                                                     0,
                                                     1))
    
        write_indented("emissionColor %f %f %f %f" % (material_slot.material.emit, material_slot.material.emit, material_slot.material.emit, material_slot.material.emit))
        # Hardness is a value from 1 - 511
        # The equation below brings it back to the range 0.0 to 10.0
        write_indented("shininess %f" % ((material_slot.material.specular_hardness - 1.0) / 51.0))
    
        close_class()
        
        if material_slot.material.active_texture != None and material_slot.material.active_texture.type == 'IMAGE' and material_slot.material.active_texture.image != None:
            # render the texture to a bitmap
            image_texture = material_slot.material.active_texture
            image = image_texture.image
            filename = os.path.join(os.path.dirname(filepath), os.path.basename(filepath).split(".")[0] + "-" + os.path.basename(image.filepath).split(".")[0] + ".png");
            original_format = current_scene.render.file_format
            current_scene.render.file_format = 'PNG'
            image.save_render(filename, current_scene)
            current_scene.render.file_format = original_format
            
            open_class("textureUnit 0")
            write_indented("GL_TEXTURE_2D ON")
            open_class("Texture2D")
            write_indented("name \"%s\"" % (image.name))
            write_indented("file \"%s\"" % (filename))
            if image_texture.repeat_x > 1:
                write_indented("wrap_s REPEAT")
            else:
                write_indented("wrap_s CLAMP")
            if image_texture.repeat_y > 1:
                write_indented("wrap_t REPEAT")
            else:
                write_indented("wrap_t CLAMP")

            write_indented("wrap_r REPEAT")
            write_indented("min_filter LINEAR_MIPMAP_LINEAR")
            write_indented("mag_filter LINEAR")
            write_indented("internalFormatMode USE_IMAGE_DATA_FORMAT")
            write_indented("subloadMode OFF")
            write_indented("resizeNonPowerOfTwo TRUE")


            close_class()
            close_class()


        close_class()
        # write the primitives
        vertices = []
        num_tris = 0
        num_quads = 0
        # first do triangles
        for face in modified_mesh.faces:
            if len(face.vertices) == 3 and face.material_index == material_index:
                vertices.append(modified_mesh.vertices[face.vertices[0]])
                vertices.append(modified_mesh.vertices[face.vertices[1]])
                vertices.append(modified_mesh.vertices[face.vertices[2]])
                num_tris += 1

        # then do quads
        for face in modified_mesh.faces:
            if len(face.vertices) == 4 and face.material_index == material_index:
                vertices.append(modified_mesh.vertices[face.vertices[0]])
                vertices.append(modified_mesh.vertices[face.vertices[1]])
                vertices.append(modified_mesh.vertices[face.vertices[2]])
                vertices.append(modified_mesh.vertices[face.vertices[3]])
                num_quads += 1


        num_primitives = 0

        if num_tris > 0:
            num_primitives += 1
        if num_quads > 0:
            num_primitives += 1
        open_class("PrimitiveSets %d" % num_primitives)

        # draw all the triangle faces
        uv_coords = []
        uv_idx = 0
        # write the texture coordinates
        texture_face_layer = modified_mesh.uv_textures.active
        if texture_face_layer != None:
            for texture_face in texture_face_layer.data:
                for vertex in texture_face.uv:
                    uv_coords.append((vertex[0], vertex[1]))

        vertex_index = 0
        if num_tris > 0:
            open_class("DrawElementsUShort TRIANGLES %d" % (num_tris * 3))
            for face in modified_mesh.faces:
                if len(face.vertices) == 3 and face.material_index == material_index:
                    write_indented("%d %d %d" % (vertex_index, vertex_index + 1, vertex_index + 2))
                    vertex_index += 3

            close_class()
        # draw all the quad faces
        if num_quads > 0:
            open_class("DrawElementsUShort QUADS %d" % (num_quads * 4))
            for face in modified_mesh.faces:
                if len(face.vertices) == 4 and face.material_index == material_index:
                    write_indented("%d %d %d %d" % (vertex_index, vertex_index + 1, vertex_index + 2, vertex_index + 3))
                    vertex_index += 4
            close_class()

        close_class()

        # write the vertices
        open_class("VertexArray Vec3Array %d" % len(vertices))
        for vertex in vertices:
            write_indented("%f %f %f" % (vertex.co[0], vertex.co[1], vertex.co[2]))
    
        close_class()

        # write the normals
        write_indented("NormalBinding PER_VERTEX")
        open_class("NormalArray Vec3Array %d" % len(vertices))
        for vertex in vertices:
            write_indented("%f %f %f" % (vertex.normal[0], vertex.normal[1], vertex.normal[2]));

        close_class()

        if len(uv_coords) > 0:
            open_class("TexCoordArray 0 Vec2Array %d" % len(uv_coords))
            for uv in uv_coords:
                write_indented("%f %f" % (uv[0], uv[1]));
            close_class()


        close_class()
        material_index += 1

    close_class()

def write_delta_matrix(o):
    open_class("Matrix")
    m = o.matrix_local.copy()
    write_indented("%f %f %f %f" % (m[0][0], m[0][1], m[0][2], m[0][3]))
    write_indented("%f %f %f %f" % (m[1][0], m[1][1], m[1][2], m[1][3]))
    write_indented("%f %f %f %f" % (m[2][0], m[2][1], m[2][2], m[2][3]))
    write_indented("%f %f %f %f" % (m[3][0], m[3][1], m[3][2], m[3][3]))
    
    close_class()
    write_indented("num_children 1")


def write_object(o):


    if o.type == "MESH":
        open_class("MatrixTransform")
        write_delta_matrix(o)
        write_mesh(o)
        close_class()
    elif o.type == "CURVE":
        print("Warning: Curve is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "SURFACE":
        print("Warning: Surface is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "META":
        print("Warning: Meta is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "FONT":
        print("Warning: Font is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "ARMATURE":
        print("Warning: Armature is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "LATTICE":
        print("Warning: Lattice is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "EMPTY":
        print("Warning: Empty is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "CAMERA":
        print("Warning: Camera is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "LAMP":
        open_class("MatrixTransform")
        write_delta_matrix(o)
        write_lamp(o)
        close_class()



def write_scene(s):
    global only_selected, current_scene

    current_scene = s

    open_class("Group")
    write_indented("name \"%s\"" % s.name)

    num_objects = 0
    for obj_base in s.object_bases:
        if (not only_selected or obj_base.select) and obj_base.object.type in ['MESH', 'LAMP']:
            num_objects += 1
    
    
    write_indented("num_children %d" % num_objects)
    for obj_base in s.object_bases:
        if not only_selected or obj_base.select: 
            write_object(obj_base.object)

    close_class()

def write_osg(context, option_filepath, option_export_animations, option_only_selected, option_apply_modifiers):
    global indent_level, filepath, export_file, export_animations, only_selected, apply_modifiers
    indent_level = 0
    only_selected = option_only_selected
    export_animations = option_export_animations
    apply_modifiers = option_apply_modifiers
    filepath = option_filepath

    print("export model to osg... " + filepath)
    export_file = open(filepath, 'w')

    for s in bpy.data.scenes:
        write_scene(s)

    export_file.close()

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty


class ExportOSG(bpy.types.Operator, ExportHelper):
    '''This appears in the tooltip of the operator and in the generated docs.'''
    bl_idname = "export.osg"  # this is important since its how bpy.ops.export.osg is constructed
    bl_label = "Export OSG"

    # ExportHelper mixin class uses this
    filename_ext = ".osg"

    filter_glob = StringProperty(default="*.osg", options={'HIDDEN'})

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    export_animations = BoolProperty(name="Include Animation", description="Create Armatures in the exported model", default=True)
    apply_modifiers = BoolProperty(name="Apply Modifiers", description="Apply modifiers to the mesh before exporting.", default=True)
    only_selected = BoolProperty(name="Only Selected", description="Only export selected objects", default=False)

    # type = EnumProperty(items=(('OPT_A', "First Option", "Description one"),
    #                            ('OPT_B', "Second Option", "Description two."),
    #                            ),
    #                     name="Example Enum",
    #                     description="Choose between two items",
    #                     default='OPT_A')

    @classmethod
    def poll(cls, context):
        return context.active_object != None

    def execute(self, context):
        return write_osg(context, self.filepath, self.export_animations, self.only_selected, self.apply_modifiers)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportOSG.bl_idname, text="OSG Export")


def register():
    bpy.utils.register_class(ExportOSG)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportOSG)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":

    i = sys.argv.index("--")
    filename = ''
    if i >= 0:
        filename = sys.argv[i+1]

    if filename != '':
        write_osg(None, filename, True, False, True)
    else:
        register()

        # test call
        bpy.ops.export.osg('INVOKE_DEFAULT')
