from pygltflib import GLTF2
import copy
import os
import numpy as np
from scipy.spatial.transform import Rotation as R


def transform_to_matrix(translation, rotation, scale):
    """Převede translation, rotation, scale na transformační matici"""
    matrix = np.identity(4)
    # Přidání měřítka
    scale_matrix = np.diag(scale + [1])
    matrix = np.dot(matrix, scale_matrix)
    # Přidání rotace (kvaternion na rotační matici)
    rotation_matrix = R.from_quat(rotation).as_matrix()
    matrix[:3, :3] = np.dot(matrix[:3, :3], rotation_matrix)
    # Přidání posunu
    matrix[:3, 3] = translation
    return matrix

def combine_transforms(parent, child):
    """Kombinace transformací parent a child uzlu (matrix nebo TRS)"""
    # Pokud parent nebo child mají matici, použijeme ji
    parent_matrix = np.array(parent.matrix).reshape(4, 4) if parent.matrix else transform_to_matrix(
        parent.translation or [0, 0, 0],
        parent.rotation or [0, 0, 0, 1],
        parent.scale or [1, 1, 1],
    )
    child_matrix = np.array(child.matrix).reshape(4, 4) if child.matrix else transform_to_matrix(
        child.translation or [0, 0, 0],
        child.rotation or [0, 0, 0, 1],
        child.scale or [1, 1, 1],
    )
    # Kombinace matic
    combined_matrix = np.dot(parent_matrix, child_matrix)
    # Rozložení kombinované matice na TRS
    return combined_matrix.flatten().tolist()


def split_glb_by_root_nodes(input_glb_path, output_dir, output_filename):
 # Načtení GLB souboru
    gltf = GLTF2().load(input_glb_path)

    # Zajištění výstupního adresáře
    os.makedirs(output_dir, exist_ok=True)

    # Funkce na validaci indexů a přečíslování
    def remap_indices(nodes, valid_indices):
        index_map = {old: new for new, old in enumerate(valid_indices)}
        for node in nodes:
            if node.children:
                # Přečíslování children
                node.children = [index_map[child] for child in node.children if child in index_map]
        return index_map

    # Získání root uzlů (1. úroveň)
    all_children = {child for node in gltf.nodes for child in (node.children or [])}
    root_nodes = [i for i, node in enumerate(gltf.nodes) if i not in all_children]

    print(f"Nalezeno {len(root_nodes)} root uzlů.")
    output_files = []

    for root_index in root_nodes:
        root_node = gltf.nodes[root_index]
        # Pokud root node nemá children, pokračujte na další root node
        if not root_node.children:
            print(f"Root uzel {root_index} nemá žádné děti, přeskočeno.")
            continue

        # Zpracování každého dítěte (2. úroveň)
        for child_index in root_node.children:
            new_gltf = copy.deepcopy(gltf)

            # Vytvoření nové scény s aktuálním child uzlem jako root
            new_root_node = copy.deepcopy(new_gltf.nodes[child_index])

            # Vyčistit původní seznam uzlů a zachovat jen hierarchii od tohoto uzlu
            def filter_nodes(node_index, kept_nodes):
                kept_nodes.add(node_index)
                node = new_gltf.nodes[node_index]
                if node.children:
                    for child in node.children:
                        filter_nodes(child, kept_nodes)

            kept_nodes = set()
            filter_nodes(child_index, kept_nodes)

            # Filtrování uzlů na základě zachovaných indexů
            valid_indices = sorted(kept_nodes)
            new_gltf.nodes = [node for i, node in enumerate(new_gltf.nodes) if i in kept_nodes]

            # Přečíslování referencí
            index_map = remap_indices(new_gltf.nodes, valid_indices)

            # Aktualizace transformace child uzlu
            child_node = new_gltf.nodes[index_map[child_index]]
            child_node.translation, child_node.rotation, child_node.scale = None, None, None
            child_node.matrix = combine_transforms(root_node, child_node)

            # Aktualizace root uzlů scény
            new_gltf.scenes[0].nodes = [index_map[child_index]]

            # Uložit nový GLB soubor
            output_path = os.path.join(output_dir, output_filename + f"-{child_index}.glb")
            output_files.append(output_path)

            new_gltf.save(output_path)

            # optimalize(output_path)

            print(f"Uložen nový soubor: {output_path}")

        return output_files