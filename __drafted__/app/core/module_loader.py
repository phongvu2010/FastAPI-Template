import importlib
import logging
import os

logger = logging.getLogger(__name__)


def discover_modules(target_submodule: str = "main"):
    """
    Automatically scan the app/modules/ and import the target submodule.
    target_submodule: "main" (for FastAPI routers) or "models" (for Alembic)
    """
    modules_base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules")

    loaded_modules = []

    if not os.path.exists(modules_base_path):
        logger.warning(f"⚠️ The modules folder does not exist at: {modules_base_path}")
        return loaded_modules

    # Browse through the subfolders in app/modules/
    for module_name in os.listdir(modules_base_path):
        module_path = os.path.join(modules_base_path, module_name)

        # Only process if it's a directory and not a system folder (__pycache__)
        if os.path.isdir(module_path) and not module_name.startswith("__"):
            try:
                # Create the import path. Example: app.modules.users.models
                module_spec = f"app.modules.{module_name}.{target_submodule}"
                # Preliminary check before importing (Optional, but cleaner)
                # importlib.util.find_spec helps check if a module exists without needing to import it.
                if importlib.util.find_spec(module_spec):
                    module = importlib.import_module(module_spec)
                    loaded_modules.append(module)
                    logger.info(f"✅ Loaded: {module_spec}")
                else:
                    logger.debug(f"ℹ️ Module {module_name} has no {target_submodule}, skipping.")
            except ImportError as e:
                logger.error(f"❌ Module cannot be loaded {module_name}.{target_submodule}: {e}")
                # Not all modules have models or main files, so skip if you don't see them.
                continue
            except Exception as e:
                logger.error(f"❌ Error loading {module_name}.{target_submodule}: {e}")

    return loaded_modules
