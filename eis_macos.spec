# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

from eis_version import __version__


hiddenimports = collect_submodules('galvani')
datas = (
    copy_metadata('galvani')
    + copy_metadata('impedance')
    + [
        ('LICENSE', '.'),
        ('README.md', '.'),
        ('CITATION.cff', '.'),
        ('CITATION.md', '.'),
        ('THIRD_PARTY_NOTICES.md', '.'),
    ]
)

a = Analysis(
    ['eis_qt.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='eis_qt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='eis_qt',
)
app = BUNDLE(
    coll,
    name='EIS Solver.app',
    icon=None,
    bundle_identifier='io.github.stpntrsvv.eissolver',
    version=__version__,
    info_plist={
        'CFBundleDisplayName': 'EIS Solver',
        'CFBundleName': 'EIS Solver',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
    },
)
