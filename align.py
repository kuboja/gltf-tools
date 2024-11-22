from pygltflib import GLTF2
import numpy as np
import trimesh

def get_bbox(glb_path):

    # Načtení GLB modelu pomocí trimesh bez textur
    scene_or_mesh = trimesh.load(glb_path, skip_materials=True, process=False)

    # Pokud je načtený objekt scénou, extrahujeme hlavní mesh s transformacemi
    if isinstance(scene_or_mesh, trimesh.Scene):
        scene_or_mesh = scene_or_mesh.dump(concatenate=True)

    # Výpočet bounding boxu a nastavení kamery tak, aby objekt fitnul do záběru
    bounding_box = scene_or_mesh.bounding_box.bounds

    print(np.round(bounding_box, 2))

    return bounding_box

def align_glb_to_center(input_path, output_path = None, align_to = [0, 0, 0]):

    # Načtení GLB souboru
    gltf = GLTF2().load(input_path)

    # check is geometry is present
    if len(gltf.scenes[0].nodes) == 0 or gltf.scenes[0].nodes[0] is None or not any([node.mesh is not None for node in gltf.nodes]):
        print(f"No geometry found in the GLB file '{input_path}'.")
        return

    bbox = get_bbox(input_path)

    # Výpočet středu ve všech osách (průměr souřadnic)
    center = (bbox[0] + bbox[1]) / 2

    size = bbox[1] - bbox[0]
    print("Size: " + str(np.round(size,4)))

    # Uložit size do souboru
    with open(input_path.replace(".glb", "_size.txt"), "w") as f:
        f.writelines("Size: ")
        f.writelines(str(size))
        f.writelines("Align to: ")
        f.writelines(str(align_to))

    if align_to[0] == 1:
        center[0] = bbox[0][0]
    elif align_to[0] == -1:
        center[0] = bbox[1][0]

    if align_to[1] == 1:
        center[1] = bbox[0][1]
    elif align_to[1] == -1:
        center[1] = bbox[1][1]

    if align_to[2] == 1:
        center[2] = bbox[0][2]
    elif align_to[2] == -1:
        center[2] = bbox[1][2]

    # Aktualizace transformace root uzlu pro zarovnání do počátku
    root_node = gltf.nodes[gltf.scenes[0].nodes[0]]
    if root_node.matrix is not None:
        # Pokud existuje aktuální transformační matice, sloučíme ji s novou translací
        current_transform = np.transpose(np.array(root_node.matrix).reshape(4, 4))
        current_transform[:3, 3] = current_transform[:3, 3] - center
        root_node.matrix = np.transpose(current_transform).flatten().tolist()
    else:
        if root_node.translation is None:
            root_node.translation = [-center[0], -center[1], -center[2]]
        else:
            root_node.translation[0] -= center[0]
            root_node.translation[1] -= center[1]
            root_node.translation[2] -= center[2]

    # Uložení zarovnaného GLB souboru
    if output_path is None:
        output_path = input_path.replace(".glb", "_aligned.glb")

    gltf.save(output_path)

    return output_path


if __name__ == "__main__":
    align_glb_to_center(
        "..\\ExteriorPlanters_10102024_01\\ExteriorPlanters_10102024_01_level1-3180_optimized.glb",
        None,
        [0, -1, 0]
    )