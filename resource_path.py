#!/usr/bin/env python3
"""
Resource path utilities for PyInstaller bundled application.
Provides functions to get correct resource paths whether running 
from source or from a bundled executable.
"""

import os
import sys


def get_base_path() -> str:
    """
    Get the base path for resources.
    
    When running from PyInstaller bundle, resources are extracted to a 
    temporary directory (_MEIPASS). When running from source, use the 
    directory containing this file.
    
    Returns:
        Base path for locating resources
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        return sys._MEIPASS
    else:
        # Running from source
        return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource file.
    
    Args:
        relative_path: Path relative to the application base directory
        
    Returns:
        Absolute path to the resource
    """
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)


def get_user_data_path() -> str:
    """
    Get the path for user data files (settings, etc.).
    
    For bundled apps, user data should be stored outside the bundle
    so it persists across updates. Uses the current working directory
    or a platform-appropriate location.
    
    Returns:
        Path for user data storage
    """
    if getattr(sys, 'frozen', False):
        # For bundled app, use executable's directory for user data
        return os.path.dirname(sys.executable)
    else:
        # Running from source
        return os.path.dirname(os.path.abspath(__file__))


def get_settings_path() -> str:
    """
    Get the path to the settings.json file.
    
    Returns:
        Full path to settings.json
    """
    return os.path.join(get_user_data_path(), 'settings.json')


def is_bundled() -> bool:
    """
    Check if the application is running from a PyInstaller bundle.
    
    Returns:
        True if running from bundle, False if running from source
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_default_engine_path() -> str:
    """
    Get the default engine path based on the current platform.
    
    Returns:
        Default engine path for the current platform, or empty string if not found
    """
    if sys.platform == 'win32':
        engine_relative = 'Windows/pikafish-avx2.exe'
    elif sys.platform == 'darwin':
        engine_relative = 'MacOS/pikafish-apple-silicon'
    else:  # Linux and others
        engine_relative = 'Linux/pikafish-avx2'
    
    engine_path = get_resource_path(engine_relative)
    
    if os.path.exists(engine_path):
        # Ensure execute permission on Unix systems
        if sys.platform != 'win32':
            try:
                import stat
                current_mode = os.stat(engine_path).st_mode
                if not (current_mode & stat.S_IXUSR):
                    os.chmod(engine_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except (OSError, PermissionError):
                pass
        return engine_path
    
    return ''


def get_engine_path(path: str) -> str:
    """
    Get the correct engine executable path.
    
    Handles both absolute paths and relative paths (like ./Linux/pikafish-avx2).
    For bundled apps with relative paths, converts to resource path.
    For bundled apps with absolute paths that don't exist, falls back to default engine.
    Also ensures the engine has execute permission on Unix systems.
    
    Args:
        path: Engine path from settings (can be relative or absolute)
        
    Returns:
        Correct absolute path to the engine executable
    """
    if not path:
        return get_default_engine_path()
    
    engine_path = None
    
    # If it's an absolute path
    if os.path.isabs(path):
        if os.path.exists(path):
            # Absolute path exists, use it directly
            engine_path = path
        elif is_bundled():
            # In bundled app, absolute path doesn't exist
            # Try to extract relative path and find in resources
            # Common patterns: /path/to/project/Linux/pikafish-avx2
            for platform_dir in ['Linux', 'Windows', 'MacOS']:
                if platform_dir in path:
                    # Extract the relative part starting from platform dir
                    idx = path.find(platform_dir)
                    relative_path = path[idx:]
                    resource_path = get_resource_path(relative_path)
                    if os.path.exists(resource_path):
                        engine_path = resource_path
                        break
            
            # If still not found, use default engine
            if not engine_path:
                engine_path = get_default_engine_path()
        else:
            # Not bundled and path doesn't exist
            engine_path = path  # Return as-is, will fail at start
    else:
        # It's a relative path
        # Remove leading ./ if present
        clean_path = path.lstrip('./').lstrip('.\\')
        
        if is_bundled():
            # In bundled app, look in the resource directory
            engine_path = get_resource_path(clean_path)
        else:
            # Running from source, resolve relative to base path
            engine_path = os.path.join(get_base_path(), clean_path)
    
    # Ensure execute permission on Unix systems
    if engine_path and os.path.exists(engine_path) and sys.platform != 'win32':
        try:
            import stat
            current_mode = os.stat(engine_path).st_mode
            if not (current_mode & stat.S_IXUSR):
                os.chmod(engine_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except (OSError, PermissionError):
            pass  # Ignore permission errors
    
    return engine_path if engine_path else ''
