[app]
title = descartecerto
package.name = descartecerto
package.domain = org.exemplo
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,css,html,js,json
source.include_patterns = static/*, assets/*, templates/*, *.kv, *.png, *.jpg, *.jpeg, *.ttf, *.css, *.html, *.js, *.json
version = 1.0
icon.filename = static/icon.png
presplash.filename = static/presplash.png
orientation = portrait
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25c
android.ndk_api = 21
android.use_new_api = True
android.permissions = CAMERA,INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO
fullscreen = 0
requirements = python3, kivy, kivymd, pyjnius, requests, Pillow, zbarcam, pyzbar
garden_requirements = 
android.entrypoint = org.kivy.android.PythonActivity
android.theme = '@android:style/Theme.NoTitleBar'
android.archs = arm64-v8a, armeabi-v7a
android.debug_symbols = True
android.enable_android_thread = True
version.code = 1
version.name = 1.0
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1

