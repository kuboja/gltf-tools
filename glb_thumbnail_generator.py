import subprocess
import trimesh
import pyrender
import numpy as np
from PIL import Image
import sys
import os

def generate_thumbnail(glb_path, output_path, width=400, height=300):

    # Načtení GLB modelu pomocí trimesh bez textur
    scene_or_mesh = trimesh.load(glb_path, skip_materials=True, process=False)
    # scene_or_mesh.show()

    # return

    # Pokud je načtený objekt scénou, extrahujeme hlavní mesh s transformacemi
    if isinstance(scene_or_mesh, trimesh.Scene):
        scene_or_mesh = scene_or_mesh.dump(concatenate=False)

    # Vytvoření scény pro renderování
    scene = pyrender.Scene(bg_color=[255, 255, 255, 255])  # Bílá barva pozadí

    # Vytvoření jednoduchého materiálu
    material = pyrender.MetallicRoughnessMaterial(
        metallicFactor=0.2,
        roughnessFactor=0.8,
        baseColorFactor=[1.0, 0.5, 0.3, 1.0]
    )

    mesh = pyrender.Mesh.from_trimesh(scene_or_mesh)#, material=material)
    scene.add(mesh)

    # Výpočet bounding boxu a nastavení kamery tak, aby objekt fitnul do záběru
    bounding_box = mesh.bounds
    centroid = (bounding_box[0] + bounding_box[1]) / 2.0
    extents = bounding_box[1] - bounding_box[0]
    distance = max(extents) * 2.5
    print(f'Centroid: {centroid}, Extents: {extents}, Distance: {distance}')

    # Nastavení ortogonální kamery zepředu
    # camera = pyrender.PerspectiveCamera(xmag=extents[0] * 1.5, ymag=extents[1] * 1.5)
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0)
    # camera = pyrender.OrthographicCamera(xmag=extents[0] * 1.5, ymag=extents[2] * 1.5)
    camera_pose_top = np.array([
        [1.0, 0.0, 0.0, centroid[0]],
        [0.0, 1.0, 0.0, centroid[1]+5],
        [0.0, 0.0, 1.0, centroid[2] + distance/2.5],
        [0.0, 0.0, 0.0, 1.0],
    ])
    camera_pose_side = np.array([
        [0.0, 0.0, 1.0, centroid[0] + distance/2.5],
        [0.0, 1.0, 0.0, centroid[1]],
        [-1.0, 0.0, 0.0, centroid[2]],
        [0.0, 0.0, 0.0, 1.0],
    ])
    scene.add(camera, pose=camera_pose_side)

    # Nastavení světla
    light = pyrender.DirectionalLight(color=np.ones(3), intensity=5.0)
    light_pose = np.array([
        [1.0, 0.0, 0.0, centroid[0]],
        [0.0, 1.0, 0.0, centroid[1] + distance * 1.5],
        [0.0, 0.0, 1.0, centroid[2] + distance * 1.5],
        [0.0, 0.0, 0.0, 1.0],
    ])
    scene.add(light, pose=light_pose)


    # Renderování scény
    renderer = pyrender.OffscreenRenderer(viewport_width=width, viewport_height=height)
    color, _ = renderer.render(scene)

    # Uložení obrázku
    image = Image.fromarray(color)
    if (output_path is None):
        output_path = os.path.splitext(glb_path)[0] + '.png'
    image.save(output_path)
    print(f'Náhled byl uložen do: {output_path}')

    # Uvolnění prostředků
    renderer.delete()


def call_thumbnail_generator(glb_path, output_path, width=400, height=300):
    if (output_path is None):
        output_path = os.path.splitext(glb_path)[0] + '.png'

    result = subprocess.run([
        'gltf-viewer.exe',
        glb_path,
        "-s",
        output_path,
        "-h" + str(height),
        "-w" + str(width)
    ], capture_output=True, text=True)

    print(result.stdout)

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Použití: python glb_thumbnail_generator.py <cesta k GLB souboru>")
    else:
        glb_path = sys.argv[1]
        output_path = os.path.splitext(glb_path)[0] + '.png'
        call_thumbnail_generator(glb_path, output_path)
        #generate_thumbnail(glb_path, output_path)