from pygltflib import GLTF2
import numpy as np
import trimesh

from split import trs_to_matrix

def get_bbox(glb_path):

    # Načtení GLB modelu pomocí trimesh bez textur
    scene_or_mesh = trimesh.load(glb_path, skip_materials=True, process=False)

    # Pokud je načtený objekt scénou, extrahujeme hlavní mesh s transformacemi
    if isinstance(scene_or_mesh, trimesh.Scene):
        scene_or_mesh = scene_or_mesh.dump(concatenate=True)

    # Výpočet bounding boxu a nastavení kamery tak, aby objekt fitnul do záběru
    bounding_box = scene_or_mesh.bounding_box.bounds

    # print(np.round(bounding_box, 2))

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
        f.writelines([
            "Size:     ",
            str(size),
            "\n",
            "Align to: ",
            str(align_to)
        ])

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

    global_transformation = trs_to_matrix(translation=-center)

    # Aktualizace transformace root uzlu pro zarovnání do počátku
    for node_index in gltf.scenes[0].nodes:
        node = gltf.nodes[node_index]
        current_matrix = np.transpose(np.array(node.matrix).reshape(4, 4)) if node.matrix else trs_to_matrix(
            node.translation or [0, 0, 0],
            node.rotation or [0, 0, 0, 1],
            node.scale or [1, 1, 1],
        )
        transformed = np.dot(global_transformation, current_matrix)
        node.matrix = np.transpose(transformed).flatten().tolist()

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
