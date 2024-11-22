from pygltflib import GLTF2, Buffer
from scipy.spatial.transform import Rotation as R
from PIL import Image
import io

def remove_empty_nodes(gltf: GLTF2):
    def is_empty(node_index: int) -> bool:
        node = gltf.nodes[node_index]
        # A node is empty if it has no mesh, no camera, and no children
        return node.mesh is None and node.camera is None and len(node.children) == 0

    # initial_node_count = len(gltf.nodes)

    # Iterate until no changes are needed
    while True:
        nodes_to_remove = set()
        # Identify empty nodes
        for i, node in enumerate(gltf.nodes):
            if is_empty(i):
                nodes_to_remove.add(i)

        # If no nodes to remove, break the loop
        if not nodes_to_remove:
            break

        # Remove references to empty nodes from parents
        for node in gltf.nodes:
            node.children = [child for child in node.children if child not in nodes_to_remove]

        # Remove empty nodes and update index mapping
        new_nodes = []
        index_mapping = {}
        new_index = 0
        for i, node in enumerate(gltf.nodes):
            if i not in nodes_to_remove:
                index_mapping[i] = new_index
                new_nodes.append(node)
                new_index += 1

        # Update children references to new indices
        for node in new_nodes:
            node.children = [index_mapping[child] for child in node.children]

        # Update scene root nodes references to new indices
        for scene in gltf.scenes:
            scene.nodes = [index_mapping[node] for node in scene.nodes if node in index_mapping]

        gltf.nodes = new_nodes

    # final_node_count = len(gltf.nodes)
    # removed_node_count = initial_node_count - final_node_count

    # print(f"Initial node count: {initial_node_count}")
    # print(f"Removed node count: {removed_node_count}")
    # print(f"Final node count: {final_node_count}")

    # count_empty = sum(1 for i in range(len(gltf.nodes)) if is_empty(i))
    # print(f"Any empty nodes left: {count_empty}")

def optimize_buffers(gltf):
    """
    Optimalizuje buffery a odstraní nevyužitá data v GLTF souboru.
    """

    # Sbíráme využité accessors
    used_accessors = set()
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            if primitive.attributes:
                for attr in primitive.attributes.__dict__.values():  # Iterujeme přes atributy
                    if attr is not None:
                        used_accessors.add(attr)
            if primitive.indices is not None:
                used_accessors.add(primitive.indices)

    # Sbíráme využité bufferViews z accessors
    used_buffer_views = {gltf.accessors[acc].bufferView for acc in used_accessors if gltf.accessors[acc].bufferView is not None}

    for image in gltf.images:
        if image.bufferView is not None:
            used_buffer_views.add(image.bufferView)

    # Vytváříme nový seznam bufferViews a mapujeme staré na nové
    new_buffer_views = []
    buffer_view_map = {}
    for old_index in sorted(used_buffer_views):
        buffer_view_map[old_index] = len(new_buffer_views)
        new_buffer_views.append(gltf.bufferViews[old_index])

    gltf.bufferViews = new_buffer_views

    # Optimalizujeme buffer data
    new_buffer_data = bytearray()
    for buffer_view in gltf.bufferViews:
        start = buffer_view.byteOffset or 0
        end = start + buffer_view.byteLength
        new_offset = len(new_buffer_data)
        new_buffer_data.extend(gltf._glb_data[start:end])
        buffer_view.byteOffset = new_offset  # Aktualizujeme offset v novém bufferu

    for accessor in gltf.accessors:
        if accessor.bufferView in buffer_view_map:
            accessor.bufferView = buffer_view_map[accessor.bufferView]

    for image in gltf.images:
        if image.bufferView in buffer_view_map:
            image.bufferView = buffer_view_map[image.bufferView]

    # Filtrování využitých accessors
    gltf.accessors = [gltf.accessors[acc] for acc in sorted(used_accessors) if acc < len(gltf.accessors)]

    # Aktualizace referencí mesh primitives
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            if primitive.attributes:
                for attr_key in dir(primitive.attributes):
                    if not attr_key.startswith('_'):
                        attr_value = getattr(primitive.attributes, attr_key, None)
                        if attr_value in used_accessors:
                            setattr(primitive.attributes, attr_key, sorted(used_accessors).index(attr_value))
            if primitive.indices is not None and primitive.indices in used_accessors:
                primitive.indices = sorted(used_accessors).index(primitive.indices)

    # Uložíme nové buffer data jako inline base64
    gltf.buffers = [Buffer(byteLength=len(new_buffer_data))]

    # Zapisujeme optimalizovaná data zpět do _glb_data
    gltf._glb_data = new_buffer_data

    return gltf

def clean_gltf(gltf):
    """
    Odstraní nepoužívané geometrie, materiály, textury a buffery z GLTF souboru.
    """

    remove_empty_nodes(gltf)

    # Shromáždění použitých meshes z uzlů
    used_meshes = {node.mesh for node in gltf.nodes if node.mesh is not None}

    # Shromáždění použitých materiálů z použitých meshes
    used_materials = set()
    for mesh_index in used_meshes:
        mesh = gltf.meshes[mesh_index]
        for primitive in mesh.primitives:
            if primitive.material is not None:
                used_materials.add(primitive.material)

    # Shromáždění použitých textur z použitých materiálů
    used_textures = set()
    for material_index in used_materials:
        material = gltf.materials[material_index]
        if material.pbrMetallicRoughness:
            pbr = material.pbrMetallicRoughness
            if pbr.baseColorTexture:
                used_textures.add(pbr.baseColorTexture.index)
            if pbr.metallicRoughnessTexture:
                used_textures.add(pbr.metallicRoughnessTexture.index)

    # Shromáždění použitých images z použitých textur
    used_images = set()
    for texture_index in used_textures:
        texture = gltf.textures[texture_index]
        if texture.source is not None:
            used_images.add(texture.source)

    used_buffers = set(range(len(gltf.buffers)))  # Buffery budeme optimalizovat později

    # Filtruj položky na základě použitých referencí
    gltf.meshes = [mesh for i, mesh in enumerate(gltf.meshes) if i in used_meshes]
    gltf.materials = [material for i, material in enumerate(gltf.materials) if i in used_materials]
    gltf.textures = [texture for i, texture in enumerate(gltf.textures) if i in used_textures]
    gltf.images = [image for i, image in enumerate(gltf.images) if i in used_images]
    gltf.buffers = [buffer for i, buffer in enumerate(gltf.buffers) if i in used_buffers]

    # Aktualizace referencí v uzlech a ostatních objektech
    def remap_indices(items, used_indices):
        """
        Přečísluje indexy položek na základě použitých referencí.
        """
        index_map = {old: new for new, old in enumerate(sorted(used_indices))}
        return [index_map[i] for i in used_indices], index_map

    _, mesh_map = remap_indices(gltf.meshes, used_meshes)
    _, material_map = remap_indices(gltf.materials, used_materials)
    _, texture_map = remap_indices(gltf.textures, used_textures)
    _, image_map = remap_indices(gltf.images, used_images)

    # Aktualizace referencí v uzlech
    for node in gltf.nodes:
        if node.mesh is not None:
            node.mesh = mesh_map[node.mesh]

    # Aktualizace referencí v primitivách
    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            if primitive.material is not None:
                primitive.material = material_map[primitive.material]
            # if primitive.indices is not None:
            #     primitive.indices = mesh_map[primitive.indices]

    # Aktualizace referencí v materiálech
    for material in gltf.materials:
        if material.pbrMetallicRoughness:
            pbr = material.pbrMetallicRoughness
            if pbr.baseColorTexture:
                pbr.baseColorTexture.index = texture_map[pbr.baseColorTexture.index]
            if pbr.metallicRoughnessTexture:
                pbr.metallicRoughnessTexture.index = texture_map[pbr.metallicRoughnessTexture.index]

    # Aktualizace referencí v texturách
    for texture in gltf.textures:
        if texture.source is not None:
            texture.source = image_map[texture.source]


def convert_images_to_webp(gltf):
    """
    Konvertuje obrázky v GLTF souboru do formátu WebP a uloží je jako binární data v _glb_data.
    """
    new_buffer_data = bytearray(gltf._glb_data)  # Vytvoření kopie původních binárních dat

    for image in gltf.images:
        if image.mimeType == "image/webp":
            # Pokud je obrázek již ve formátu WebP, přeskočíme ho
            continue

        if image.bufferView is not None:
            buffer_view = gltf.bufferViews[image.bufferView]
            start = buffer_view.byteOffset or 0
            end = start + buffer_view.byteLength
            image_data = io.BytesIO(new_buffer_data[start:end])

            # Načtení obrázku pomocí PIL
            img = Image.open(image_data)

            # Konverze obrázku do WebP
            output = io.BytesIO()
            img.save(output, format="WEBP", quality=85)
            output.seek(0)

            # Aktualizace buffer view s novými daty
            new_image_data = output.read()
            new_offset = len(new_buffer_data)
            new_buffer_data.extend(new_image_data)

            buffer_view.byteOffset = new_offset
            buffer_view.byteLength = len(new_image_data)
            buffer_view.buffer = 0  # Předpokládáme použití prvního bufferu

             # Aktualizace MIME typu na image/webp
            image.mimeType = "image/webp"

    # Aktualizace GLB dat s novými obrázky
    gltf._glb_data = new_buffer_data

if __name__ == "__main__":

    # Načtení GLB souboru
    gltf = GLTF2().load('..\\ExteriorPlanters_10102024_01\\ExteriorPlanters_10102024_01_level1-2141.glb')

    # Optimalizace GLTF souboru
    remove_empty_nodes(gltf)

    clean_gltf(gltf)

    optimize_buffers(gltf)

    # Uložení GLB souboru
    gltf.save(r"..\ExteriorPlanters_10102024_01\ExteriorPlanters_10102024_01_level1-2141_test.glb")
