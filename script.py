from pygltflib import GLTF2
import os
from attributes import remove_normals
from glb_thumbnail_generator import call_histruct_renderer, call_thumbnail_generator
from align import align_glb_to_center
from optimize import clean_gltf, optimize_buffers, remove_empty_nodes
from split import split_glb_by_root_nodes
from texture import process_images_in_gltf
import shutil


def split(input_glb_path, output_dir, output_filename):
    split_glb_by_root_nodes(input_glb_path, output_dir, output_filename)

def clean(path):
    # Načtení GLB souboru
    gltf = GLTF2().load(path)

    remove_empty_nodes(gltf)

    clean_gltf(gltf)

    optimize_buffers(gltf)

    # process_images_in_gltf(gltf)

    remove_normals(gltf)

    new_path = path.replace('.glb', '_clean.glb')
    gltf.save(new_path)

    return new_path

def image_optimize(path):
    # Načtení GLB souboru
    gltf = GLTF2().load(path)

    process_images_in_gltf(gltf)

    new_path = path.replace('.glb', '_optimized.glb')
    gltf.save(new_path)

    return new_path

def split_to_level(base_glb_path, name, temp_folder, level, stop_level):

    output_name_level = name + "_level" + str(level)
    new_files_level = split_glb_by_root_nodes(base_glb_path, temp_folder, output_name_level)

    if level == stop_level:
        return new_files_level
    
    for file in new_files_level:
        return split_to_level(file, name, temp_folder, level + 1, stop_level)
    

def runName(basePath, output_folder, name):

    output_folder = os.path.join(output_folder, name)
    os.makedirs(output_folder, exist_ok=True)

    glb_path = os.path.join(basePath, name + ".glb")

    temp_folder = os.path.join(basePath, "temp\\", name)

    splited_files = split_to_level(glb_path, name, temp_folder, 0, 2)

    print("Splited files:")
    print(splited_files)

    files = []

    i = 1
    for file in splited_files:

        align_file = align_glb_to_center(file, None, [0, 1, 0])
        clean_file = clean(align_file)
        optimalized_file = image_optimize(clean_file)

        thumbnail_file = optimalized_file
        final_file = optimalized_file

        if final_file is None:
            continue
        
        thumnail_path = call_histruct_renderer(thumbnail_file, None, 512, 512)

        # mode final file to output folder, replace all after "-" with index
        final_name = os.path.join( output_folder, os.path.basename(final_file).split("-")[0] + "-" + str(i))
        final_glb = final_name + ".glb"
        final_txt = final_name + "_size.txt"
        final_png = final_name + ".png"

        files.append(final_glb)

        # copy final file
        shutil.copy(final_file, final_glb)
        shutil.copy(file.replace(".glb", "_size.txt"), final_txt)
        if os.path.exists(thumnail_path):
            shutil.copy(thumnail_path, final_png)

        i += 1

    return files



if __name__ == "__main__":
    
    basePath = "..\\"
    output_folder = os.path.join(basePath, "output")
    
    # Zajištění výstupního adresáře
    os.makedirs(output_folder, exist_ok=True)

    output_files_file_path = os.path.join(output_folder, "all_models.txt")

    # save generated file paths to txt file
    with open(output_files_file_path, "w") as file:
        file.write("")

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
        files = runName(basePath, output_folder, name)

        with open(output_files_file_path, "a") as file:
            for f in files:
                file.write(f + "\n")
            file.write("\n")


