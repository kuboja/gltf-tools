from pygltflib import GLTF2, Node
import copy
import os
import numpy as np
from scipy.spatial.transform import Rotation as R


def trs_to_matrix(translation, rotation = None, scale = None):
    """Převede translation, rotation, scale na transformační matici"""
    matrix = np.identity(4)
    # Přidání měřítka
    if scale is not None:
        scale_matrix = np.diag(scale + [1])
        matrix = np.dot(matrix, scale_matrix)
    # Přidání rotace (kvaternion na rotační matici)
    if rotation is not None:
        rotation_matrix = R.from_quat(rotation).as_matrix()
        matrix[:3, :3] = np.dot(matrix[:3, :3], rotation_matrix)
    # Přidání posunu
    if translation is not None:
        matrix[:3, 3] = translation
    return matrix

def combine_transforms(parent: Node, child: Node):
    """Kombinace transformací parent a child uzlu (matrix nebo TRS)"""

    parent_matrix = np.transpose(np.array(parent.matrix).reshape(4, 4)) if parent.matrix else trs_to_matrix(
        parent.translation or [0, 0, 0],
        parent.rotation or [0, 0, 0, 1],
        parent.scale or [1, 1, 1],
    )

    child_matrix = np.transpose(np.array(child.matrix).reshape(4, 4)) if child.matrix else trs_to_matrix(
        child.translation or [0, 0, 0],
        child.rotation or [0, 0, 0, 1],
        child.scale or [1, 1, 1],
    )

    combined_matrix = np.dot(parent_matrix, child_matrix)

    return np.transpose(combined_matrix).flatten().tolist()

def node_is_empty(gltf: GLTF2, node_index: int) -> bool:
    node = gltf.nodes[node_index]
    # A node is empty if it has no mesh, and no children or all children are empty
    return (
        node.mesh is None and (
            len(node.children) == 0 or
            all(node_is_empty(gltf, child) for child in node.children)
        )
    )

# Funkce na validaci indexů a přečíslování
def remap_indices(nodes, valid_indices):
    index_map = {old: new for new, old in enumerate(valid_indices)}
    for node in nodes:
        if node.children:
            # Přečíslování children
            node.children = [index_map[child] for child in node.children if child in index_map]
    return index_map

# Vyčistit původní seznam uzlů a zachovat jen hierarchii od tohoto uzlu
def filter_nodes(gltf: GLTF2, node_index, kept_nodes):
    kept_nodes.add(node_index)
    node = gltf.nodes[node_index]
    if node.children:
        for child in node.children:
            filter_nodes(gltf, child, kept_nodes)

def filter_nodes_from_root(gltf: GLTF2, node_index, output_dir, output_filename):
    new_gltf = copy.deepcopy(gltf)

    root_node = new_gltf.nodes[node_index]
    new_scene_nodes = gltf.nodes[node_index].children

    kept_nodes = set()
    for node in new_scene_nodes:
        filter_nodes(gltf, node, kept_nodes)

    # Filtrování uzlů na základě zachovaných indexů
    valid_indices = sorted(kept_nodes)
    new_gltf.nodes = [node for i, node in enumerate(new_gltf.nodes) if i in kept_nodes]

    # Přečíslování referencí
    index_map = remap_indices(new_gltf.nodes, valid_indices)

    # Aktualizace transformace child uzlu
    for index in new_scene_nodes:
        child_node = new_gltf.nodes[index_map[index]]
        transformation_matrix = combine_transforms(root_node, child_node)
        child_node.matrix = transformation_matrix
        child_node.translation, child_node.rotation, child_node.scale = None, None, None

    # Aktualizace root uzlů scény
    new_gltf.scenes[0].nodes = [index_map[node] for node in new_scene_nodes]

    # Uložit nový GLB soubor
    name = root_node.name or f"node{node_index}"
    output_path = os.path.join(output_dir, output_filename + f"-{name}.glb")
    new_gltf.save(output_path)

    print(f"Uložen nový soubor: {output_path}")

    return output_path

def split_glb_by_root_nodes(input_glb_path, output_dir, output_filename):
    # Načtení GLB souboru
    gltf = GLTF2().load(input_glb_path)

    # Zajištění výstupního adresáře
    os.makedirs(output_dir, exist_ok=True)

    print(f"Scéna v souboru '{input_glb_path}' obsahuje {len(gltf.scenes[0].nodes)} uzlů. A celkem {sum(len(gltf.nodes[node].children) for node in gltf.scenes[0].nodes)} dětských úzlů.")
    
    output_files = []

    if len(gltf.scenes[0].nodes) == 0:
        print(f"Scéna v souboru '{input_glb_path}' neobsahuje žádné uzly.")
        return output_files

    for scene_node_index in gltf.scenes[0].nodes:
        scene_node = gltf.nodes[scene_node_index]
        
        # Pokud root node nemá children, pokračujte na další root node
        if node_is_empty(gltf, scene_node_index):
            print(f"Uzel scény s indexem '{scene_node_index}' ({scene_node.name}) je prázdný, přeskočeno.")
            continue

        output_path = filter_nodes_from_root(gltf, scene_node_index, output_dir, output_filename)
        output_files.append(output_path)

    return output_files

if __name__ == "__main__":

    path = r"..\temp\RegularDoors_10152024_01\RegularDoors_10152024_01_level0-1.glb"
    path = r"..\test\test-0.glb"

    # Načtení GLB souboru
    gltf = GLTF2().load(path)

    split_glb_by_root_nodes(path, r"..\test", "test")
