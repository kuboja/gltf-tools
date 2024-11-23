from pygltflib import GLTF2
from PIL import Image
import io

def get_buffer_data(gltf: GLTF2):
    """
    Načte binární data bufferů do paměti.

    :param gltf: GLTF objekt obsahující buffery.
    """
    # Rozlišení mezi GLB a GLTF
    if hasattr(gltf, '_glb_data') and gltf._glb_data is not None:
        # Práce s `_glb_data`
        buffer_data = [bytearray(gltf._glb_data)]
    else:
        # Práce s více buffery v GLTF
        buffer_data = [bytearray(buffer.data) for buffer in gltf.buffers]

    return buffer_data


def update_buffer_data(gltf: GLTF2, buffer_data):
    """
    Aktualizuje binární data bufferů v GLTF souboru.

    :param gltf: GLTF objekt obsahující buffery.
    :param buffer_data: List s binárními daty bufferů.
    """
    # Rozlišení mezi GLB a GLTF
    if hasattr(gltf, '_glb_data') and gltf._glb_data is not None:
        # Práce s `_glb_data`
        gltf._glb_data = buffer_data[0]
    else:
        # Práce s více buffery v GLTF
        for i, buffer in enumerate(gltf.buffers):
            buffer.data = bytes(buffer_data[i])


def convert_images_to_webp(gltf, min_size_kb=50):
    """
    Konvertuje obrázky v GLTF souboru do formátu WebP a uloží je jako binární data v _glb_data.
    Obrázky se konvertují pouze, pokud jejich velikost přesahuje zadaný práh (v kB).

    :param gltf: GLTF objekt obsahující obrázky.
    :param min_size_kb: Minimální velikost obrázku (v kB) pro konverzi.
    """
    # new_buffer_data = bytearray(gltf._glb_data)  # Vytvoření kopie původních binárních dat

    buffer_data = get_buffer_data(gltf)

    for image in gltf.images:
        if image.mimeType == "image/webp":
            # Pokud je obrázek již ve formátu WebP, přeskočíme ho
            continue

        if image.bufferView is not None:
            buffer_view = gltf.bufferViews[image.bufferView]
            buffer_index = buffer_view.buffer
            start = buffer_view.byteOffset or 0
            end = start + buffer_view.byteLength

            # Podmínka pro minimální velikost obrázku
            if buffer_view.byteLength < min_size_kb * 1024:
                # Pokud je obrázek menší než daný práh, přeskočíme ho
                continue

            image_data = io.BytesIO(buffer_data[buffer_index][start:end])

            # Načtení obrázku pomocí PIL
            img = Image.open(image_data)

            # Konverze obrázku do WebP
            output = io.BytesIO()
            img.save(output, format="WEBP", quality=85)
            output.seek(0)

            # Aktualizace bufferu s novými daty
            new_image_data = output.read()
            new_offset = len(buffer_data[buffer_index])
            buffer_data[buffer_index].extend(new_image_data)

            # Aktualizace bufferView s novými daty
            buffer_view.byteOffset = new_offset
            buffer_view.byteLength = len(new_image_data)

             # Aktualizace MIME typu na image/webp
            image.mimeType = "image/webp"

    # Aktualizace GLB bufferů
    update_buffer_data(gltf, buffer_data)


def resize_images_in_gltf(gltf: GLTF2, max_width: float = 1024, max_height: float = 1024):
    """
    Zmenší obrázky v GLTF souboru na dané maximální rozlišení a uloží je jako binární data v _glb_data.

    :param gltf: GLTF objekt obsahující obrázky.
    :param max_width: Maximální šířka obrázku.
    :param max_height: Maximální výška obrázku.
    """
    buffer_data = get_buffer_data(gltf)

    for image in gltf.images:
        if image.bufferView is not None:
            buffer_view = gltf.bufferViews[image.bufferView]
            buffer_index = buffer_view.buffer
            start = buffer_view.byteOffset or 0
            end = start + buffer_view.byteLength

            image_data = io.BytesIO(buffer_data[buffer_index][start:end])

            # Načtení obrázku pomocí PIL
            img = Image.open(image_data)

            # Změna velikosti obrázku, pokud přesahuje maximální rozměry
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height))

                # Uložení změněného obrázku
                output = io.BytesIO()
                img_format = img.format or "PNG"  # Zachování původního formátu, pokud je známý
                img.save(output, format=img_format, quality=85)
                output.seek(0)

                # Aktualizace bufferu s novými daty
                new_image_data = output.read()
                new_offset = len(buffer_data[buffer_index])
                buffer_data[buffer_index].extend(new_image_data)

                # Aktualizace bufferView s novými daty
                buffer_view.byteOffset = new_offset
                buffer_view.byteLength = len(new_image_data)

    # Aktualizace GLB bufferů
    update_buffer_data(gltf, buffer_data)


def process_images_in_gltf(gltf: GLTF2, max_width: float = 1024, max_height: float = 1024, min_size_kb: float = 50, quality: int = 85):
    """
    Převádí obrázky v GLTF souboru na formát WebP a zmenšuje je na zadané maximální rozměry.
    Obrázky se zpracovávají pouze, pokud jejich velikost přesahuje zadaný práh (v kB).

    :param gltf: GLTF objekt obsahující obrázky.
    :param max_width: Maximální šířka obrázku.
    :param max_height: Maximální výška obrázku.
    :param min_size_kb: Minimální velikost obrázku (v kB) pro zpracování.
    """
    buffer_data = get_buffer_data(gltf)

    for image in gltf.images:
        if image.bufferView is not None:
            buffer_view = gltf.bufferViews[image.bufferView]
            buffer_index = buffer_view.buffer
            start = buffer_view.byteOffset or 0
            end = start + buffer_view.byteLength


            # Podmínka pro minimální velikost obrázku
            if buffer_view.byteLength < min_size_kb * 1024:
                # pokud je obrázek menší než daný práh, přeskočíme ho
                continue

            image_data = io.BytesIO(buffer_data[buffer_index][start:end])

            # Načtení obrázku pomocí PIL
            img = Image.open(image_data)

            doResize = img.width > max_width or img.height > max_height

            if not doResize and image.mimeType == "image/webp":
                # pokud není třeba zmenšovat a obrázek je již ve formátu WebP, přeskočíme ho 
                continue

            # Změna velikosti obrázku, pokud přesahuje maximální rozměry
            if doResize:
                img.thumbnail((max_width, max_height))  # Zmenšení obrázku

            # Konverze obrázku do WebP
            output = io.BytesIO()
            img.save(output, format="WEBP", quality=quality)
            output.seek(0)

            # Aktualizace bufferu s novými daty
            new_image_data = output.read()
            new_offset = len(buffer_data[buffer_index])
            buffer_data[buffer_index].extend(new_image_data)

            # Aktualizace bufferView s novými daty
            buffer_view.byteOffset = new_offset
            buffer_view.byteLength = len(new_image_data)

            # Aktualizace MIME typu na image/webp
            image.mimeType = "image/webp"

    # Aktualizace GLB dat
    update_buffer_data(gltf, buffer_data)


if __name__ == "__main__":

    path = r"..\Sconces_10102024_01\Sconces_10102024_01_level1-31_optimized.glb"

    # Načtení GLB souboru
    gltf = GLTF2().load(path)

    # convert_images_to_webp(gltf)
    resize_images_in_gltf(gltf)

    # process_images_in_gltf(gltf)

    # Uložení GLB souboru
    gltf.save(path.replace('.glb', '_resized.glb'))
