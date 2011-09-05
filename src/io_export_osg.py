bl_info = {
    "name": "Open Scene Graph Model Format (.osg)",
    "author": "Damyon Wiese",
    "version": (2, 1, 2),
    "blender": (2, 5, 8),
    "api": 37702,
    "location": "File > Export > OpenSceneGraph (.osg)",
    "description": "Export OSG Model Format (.osg)",
    "warning": "Unstable!",
    "wiki_url": "http://code.google.com/p/blender-osgexport-25/wiki",
    "tracker_url": "http://code.google.com/p/blender-osgexport-25/issues/",
    "category": "Import-Export"}

import bpy
import os
import re
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

    
def write_mesh(m, recursive, animation):
    global current_scene, export_animations, orphan_meshes

    orphan_meshes.remove(m)
    open_class("Geode")
    write_indented("name \"%s\"" % m.name)
    # count the drawables
    # draw each material as a separate geometry - but they all share the same vertex and normal lists

    modified_mesh = m.to_mesh(current_scene, apply_modifiers, 'RENDER')
    material_index = 0

    # flatten the primitives
    vertices = []
    num_tris = 0
    num_quads = 0
    # first do triangles
    for face in modified_mesh.faces:
        if len(face.vertices) == 3:
            vertices.append(modified_mesh.vertices[face.vertices[0]])
            vertices.append(modified_mesh.vertices[face.vertices[1]])
            vertices.append(modified_mesh.vertices[face.vertices[2]])
            num_tris += 1

    # then do quads
    for face in modified_mesh.faces:
        if len(face.vertices) == 4:
            vertices.append(modified_mesh.vertices[face.vertices[0]])
            vertices.append(modified_mesh.vertices[face.vertices[1]])
            vertices.append(modified_mesh.vertices[face.vertices[2]])
            vertices.append(modified_mesh.vertices[face.vertices[3]])
            num_quads += 1

    if animation and export_animations:
        # TODO - wrap the geometry in a rig geometry
        write_indented("num_drawables 1")
        open_class("osgAnimation::RigGeometry")
        write_indented("name \"%s\"" % (m.name))

        # export the vertex groups
        write_indented("num_influences %d" % (len(m.vertex_groups)))
        for vertex_group in m.vertex_groups:
            weights = {}
            for index in range(0, len(vertices)):
                for vertex_vertex_group in vertices[index].groups:
                    if vertex_vertex_group.group == vertex_group.index:
                        weights[index] = vertex_vertex_group.weight

            open_class("osgAnimation::VertexInfluence \"%s\" %d" % (vertex_group.name, len(weights)))
            for index, weight in weights.items():
                write_indented("%d %f" % (index, weight))
            close_class()



    write_indented("num_drawables %d" % len(m.material_slots))

    for material_slot in m.material_slots:
        open_class("Geometry")

        # write the material
        open_class("StateSet")

        if material_slot.material.alpha < 1.0:
            write_indented("GL_BLEND ON")
            write_indented("rendering_hint TRANSPARENT_BIN")
        else:
            write_indented("rendering_hint OPAQUE_BIN")

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
                                                     material_slot.material.alpha))
        
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
            exported = True
            try:
                image.save_render(filename, current_scene)
            except:
                exported = False
            current_scene.render.file_format = original_format
            
            if exported:
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


        num_primitives = 0

        if num_tris > 0:
            num_primitives += 1
        if num_quads > 0:
            num_primitives += 1
        open_class("PrimitiveSets %d" % num_primitives)

        # draw all the triangle faces
        uv_coords = {} 
        # write the texture coordinates
        texture_face_layer = modified_mesh.uv_textures.active
        if texture_face_layer != None:
            for face_index, texture_face in enumerate(texture_face_layer.data):
                uv_coords[face_index] = []
                for vertex in texture_face.uv:
                    uv_coords[face_index].append((vertex[0], vertex[1]))

        vertex_index = 0
        uv_reordered = []
        if num_tris > 0:
            open_class("DrawElementsUShort TRIANGLES %d" % (num_tris * 3))
            for face_index, face in enumerate(modified_mesh.faces):
                if len(face.vertices) == 3:
                    if face.material_index == material_index:
                        write_indented("%d %d %d" % (vertex_index, vertex_index + 1, vertex_index + 2))
                        if len(uv_coords) > 0:
                            uv_reordered.append(uv_coords[face_index][0])
                            uv_reordered.append(uv_coords[face_index][1])
                            uv_reordered.append(uv_coords[face_index][2])
                    vertex_index += 3

            close_class()
        # draw all the quad faces
        if num_quads > 0:
            open_class("DrawElementsUShort QUADS %d" % (num_quads * 4))
            for face_index, face in enumerate(modified_mesh.faces):
                if len(face.vertices) == 4:
                    if face.material_index == material_index:
                        write_indented("%d %d %d %d" % (vertex_index, vertex_index + 1, vertex_index + 2, vertex_index + 3))
                        if len(uv_coords) > 0:
                            uv_reordered.append(uv_coords[face_index][0])
                            uv_reordered.append(uv_coords[face_index][1])
                            uv_reordered.append(uv_coords[face_index][2])
                            uv_reordered.append(uv_coords[face_index][3])
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

        if len(uv_reordered) > 0:
            open_class("TexCoordArray 0 Vec2Array %d" % len(uv_reordered))


            for uv in uv_reordered:
                write_indented("%f %f" % (uv[0], uv[1]));
            close_class()


        close_class()
        material_index += 1
    
    if animation and export_animations:
        # TODO - wrap the geometry in a rig geometry
        close_class()

    close_class()

    if recursive:
        child_meshes = find_mesh_child_meshes(m)
        for child_mesh in child_meshes:
            
            open_class("MatrixTransform")
            m = child_mesh.matrix_local.copy()

            write_matrix(m)
            write_mesh(child_mesh, True, animation)
            close_class()

def write_identity_matrix():
    open_class("Matrix")
    m = mathutils.Matrix()
    m.identity()
    write_indented("%f %f %f %f" % (m[0][0], m[0][1], m[0][2], m[0][3]))
    write_indented("%f %f %f %f" % (m[1][0], m[1][1], m[1][2], m[1][3]))
    write_indented("%f %f %f %f" % (m[2][0], m[2][1], m[2][2], m[2][3]))
    write_indented("%f %f %f %f" % (m[3][0], m[3][1], m[3][2], m[3][3]))
    
    close_class()
    write_indented("num_children 1")

def write_delta_matrix(o):
    open_class("Matrix")
    m = o.matrix_local.copy()
    write_indented("%f %f %f %f" % (m[0][0], m[0][1], m[0][2], m[0][3]))
    write_indented("%f %f %f %f" % (m[1][0], m[1][1], m[1][2], m[1][3]))
    write_indented("%f %f %f %f" % (m[2][0], m[2][1], m[2][2], m[2][3]))
    write_indented("%f %f %f %f" % (m[3][0], m[3][1], m[3][2], m[3][3]))
    
    close_class()
    write_indented("num_children 1")

def find_armature_child_meshes(armature):
    global current_scene
    child_meshes = []
    for o in current_scene.objects:
        if o.type == 'MESH':
            for m in o.modifiers:
                if m.type == "ARMATURE":
                    if m.object == armature:
                        child_meshes.append(o)

    return child_meshes

def find_mesh_child_meshes(mesh):
    global current_scene
    child_meshes = []
    for o in current_scene.objects:
        if o.type == 'MESH' and o.parent == mesh:
            child_meshes.append(o)

    return child_meshes

def find_bone_child_meshes(bone):
    global current_scene
    child_meshes = []
    for o in current_scene.objects:
        if o.type == 'MESH' and o.parent_type == 'BONE' and o.parent_bone == bone.name:
            child_meshes.append(o)

    return child_meshes


def write_bone(bone, armature_matrix):
    open_class("osgAnimation::Bone")
    write_indented("name \"%s\"" % (bone.name))

    open_class("UpdateCallbacks")

    open_class("osgAnimation::UpdateBone")
    write_indented("name \"%s\"" % (bone.name))

    open_class("osgAnimation::StackedMatrixElement")
    write_indented("name \"bindmatrix\"")

    open_class("Matrix")
    # if bone.parent:
    #     matrix_relative = bone.matrix_local * bone.parent.matrix_local.inverted()
    # else:
    #     matrix_relative = bone.matrix_local.copy()

    rotate = False
    bone_matrix = bone.matrix.copy()
    bone_rotation = bone.rotation_quaternion

    euler = bone_rotation.to_euler()
    # reorder euler
    #t = euler.x
    #euler.x = euler.y
    #euler.y = -t

    bone_rotation = euler.to_quaternion()
    # do something with bone rotation
    # create a test case
    #bone_matrix = bone_matrix * bone_rotation.to_matrix().to_4x4()
    #bone_matrix = bone_rotation.to_matrix().to_4x4() * bone_matrix
    if bone.parent:
        # candidates here are
        # parent.matrix
        # parent.matrix_basis
        # parent.matrix_channel
        # parent.bone.matrix_local - no
        # parent.bone.matrix - 3x3 ?
        # parent_matrix = bone.parent.bone.matrix_local.copy()
        # parent_matrix = bone.parent.matrix.copy() strangely close - i think the position was off
        parent_matrix = bone.parent.matrix.copy()
        if rotate:
            parent_matrix = parent_matrix * mathutils.Matrix.Rotation(math.radians(90), 4, 'Z')
        bone_matrix = parent_matrix.inverted() * bone_matrix

    if rotate:
        bone_matrix = bone_matrix * mathutils.Matrix.Rotation(math.radians(90), 4, 'Z')



    write_indented("%f %f %f %f" % (bone_matrix[0][0], bone_matrix[0][1], bone_matrix[0][2], bone_matrix[0][3]))
    write_indented("%f %f %f %f" % (bone_matrix[1][0], bone_matrix[1][1], bone_matrix[1][2], bone_matrix[1][3]))
    write_indented("%f %f %f %f" % (bone_matrix[2][0], bone_matrix[2][1], bone_matrix[2][2], bone_matrix[2][3]))
    write_indented("%f %f %f %f" % (bone_matrix[3][0], bone_matrix[3][1], bone_matrix[3][2], bone_matrix[3][3]))
    close_class()
    close_class()

    open_class("osgAnimation::StackedTranslateElement")
    write_indented("name \"translate\"")
    close_class()
    
    open_class("osgAnimation::StackedQuaternionElement")
    write_indented("name \"quaternion\"")
    close_class()

    open_class("osgAnimation::StackedScaleElement")
    write_indented("name \"scale\"")
    close_class()

    close_class()

    close_class()
    
    open_class("InvBindMatrixInSkeletonSpace")

    # inverse_bind_matrix = bone.matrix_local.inverted()
    # bind_matrix = bone.matrix.copy() * bone_rotation.to_matrix().to_4x4() 
    bind_matrix = bone.matrix.copy() 
    #bind_matrix = bind_matrix * mathutils.Matrix.Rotation(math.radians(90), 4, 'Z')
    inverse_bind_matrix = bind_matrix.inverted()
    write_indented("%f %f %f %f" % (inverse_bind_matrix[0][0], inverse_bind_matrix[0][1], inverse_bind_matrix[0][2], inverse_bind_matrix[0][3]))
    write_indented("%f %f %f %f" % (inverse_bind_matrix[1][0], inverse_bind_matrix[1][1], inverse_bind_matrix[1][2], inverse_bind_matrix[1][3]))
    write_indented("%f %f %f %f" % (inverse_bind_matrix[2][0], inverse_bind_matrix[2][1], inverse_bind_matrix[2][2], inverse_bind_matrix[2][3]))
    write_indented("%f %f %f %f" % (inverse_bind_matrix[3][0], inverse_bind_matrix[3][1], inverse_bind_matrix[3][2], inverse_bind_matrix[3][3]))
    close_class() 


    mesh_children = find_bone_child_meshes(bone)

    write_indented("num_children %d" % (len(bone.children) + len(mesh_children)))
    for child in bone.children:
        write_bone(child, armature_matrix)


    for child in mesh_children:

        open_class("MatrixTransform")
        m = inverse_bind_matrix * child.matrix_local.copy()

        write_matrix(m)
        write_mesh(child, True, False)
        close_class()


    close_class()

def write_matrix(m):
    open_class("Matrix")
    write_indented("%f %f %f %f" % (m[0][0], m[0][1], m[0][2], m[0][3]))
    write_indented("%f %f %f %f" % (m[1][0], m[1][1], m[1][2], m[1][3]))
    write_indented("%f %f %f %f" % (m[2][0], m[2][1], m[2][2], m[2][3]))
    write_indented("%f %f %f %f" % (m[3][0], m[3][1], m[3][2], m[3][3]))
    
    close_class()
    write_indented("num_children 1")



def write_armature(obj):
    original_pose_position = obj.data.pose_position
    obj.data.pose_position = 'REST'
    armature = obj.data
    open_class("osgAnimation::Skeleton")
    write_indented("name \"%s\"" % (armature.name))
    open_class("UpdateCallbacks")
    open_class("osgAnimation::UpdateSkeleton")
    close_class()
    close_class()

    open_class("Matrix")
    skeleton_matrix = obj.matrix_world.copy()
    write_indented("%f %f %f %f" % (skeleton_matrix[0][0], skeleton_matrix[0][1], skeleton_matrix[0][2], skeleton_matrix[0][3]))
    write_indented("%f %f %f %f" % (skeleton_matrix[1][0], skeleton_matrix[1][1], skeleton_matrix[1][2], skeleton_matrix[1][3]))
    write_indented("%f %f %f %f" % (skeleton_matrix[2][0], skeleton_matrix[2][1], skeleton_matrix[2][2], skeleton_matrix[2][3]))
    write_indented("%f %f %f %f" % (skeleton_matrix[3][0], skeleton_matrix[3][1], skeleton_matrix[3][2], skeleton_matrix[3][3]))
    
    close_class()

    root_bones = []
    # bones
    for bone in obj.pose.bones:
        m = mathutils.Matrix()
        m.identity()
        bone.matrix = m
        # only add the root bones
        if bone.parent == None:
            root_bones.append(bone)

    # meshes
    mesh_children = find_armature_child_meshes(obj)

    write_indented("num_children %d" % (len(root_bones) + len(mesh_children)))
    for bone in root_bones:
        write_bone(bone, skeleton_matrix)

    for mesh in mesh_children:
        open_class("MatrixTransform")
        #if export_animations:
        #    write_identity_matrix()
        #else:
        m = mesh.matrix_local.copy()

        write_matrix(m)

        write_mesh(mesh, False, export_animations)
        close_class()

    close_class()
    obj.data.pose_position = original_pose_position

def write_object(o):
    global export_animations

    armature = None

    if o.type == "MESH":
        pass
        #if export_animations:
        #    # hunt for an armature modifier
        #    for modifier in o.modifiers:
        #        if modifier.type == "ARMATURE":
        #            armature = modifier.object
#
#
#        if armature != None:
#            write_armature(armature)
#
#        open_class("MatrixTransform")
#        if export_animations:
#            write_identity_matrix()
#        else:
#            write_delta_matrix(o)
#        write_mesh(o, False, export_animations)
#        close_class()
#        if armature != None:
#            close_class()
    elif o.type == "CURVE":
        print("Warning: Curve is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "SURFACE":
        print("Warning: Surface is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "META":
        print("Warning: Meta is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "FONT":
        print("Warning: Font is not supported by openscenegraph exporter. Skipping.\n")
    elif o.type == "ARMATURE":
        write_armature(o)
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

def get_pose_bone_by_name(name):
    for o in bpy.data.objects:
        if o.pose:
            for pose_bone in o.pose.bones:
                if pose_bone.bone.name == name:
                    return pose_bone
                for child in pose_bone.children_recursive:
                    if child.bone.name == name:
                        return child
    return None

def get_bone_from_path(path):
    result = re.search("bones\[\"([^\"]*)\"\]", path)
    if result != None:
        return result.group(1)
    print("Could not get bone from path: %s" % path);
    return None

def get_property_from_path(path):
    result = re.search("\.([^.]*)$", path)
    if result != None:
        return result.group(1)
    print("Could not get property from path: %s" % path);
    return None

def get_action_fcurve(action, path, array_index):
    for fcurve in action.fcurves:
        if fcurve.data_path == path and fcurve.array_index == array_index:
            return fcurve
    return None

def write_actions(actions):
    global current_scene
    open_class("UpdateCallbacks")
    open_class("osgAnimation::BasicAnimationManager")
    write_indented("num_animations %d" % (len(actions)))
    for action in actions:
        open_class("osgAnimation::Animation")
        write_indented("name \"%s\"" % (action.name))

        # restructure fcurves into channels (a channel combines x, y, and z for translation for example)
        channels = {}
        for fcurve in action.fcurves:
            if fcurve.data_path not in channels:
                channels[fcurve.data_path] = {}

            for keyframe in fcurve.keyframe_points:
                if keyframe.co[0] not in channels[fcurve.data_path]:
                    channels[fcurve.data_path][keyframe.co[0]] = {}
                channels[fcurve.data_path][keyframe.co[0]][fcurve.array_index] = keyframe.co[1]

        # fix any "holes" ie in blender we can animate on the x channel only - in this case we should either drop the animation or evaluate the curve at the hole
        for path in iter(channels):
            channel = channels[path]
            bone_name = get_bone_from_path(path)
            bone_property = get_property_from_path(path)
            channel_skipped = False

            if bone_name != None and bone_property != None:
                num_properties = 0
                if bone_property.lower() == 'scale':
                    num_properties = 3
                elif bone_property.lower() == 'location':
                    num_properties = 3
                elif bone_property.lower() == 'rotation_euler':
                    pose_bone = get_pose_bone_by_name(bone_name)
                    if pose_bone != None and 'Z' in pose_bone.rotation_mode:
                        num_properties = 3
                elif bone_property.lower() == 'rotation_quaternion':
                    pose_bone = get_pose_bone_by_name(bone_name)
                    if pose_bone != None and pose_bone.rotation_mode == 'QUATERNION':
                        num_properties = 4
                if num_properties > 0:
                    for keyframe in channels[path].keys():
                        for i in range(0, num_properties):
                            if not i in channels[path][keyframe]:
                                fcurve = get_action_fcurve(action, path, i)
                                if fcurve != None:
                                    channels[path][keyframe][i] = fcurve.evaluate(keyframe)
                                else:
                                    # no fcurve exists for this property
                                    # we will have to skip the entire action
                                    channels.remove(path)
                                    channel_skipped = True
                        if channel_skipped:
                            break
                    if channel_skipped:
                        break


        write_indented("num_channels %d" % (len(channels)))
        
        for path in iter(channels):
            channel = channels[path]
            bone_name = get_bone_from_path(path)
            bone_property = get_property_from_path(path)

            if bone_name != None and bone_property != None:
                if bone_property.lower() == 'scale':
                    open_class("Vec3LinearChannel")
                    write_indented("name \"scale\"")
                    write_indented("target \"%s\"" % (bone_name))
                    open_class("Keyframes %d" % (len(channel)))

                    for timestamp in sorted(channel.keys()):
                        #write_indented("key %f %f %f %f" % (timestamp/current_scene.render.fps, channel[timestamp][1], channel[timestamp][0], channel[timestamp][2]))
                        write_indented("key %f %f %f %f" % (timestamp/current_scene.render.fps, channel[timestamp][0], channel[timestamp][1], channel[timestamp][2]))

                    close_class()
                    close_class()
                elif bone_property.lower() == 'location':
                    open_class("Vec3LinearChannel")
                    write_indented("name \"translate\"")
                    write_indented("target \"%s\"" % (bone_name))
                    open_class("Keyframes %d" % (len(channel)))
                    for timestamp in sorted(channel.keys()):
                        # note the axis translation
                        #write_indented("key %f %f %f %f" % (timestamp/current_scene.render.fps, channel[timestamp][1], -channel[timestamp][0], channel[timestamp][2]))
                        #write_indented("key %f %f %f %f" % (timestamp/current_scene.render.fps, channel[timestamp][1], channel[timestamp][0], channel[timestamp][2]))
                        write_indented("key %f %f %f %f" % (timestamp/current_scene.render.fps, channel[timestamp][0], channel[timestamp][1], channel[timestamp][2]))

                    close_class()
                    close_class()
                elif bone_property.lower() == 'rotation_euler':
                    # first - tweak the axis
                    # then convert to quaternion
                    pose_bone = get_pose_bone_by_name(bone_name)
                    if pose_bone != None and 'Z' in pose_bone.rotation_mode:
                        open_class("QuatSphericalLinearChannel")
                        write_indented("name \"quaternion\"")
                        write_indented("target \"%s\"" % (bone_name))
                        open_class("Keyframes %d" % (len(channel)))
                        for timestamp in sorted(channel.keys()):
                            euler = mathutils.Euler()
                            euler.order = pose_bone.rotation_mode
                            euler.x = channel[timestamp][0]
                            euler.y = channel[timestamp][1]
                            euler.z = channel[timestamp][2]

                            # reorder euler
                         #   t = euler.x
                          #  euler.x = euler.y
                           # euler.y = -t

                            quat = euler.to_quaternion()

                            # quat.rotate(mathutils.Matrix.Rotation(math.radians(180), 4, 'Z'))
                            # quat.
                            write_indented("key %f %f %f %f %f" % (timestamp/current_scene.render.fps, quat.x, quat.y, quat.z, quat.w))

                        close_class()
                        close_class()
                elif bone_property.lower() == 'rotation_quaternion':
                    pose_bone = get_pose_bone_by_name(bone_name)
                    if pose_bone != None and pose_bone.rotation_mode == 'QUATERNION':
                        open_class("QuatSphericalLinearChannel")
                        write_indented("name \"quaternion\"")
                        write_indented("target \"%s\"" % (bone_name))
                        open_class("Keyframes %d" % (len(channel)))
                        for timestamp in sorted(channel.keys()):
                            quat = mathutils.Quaternion()
                            quat.w = channel[timestamp][0]
                            quat.x = channel[timestamp][1]
                            quat.y = channel[timestamp][2]
                            quat.z = channel[timestamp][3]

                            # convert to euler fix the axis and then back to quat
                            #euler = quat.to_euler('XYZ')
                            #t = euler.x
                            #euler.x = euler.y
                            #euler.y = -t
                            #quat = euler.to_quaternion()

                            # quat.rotate(mathutils.Matrix.Rotation(math.radians(-90), 4, 'Y'))

                            write_indented("key %f %f %f %f %f" % (timestamp/current_scene.render.fps, quat.x, quat.y, quat.z, quat.w))

                        close_class()
                        close_class()
                # end if bone_name and bone_property
            # end for path in channels
        close_class()

    close_class()
    close_class()

def write_scene(s):
    global only_selected, current_scene, export_animations, orphan_meshes

    orphan_meshes = []
    current_scene = s

    open_class("Group")
    write_indented("name \"%s\"" % s.name)

    num_objects = 0
    if export_animations:
        num_objects += 1

    for obj_base in s.object_bases:
        if (not only_selected or obj_base.select) and obj_base.object.type in ['MESH', 'LAMP']:
            num_objects += 1

    for m in s.objects:
        if m.type == 'MESH':
            orphan_meshes.append(m)

    
    write_indented("num_children %d" % num_objects)
    if export_animations:
        write_actions(bpy.data.actions)

    for obj_base in s.object_bases:
        if not only_selected or obj_base.select: 
            write_object(obj_base.object)

    for orphan_mesh in orphan_meshes:
        open_class("MatrixTransform")
        write_delta_matrix(orphan_mesh)
        write_mesh(orphan_mesh, False, False)
        close_class()


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
    '''Export meshes, lights and animation to OpenSceneGraph text format (.osg)'''
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
