import bpy
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
        write_indented("linear_attenuation %f" % lamp.linear_attenuation)
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

        open_class("Material")
        write_indented("name \"%s\"" % material_slot.name)
        
        write_indented("ColorMode OFF")
        write_indented("ambientColor %f %f %f %f" % (current_scene.world.ambient_color[0], 
                                                     current_scene.world.ambient_color[1], 
                                                     current_scene.world.ambient_color[2], 
                                                     material_slot.material.ambient))

        d = material_slot.material.diffuse_color
        if material_slot.material.use_object_color:
            d[0] *= m.color[0]
            d[1] *= m.color[1]
            d[2] *= m.color[2]

        write_indented("diffuseColor %f %f %f %f" % (d[0],
                                                     d[1],
                                                     d[2],
                                                     material_slot.material.diffuse_intensity))
        
        write_indented("specularColor %f %f %f %f" % (material_slot.material.specular_color[0] * material_slot.material.specular_intensity,
                                                     material_slot.material.specular_color[1] * material_slot.material.specular_intensity,
                                                     material_slot.material.specular_color[2] * material_slot.material.specular_intensity,
                                                     material_slot.material.specular_intensity))
    
        write_indented("emissionColor %f %f %f %f" % (material_slot.material.emit, material_slot.material.emit, material_slot.material.emit, material_slot.material.emit))
        # Hardness is a value from 1 - 511
        # The equation below brings it back to the range 0.0 to 10.0
        write_indented("shininess %f" % ((material_slot.material.specular_hardness - 1.0) / 51.0))
    
        close_class()

        close_class()
        # write the primitives
        num_tris = 0
        num_quads = 0
        num_primitives = 0
        for face in modified_mesh.faces:
            if len(face.vertices) == 3 and face.material_index == material_index:
                num_tris += 1
            elif len(face.vertices) == 4 and face.material_index == material_index:
                num_quads += 1
        if num_tris > 0:
            num_primitives += 1
        if num_quads > 0:
            num_primitives += 1
        open_class("PrimitiveSets %d" % num_primitives)

        # draw all the triangle faces
        if num_tris > 0:
            open_class("DrawElementsUShort TRIANGLES %d" % num_tris)
            for face in modified_mesh.faces:
                if len(face.vertices) == 3 and face.material_index == material_index:
                    write_indented("%d %d %d" % (face.vertices[0], face.vertices[1], face.vertices[2]))
            close_class()
        # draw all the quad faces
        if num_quads > 0:
            open_class("DrawElementsUShort QUADS %d" % num_quads)
            for face in modified_mesh.faces:
                if len(face.vertices) == 4 and face.material_index == material_index:
                    write_indented("%d %d %d %d" % (face.vertices[0], face.vertices[1], face.vertices[2], face.vertices[3]))
            close_class()

        close_class()

        # write the vertices
        open_class("VertexArray Vec3Array %d" % len(modified_mesh.vertices))
        for vertex in modified_mesh.vertices:
            write_indented("%f %f %f" % (vertex.co[0], vertex.co[1], vertex.co[2]))
    
        close_class()

        # write the normals
        write_indented("NormalBinding PER_VERTEX")
        open_class("NormalArray Vec3Array %d" % len(modified_mesh.vertices))
        for vertex in modified_mesh.vertices:
            write_indented("%f %f %f" % (vertex.normal[0], vertex.normal[1], vertex.normal[2]));

        close_class()
        close_class()
        material_index += 1

    close_class()


def write_object(o):

    if o.type == "MESH":
        write_mesh(o)
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
        write_lamp(o)



def write_scene(s):
    global only_selected, current_scene

    current_scene = s

    open_class("Group")
    write_indented("name \"%s\"" % s.name)

    num_objects = 0
    if only_selected:
        for obj_base in s.object_bases:
            if obj_base.select:
                num_objects += 1
    else:
        num_objects = len(s.object_bases)
    
    
    write_indented("num_children %d" % num_objects)
    for obj_base in s.object_bases:
        if not only_selected or obj_base.select: 
            write_object(obj_base.object)

    close_class()

def write_osg(context, filepath, option_export_animations, option_only_selected, option_apply_modifiers):
    global indent_level, export_file, export_animations, only_selected, apply_modifiers
    indent_level = 0
    only_selected = option_only_selected
    export_animations = option_export_animations
    apply_modifiers = option_apply_modifiers

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
