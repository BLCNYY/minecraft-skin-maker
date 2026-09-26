"""Build and validate a self-contained, free Bedrock skin pack."""
import io
import json
import re
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from PIL import Image
from design import validate_image, validate_png

GEOMETRIES = {"classic": "geometry.humanoid.custom", "slim": "geometry.humanoid.customSlim"}


def _text(value):
    return " ".join(str(value).replace("=", "-").splitlines()).strip()


def package(png, destination, name, model):
    check = validate_png(png, model)
    if not check["ok"]:
        raise ValueError("Invalid skin: " + "; ".join(check["errors"]))
    header_uuid, module_uuid = str(uuid.uuid4()), str(uuid.uuid4())
    pack_key = "skin_" + header_uuid.replace("-", "")
    name = _text(name) or "My Skin"
    # Follow Microsoft's 2025 Introduction to Skin Packs and sample pack.
    manifest = {"format_version": 2,
                "header": {"name": "pack.name", "uuid": header_uuid, "version": [1, 0, 0]},
                "modules": [{"type": "skin_pack", "uuid": module_uuid, "version": [1, 0, 0]}]}
    skins = {"serialize_name": pack_key, "localization_name": pack_key,
             "skins": [{"localization_name": "main", "geometry": GEOMETRIES[model],
                        "texture": "skin.png", "type": "free"}]}
    files = {"manifest.json": json.dumps(manifest, indent=2),
             "skins.json": json.dumps(skins, indent=2),
             "texts/languages.json": json.dumps(["en_US"]),
             "texts/en_US.lang": f"pack.name={name}\nskinpack.{pack_key}={name}\nskin.{pack_key}.main={name}\n",
             "skin.png": Path(png).read_bytes()}
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for key, value in files.items():
            archive.writestr(key, value.encode("utf-8") if isinstance(value, str) else value)
    return validate_pack(destination, expected_model=model, expected_png=png)


def validate_pack(path, expected_model=None, expected_png=None):
    errors = []
    details = {}
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                errors.append("Duplicate ZIP members")
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or ".." in pure.parts or "\\" in name:
                    errors.append(f"Unsafe ZIP member: {name}")
            if sum(x.file_size for x in archive.infolist()) > 16_000_000:
                raise ValueError("Skin pack exceeds the validator's 16 MB uncompressed limit")
            if archive.testzip():
                errors.append("ZIP CRC check failed")
            required = {"manifest.json", "skins.json", "texts/en_US.lang", "texts/languages.json"}
            if required-set(names):
                raise ValueError(f"Missing root-level pack files: {sorted(required-set(names))}")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("format_version") not in (1, 2):
                errors.append("Unsupported manifest format_version")
            header = manifest["header"]
            modules = manifest["modules"]
            if len(modules) != 1 or modules[0].get("type") != "skin_pack":
                errors.append("Expected one skin_pack module")
            ids = []
            for entry in [header]+modules:
                identifier = str(uuid.UUID(entry["uuid"]))
                if identifier == str(uuid.UUID(int=0)):
                    errors.append("UUID may not be nil")
                ids.append(identifier)
                version = entry.get("version")
                if not isinstance(version, list) or len(version) != 3 or any(type(n) is not int or n < 0 for n in version):
                    errors.append("Versions must be three nonnegative integers")
            if len(ids) != len(set(ids)):
                errors.append("Header and module UUIDs must differ")
            skins = json.loads(archive.read("skins.json"))
            key = skins["serialize_name"]
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_]+", key):
                errors.append("serialize_name must use letters, digits or underscores")
            if skins.get("localization_name") != key:
                errors.append("Pack localization_name must match serialize_name")
            languages = json.loads(archive.read("texts/languages.json"))
            if not isinstance(languages, list) or "en_US" not in languages or len(languages) != len(set(languages)):
                raise ValueError("languages.json must contain unique language codes including en_US")
            translations = {}
            for language in languages:
                if not isinstance(language, str) or not re.fullmatch(r"[a-z]{2}_[A-Z]{2}", language):
                    raise ValueError("Invalid locale code")
                entries = {}
                for line in archive.read(f"texts/{language}.lang").decode("utf-8-sig").splitlines():
                    if not line.strip() or line.lstrip().startswith("#"):
                        continue
                    k, v = line.split("=", 1)
                    if k in entries:
                        errors.append(f"Duplicate localization key {k}")
                    entries[k] = v
                translations[language] = entries
            required_keys = {"pack.name", f"skinpack.{key}"}
            if header.get("name") != "pack.name" and not header.get("name"):
                errors.append("Manifest header name is empty")
            records = skins["skins"]
            if not isinstance(records, list) or not records:
                raise ValueError("Pack must include at least one skin")
            local_keys = []
            for entry in records:
                local_key = entry["localization_name"]
                if not re.fullmatch(r"[A-Za-z0-9_]+", local_key):
                    errors.append("Invalid skin localization key")
                local_keys.append(local_key)
                required_keys.add(f"skin.{key}.{local_key}")
                if entry.get("type") != "free":
                    errors.append("Included skins must be free")
                model = next((m for m, geom in GEOMETRIES.items() if geom == entry.get("geometry")), None)
                if model is None:
                    errors.append("Unknown player geometry")
                    continue
                if expected_model and model != expected_model:
                    errors.append("Pack geometry does not match requested model")
                filename = entry["texture"]
                if not re.fullmatch(r"[A-Za-z0-9_-]+\.png", filename):
                    errors.append("Skin texture must be a PNG at ZIP root")
                    continue
                content = archive.read(filename)
                if expected_png and content != Path(expected_png).read_bytes():
                    errors.append("Pack texture differs from delivered PNG")
                with Image.open(io.BytesIO(content)) as skin:
                    if skin.format != "PNG":
                        errors.append("Texture bytes are not PNG")
                    skin.load()
                    errors.extend(validate_image(skin, model)["errors"])
            if len(local_keys) != len(set(local_keys)):
                errors.append("Skin localization keys must be unique")
            for lang, entries in translations.items():
                for key in required_keys:
                    if not entries.get(key):
                        errors.append(f"Missing localization {lang}: {key}")
            details = {"uuid": ids[0], "skin_count": len(records), "zip_members": names}
    except (ValueError, KeyError, TypeError, IndexError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "errors": errors, **details}
