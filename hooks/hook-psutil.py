# PyInstaller hook for psutil
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata

hiddenimports = collect_submodules('psutil')
datas = copy_metadata('psutil')
