from pathlib import Path

project = Path.cwd()

a = Analysis(
    ['run.py'],
    pathex=[str(project / 'src')],
    binaries=[],
    datas=[
        (str(project / 'resources'), 'resources'),
        (str(project / 'config' / 'oauth_client.example.json'), 'config'),
    ],
    hiddenimports=[
        'googleapiclient.discovery',
        'googleapiclient.http',
        'google_auth_oauthlib.flow',
        'keyring.backends.Windows',
        'zoneinfo',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UPLOAD PLUGG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project / 'resources' / 'upload_plugg.ico'),
    version=str(project / 'build' / 'file_version_info.txt'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UPLOAD PLUGG',
)
