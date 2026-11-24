[app]
title = Jazira Agri OS
package.name = jaziraagri
package.domain = org.husein

source.dir = .
source.include_exts = py,png,jpg,kv,db,json,txt
source.include_patterns = src/*,src/jazira_agri/*,config/*
source.exclude_dirs = .git,.github,bin,.buildozer,tests,__pycache__

version = 0.1.0

requirements = python3,kivy==2.3.0,numpy,sqlite3,requests,openssl

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_FINE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
