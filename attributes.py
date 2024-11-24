from pygltflib import GLTF2


def remove_normals(gltf: GLTF2):
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            if primitive.attributes.NORMAL:
                del primitive.attributes.NORMAL
            if primitive.attributes.TANGENT:
                del primitive.attributes.TANGENT
    return gltf


def test():

    path = r"D:\femcad\Venly\GLB\output\RegularDoors_10152024_01\RegularDoors_10152024_01_level1-1.glb"

    # Načtení GLB souboru
    gltf = GLTF2().load(path)

    remove_normals(gltf)

    new_path = path.replace('.glb', '_no_normals.glb')

    gltf.save(new_path)

if __name__ == "__main__":
    test()
