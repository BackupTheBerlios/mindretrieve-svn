rmdir /s /q build
rmdir /s /q dist
setup.py -v py2exe
setup.py sdist
"d:\Program Files\Inno Setup 4\Compil32.exe" /cc install.iss