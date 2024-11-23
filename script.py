from pygltflib import GLTF2
import os
from scipy.spatial.transform import Rotation as R
from glb_thumbnail_generator import call_thumbnail_generator
from align import align_glb_to_center
from optimize import clean_gltf, process_images_in_gltf, optimize_buffers, remove_empty_nodes
from split import split_glb_by_root_nodes


def split(input_glb_path, output_dir, output_filename):
    split_glb_by_root_nodes(input_glb_path, output_dir, output_filename)

def optimalize(path):
    # Načtení GLB souboru
    gltf = GLTF2().load(path)

    remove_empty_nodes(gltf)

    clean_gltf(gltf)

    optimize_buffers(gltf)

    process_images_in_gltf(gltf)

    new_path = path.replace('.glb', '_optimized.glb')
    gltf.save(new_path)

    return new_path


def runName(name):

    # Příklad použití
    basePath = "..\\"

    glb_path = os.path.join(basePath, name + ".glb")

    output_folder = os.path.join(basePath, name)


    output_name_level0 = name + "_level0"

    new_files_level0 = split_glb_by_root_nodes(glb_path, output_folder, output_name_level0)

    print(new_files_level0)

    for file in new_files_level0:
        output_name_level1 = name + "_level1"
        new_files_level1 = split_glb_by_root_nodes(file, output_folder, output_name_level1)

        for file1 in new_files_level1:
            call_thumbnail_generator(file1, None, 512, 512)
            optimalized_file = optimalize(file1)
            align_glb_to_center(optimalized_file, None, [0, 1, 0])


if __name__ == "__main__":
    

    names = [
        "ExteriorAccessories_10152024_01",
        "ExteriorPlanters_10102024_01",
        "Lighting_10102024_01",
        "Materials_10152024_01",
        "Porches_10102024_01",
        "RegularDoors_10152024_01",
        "Sconces_10102024_01",
        "Windows_10152024_01",
        "FrontADD_10102024_01",
        "LargeDoors_10152024_01",
        "LargeGlass_10152024_01"
    ]

    for name in names:
        runName(name)

