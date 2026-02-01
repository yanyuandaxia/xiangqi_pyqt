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
    
    # 1. Try platform-specific path
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
        
    # 2. Try root directory (pikafish or pikafish.exe)
    root_names = ['pikafish.exe'] if sys.platform == 'win32' else ['pikafish']
    for name in root_names:
        engine_path = get_resource_path(name)
        if os.path.exists(engine_path):
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
    
    Args:
        path: Engine path from settings (can be relative or absolute)
        
    Returns:
        Correct absolute path to the engine executable
    """
    if not path:
        return get_default_engine_path()
    
    # If running in bundle, prefer the internal engine
    # This handles the case where user had a path like "/usr/bin/pikafish" saved,
    # but now runs the bundled version which has its own pikafish.
    if is_bundled():
        default_engine = get_default_engine_path()
        if default_engine:
            return default_engine
    
    # If not bundled (or internal engine not found which is weird for bundled),
    # treat path normally
    
    # If it's an absolute path
    if os.path.isabs(path):
        if os.path.exists(path):
            return path
        # If absolute path doesn't exist, try default fallback
        return get_default_engine_path()
    else:
        # It's a relative path
        clean_path = path.lstrip('./').lstrip('.\\')
        engine_path = os.path.join(get_base_path(), clean_path)
        
        if os.path.exists(engine_path):
            # chmod logic repeated here or assume user handles it for external relative paths
             if sys.platform != 'win32':
                try:
                    import stat
                    current_mode = os.stat(engine_path).st_mode
                    if not (current_mode & stat.S_IXUSR):
                        os.chmod(engine_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                except (OSError, PermissionError):
                    pass
             return engine_path
             
        return get_default_engine_path()
